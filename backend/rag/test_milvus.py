from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Milvus 连接配置
MILVUS_HOST = "10.128.15.221"  # 替换为您的 Milvus 服务器地址
MILVUS_PORT = "19530"          # Milvus 默认端口
DATABASE_NAME = "text2sql_milvus_sakila_hetao"  # 数据库名称
COLLECTION_NAME = "text2sql_milvus_sakila_hetao"  # 集合名称

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

        # 2. 检查并删除现有集合（如果存在）
        if utility.has_collection(COLLECTION_NAME):
            logger.info(f"集合 '{COLLECTION_NAME}' 已存在，正在删除...")
            collection = Collection(COLLECTION_NAME)
            collection.drop()
            logger.info(f"✅ 集合 '{COLLECTION_NAME}' 已被删除")

        # 3. 定义集合 Schema - 严格遵循您的字段定义
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),  # 维度为768
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="sql_query", dtype=DataType.VARCHAR, max_length=2000)
        ]
        schema = CollectionSchema(fields, description="Collection for text-to-sql tasks")
        collection = Collection(name=COLLECTION_NAME, schema=schema)
        logger.info(f"✅ 集合 '{COLLECTION_NAME}' 创建成功")

        # 4. 准备测试数据 - 确保数据类型与Schema定义完全匹配！
        test_data = [
            {
                "id": 1001,  # 必须是 Python int (对应INT64)
                "embedding": np.random.rand(768).astype(np.float32).tolist(), # 必须是list of float32, 维度768
                "question": "How many films were rented in July?", # 必须是str，且长度<=500
                "sql_query": "SELECT COUNT(*) FROM rental WHERE rental_date BETWEEN '2005-07-01' AND '2005-07-31'" # 必须是str，且长度<=2000
            },
            {
                "id": 1002,
                "embedding": np.random.rand(768).astype(np.float32).tolist(),
                "question": "List customers from Canada",
                "sql_query": "SELECT first_name, last_name FROM customer WHERE address_id IN (SELECT address_id FROM address WHERE city_id IN (SELECT city_id FROM city WHERE country_id = (SELECT country_id FROM country WHERE country = 'Canada')))"
            }
        ]

        # 5. 按字段名组织插入数据 - 确保键名与字段名完全一致，且同一字段下数据类型严格统一
        data_to_insert = [
            [item["id"] for item in test_data], # List[int]
            [item["embedding"] for item in test_data], # List[List[float]]
            [item["question"] for item in test_data], # List[str]
            [item["sql_query"] for item in test_data] # List[str]
        ]

        # （可选但推荐）插入前打印检查数据类型和维度
        logger.info("插入前数据格式检查:")
        logger.info(f"  id 类型: {type(data_to_insert[0][0])}, 值: {data_to_insert[0][0]}")
        logger.info(f"  embedding 类型: {type(data_to_insert[1][0])}, 维度: {len(data_to_insert[1][0])}, 元素类型: {type(data_to_insert[1][0][0])}")
        logger.info(f"  question 类型: {type(data_to_insert[2][0])}, 长度: {len(data_to_insert[2][0])}")
        logger.info(f"  sql_query 类型: {type(data_to_insert[3][0])}, 长度: {len(data_to_insert[3][0])}")

        # 6. 插入数据
        logger.info("🔄 正在插入数据...")
        insert_result = collection.insert(data_to_insert)
        logger.info(f"✅ 插入成功! 插入记录数: {len(insert_result.primary_keys)}")
        logger.info(f"   主键 IDs: {insert_result.primary_keys}")

        # 7. 刷新数据，使其持久化并可被搜索
        collection.flush()
        logger.info("✅ 数据已刷新")

        # 8. 创建索引以提升查询性能
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        logger.info("✅ 向量索引创建成功")

        # 9. 将集合加载到内存（使数据可被查询）
        collection.load()
        logger.info("✅ 集合已加载到内存")

        # 10. 验证数据：查询集合中的实体数量
        logger.info(f"📊 集合中的总实体数: {collection.num_entities}")

        # 11. （可选）执行简单查询验证
        query_results = collection.query(
            expr="id in [1001, 1002]",
            output_fields=["id", "question", "sql_query"]
        )
        logger.info("✅ 查询验证结果:")
        for result in query_results:
            logger.info(f"  ID: {result['id']}, Question: {result['question']}")

    except Exception as e:
        logger.error(f"❌ 操作过程中发生错误: {e}")
        # 特别处理常见的连接和数据类型错误
        if "Database not found" in str(e):
            logger.error(f"💡 请确保数据库 '{DATABASE_NAME}' 已在 Milvus 实例中存在。")
        elif "DataNotMatchException" in str(e) or "same type" in str(e):
            logger.error("💡 数据类型不匹配！请仔细检查：")
            logger.error("  1. 字段名称是否与Schema完全一致")
            logger.error("  2. 向量维度是否为768")
            logger.error("  3. 所有字段下的数据类型是否统一且与Schema定义匹配")
            logger.error("  4. 字符串长度是否超过Schema定义的限制")
    finally:
        # 12. 断开连接
        try:
            connections.disconnect("default")
            logger.info("✅ 与 Milvus 服务器的连接已断开")
        except Exception as e:
            logger.warning(f"断开连接时发生警告: {e}")

if __name__ == "__main__":
    main()