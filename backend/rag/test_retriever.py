#!/usr/bin/env python3
"""
测试检索器功能
"""

import json
from retriever import init_milvus_connection, batch_retrieve_questions

def test_retriever():
    """测试检索器功能"""
    print("🚀 测试检索器功能...")
    
    # 初始化连接
    print("🔗 正在初始化Milvus连接...")
    if not init_milvus_connection():
        print("❌ Milvus 连接失败")
        return
    
    print("✅ Milvus连接成功")
    
    # 加载测试数据
    try:
        print("📂 正在加载测试数据...")
        with open('F:\\llm\\code\\rag-new-project001\\data\\q2sql_pairs.json', 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        # 只处理前3个问题进行测试
        selected_questions = questions_data[:3]
        
        print(f"📋 加载了 {len(selected_questions)} 个测试问题")
        for i, q in enumerate(selected_questions, 1):
            print(f"  {i}. {q['question']}")
        
        # 执行批量检索
        print("🔍 开始执行批量检索...")
        output_file = "F:\\llm\\code\\rag-new-project001\\data\\test_retrieval_results.txt"
        results = batch_retrieve_questions(selected_questions, output_file)
        
        print(f"✅ 测试完成！生成了 {len(results)} 个检索结果")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_retriever()
