# text2sql-rag-v2-fixed.py
import os
import logging
import re
import requests
import json
from dotenv import load_dotenv
import numpy as np

# 尝试导入 SQLAlchemy，如果失败则提供明确的错误信息
try:
    from sqlalchemy import create_engine, text
except ImportError as e:
    print("错误: 缺少必要的依赖包，请执行以下命令安装：")
    print("pip install sqlalchemy pymysql pymilvus requests python-dotenv pyyaml numpy")
    raise e

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
SILICON_FLOW_CHAT_MODEL = os.getenv("SILICON_FLOW_CHAT_MODEL", "Qwen/QwQ-32B")

# 3. Milvus 连接配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "10.128.15.221")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
DATABASE_NAME = os.getenv("MILVUS_DB_NAME", "text2sql_milvus_sakila_hetao")

# 集合名称
COLLECTION_DDL = "ddl_knowledge"
COLLECTION_Q2SQL = "q2sql_knowledge" 
COLLECTION_DBDESC = "dbdesc_knowledge"

# 4. 数据库配置
DB_URL = os.getenv(
    "SAKILA_DB_URL", 
    "mysql+pymysql://root:Rzx#1218@10.128.15.5:3306/sakila"
)

# 5. 初始化 Milvus 连接
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
                # 打印集合结构信息
                try:
                    collection = Collection(coll_name)
                    schema = collection.schema
                    print(f"集合 '{coll_name}' 的字段:")
                    for field in schema.fields:
                        print(f"  - {field.name} (类型: {field.dtype})")
                    
                    # 打印索引信息
                    indexes = collection.indexes
                    for index in indexes:
                        print(f"  - 索引: {index.params}")
                except Exception as e:
                    logging.warning(f"无法获取集合 '{coll_name}' 的详细信息: {e}")
            else:
                logging.warning(f"⚠️ 集合 '{coll_name}' 不存在，检索将返回空结果")
                
        return True
    except Exception as e:
        logging.error(f"❌ Milvus 连接失败: {e}")
        return False

# 6. Silicon Flow 嵌入函数
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

# 7. Silicon Flow 聊天补全函数
def siliconflow_chat_completion(messages: list, temperature: float = 0.1) -> str:
    """使用 Silicon Flow 聊天补全接口"""
    try:
        url = f"{SILICON_FLOW_API_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {SILICON_FLOW_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": SILICON_FLOW_CHAT_MODEL,
            "messages": messages,
            "temperature": temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0]['message']
                content = message['content'].strip()
                logging.info("✅ Silicon Flow 聊天补全调用成功")
                return content
            else:
                logging.error("❌ 响应中没有找到有效的回复内容")
                return None
        else:
            logging.error(f"❌ Silicon Flow 聊天 API 请求失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"❌ 聊天补全异常: {e}")
        return None

# 8. 动态检测向量字段名称
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

# 9. 动态检测度量类型
def get_metric_type(collection_name):
    """动态检测集合的度量类型"""
    # 根据错误信息，我们知道集合使用的是 COSINE
    # 我们可以为不同的集合设置不同的度量类型，或者统一使用 COSINE
    metric_types = {
        COLLECTION_DDL: "COSINE",
        COLLECTION_Q2SQL: "COSINE", 
        COLLECTION_DBDESC: "COSINE"
    }
    
    return metric_types.get(collection_name, "COSINE")

# 10. 修复的检索函数
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
        
        # 修复：兼容不同版本的 PyMilvus
        try:
            # 尝试直接加载集合（兼容新版本）
            collection.load()
        except Exception as load_error:
            logging.warning(f"集合加载方式1失败，尝试备用方法: {load_error}")
            try:
                # 备用加载方法
                if hasattr(collection, 'is_loaded') and not collection.is_loaded:
                    collection.load()
            except Exception as e:
                logging.error(f"集合加载失败: {e}")
                return []
            
        # 搜索参数 - 使用正确的度量类型
        search_params = {
            "metric_type": metric_type,  # 使用动态检测的度量类型
            "params": {"nprobe": 2}
        }
        
        # 执行搜索
        results = collection.search(
            data=[query_emb],
            anns_field=vector_field,  # 使用动态检测的字段名
            param=search_params,
            limit=top_k,
            output_fields=output_fields
        )
        
        # 处理结果 - 兼容不同版本的返回格式
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
                        # 兼容不同版本的实体访问方式
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
        
        # 打印检索结果的具体内容
        if hits:
            print(f"\n📋 {collection_name} 检索结果详情:")
            print("-" * 80)
            for i, hit in enumerate(hits, 1):
                print(f"结果 {i}:")
                print(f"  ID: {hit['id']}")
                print(f"  相似度分数: {hit['distance']:.4f}")
                if hit['entity']:
                    print(f"  内容:")
                    for field, value in hit['entity'].items():
                        if value:
                            # 限制显示长度，避免输出过长
                            display_value = str(value)
                            if len(display_value) > 200:
                                display_value = display_value[:200] + "..."
                            print(f"    {field}: {display_value}")
                print("-" * 40)
        else:
            print(f"❌ {collection_name} 未检索到任何结果")
            
        # 调试：检查检索到的结果是否真的不同
        if len(hits) > 1:
            print(f"🔍 调试信息 - 检查结果多样性:")
            ids = [hit['id'] for hit in hits]
            distances = [hit['distance'] for hit in hits]
            print(f"  结果ID列表: {ids}")
            print(f"  相似度分数列表: {distances}")
            if len(set(ids)) == 1:
                print("  ⚠️ 警告：所有结果的ID都相同！")
            if len(set(distances)) == 1:
                print("  ⚠️ 警告：所有结果的相似度分数都相同！")
        
        return hits
        
    except Exception as e:
        logging.error(f"[检索] {collection_name} 检索失败: {e}")
        return []

# 11. SQL 提取函数
def extract_sql(text: str) -> str:
    """从文本中提取 SQL 语句"""
    if not text:
        return ""
    
    # 尝试匹配 SQL 代码块
    sql_blocks = re.findall(r'```sql\n(.*?)\n```', text, re.DOTALL)
    if sql_blocks:
        return sql_blocks[0].strip()
    
    # 如果没有找到代码块，尝试匹配 SELECT 语句
    select_match = re.search(r'SELECT.*?;', text, re.DOTALL)
    if select_match:
        return select_match.group(0).strip()
    
    # 尝试匹配 UPDATE 语句
    update_match = re.search(r'UPDATE.*?;', text, re.DOTALL)
    if update_match:
        return update_match.group(0).strip()
    
    # 尝试匹配 INSERT 语句  
    insert_match = re.search(r'INSERT.*?;', text, re.DOTALL)
    if insert_match:
        return insert_match.group(0).strip()
        
    # 尝试匹配 DELETE 语句
    delete_match = re.search(r'DELETE.*?;', text, re.DOTALL)
    if delete_match:
        return delete_match.group(0).strip()
    
    # 如果都没有找到，返回原始文本
    return text.strip()

# 12. 测试数据库连接
def test_database_connection():
    """测试数据库连接是否正常"""
    try:
        # 检查是否安装了 pymysql
        try:
            import pymysql
        except ImportError:
            print("❌ 未安装 pymysql，请执行: pip install pymysql")
            return False
            
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            # 执行一个简单的测试查询
            result = conn.execute(text("SELECT 1"))
            test_result = result.scalar()
            if test_result == 1:
                logging.info("✅ 数据库连接测试成功")
                return True
            else:
                logging.error("❌ 数据库连接测试失败")
                return False
    except Exception as e:
        logging.error(f"❌ 数据库连接失败: {e}")
        return False

# 13. 执行 SQL 查询
def execute_sql_query(sql: str):
    """执行 SQL 查询并返回结果"""
    try:
        engine = create_engine(DB_URL)
        
        with engine.connect() as conn:
            # 判断 SQL 类型
            sql_upper = sql.upper().strip()
            
            if sql_upper.startswith('SELECT'):
                # 查询语句
                result = conn.execute(text(sql))
                cols = result.keys()
                rows = result.fetchall()
                
                print("\n" + "="*60)
                print("📊 查询结果：")
                print("="*60)
                print(f"📋 列名: {cols}")
                print("-" * 60)
                for i, r in enumerate(rows, 1):
                    print(f"{i}. {r}")
                print("="*60)
                print(f"✅ 总计: {len(rows)} 条记录")
                
            elif sql_upper.startswith(('UPDATE', 'INSERT', 'DELETE')):
                # DML 语句
                result = conn.execute(text(sql))
                conn.commit()  # 提交事务
                affected_rows = result.rowcount
                
                print("\n" + "="*60)
                print("✅ SQL 执行成功")
                print("="*60)
                print(f"📋 执行的SQL: {sql}")
                print(f"📊 影响的行数: {affected_rows}")
                print("="*60)
                
            else:
                # 其他类型的 SQL
                result = conn.execute(text(sql))
                conn.commit()
                print(f"✅ SQL 执行完成: {sql}")
                
    except Exception as e:
        logging.error(f"[执行] 执行失败: {e}")
        print(f"❌ 执行错误：{e}")

# 14. 核心流程：自然语言 -> SQL -> 执行 -> 返回
def text2sql(question: str):
    """将自然语言查询转换为 SQL 并执行"""
    if not question.strip():
        print("❌ 问题不能为空")
        return
    
    print(f"\n🔍 处理查询: {question}")
    
    # 14.1 用户提问嵌入
    q_emb = get_silicon_flow_embedding(question)
    if q_emb is None:
        print("❌ 嵌入生成失败，无法继续检索")
        return
    
    logging.info(f"[检索] 问题嵌入完成，维度: {len(q_emb)}")
    
    # 调试：显示向量的一部分来验证是否不同
    print(f"🔍 问题向量前10维: {q_emb[:10]}")
    print(f"🔍 问题向量后10维: {q_emb[-10:]}")
    print(f"🔍 向量总和: {sum(q_emb):.6f}")
    print(f"🔍 向量均值: {sum(q_emb)/len(q_emb):.6f}")

    # 14.2 RAG 检索：DDL
    print(f"\n🔍 正在检索DDL结构信息...")
    ddl_hits = retrieve(COLLECTION_DDL, q_emb, top_k=3, output_fields=["ddl_text"])
    logging.info(f"[检索] DDL检索结果数量: {len(ddl_hits)}")
    try:
        ddl_context = "\n".join(hit["entity"].get("ddl_text", "") for hit in ddl_hits if hit["entity"].get("ddl_text"))
    except Exception as e:
        logging.error(f"[检索] DDL处理错误: {e}")
        ddl_context = ""

    # 14.3 RAG 检索：示例对
    print(f"\n🔍 正在检索问答示例...")
    q2sql_hits = retrieve(COLLECTION_Q2SQL, q_emb, top_k=3, output_fields=["question", "sql_text"])
    logging.info(f"[检索] Q2SQL检索结果数量: {len(q2sql_hits)}")
    try:
        example_context = "\n".join(
            f"NL: \"{hit['entity'].get('question', '')}\"\nSQL: \"{hit['entity'].get('sql_text', '')}\"" 
            for hit in q2sql_hits if hit["entity"].get("question") and hit["entity"].get("sql_text")
        )
    except Exception as e:
        logging.error(f"[检索] Q2SQL处理错误: {e}")
        example_context = ""

    # 14.4 RAG 检索：字段描述
    print(f"\n🔍 正在检索字段描述信息...")
    desc_hits = retrieve(COLLECTION_DBDESC, q_emb, top_k=8, output_fields=["table_name", "column_name", "description"])
    logging.info(f"[检索] 字段描述检索结果数量: {len(desc_hits)}")
    try:
        desc_context = "\n".join(
            f"{hit['entity'].get('table_name', '')}.{hit['entity'].get('column_name', '')}: {hit['entity'].get('description', '')}"
            for hit in desc_hits if hit["entity"].get("table_name")
        )
    except Exception as e:
        logging.error(f"[检索] 字段描述处理错误: {e}")
        desc_context = ""

    # 14.5 显示检索到的上下文信息
    print(f"\n📊 检索上下文总结:")
    print("=" * 60)
    print(f"📋 DDL结构信息: {len(ddl_context)} 字符")
    print(f"📋 问答示例: {len(example_context)} 字符") 
    print(f"📋 字段描述: {len(desc_context)} 字符")
    print("=" * 60)
    
    # 显示实际检索到的内容片段
    print(f"\n🔍 实际检索内容预览:")
    print("-" * 60)
    print(f"📋 DDL内容前200字符: {ddl_context[:200]}...")
    print(f"📋 问答内容前200字符: {example_context[:200]}...")
    print(f"📋 描述内容前200字符: {desc_context[:200]}...")
    print("-" * 60)
    
    # 14.6 Prompt 组装
    system_prompt = """你是一个专业的SQL生成助手。请根据提供的数据库结构、字段描述和示例，将自然语言查询转换为准确的SQL语句。

请严格遵循以下要求：
1. 只返回SQL语句，不要包含任何解释或说明
2. 确保SQL语法正确
3. 使用提供的表名和字段名
4. 如果问题涉及日期范围，请使用合适的日期函数
5. 如果需要连接多个表，请确保连接条件正确
6. 注意：Sakila数据库中的演员表是actor，不是actors"""

    user_prompt = (
        f"### 数据库结构定义:\n{ddl_context}\n\n"
        f"### 字段描述:\n{desc_context}\n\n"
        f"### 示例查询:\n{example_context}\n\n"
        f"### 用户查询:\n{question}\n\n"
        f"请生成对应的SQL查询语句："
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    print("🤖 正在生成SQL...")

    # 14.7 调用 Silicon Flow 聊天补全接口
    raw_sql = siliconflow_chat_completion(messages, temperature=0.1)
    
    if raw_sql is None:
        print("❌ SQL生成失败")
        return
        
    sql = extract_sql(raw_sql)
    logging.info(f"[生成] 原始输出: {raw_sql}")
    logging.info(f"[生成] 提取的SQL: {sql}")

    if not sql:
        print("❌ 未能提取到有效的SQL语句")
        return

    print(f"📋 生成的SQL: {sql}")

    # 14.8 执行并打印结果
    execute_sql_query(sql)

# 15. 程序入口
if __name__ == "__main__":
    print("🚀 Text2SQL RAG 系统启动中...")
    
    # 检查依赖
    print("📦 检查依赖包...")
    try:
        import sqlalchemy
        import pymilvus
        import requests
        # 特别检查 pymysql
        try:
            import pymysql
            print("✅ pymysql 已安装")
        except ImportError:
            print("❌ 未安装 pymysql，请执行: pip install pymysql")
            exit(1)
        print("✅ 所有依赖包检查通过")
    except ImportError as e:
        print("❌ 缺少依赖包，请执行以下命令安装：")
        print("pip install sqlalchemy pymysql pymilvus requests python-dotenv pyyaml numpy")
        exit(1)
    
    # 初始化 Milvus 连接
    print("🔗 连接 Milvus 数据库...")
    if not init_milvus_connection():
        print("❌ Milvus 连接失败，程序退出")
        exit(1)
    
    # 测试数据库连接
    print("🔗 测试数据库连接...")
    if not test_database_connection():
        print("❌ 数据库连接测试失败")
        exit(1)
    
    print("✅ 系统初始化完成！")
    
    try:
        while True:
            print("\n" + "="*60)
            user_q = input("💬 请输入您的自然语言查询（输入 'quit' 退出）: ").strip()
            
            if user_q.lower() in ['quit', 'exit', '退出', 'q']:
                print("👋 感谢使用，再见！")
                break
                
            if not user_q:
                print("❌ 输入不能为空，请重新输入。")
                continue
                
            text2sql(user_q)
            
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