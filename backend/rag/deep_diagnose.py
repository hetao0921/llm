#!/usr/bin/env python3
"""
深度诊断检索问题
"""

import os
import sys
import logging
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_embedding_api():
    """测试嵌入API是否返回不同的向量"""
    
    print("🔍 测试嵌入API...")
    print("=" * 60)
    
    # API配置
    API_URL = "https://api.siliconflow.cn/v1/embeddings"
    API_TOKEN = "sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn"
    MODEL = "BAAI/bge-large-en-v1.5"
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 测试不同的问题
    test_questions = [
        "List all actors",
        "Show all films", 
        "Find customers",
        "What are payments?",
        "Delete actor"
    ]
    
    embeddings = []
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n问题 {i}: {question}")
        
        payload = {
            "model": MODEL,
            "input": question
        }
        
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                embedding = result['data'][0]['embedding']
                embeddings.append(embedding)
                
                print(f"  ✅ 成功，维度: {len(embedding)}")
                print(f"  📊 前5维: {embedding[:5]}")
                print(f"  📊 后5维: {embedding[-5:]}")
                print(f"  📊 总和: {sum(embedding):.6f}")
                
            else:
                print(f"  ❌ 失败，状态码: {response.status_code}")
                print(f"  📋 响应: {response.text}")
                
        except Exception as e:
            print(f"  ❌ 异常: {e}")
    
    # 检查向量是否不同
    if len(embeddings) > 1:
        print(f"\n🔍 向量比较:")
        print("-" * 40)
        
        for i in range(len(embeddings)):
            for j in range(i+1, len(embeddings)):
                # 检查是否完全相同
                if embeddings[i] == embeddings[j]:
                    print(f"  ❌ 问题 {i+1} 和问题 {j+1} 的向量完全相同！")
                else:
                    # 计算差异
                    diff_count = sum(1 for a, b in zip(embeddings[i], embeddings[j]) if a != b)
                    print(f"  ✅ 问题 {i+1} 和问题 {j+1} 有 {diff_count} 个维度不同")
    
    return embeddings

def test_milvus_connection():
    """测试Milvus连接和数据"""
    
    print("\n🔍 测试Milvus连接...")
    print("=" * 60)
    
    try:
        from pymilvus import connections, Collection, utility
        
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
        print(f"✅ 成功连接到 Milvus")
        
        # 检查集合
        collections = ["ddl_knowledge", "q2sql_knowledge", "dbdesc_knowledge"]
        
        for coll_name in collections:
            print(f"\n📋 检查集合: {coll_name}")
            
            if utility.has_collection(coll_name):
                collection = Collection(coll_name)
                collection.load()
                
                # 获取集合信息
                print(f"  ✅ 集合存在")
                
                # 查询一些数据
                try:
                    results = collection.query(
                        expr="id >= 0",
                        limit=3,
                        output_fields=["id"]
                    )
                    print(f"  📊 查询到 {len(results)} 条记录")
                    
                    if results:
                        print(f"  📋 示例ID: {[r['id'] for r in results]}")
                        
                        # 检查向量是否不同
                        if len(results) > 1:
                            # 获取向量数据
                            vector_results = collection.query(
                                expr=f"id in {[r['id'] for r in results]}",
                                output_fields=["vector"]
                            )
                            
                            if vector_results:
                                vectors = [r['vector'] for r in vector_results]
                                print(f"  🔍 检查向量多样性...")
                                
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
                                    print(f"  ❌ 警告：所有向量都相同！")
                                else:
                                    print(f"  ✅ 向量有差异")
                    
                except Exception as e:
                    print(f"  ❌ 查询失败: {e}")
            else:
                print(f"  ❌ 集合不存在")
                
    except Exception as e:
        print(f"❌ Milvus连接失败: {e}")

def test_retrieval_logic():
    """测试检索逻辑"""
    
    print("\n🔍 测试检索逻辑...")
    print("=" * 60)
    
    try:
        # 导入主模块
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from importlib import import_module
        main_module = import_module('05-text2sql-rag-v2-ok-1')
        
        # 测试不同问题的检索
        test_questions = [
            "List all actors",
            "Show all films",
            "Find customers"
        ]
        
        for question in test_questions:
            print(f"\n问题: {question}")
            
            # 获取嵌入
            q_emb = main_module.get_silicon_flow_embedding(question)
            if q_emb is None:
                print("  ❌ 嵌入生成失败")
                continue
            
            print(f"  ✅ 嵌入生成成功，维度: {len(q_emb)}")
            print(f"  📊 向量前5维: {q_emb[:5]}")
            
            # 测试检索
            try:
                ddl_hits = main_module.retrieve("ddl_knowledge", q_emb, top_k=2, output_fields=["ddl_text"])
                print(f"  📋 DDL检索结果: {len(ddl_hits)} 条")
                
                if ddl_hits:
                    # 检查内容是否不同
                    contents = [hit["entity"].get("ddl_text", "") for hit in ddl_hits]
                    if len(set(contents)) == 1:
                        print(f"  ❌ 警告：所有DDL内容都相同！")
                    else:
                        print(f"  ✅ DDL内容有差异")
                        
            except Exception as e:
                print(f"  ❌ 检索失败: {e}")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    print("🚀 深度诊断检索问题")
    print("=" * 60)
    
    # 1. 测试嵌入API
    embeddings = test_embedding_api()
    
    # 2. 测试Milvus连接
    test_milvus_connection()
    
    # 3. 测试检索逻辑
    test_retrieval_logic()
    
    print("\n✅ 诊断完成！")
    print("💡 如果发现问题，请重新摄入数据")

if __name__ == "__main__":
    main()
