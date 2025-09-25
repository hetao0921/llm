#!/usr/bin/env python3
"""
测试统计功能
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
    question_lower = question.lower()
    
    for table in table_names:
        # 匹配单数和复数形式
        if table.lower() in question_lower or f"{table.lower()}s" in question_lower:
            found_tables.append(table)
    
    return found_tables

def simple_match(question: str, ddl_content: Dict, db_description: Dict) -> Dict[str, str]:
    """简单的关键词匹配方法（备用方案）"""
    tables = extract_table_names(question)
    
    ddl_results = []
    desc_results = []
    ddl_column_count = 0
    desc_column_count = 0
    
    for table in tables:
        if table in ddl_content:
            ddl_results.append(f"表 {table}:\n{ddl_content[table]}")
            # 统计DDL中的列数（通过计算CREATE TABLE语句中的字段定义）
            ddl_text = ddl_content[table]
            # 简单统计：计算行数减去CREATE TABLE、PRIMARY KEY、KEY等行
            lines = ddl_text.split('\n')
            column_lines = [line for line in lines if line.strip().startswith('`') and '`' in line]
            ddl_column_count += len(column_lines)
        
        if table in db_description:
            table_desc = db_description[table]
            desc_text = f"表 {table}:\n"
            for field, description in table_desc.items():
                desc_text += f"  {field}: {description}\n"
            desc_results.append(desc_text)
            # 统计数据库描述中的列数
            desc_column_count += len(table_desc)
    
    return {
        "ddl_statements": "\n\n".join(ddl_results) if ddl_results else "未找到相关DDL语句",
        "db_description": "\n\n".join(desc_results) if desc_results else "未找到相关数据库描述",
        "ddl_column_count": ddl_column_count,
        "desc_column_count": desc_column_count
    }

def process_questions():
    """主处理函数 - 只处理前3个问题"""
    # 加载文件
    q2sql_pairs, ddl_content, db_description = load_files()
    
    # 只提取前3个问题
    selected_questions = q2sql_pairs[:3]
    
    results = []
    
    print("开始处理前3个问题...")
    for i, pair in enumerate(selected_questions, 1):
        question = pair["question"]
        print(f"处理第 {i} 个问题: {question}")
        
        # 使用简单关键词匹配
        simple_result = simple_match(question, ddl_content, db_description)
        results.append({
            "question": question,
            "ddl_statements": simple_result["ddl_statements"],
            "db_description": simple_result["db_description"],
            "standard_answer": pair["sql"],  # 添加标准答案
            "ddl_column_count": simple_result["ddl_column_count"],  # 添加DDL列数统计
            "desc_column_count": simple_result["desc_column_count"]  # 添加描述列数统计
        })
    
    # 输出到txt文件
    output_file = "F:\\llm\\code\\rag-new-project001\\data\\question_analysis_results_stats_test.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write("=" * 80 + "\n")
            f.write(f"问题: {result['question']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"DDL语句:\n{result['ddl_statements']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"数据库描述:\n{result['db_description']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"标准答案:\n{result['standard_answer']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"DDL列数统计: {result['ddl_column_count']}\n")
            f.write(f"描述列数统计: {result['desc_column_count']}\n")
            f.write("=" * 80 + "\n\n")
    
    print(f"处理完成！结果已保存到 {output_file}")
    
    # 同时输出到控制台
    print("\n处理结果概要:")
    for i, result in enumerate(results, 1):
        print(f"{i}. 问题: {result['question']}")
        print(f"   DDL语句长度: {len(result['ddl_statements'])} 字符")
        print(f"   数据库描述长度: {len(result['db_description'])} 字符")
        print(f"   标准答案长度: {len(result['standard_answer'])} 字符")
        print(f"   DDL列数统计: {result['ddl_column_count']}")
        print(f"   描述列数统计: {result['desc_column_count']}")
        print()

if __name__ == "__main__":
    process_questions()
