#!/usr/bin/env python3
"""
调试匹配问题
"""

import json
import yaml
from typing import List, Dict, Any

def load_files():
    """加载所有必要的文件"""
    # 加载q2sql_pairs.json
    with open('F:\\llm\\code\\rag-new-project001\\data\\q2sql_pairs.json', 'r', encoding='utf-8') as f:
        q2sql_pairs = json.load(f)
    
    # 加载ddl_statements.yaml
    with open('F:\\llm\\code\\rag-new-project001\\data\\ddl_statements.yaml', 'r', encoding='utf-8') as f:
        ddl_content = yaml.safe_load(f)
    
    # 加载db_description.yaml
    with open('F:\\llm\\code\\rag-new-project001\\data\\db_description.yaml', 'r', encoding='utf-8') as f:
        db_description = yaml.safe_load(f)
    
    return q2sql_pairs, ddl_content, db_description

def extract_table_names(question: str) -> List[str]:
    """从问题中提取可能的表名"""
    # 常见表名列表（从db_description中获取）
    table_names = [
        'actor', 'address', 'category', 'city', 'country', 'customer', 
        'film', 'inventory', 'payment', 'rental', 'staff', 'store',
        'film_actor', 'film_category', 'language'
    ]
    
    found_tables = []
    for table in table_names:
        if table.lower() in question.lower():
            found_tables.append(table)
    
    return found_tables

def debug_match(question: str, ddl_content: Dict, db_description: Dict):
    """调试匹配过程"""
    print(f"🔍 调试问题: {question}")
    print("=" * 60)
    
    # 1. 提取表名
    tables = extract_table_names(question)
    print(f"📋 提取到的表名: {tables}")
    
    # 2. 检查DDL内容
    print(f"\n📋 DDL内容检查:")
    for table in tables:
        if table in ddl_content:
            print(f"  ✅ 找到表 {table} 的DDL")
            print(f"  📄 DDL内容: {ddl_content[table][:100]}...")
        else:
            print(f"  ❌ 未找到表 {table} 的DDL")
    
    # 3. 检查数据库描述
    print(f"\n📋 数据库描述检查:")
    for table in tables:
        if table in db_description:
            print(f"  ✅ 找到表 {table} 的描述")
            table_desc = db_description[table]
            print(f"  📄 描述内容:")
            for field, description in table_desc.items():
                print(f"    {field}: {description}")
        else:
            print(f"  ❌ 未找到表 {table} 的描述")
    
    # 4. 检查数据结构
    print(f"\n📋 数据结构检查:")
    print(f"  DDL内容类型: {type(ddl_content)}")
    print(f"  DDL内容键: {list(ddl_content.keys())[:5]}...")
    print(f"  数据库描述类型: {type(db_description)}")
    print(f"  数据库描述键: {list(db_description.keys())[:5]}...")

def main():
    """主函数"""
    print("🚀 调试匹配问题")
    print("=" * 60)
    
    # 加载文件
    q2sql_pairs, ddl_content, db_description = load_files()
    
    # 测试第一个问题
    test_question = q2sql_pairs[0]["question"]
    debug_match(test_question, ddl_content, db_description)

if __name__ == "__main__":
    main()
