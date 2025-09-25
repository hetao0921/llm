#!/usr/bin/env python3
"""
测试生成器功能
"""

import sys
import os

# 添加父目录到路径，以便导入generator模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator import test_database_connection, process_retrieval_results_file, batch_generate_sql

def test_generator():
    """测试生成器功能"""
    print("🚀 测试生成器功能...")
    
    # 测试数据库连接
    print("🔗 测试数据库连接...")
    if not test_database_connection():
        print("❌ 数据库连接失败")
        return
    
    print("✅ 数据库连接成功")
    
    # 从检索结果文件读取数据
    print("📂 读取检索结果文件...")
    file_path = "F:\\llm\\code\\rag-new-project001\\data\\test_retrieval_results.txt"
    
    try:
        retrieval_results = process_retrieval_results_file(file_path)
        if not retrieval_results:
            print("❌ 无法读取检索结果文件")
            return
        
        print(f"📋 读取到 {len(retrieval_results)} 个检索结果")
        for i, result in enumerate(retrieval_results, 1):
            print(f"  {i}. {result['question']}")
        
        # 批量生成SQL
        print("🤖 开始批量生成SQL...")
        output_file = "F:\\llm\\code\\rag-new-project001\\data\\test_generation_results.txt"
        results = batch_generate_sql(retrieval_results, output_file)
        
        print(f"✅ 测试完成！生成了 {len(results)} 个SQL结果")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generator()
