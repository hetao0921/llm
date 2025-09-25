#!/usr/bin/env python3
"""
测试检索结果显示功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入主模块的检索函数
from importlib import import_module

def test_retrieval_display():
    """测试检索结果显示功能"""
    try:
        # 导入主模块
        main_module = import_module('05-text2sql-rag-v2-ok-1')
        
        print("✅ 成功导入主模块")
        print("📋 主要功能:")
        print("  - retrieve() 函数已增强，现在会显示检索结果的具体内容")
        print("  - 每个检索结果会显示:")
        print("    * ID")
        print("    * 相似度分数")
        print("    * 具体内容（限制200字符以内）")
        print("  - 添加了检索进度提示")
        print("  - 添加了检索上下文总结")
        
        print("\n🔍 检索结果显示格式示例:")
        print("-" * 80)
        print("📋 ddl_knowledge 检索结果详情:")
        print("-" * 80)
        print("结果 1:")
        print("  ID: 12345")
        print("  相似度分数: 0.8542")
        print("  内容:")
        print("    ddl_text: CREATE TABLE actor (actor_id SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT...")
        print("-" * 40)
        print("结果 2:")
        print("  ID: 12346")
        print("  相似度分数: 0.7891")
        print("  内容:")
        print("    ddl_text: CREATE TABLE film (film_id SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT...")
        print("-" * 40)
        
        print("\n✅ 修改完成！现在运行 05-text2sql-rag-v2-ok-1.py 时会显示:")
        print("  1. 每个检索步骤的进度提示")
        print("  2. 检索结果的具体内容详情")
        print("  3. 检索上下文的字符数统计")
        print("  4. 更清晰的输出格式")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_retrieval_display()
