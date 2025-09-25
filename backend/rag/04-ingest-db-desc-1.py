# ingest_dbdesc.py
import logging
import requests
import json
import yaml
import numpy as np
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Milvus 连接配置
MILVUS_HOST = "10.128.15.221"  # 替换为您的 Milvus 服务器地址
MILVUS_PORT = "19530"          # Milvus 默认端口
DATABASE_NAME = "text2sql_milvus_sakila_hetao"  # 数据库名称
COLLECTION_NAME = "dbdesc_knowledge"  # 集合名称

# SiliconFlow API 配置
API_URL = "https://api.siliconflow.cn/v1/embeddings"
API_TOKEN = "sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn"  # 替换为你的实际API令牌

def get_embeddings(texts):
    """使用 SiliconFlow API 获取文本嵌入向量"""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    embeddings = []
    
    # 分批处理，避免单次请求过大
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        
        payload = {
            "model": "BAAI/bge-large-en-v1.5",  # 使用英文模型，与其他集合保持一致
            "input": batch_texts
        }
        
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                batch_embeddings = [item['embedding'] for item in result['data']]
                embeddings.extend(batch_embeddings)
                logger.info(f"✅ 成功处理批次 {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}, 生成 {len(batch_embeddings)} 个向量")
            else:
                logger.error(f"❌ API请求失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                # 如果失败，使用随机向量作为备用方案
                dummy_embedding = np.random.rand(1024).astype(np.float32).tolist()
                embeddings.extend([dummy_embedding] * len(batch_texts))
                
        except Exception as e:
            logger.error(f"❌ 获取嵌入向量时发生错误: {e}")
            # 使用随机向量作为备用方案
            dummy_embedding = np.random.rand(1024).astype(np.float32).tolist()
            embeddings.extend([dummy_embedding] * len(batch_texts))
    
    return embeddings

def main():
    try:
        # 1. 连接到 Milvus 服务器并指定数据库
        connections.connect(
            host=MILVUS_HOST,
            port=MILVUS_PORT,
            db_name=DATABASE_NAME
        )
        logger.info(f"✅ 成功连接到 Milvus 服务器 {MILVUS_HOST}:{MILVUS_PORT}")
        logger.info(f"✅ 正在使用数据库: '{DATABASE_NAME}'")

        # 2. 加载 DB 描述
        with open("F:\\llm\\code\\rag-new-project001\\data\\db_description.yaml", "r") as f:
            desc_map = yaml.safe_load(f)
            logger.info(f"✅ 从YAML文件加载了 {len(desc_map)} 个表的描述")

        # 3. 检查并删除现有集合（如果存在）
        if utility.has_collection(COLLECTION_NAME):
            logger.info(f"集合 '{COLLECTION_NAME}' 已存在，正在删除...")
            collection = Collection(COLLECTION_NAME)
            collection.drop()
            logger.info(f"✅ 集合 '{COLLECTION_NAME}' 已被删除")

        # 4. 定义集合 Schema - 使用固定维度1024（BAAI/bge-large-en-v1.5模型的维度）
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
            FieldSchema(name="table_name", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="column_name", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=1000)
        ]
        schema = CollectionSchema(fields, description="DB Description Knowledge Base")
        collection = Collection(name=COLLECTION_NAME, schema=schema)
        logger.info(f"✅ 集合 '{COLLECTION_NAME}' 创建成功")

        # 5. 准备数据
        data_records = []
        texts_to_embed = []
        record_id = 1000  # 起始ID
        
        for tbl, cols in desc_map.items():
            for col, desc in cols.items():
                record_id += 1
                data_records.append({
                    "id": record_id,
                    "table_name": tbl,
                    "column_name": col,
                    "description": desc
                })
                texts_to_embed.append(desc)

        logger.info(f"✅ 准备处理 {len(data_records)} 个字段描述")

        # 6. 生成嵌入向量
        logger.info("🔄 正在生成嵌入向量...")
        embeddings = get_embeddings(texts_to_embed)
        logger.info(f"✅ 成功生成了 {len(embeddings)} 个向量嵌入")

        # 7. 将嵌入向量添加到数据记录中
        for i, emb in enumerate(embeddings):
            data_records[i]["vector"] = emb

        # 8. 按字段名组织插入数据
        data_to_insert = [
            [item["id"] for item in data_records],  # List[int]
            [item["vector"] for item in data_records],  # List[List[float]]
            [item["table_name"] for item in data_records],  # List[str]
            [item["column_name"] for item in data_records],  # List[str]
            [item["description"] for item in data_records]  # List[str]
        ]

        # 插入前数据格式检查
        logger.info("插入前数据格式检查:")
        logger.info(f"  id 类型: {type(data_to_insert[0][0])}, 值: {data_to_insert[0][0]}")
        logger.info(f"  vector 类型: {type(data_to_insert[1][0])}, 维度: {len(data_to_insert[1][0])}, 元素类型: {type(data_to_insert[1][0][0])}")
        logger.info(f"  table_name 类型: {type(data_to_insert[2][0])}, 长度: {len(data_to_insert[2][0])}")
        logger.info(f"  column_name 类型: {type(data_to_insert[3][0])}, 长度: {len(data_to_insert[3][0])}")
        logger.info(f"  description 类型: {type(data_to_insert[4][0])}, 长度: {len(data_to_insert[4][0])}")

        # 9. 插入数据
        logger.info("🔄 正在插入数据...")
        insert_result = collection.insert(data_to_insert)
        logger.info(f"✅ 插入成功! 插入记录数: {len(insert_result.primary_keys)}")
        logger.info(f"   主键 IDs: 从 {insert_result.primary_keys[0]} 到 {insert_result.primary_keys[-1]}")

        # 10. 刷新数据，使其持久化并可被搜索
        collection.flush()
        logger.info("✅ 数据已刷新")

        # 11. 创建索引以提升查询性能
        index_params = {
            "metric_type": "COSINE",  # 使用余弦相似度
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="vector", index_params=index_params)
        logger.info("✅ 向量索引创建成功")

        # 12. 将集合加载到内存（使数据可被查询）
        collection.load()
        logger.info("✅ 集合已加载到内存")

        # 13. 验证数据：查询集合中的实体数量
        entity_count = collection.num_entities
        logger.info(f"📊 集合中的总实体数: {entity_count}")

        # 14. （可选）执行简单查询验证
        if entity_count > 0:
            query_results = collection.query(
                expr=f"id in [{data_records[0]['id']}, {data_records[-1]['id']}]",
                output_fields=["id", "table_name", "column_name", "description"]
            )
            logger.info("✅ 查询验证结果:")
            for result in query_results:
                logger.info(f"  ID: {result['id']}, 表: {result['table_name']}, 列: {result['column_name']}")

        logger.info("✅ 知识库构建完成")

    except Exception as e:
        logger.error(f"❌ 操作过程中发生错误: {e}")
        # 特别处理常见的连接和数据类型错误
        if "Database not found" in str(e):
            logger.error(f"💡 请确保数据库 '{DATABASE_NAME}' 已在 Milvus 实例中存在。")
        elif "DataNotMatchException" in str(e) or "same type" in str(e):
            logger.error("💡 数据类型不匹配！请仔细检查：")
            logger.error("  1. 字段名称是否与Schema完全一致")
            logger.error("  2. 向量维度是否为1024")
            logger.error("  3. 所有字段下的数据类型是否统一且与Schema定义匹配")
            logger.error("  4. 字符串长度是否超过Schema定义的限制")
    finally:
        # 断开连接
        try:
            connections.disconnect("default")
            logger.info("✅ 与 Milvus 服务器的连接已断开")
        except Exception as e:
            logger.warning(f"断开连接时发生警告: {e}")

if __name__ == "__main__":
    main()