#!/usr/bin/env python3
"""
测试向量嵌入的多样性
"""

import os
import sys
import numpy as np
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入主模块的嵌入函数
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_embedding_diversity():
    """测试不同问题是否生成不同的向量嵌入"""
    
    # 导入嵌入函数
    try:
        from importlib import import_module
        main_module = import_module('05-text2sql-rag-v2-ok-1')
        get_embedding = main_module.get_silicon_flow_embedding
    except Exception as e:
        print(f"❌ 无法导入嵌入函数: {e}")
        return
    
    # 测试不同的问题
    test_questions = [
        "List all actors with their IDs and names",
        "Show me all films and their descriptions", 
        "Find customers who rented movies",
        "What are the payment amounts?",
        "Delete actor with ID 1"
    ]
    
    print("🔍 测试向量嵌入多样性...")
    print("=" * 60)
    
    embeddings = []
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n问题 {i}: {question}")
        
        # 获取嵌入向量
        embedding = get_embedding(question)
        
        if embedding is None:
            print(f"  ❌ 嵌入生成失败")
            continue
            
        embeddings.append(embedding)
        
        # 显示向量信息
        print(f"  ✅ 向量维度: {len(embedding)}")
        print(f"  📊 向量前5维: {embedding[:5]}")
        print(f"  📊 向量后5维: {embedding[-5:]}")
        print(f"  📊 向量总和: {sum(embedding):.6f}")
        print(f"  📊 向量均值: {sum(embedding)/len(embedding):.6f}")
    
    # 检查向量是否不同
    if len(embeddings) > 1:
        print(f"\n🔍 向量多样性分析:")
        print("=" * 60)
        
        # 计算向量之间的相似度
        for i in range(len(embeddings)):
            for j in range(i+1, len(embeddings)):
                # 计算余弦相似度
                emb1 = np.array(embeddings[i])
                emb2 = np.array(embeddings[j])
                
                # 余弦相似度
                cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                
                # 欧几里得距离
                euclidean_dist = np.linalg.norm(emb1 - emb2)
                
                print(f"问题 {i+1} vs 问题 {j+1}:")
                print(f"  余弦相似度: {cosine_sim:.6f}")
                print(f"  欧几里得距离: {euclidean_dist:.6f}")
                
                if cosine_sim > 0.99:
                    print(f"  ⚠️ 警告：向量几乎完全相同！")
                elif cosine_sim > 0.95:
                    print(f"  ⚠️ 注意：向量非常相似")
                else:
                    print(f"  ✅ 向量差异正常")
        
        # 检查是否有完全相同的向量
        unique_embeddings = []
        for emb in embeddings:
            is_unique = True
            for unique_emb in unique_embeddings:
                if np.array_equal(emb, unique_emb):
                    is_unique = False
                    break
            if is_unique:
                unique_embeddings.append(emb)
        
        print(f"\n📊 总结:")
        print(f"  总问题数: {len(test_questions)}")
        print(f"  成功生成向量: {len(embeddings)}")
        print(f"  唯一向量数: {len(unique_embeddings)}")
        
        if len(unique_embeddings) == len(embeddings):
            print(f"  ✅ 所有向量都是唯一的")
        else:
            print(f"  ❌ 存在重复的向量！")
            print(f"  🔍 重复数量: {len(embeddings) - len(unique_embeddings)}")

if __name__ == "__main__":
    test_embedding_diversity()
