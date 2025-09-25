#!/usr/bin/env python3
"""
对比RAG检索结果和黄金标准结果
"""

import re
import os
from typing import List, Dict, Any, Set

def parse_txt_file(file_path: str) -> List[Dict[str, Any]]:
    """解析TXT文件，提取问题和相关数据"""
    results = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按分隔符分割各个问题
        sections = content.split("=" * 80)
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            if len(lines) < 5:  # 确保有足够的内容
                continue
                
            question = ""
            standard_answer = ""
            ddl_results = ""
            desc_results = ""
            ddl_count = 0
            desc_count = 0
            
            current_field = ""
            content_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith("问题:"):
                    question = line.replace("问题:", "").strip()
                elif line.startswith("标准答案:"):
                    standard_answer = line.replace("标准答案:", "").strip()
                elif line.startswith("DDL语句:") or line.startswith("DDL返回结果:"):
                    current_field = "ddl"
                    content_lines = []
                elif line.startswith("数据库描述:") or line.startswith("数据库描述返回结果:"):
                    current_field = "desc"
                    content_lines = []
                elif line.startswith("DDL统计:") or line.startswith("DDL列数统计:"):
                    try:
                        ddl_count = int(line.split(":")[1].strip())
                    except:
                        ddl_count = 0
                elif line.startswith("描述统计:") or line.startswith("数据库描述统计:") or line.startswith("描述列数统计:"):
                    try:
                        desc_count = int(line.split(":")[1].strip())
                    except:
                        desc_count = 0
                elif line.startswith("-" * 40):
                    if current_field == "ddl":
                        ddl_results = "\n".join(content_lines)
                    elif current_field == "desc":
                        desc_results = "\n".join(content_lines)
                    current_field = ""
                    content_lines = []
                elif current_field and line:
                    content_lines.append(line)
            
            if question:
                results.append({
                    "question": question,
                    "standard_answer": standard_answer,
                    "ddl_results": ddl_results,
                    "desc_results": desc_results,
                    "ddl_count": ddl_count,
                    "desc_count": desc_count
                })
        
        return results
        
    except Exception as e:
        print(f"❌ 解析文件失败 {file_path}: {e}")
        return []

def extract_table_names(text: str) -> Set[str]:
    """从文本中提取表名"""
    if not text:
        return set()
    
    # 常见的表名列表
    table_names = [
        'actor', 'address', 'category', 'city', 'country', 'customer', 
        'film', 'inventory', 'payment', 'rental', 'staff', 'store',
        'film_actor', 'film_category', 'language'
    ]
    
    found_tables = set()
    text_lower = text.lower()
    
    for table in table_names:
        if table.lower() in text_lower:
            found_tables.add(table)
    
    return found_tables

def compare_ddl_content(rag_ddl: str, gold_ddl: str) -> Dict[str, int]:
    """比较DDL内容"""
    rag_tables = extract_table_names(rag_ddl)
    gold_tables = extract_table_names(gold_ddl)
    
    # 包含统计：RAG结果在黄金标准中找到的表数量
    intersection = rag_tables.intersection(gold_tables)
    contain_count = len(intersection) if gold_tables else 0
    
    # 相等统计：两边表完全一样
    equal_count = 1 if rag_tables == gold_tables and rag_tables else 0
    
    return {
        "contain_count": contain_count,
        "equal_count": equal_count
    }

def compare_desc_content(rag_desc: str, gold_desc: str) -> Dict[str, int]:
    """比较数据库描述内容"""
    rag_tables = extract_table_names(rag_desc)
    gold_tables = extract_table_names(gold_desc)
    
    # 包含统计：RAG结果在黄金标准中找到的表数量
    intersection = rag_tables.intersection(gold_tables)
    contain_count = len(intersection) if gold_tables else 0
    
    # 相等统计：两边表完全一样
    equal_count = 1 if rag_tables == gold_tables and rag_tables else 0
    
    return {
        "contain_count": contain_count,
        "equal_count": equal_count
    }

def compare_combined_content(rag_ddl: str, rag_desc: str, gold_ddl: str, gold_desc: str) -> Dict[str, int]:
    """比较DDL+描述的组合内容"""
    # 合并RAG的表
    rag_tables = extract_table_names(rag_ddl).union(extract_table_names(rag_desc))
    
    # 合并黄金标准的表
    gold_tables = extract_table_names(gold_ddl).union(extract_table_names(gold_desc))
    
    # 包含统计：RAG结果在黄金标准中找到的表数量
    intersection = rag_tables.intersection(gold_tables)
    contain_count = len(intersection) if gold_tables else 0
    
    # 相等统计：两边表完全一样
    equal_count = 1 if rag_tables == gold_tables and rag_tables else 0
    
    return {
        "contain_count": contain_count,
        "equal_count": equal_count
    }

def compare_results():
    """主对比函数"""
    print("🚀 开始对比RAG检索结果和黄金标准...")
    
    # 文件路径
    rag_file = "F:\\llm\\code\\rag-new-project001\\data\\test_retrieval_results.txt"
    gold_file = "F:\\llm\\code\\rag-new-project001\\data\\question_analysis_results.txt"
    output_file = "F:\\llm\\code\\rag-new-project001\\data\\comparison_results.txt"
    
    # 解析文件
    print("📂 解析RAG检索结果文件...")
    rag_results = parse_txt_file(rag_file)
    print(f"📋 解析到 {len(rag_results)} 个RAG结果")
    
    print("📂 解析黄金标准文件...")
    gold_results = parse_txt_file(gold_file)
    print(f"📋 解析到 {len(gold_results)} 个黄金标准结果")
    
    if not rag_results or not gold_results:
        print("❌ 无法解析文件，退出")
        return
    
    # 创建对比结果
    comparison_results = []
    
    print("🔍 开始对比...")
    for i, rag_item in enumerate(rag_results):
        rag_question = rag_item["question"]
        
        # 在黄金标准中找到对应的问题
        gold_item = None
        for gold in gold_results:
            if gold["question"] == rag_question:
                gold_item = gold
                break
        
        if not gold_item:
            print(f"⚠️ 在黄金标准中未找到问题: {rag_question}")
            continue
        
        # 统计逻辑
        rag_ddl_has_value = 1 if rag_item["ddl_results"].strip() else 0
        rag_desc_has_value = 1 if rag_item["desc_results"].strip() else 0
        gold_ddl_has_value = 1 if gold_item["ddl_results"].strip() else 0
        gold_desc_has_value = 1 if gold_item["desc_results"].strip() else 0
        
        # DDL内容对比
        ddl_comparison = compare_ddl_content(rag_item["ddl_results"], gold_item["ddl_results"])
        
        # 描述内容对比
        desc_comparison = compare_desc_content(rag_item["desc_results"], gold_item["desc_results"])
        
        # 组合内容对比
        combined_comparison = compare_combined_content(
            rag_item["ddl_results"], rag_item["desc_results"],
            gold_item["ddl_results"], gold_item["desc_results"]
        )
        
        comparison_results.append({
            "question": rag_question,
            "standard_answer": rag_item["standard_answer"],
            "rag_ddl": rag_item["ddl_results"],
            "rag_desc": rag_item["desc_results"],
            "rag_ddl_count": rag_item["ddl_count"],
            "rag_desc_count": rag_item["desc_count"],
            "gold_ddl": gold_item["ddl_results"],
            "gold_desc": gold_item["desc_results"],
            "gold_ddl_count": gold_item["ddl_count"],
            "gold_desc_count": gold_item["desc_count"],
            "ddl_has_value": rag_ddl_has_value,
            "desc_has_value": rag_desc_has_value,
            "gold_ddl_has_value": gold_ddl_has_value,
            "gold_desc_has_value": gold_desc_has_value,
            "ddl_contain_count": ddl_comparison["contain_count"],
            "desc_contain_count": desc_comparison["contain_count"],
            "combined_contain_count": combined_comparison["contain_count"],
            "combined_equal_count": combined_comparison["equal_count"]
        })
        
        print(f"✅ 对比完成第 {i+1}/{len(rag_results)} 个问题")
    
    # 输出结果到文件
    print(f"📄 输出对比结果到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入表头
        f.write("问题\t标准答案\tRAG检索-DDL语句\tRAG检索-数据库描述\tRAG检索-DDL语句统计\tRAG检索-数据库描述统计\t")
        f.write("黄金标准-DDL语句\t黄金标准-数据库描述\t黄金标准-DDL语句统计\t黄金标准-数据库描述统计\t")
        f.write("DDL语句比对-统计\t数据库描述比对-统计\tDDL语句+数据库描述比对-包含统计\tDDL语句+数据库描述比对-相等统计\n")
        
        # 写入数据
        for result in comparison_results:
            f.write(f"{result['question']}\t")
            f.write(f"{result['standard_answer']}\t")
            f.write(f"{result['rag_ddl']}\t")
            f.write(f"{result['rag_desc']}\t")
            f.write(f"{result['rag_ddl_count']}\t")
            f.write(f"{result['rag_desc_count']}\t")
            f.write(f"{result['gold_ddl']}\t")
            f.write(f"{result['gold_desc']}\t")
            f.write(f"{result['gold_ddl_count']}\t")
            f.write(f"{result['gold_desc_count']}\t")
            f.write(f"{result['ddl_has_value']}\t")
            f.write(f"{result['desc_has_value']}\t")
            f.write(f"{result['combined_contain_count']}\t")
            f.write(f"{result['combined_equal_count']}\n")
    
    # 输出统计信息
    print(f"\n📊 对比统计:")
    print(f"总问题数: {len(comparison_results)}")
    
    if comparison_results:
        ddl_has_value_count = sum(1 for r in comparison_results if r['ddl_has_value'])
        desc_has_value_count = sum(1 for r in comparison_results if r['desc_has_value'])
        combined_equal_count = sum(1 for r in comparison_results if r['combined_equal_count'])
        
        print(f"DDL语句有值的问题数: {ddl_has_value_count}")
        print(f"数据库描述有值的问题数: {desc_has_value_count}")
        print(f"DDL+描述完全相等的问题数: {combined_equal_count}")
        
        print(f"DDL语句覆盖率: {ddl_has_value_count/len(comparison_results)*100:.1f}%")
        print(f"数据库描述覆盖率: {desc_has_value_count/len(comparison_results)*100:.1f}%")
        print(f"完全匹配率: {combined_equal_count/len(comparison_results)*100:.1f}%")
    
    print(f"✅ 对比完成！结果已保存到: {output_file}")

if __name__ == "__main__":
    compare_results()
