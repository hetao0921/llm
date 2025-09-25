import logging
import json
import requests
import numpy as np
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import time
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置参数
MILVUS_HOST = "10.128.15.221"  # Milvus服务器地址
MILVUS_PORT = "19530"          # Milvus端口
DATABASE_NAME = "text2sql_milvus_sakila_hetao"  # 数据库名称
COLLECTION_NAME = "q2sql_knowledge"  # 集合名称

# 硅基流动API配置
API_URL = "https://api.siliconflow.cn/v1/embeddings"
API_TOKEN = "sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn"  # 替换为你的实际API令牌
BATCH_SIZE = 20  # 分批处理，每批最多20个文本

def escape_single_quotes(text):
    """转义字符串中的单引号"""
    return text.replace("'", "\\'")

def get_embeddings_batch(texts):
    """使用硅基流动API分批获取文本嵌入向量"""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    all_embeddings = []
    
    # 分批处理文本
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i+BATCH_SIZE]
        
        # 准备请求数据
        payload = {
            "model": "BAAI/bge-large-en-v1.5",  # 使用英文模型，适合问题文本
            "input": batch_texts
        }
        
        try:
            # 发送请求
            response = requests.post(API_URL, headers=headers, json=payload)
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                batch_embeddings = [item['embedding'] for item in result['data']]
                all_embeddings.extend(batch_embeddings)
                logger.info(f"成功生成批次 {i//BATCH_SIZE + 1} 的嵌入向量 ({len(batch_embeddings)} 个)")
            else:
                logger.error(f"API请求失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                raise Exception(f"API请求失败: {response.status_code}")
                
            # 添加短暂延迟，避免API限流
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"获取嵌入向量时发生错误: {e}")
            raise
    
    logger.info(f"总共生成 {len(all_embeddings)} 个嵌入向量，维度: {len(all_embeddings[0])}")
    return all_embeddings

def main():
    try:
        # 1. 加载 Q->SQL 对
        with open("F:\\llm\\code\\rag-new-project001\\data\\q2sql_pairs.json", "r") as f:
            pairs = json.load(f)
            logger.info(f"从JSON文件加载了 {len(pairs)} 个问答对")

        # 2. 准备数据
        questions = [pair["question"] for pair in pairs]
        sql_texts = [pair["sql"] for pair in pairs]
        
        # 3. 分批获取嵌入向量
        embeddings = get_embeddings_batch(questions)
        vector_dim = len(embeddings[0])
        
        # 4. 连接到Milvus服务器
        connections.connect(
            host=MILVUS_HOST,
            port=MILVUS_PORT,
            db_name=DATABASE_NAME
        )
        logger.info(f"成功连接到Milvus服务器 {MILVUS_HOST}:{MILVUS_PORT}")
        logger.info(f"正在使用数据库: '{DATABASE_NAME}'")

        # 5. 检查并删除现有集合（如果存在）
        if utility.has_collection(COLLECTION_NAME):
            logger.info(f"集合 '{COLLECTION_NAME}' 已存在，正在删除...")
            collection = Collection(COLLECTION_NAME)
            collection.drop()
            logger.info(f"集合 '{COLLECTION_NAME}' 已被删除")

        # 6. 定义集合Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="sql_text", dtype=DataType.VARCHAR, max_length=2000),
        ]
        schema = CollectionSchema(fields, description="Q2SQL Knowledge Base", enable_dynamic_field=False)
        collection = Collection(name=COLLECTION_NAME, schema=schema)
        logger.info(f"集合 '{COLLECTION_NAME}' 创建成功")

        # 7. 准备插入数据
        data_to_insert = [
            embeddings,  # 向量列表
            questions,   # 问题列表
            sql_texts    # SQL文本列表
        ]
        
        # 8. 插入数据
        logger.info("正在插入数据...")
        insert_result = collection.insert(data_to_insert)
        logger.info(f"插入成功! 插入记录数: {len(insert_result.primary_keys)}")
        logger.info(f"主键IDs: {insert_result.primary_keys}")

        # 9. 刷新数据
        collection.flush()
        logger.info("数据已刷新")

        # 10. 创建索引
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index(field_name="vector", index_params=index_params)
        logger.info("向量索引创建成功")

        # 11. 将集合加载到内存
        collection.load()
        logger.info("集合已加载到内存")

        # 12. 验证数据
        logger.info(f"集合中的总实体数: {collection.num_entities}")
        
        # 13. 执行简单查询验证 - 使用ID查询而不是问题文本查询
        # 获取前两个记录的ID
        first_two_ids = insert_result.primary_keys[:2]
        
        # 使用ID查询，避免字符串转义问题
        query_results = collection.query(
            expr=f"id in [{first_two_ids[0]}, {first_two_ids[1]}]",
            output_fields=["id", "question"]
        )
            
        logger.info("查询验证结果:")
        for result in query_results:
            logger.info(f"ID: {result['id']}, 问题: {result['question'][:50]}...")

    except Exception as e:
        logger.error(f"操作过程中发生错误: {e}")
        # 特别处理常见的连接和数据类型错误
        if "Database not found" in str(e):
            logger.error(f"请确保数据库 '{DATABASE_NAME}' 已在Milvus实例中存在。")
        elif "DataNotMatchException" in str(e) or "same type" in str(e):
            logger.error("数据类型不匹配！请仔细检查：")
            logger.error("1. 字段名称是否与Schema完全一致")
            logger.error("2. 向量维度是否匹配")
            logger.error("3. 所有字段下的数据类型是否统一且与Schema定义匹配")
            logger.error("4. 字符串长度是否超过Schema定义的限制")
    finally:
        # 断开连接
        try:
            connections.disconnect("default")
            logger.info("与Milvus服务器的连接已断开")
        except Exception as e:
            logger.warning(f"断开连接时发生警告: {e}")

if __name__ == "__main__":
    main()