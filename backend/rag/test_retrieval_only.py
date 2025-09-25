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
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from importlib import import_module
        main_module = import_module('05-text2sql-rag-v2-ok-1')
        
        # 测试不同问题
        test_questions = [
            "List all actors with their IDs and names",
            "Show me all films and their descriptions", 
            "Find customers who rented movies",
            "What are the payment amounts?",
            "Delete actor with ID 1"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n🔍 测试问题 {i}: {question}")
            print("-" * 60)
            
            # 获取嵌入
            q_emb = main_module.get_silicon_flow_embedding(question)
            if q_emb is None:
                print("  ❌ 嵌入生成失败")
                continue
            
            print(f"  ✅ 嵌入生成成功，维度: {len(q_emb)}")
            print(f"  📊 向量前5维: {q_emb[:5]}")
            print(f"  📊 向量总和: {sum(q_emb):.6f}")
            
            # 测试DDL检索
            print(f"\n  🔍 测试DDL检索...")
            ddl_hits = main_module.retrieve("ddl_knowledge", q_emb, top_k=3, output_fields=["ddl_text"])
            
            if ddl_hits:
                ddl_context = "\n".join(
                    hit["entity"].get("ddl_text", "") 
                    for hit in ddl_hits if hit["entity"].get("ddl_text")
                )
                print(f"    📊 DDL检索结果: {len(ddl_hits)} 条")
                print(f"    📊 DDL内容长度: {len(ddl_context)} 字符")
                print(f"    📄 DDL内容前100字符: {ddl_context[:100]}...")
                
                # 检查内容是否相同
                ddl_contents = [hit["entity"].get("ddl_text", "") for hit in ddl_hits]
                if len(set(ddl_contents)) == 1:
                    print(f"    ❌ 警告：所有DDL内容都相同！")
                else:
                    print(f"    ✅ DDL内容有差异")
            else:
                print(f"    ❌ DDL检索失败")
            
            # 测试Q2SQL检索
            print(f"\n  🔍 测试Q2SQL检索...")
            q2sql_hits = main_module.retrieve("q2sql_knowledge", q_emb, top_k=3, output_fields=["question", "sql_text"])
            
            if q2sql_hits:
                example_context = "\n".join(
                    f"NL: \"{hit['entity'].get('question', '')}\"\nSQL: \"{hit['entity'].get('sql_text', '')}\"" 
                    for hit in q2sql_hits if hit["entity"].get("question") and hit["entity"].get("sql_text")
                )
                print(f"    📊 Q2SQL检索结果: {len(q2sql_hits)} 条")
                print(f"    📊 Q2SQL内容长度: {len(example_context)} 字符")
                print(f"    📄 Q2SQL内容前100字符: {example_context[:100]}...")
                
                # 检查内容是否相同
                q2sql_questions = [hit["entity"].get("question", "") for hit in q2sql_hits]
                if len(set(q2sql_questions)) == 1:
                    print(f"    ❌ 警告：所有Q2SQL问题都相同！")
                else:
                    print(f"    ✅ Q2SQL内容有差异")
            else:
                print(f"    ❌ Q2SQL检索失败")
            
            # 测试字段描述检索
            print(f"\n  🔍 测试字段描述检索...")
            desc_hits = main_module.retrieve("dbdesc_knowledge", q_emb, top_k=8, output_fields=["table_name", "column_name", "description"])
            
            if desc_hits:
                desc_context = "\n".join(
                    f"{hit['entity'].get('table_name', '')}.{hit['entity'].get('column_name', '')}: {hit['entity'].get('description', '')}"
                    for hit in desc_hits if hit["entity"].get("table_name")
                )
                print(f"    📊 字段描述检索结果: {len(desc_hits)} 条")
                print(f"    📊 字段描述内容长度: {len(desc_context)} 字符")
                print(f"    📄 字段描述内容前100字符: {desc_context[:100]}...")
                
                # 检查内容是否相同
                desc_contents = [f"{hit['entity'].get('table_name', '')}.{hit['entity'].get('column_name', '')}: {hit['entity'].get('description', '')}" for hit in desc_hits]
                if len(set(desc_contents)) == 1:
                    print(f"    ❌ 警告：所有字段描述都相同！")
                else:
                    print(f"    ✅ 字段描述内容有差异")
            else:
                print(f"    ❌ 字段描述检索失败")
            
            print(f"\n  📊 总结:")
            print(f"    DDL: {len(ddl_context) if 'ddl_context' in locals() else 0} 字符")
            print(f"    Q2SQL: {len(example_context) if 'example_context' in locals() else 0} 字符")
            print(f"    字段描述: {len(desc_context) if 'desc_context' in locals() else 0} 字符")
            
            # 清理变量
            if 'ddl_context' in locals():
                del ddl_context
            if 'example_context' in locals():
                del example_context
            if 'desc_context' in locals():
                del desc_context
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_retrieval_only()
