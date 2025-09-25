#!/usr/bin/env python3
"""
检查数据库中的数据
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_database_data():
    """检查数据库中的数据"""
    
    print("🔍 检查数据库中的数据...")
    print("=" * 60)
    
    try:
        print("📦 正在导入pymilvus...")
        from pymilvus import connections, Collection, utility
        print("✅ pymilvus导入成功")
        
        # 连接参数
        MILVUS_HOST = "10.128.15.221"
        MILVUS_PORT = "19530"
        DATABASE_NAME = "text2sql_milvus_sakila_hetao"
        
        # 连接Milvus
        print(f"🔗 正在连接到 Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
        connections.connect(
            host=MILVUS_HOST,
            port=MILVUS_PORT,
            db_name=DATABASE_NAME
        )
        print(f"✅ 成功连接到 Milvus")
        
        # 检查每个集合
        collections = {
            "ddl_knowledge": ["ddl_text"],
            "q2sql_knowledge": ["question", "sql_text"],
            "dbdesc_knowledge": ["table_name", "column_name", "description"]
        }
        
        for coll_name, fields in collections.items():
            print(f"\n📋 检查集合: {coll_name}")
            print("-" * 40)
            
            if utility.has_collection(coll_name):
                collection = Collection(coll_name)
                collection.load()
                
                # 查询前5条记录
                try:
                    results = collection.query(
                        expr="id >= 0",
                        limit=5,
                        output_fields=fields
                    )
                    
                    print(f"  📊 查询到 {len(results)} 条记录")
                    
                    if results:
                        # 检查内容是否相同
                        for field in fields:
                            values = [r.get(field, "") for r in results]
                            unique_values = set(values)
                            
                            print(f"  📋 字段 {field}:")
                            print(f"    总记录数: {len(values)}")
                            print(f"    唯一值数: {len(unique_values)}")
                            
                            if len(unique_values) == 1:
                                print(f"    ❌ 警告：所有 {field} 值都相同！")
                                print(f"    📄 内容: {list(unique_values)[0][:100]}...")
                            else:
                                print(f"    ✅ 内容有差异")
                                # 显示前几个不同的值
                                for i, value in enumerate(list(unique_values)[:3]):
                                    print(f"      值 {i+1}: {str(value)[:100]}...")
                    
                    # 检查向量是否相同
                    print(f"  🔍 检查向量多样性...")
                    vector_results = collection.query(
                        expr="id >= 0",
                        limit=3,
                        output_fields=["vector"]
                    )
                    
                    if vector_results:
                        vectors = [r['vector'] for r in vector_results]
                        
                        # 比较向量
                        all_same = True
                        for i in range(len(vectors)):
                            for j in range(i+1, len(vectors)):
                                if vectors[i] != vectors[j]:
                                    all_same = False
                                    break
                            if not all_same:
                                break
                        
                        if all_same:
                            print(f"    ❌ 警告：所有向量都相同！")
                        else:
                            print(f"    ✅ 向量有差异")
                            
                except Exception as e:
                    print(f"  ❌ 查询失败: {e}")
            else:
                print(f"  ❌ 集合不存在")
                
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()

def test_simple_retrieval():
    """测试简单检索"""
    
    print("\n🔍 测试简单检索...")
    print("=" * 60)
    
    try:
        from pymilvus import connections, Collection, utility
        import numpy as np
        
        # 连接参数
        MILVUS_HOST = "10.128.15.221"
        MILVUS_PORT = "19530"
        DATABASE_NAME = "text2sql_milvus_sakila_hetao"
        
        # 连接Milvus
        connections.connect(
            host=MILVUS_HOST,
            port=MILVUS_PORT,
            db_name=DATABASE_NAME
        )
        
        # 测试DDL集合
        collection_name = "ddl_knowledge"
        if utility.has_collection(collection_name):
            collection = Collection(collection_name)
            collection.load()
            
            # 创建两个不同的查询向量
            query1 = np.random.random(1024).tolist()
            query2 = np.random.random(1024).tolist()
            
            print(f"📋 测试集合: {collection_name}")
            
            # 第一次检索
            print(f"🔍 第一次检索...")
            results1 = collection.search(
                data=[query1],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=3,
                output_fields=["ddl_text"]
            )
            
            if results1 and len(results1) > 0:
                print(f"  📊 检索到 {len(results1[0])} 条结果")
                for i, hit in enumerate(results1[0]):
                    print(f"    结果 {i+1}: ID={hit.id}, 距离={hit.distance:.4f}")
            
            # 第二次检索
            print(f"🔍 第二次检索...")
            results2 = collection.search(
                data=[query2],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=3,
                output_fields=["ddl_text"]
            )
            
            if results2 and len(results2) > 0:
                print(f"  📊 检索到 {len(results2[0])} 条结果")
                for i, hit in enumerate(results2[0]):
                    print(f"    结果 {i+1}: ID={hit.id}, 距离={hit.distance:.4f}")
            
            # 比较结果
            if results1 and results2 and len(results1[0]) > 0 and len(results2[0]) > 0:
                ids1 = [hit.id for hit in results1[0]]
                ids2 = [hit.id for hit in results2[0]]
                
                if ids1 == ids2:
                    print(f"  ❌ 警告：两次检索返回相同的ID！")
                else:
                    print(f"  ✅ 两次检索返回不同的ID")
                    print(f"    第一次ID: {ids1}")
                    print(f"    第二次ID: {ids2}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    print("🚀 检查数据库数据")
    print("=" * 60)
    
    # 1. 检查数据库数据
    check_database_data()
    
    # 2. 测试简单检索
    test_simple_retrieval()
    
    print("\n✅ 检查完成！")

if __name__ == "__main__":
    main()
