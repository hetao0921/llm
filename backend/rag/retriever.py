#!/usr/bin/env python3
"""
Text2SQL RAG 检索器
负责将自然语言问题向量化，从向量库检索相关数据，并输出到文件
"""

import os
import logging
import requests
import json
import csv
from dotenv import load_dotenv
from typing import List, Dict, Any

# 尝试导入 PyMilvus
try:
    from pymilvus import connections, Collection, utility
except ImportError as e:
    print("错误: 缺少 pymilvus 包，请执行：pip install pymilvus")
    raise e

# 1. 环境与日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()  # 加载 .env 环境变量

# 2. Silicon Flow 配置
SILICON_FLOW_API_URL = "https://api.siliconflow.cn/v1"
SILICON_FLOW_API_TOKEN = os.getenv("SILICON_FLOW_API_TOKEN", "sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn")
SILICON_FLOW_EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"  # 使用英文模型，与数据摄入时保持一致

# 3. Milvus 连接配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "10.128.15.221")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
DATABASE_NAME = os.getenv("MILVUS_DB_NAME", "text2sql_milvus_sakila_hetao")

# 集合名称
COLLECTION_DDL = "ddl_knowledge"
COLLECTION_Q2SQL = "q2sql_knowledge" 
COLLECTION_DBDESC = "dbdesc_knowledge"

# 4. 初始化 Milvus 连接
def init_milvus_connection():
    """初始化 Milvus 连接"""
    try:
        connections.connect(
            host=MILVUS_HOST,
            port=MILVUS_PORT,
            db_name=DATABASE_NAME
        )
        logging.info(f"✅ 成功连接到 Milvus 服务器 {MILVUS_HOST}:{MILVUS_PORT}")
        logging.info(f"✅ 正在使用数据库: '{DATABASE_NAME}'")
        
        # 检查集合是否存在
        collections = {
            COLLECTION_DDL: utility.has_collection(COLLECTION_DDL),
            COLLECTION_Q2SQL: utility.has_collection(COLLECTION_Q2SQL),
            COLLECTION_DBDESC: utility.has_collection(COLLECTION_DBDESC)
        }
        
        for coll_name, exists in collections.items():
            if exists:
                logging.info(f"✅ 集合 '{coll_name}' 存在")
            else:
                logging.warning(f"⚠️ 集合 '{coll_name}' 不存在，检索将返回空结果")
                
        return True
    except Exception as e:
        logging.error(f"❌ Milvus 连接失败: {e}")
        return False

# 5. Silicon Flow 嵌入函数
def get_silicon_flow_embedding(text: str) -> list:
    """使用 Silicon Flow API 获取文本嵌入向量"""
    try:
        url = f"{SILICON_FLOW_API_URL}/embeddings"
        headers = {
            "Authorization": f"Bearer {SILICON_FLOW_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": SILICON_FLOW_EMBEDDING_MODEL,
            "input": text
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            embedding = result['data'][0]['embedding']
            logging.info(f"✅ 嵌入向量生成成功，维度: {len(embedding)}")
            return embedding
        else:
            logging.error(f"❌ Silicon Flow 嵌入 API 请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"❌ 嵌入生成异常: {e}")
        return None

# 6. 动态检测向量字段名称
def get_vector_field_name(collection):
    """动态检测集合中的向量字段名称"""
    try:
        schema = collection.schema
        for field in schema.fields:
            # 查找浮点向量类型的字段
            if hasattr(field, 'dtype') and 'FLOAT_VECTOR' in str(field.dtype):
                return field.name
            # 或者查找包含特定关键词的字段名
            if any(keyword in field.name.lower() for keyword in ['vector', 'embedding', 'vec']):
                return field.name
        # 如果没有找到，返回默认值
        return "vector"
    except Exception as e:
        logging.warning(f"无法检测向量字段名称，使用默认值: {e}")
        return "vector"

# 7. 动态检测度量类型
def get_metric_type(collection_name):
    """动态检测集合的度量类型"""
    metric_types = {
        COLLECTION_DDL: "COSINE",
        COLLECTION_Q2SQL: "COSINE", 
        COLLECTION_DBDESC: "COSINE"
    }
    return metric_types.get(collection_name, "COSINE")

# 8. 检索函数
def retrieve(collection_name: str, query_emb: list, top_k: int = 3, output_fields: list = None):
    """从指定集合中检索相似内容"""
    try:
        if not utility.has_collection(collection_name):
            logging.warning(f"集合 '{collection_name}' 不存在")
            return []
            
        collection = Collection(collection_name)
        
        # 动态检测向量字段名称
        vector_field = get_vector_field_name(collection)
        logging.info(f"检测到集合 '{collection_name}' 的向量字段: {vector_field}")
        
        # 动态检测度量类型
        metric_type = get_metric_type(collection_name)
        logging.info(f"使用度量类型: {metric_type}")
        
        # 加载集合
        try:
            collection.load()
        except Exception as load_error:
            logging.warning(f"集合加载方式1失败，尝试备用方法: {load_error}")
            try:
                if hasattr(collection, 'is_loaded') and not collection.is_loaded:
                    collection.load()
            except Exception as e:
                logging.error(f"集合加载失败: {e}")
                return []
            
        # 搜索参数
        search_params = {
            "metric_type": metric_type,
            "params": {"nprobe": 10}
        }
        
        # 执行搜索
        results = collection.search(
            data=[query_emb],
            anns_field=vector_field,
            param=search_params,
            limit=top_k,
            output_fields=output_fields
        )
        
        # 处理结果
        hits = []
        if results and len(results) > 0:
            for result in results[0]:
                hit_data = {
                    "id": result.id,
                    "distance": result.distance,
                    "entity": {}
                }
                
                # 添加输出字段
                if output_fields:
                    for field in output_fields:
                        try:
                            if hasattr(result, 'entity') and hasattr(result.entity, field):
                                hit_data["entity"][field] = getattr(result.entity, field)
                            elif hasattr(result, field):
                                hit_data["entity"][field] = getattr(result, field)
                            else:
                                hit_data["entity"][field] = None
                        except Exception as e:
                            logging.warning(f"获取字段 {field} 失败: {e}")
                            hit_data["entity"][field] = None
                
                hits.append(hit_data)
        
        logging.info(f"[检索] {collection_name} 检索到 {len(hits)} 条结果")
        return hits
        
    except Exception as e:
        logging.error(f"[检索] {collection_name} 检索失败: {e}")
        return []

# 9. 统计函数
def count_ddl_columns(ddl_text: str) -> int:
    """统计DDL中的列数"""
    if not ddl_text:
        return 0
    
    lines = ddl_text.split('\n')
    column_lines = [line for line in lines if line.strip().startswith('`') and '`' in line]
    return len(column_lines)

def count_desc_columns(desc_text: str) -> int:
    """统计数据库描述中的列数"""
    if not desc_text:
        return 0
    
    # 计算描述中的字段数量（通过计算冒号的数量）
    return desc_text.count(':')

# 10. 核心检索函数
def retrieve_for_question(question: str, standard_answer: str = ""):
    """为单个问题执行检索并返回结果"""
    print(f"\n🔍 处理查询: {question}")
    
    # 生成问题嵌入
    q_emb = get_silicon_flow_embedding(question)
    if q_emb is None:
        print("❌ 嵌入生成失败，无法继续检索")
        return None
    
    logging.info(f"[检索] 问题嵌入完成，维度: {len(q_emb)}")
    
    # 调试：显示向量信息
    print(f"🔍 问题向量前10维: {q_emb[:10]}")
    print(f"🔍 问题向量后10维: {q_emb[-10:]}")
    print(f"🔍 向量总和: {sum(q_emb):.6f}")
    print(f"🔍 向量均值: {sum(q_emb)/len(q_emb):.6f}")

    # 检索DDL结构信息
    print(f"\n🔍 正在检索DDL结构信息...")
    ddl_hits = retrieve(COLLECTION_DDL, q_emb, top_k=3, output_fields=["ddl_text"])
    logging.info(f"[检索] DDL检索结果数量: {len(ddl_hits)}")
    
    ddl_results = []
    for hit in ddl_hits[:3]:  # 限制最多3条
        if hit["entity"].get("ddl_text"):
            ddl_results.append(hit["entity"]["ddl_text"])
    
    ddl_context = "\n".join(ddl_results)
    ddl_column_count = count_ddl_columns(ddl_context)

    # 检索问答示例
    print(f"\n🔍 正在检索问答示例...")
    q2sql_hits = retrieve(COLLECTION_Q2SQL, q_emb, top_k=3, output_fields=["question", "sql_text"])
    logging.info(f"[检索] Q2SQL检索结果数量: {len(q2sql_hits)}")
    
    example_results = []
    for hit in q2sql_hits[:3]:  # 限制最多3条
        if hit["entity"].get("question") and hit["entity"].get("sql_text"):
            example_results.append(f"NL: \"{hit['entity']['question']}\"\nSQL: \"{hit['entity']['sql_text']}\"")
    
    example_context = "\n".join(example_results)

    # 检索字段描述信息
    print(f"\n🔍 正在检索字段描述信息...")
    desc_hits = retrieve(COLLECTION_DBDESC, q_emb, top_k=3, output_fields=["table_name", "column_name", "description"])
    logging.info(f"[检索] 字段描述检索结果数量: {len(desc_hits)}")
    
    desc_results = []
    for hit in desc_hits[:3]:  # 限制最多3条
        if hit["entity"].get("table_name"):
            desc_results.append(f"{hit['entity']['table_name']}.{hit['entity']['column_name']}: {hit['entity']['description']}")
    
    desc_context = "\n".join(desc_results)
    desc_column_count = count_desc_columns(desc_context)

    # 显示检索结果总结
    print(f"\n📊 检索结果总结:")
    print("=" * 60)
    print(f"📋 DDL结构信息: {len(ddl_context)} 字符")
    print(f"📋 问答示例: {len(example_context)} 字符") 
    print(f"📋 字段描述: {len(desc_context)} 字符")
    print(f"📋 DDL列数统计: {ddl_column_count}")
    print(f"📋 描述列数统计: {desc_column_count}")
    print("=" * 60)
    
    # 显示实际检索到的内容片段
    print(f"\n🔍 实际检索内容预览:")
    print("-" * 60)
    print(f"📋 DDL内容前200字符: {ddl_context[:200]}...")
    print(f"📋 问答内容前200字符: {example_context[:200]}...")
    print(f"📋 描述内容前200字符: {desc_context[:200]}...")
    print("-" * 60)
    
    return {
        "question": question,
        "standard_answer": standard_answer,
        "ddl_results": ddl_context,
        "desc_results": desc_context,
        "ddl_column_count": ddl_column_count,
        "desc_column_count": desc_column_count
    }

# 11. 批量处理函数
def batch_retrieve_questions(questions_data: List[Dict[str, str]], output_file: str = "retrieval_results.txt"):
    """批量处理问题并输出到文件"""
    results = []
    
    print(f"🚀 开始批量检索 {len(questions_data)} 个问题...")
    
    for i, item in enumerate(questions_data, 1):
        question = item.get("question", "")
        standard_answer = item.get("sql", "")
        
        print(f"\n处理第 {i}/{len(questions_data)} 个问题...")
        
        result = retrieve_for_question(question, standard_answer)
        if result:
            results.append(result)
    
    # 输出到TXT文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write("=" * 80 + "\n")
            f.write(f"问题: {result['question']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"标准答案: {result['standard_answer']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"DDL返回结果:\n{result['ddl_results']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"数据库描述返回结果:\n{result['desc_results']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"DDL统计: {result['ddl_column_count']}\n")
            f.write(f"数据库描述统计: {result['desc_column_count']}\n")
            f.write("=" * 80 + "\n\n")
    
    print(f"\n✅ 批量检索完成！")
    print(f"📄 结果已保存到: {output_file}")
    
    return results

# 12. 程序入口
if __name__ == "__main__":
    print("🚀 Text2SQL RAG 检索器启动中...")
    
    # 检查依赖
    print("📦 检查依赖包...")
    try:
        import pymilvus
        import requests
        print("✅ 所有依赖包检查通过")
    except ImportError as e:
        print("❌ 缺少依赖包，请执行以下命令安装：")
        print("pip install pymilvus requests python-dotenv")
        exit(1)
    
    # 初始化 Milvus 连接
    print("🔗 连接 Milvus 数据库...")
    if not init_milvus_connection():
        print("❌ Milvus 连接失败，程序退出")
        exit(1)
    
    print("✅ 检索器初始化完成！")
    
    try:
        while True:
            print("\n" + "="*60)
            print("请选择操作模式：")
            print("1. 单个问题检索")
            print("2. 批量问题检索")
            print("3. 退出")
            
            choice = input("请输入选择 (1/2/3): ").strip()
            
            if choice == "1":
                # 单个问题检索
                question = input("💬 请输入自然语言查询: ").strip()
                if question:
                    result = retrieve_for_question(question)
                    if result:
                        print(f"\n✅ 检索完成！")
                        print(f"📋 DDL列数: {result['ddl_column_count']}")
                        print(f"📋 描述列数: {result['desc_column_count']}")
                else:
                    print("❌ 输入不能为空")
                    
            elif choice == "2":
                # 批量问题检索
                try:
                    # 加载问题数据
                    with open('F:\\llm\\code\\rag-new-project001\\data\\q2sql_pairs.json', 'r', encoding='utf-8') as f:
                        questions_data = json.load(f)
                    
                    # 只处理前10个问题
                    selected_questions = questions_data[:10]
                    
                    output_file = "F:\\llm\\code\\rag-new-project001\\data\\retrieval_results.txt"
                    results = batch_retrieve_questions(selected_questions, output_file)
                    
                except Exception as e:
                    print(f"❌ 批量检索失败: {e}")
                    
            elif choice == "3":
                print("👋 感谢使用，再见！")
                break
            else:
                print("❌ 无效选择，请重新输入")
                
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        logging.error(f"程序执行异常: {e}")
        print(f"❌ 程序异常: {e}")
    finally:
        # 断开 Milvus 连接
        try:
            connections.disconnect("default")
            print("✅ 与 Milvus 服务器的连接已断开")
        except Exception as e:
            print(f"⚠️ 断开连接时发生警告: {e}")
