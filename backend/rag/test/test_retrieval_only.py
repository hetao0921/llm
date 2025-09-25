#!/usr/bin/env python3
"""
只测试检索功能，不涉及其他依赖
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_retrieval_only():
    """只测试检索功能"""
    
    print("🔍 测试检索功能...")
    print("=" * 60)
    
    try:
        # 导入主模块
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from importlib import import_module
        main_module = import_module('05-text2sql-rag-v2-ok-1')
        
        # 测试不同问题
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

if __name__ == "__main__":
    test_retrieval_only()
