#!/usr/bin/env python3
"""
对比RAG检索结果和黄金标准结果
"""

import re
import os
import yaml
from typing import List, Dict, Any, Set
from sqlalchemy import create_engine, text

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

def extract_table_names_from_ddl(text: str) -> Set[str]:
    """从DDL语句中提取表名和视图名（匹配CREATE TABLE和所有VIEW语句）"""
    if not text:
        return set()
    
    found_tables = set()
    text_lower = text.lower()
    
    # 使用正则表达式匹配CREATE TABLE和所有VIEW语句
    import re
    
    # 匹配CREATE TABLE语句中的表名
    table_pattern = r'create\s+table\s+(?:if\s+not\s+exists\s+)?`?(\w+)`?'
    table_matches = re.findall(table_pattern, text_lower)
    found_tables.update(table_matches)
    
    # 匹配所有VIEW语句中的视图名（包括DEFINER VIEW等）
    # 匹配任何包含"view"关键字的语句，提取view后面的名称
    view_pattern = r'(?:definer\s+)?view\s+`?(\w+)`?'
    view_matches = re.findall(view_pattern, text_lower)
    found_tables.update(view_matches)
    
    return found_tables

def extract_table_names_from_description(text: str) -> Set[str]:
    """从数据库描述中提取表名（保留之前的逻辑）"""
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

def extract_table_names_from_ddl_as_string(text: str) -> str:
    """从DDL语句中提取表名，返回逗号分隔的字符串"""
    tables = extract_table_names_from_ddl(text)
    return ",".join(sorted(tables)) if tables else ""

def extract_table_names_from_description_as_string(text: str) -> str:
    """从数据库描述中提取表名，返回逗号分隔的字符串"""
    tables = extract_table_names_from_description(text)
    return ",".join(sorted(tables)) if tables else ""

def count_table_names_from_ddl(text: str) -> int:
    """统计DDL文本中的表名数量"""
    return len(extract_table_names_from_ddl(text))

def count_table_names_from_description(text: str) -> int:
    """统计数据库描述文本中的表名数量"""
    return len(extract_table_names_from_description(text))

def compare_ddl_content(rag_ddl: str, gold_ddl: str) -> Dict[str, int]:
    """比较DDL内容"""
    rag_tables = extract_table_names_from_ddl(rag_ddl)
    gold_tables = extract_table_names_from_ddl(gold_ddl)
    
    # 包含统计：RAG结果在黄金标准中找到的表数量
    intersection = rag_tables.intersection(gold_tables)
    include_count = len(intersection) if gold_tables else 0
    
    # 相等统计：两边表完全一样
    equal_count = 1 if rag_tables == gold_tables and rag_tables else 0
    
    return {
        "include_count": include_count,
        "equal_count": equal_count
    }

def compare_desc_content(rag_desc: str, gold_desc: str) -> Dict[str, int]:
    """比较数据库描述内容"""
    rag_tables = extract_table_names_from_description(rag_desc)
    gold_tables = extract_table_names_from_description(gold_desc)
    
    # 包含统计：RAG结果在黄金标准中找到的表数量
    intersection = rag_tables.intersection(gold_tables)
    include_count = len(intersection) if gold_tables else 0
    
    # 相等统计：两边表完全一样
    equal_count = 1 if rag_tables == gold_tables and rag_tables else 0
    
    return {
        "include_count": include_count,
        "equal_count": equal_count
    }

def get_ddl_total_count():
    """获取DDL语句总数"""
    ddl_file = "F:\\llm\\code\\rag-new-project001\\data\\ddl_statements.yaml"
    try:
        with open(ddl_file, 'r', encoding='utf-8') as f:
            ddl_data = yaml.safe_load(f)
        return len(ddl_data) if ddl_data else 0
    except Exception as e:
        print(f"❌ 读取DDL文件失败: {e}")
        return 0

def get_db_desc_total_count():
    """获取数据库描述总数"""
    db_desc_file = "F:\\llm\\code\\rag-new-project001\\data\\db_description.yaml"
    try:
        with open(db_desc_file, 'r', encoding='utf-8') as f:
            db_desc_data = yaml.safe_load(f)
        return len(db_desc_data) if db_desc_data else 0
    except Exception as e:
        print(f"❌ 读取数据库描述文件失败: {e}")
        return 0

def create_table_if_not_exists(engine):
    """创建表（如果不存在）"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS compare_result (
        id INT AUTO_INCREMENT PRIMARY KEY,
        question TEXT NOT NULL COMMENT '问题',
        standard_answer TEXT COMMENT '标准答案',
        rag_ddl TEXT COMMENT 'RAG检索-DDL语句',
        rag_ddl_extracted_value TEXT COMMENT 'RAG检索-DDL语句提取值',
        rag_db_description TEXT COMMENT 'RAG检索-数据库描述',
        rag_db_desc_extracted_value TEXT COMMENT 'RAG检索-数据库描述提取值',
        rag_ddl_statistics TINYINT COMMENT 'RAG检索-DDL语句统计(1有值，0无值)',
        rag_db_desc_statistics TINYINT COMMENT 'RAG检索-数据库描述统计(1有值，0无值)',
        standard_ddl TEXT COMMENT '黄金标准-DDL语句',
        standard_ddl_extracted_value TEXT COMMENT '黄金标准-DDL语句提取值',
        standard_db_desc TEXT COMMENT '黄金标准-数据库描述',
        standard_db_desc_extracted_value TEXT COMMENT '黄金标准-数据库描述提取值',
        standard_ddl_statistics TINYINT COMMENT '黄金标准-DDL语句统计(1有值，0无值)',
        standard_db_desc_statistics TINYINT COMMENT '黄金标准-数据库描述统计(1有值，0无值)',
        ddl_include_statistics TINYINT COMMENT 'DDL语句-包含统计(1有匹配，0无匹配)',
        db_desc_include_statistics TINYINT COMMENT '数据库描述-包含统计(1有匹配，0无匹配)',
        ddl_equal_statistics TINYINT COMMENT 'DDL语句-相等统计(1完全相同，0不同)',
        db_desc_equal_statistics TINYINT COMMENT '数据库描述-相等统计(1完全相同，0不同)',
        topk_value INT COMMENT 'TOPK值',
        recall DECIMAL(5,4) COMMENT '召回率',
        precisions DECIMAL(5,4) COMMENT '精确率',
        accuracy DECIMAL(5,4) COMMENT '准确率',
        f2_score DECIMAL(5,4) COMMENT 'F2值',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RAG检索结果与黄金标准的比对结果'
    """
    
    try:
        with engine.connect() as conn:
            # 先测试数据库连接
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            print(f"🔗 数据库连接测试成功: {test_value}")
            
            # 创建表
            conn.execute(text(create_table_sql))
            conn.commit()
            print("✅ 表创建成功或已存在")
            
            # 验证表是否存在
            result = conn.execute(text("SHOW TABLES LIKE 'compare_result'"))
            if result.fetchone():
                print("✅ 表 compare_result 确认存在")
            else:
                print("❌ 表 compare_result 不存在")
                return False
                
        return True
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def insert_comparison_results(engine, comparison_results):
    """将对比结果插入数据库"""
    if not comparison_results:
        print("⚠️ 没有对比结果需要插入")
        return False
        
    print(f"📊 准备插入 {len(comparison_results)} 条记录")
    
    # 先打印第一条记录的结构，用于调试
    if comparison_results:
        first_result = comparison_results[0]
        print("🔍 第一条记录的结构:")
        for key, value in first_result.items():
            print(f"  {key}: {type(value).__name__} = {str(value)[:100]}...")
        
        print("🔍 检查关键字段:")
        print(f"  recall_rate: {first_result.get('recall_rate', 'MISSING')}")
        print(f"  precision_rate: {first_result.get('precision_rate', 'MISSING')}")
        print(f"  accuracy_rate: {first_result.get('accuracy_rate', 'MISSING')}")
        print(f"  f2_score: {first_result.get('f2_score', 'MISSING')}")
    
    insert_sql = """
    INSERT INTO compare_result (
        question, standard_answer, rag_ddl, rag_ddl_extracted_value, rag_db_description, rag_db_desc_extracted_value,
        rag_ddl_statistics, rag_db_desc_statistics,
        standard_ddl, standard_ddl_extracted_value, standard_db_desc, standard_db_desc_extracted_value,
        standard_ddl_statistics, standard_db_desc_statistics,
        ddl_include_statistics, db_desc_include_statistics,
        ddl_equal_statistics, db_desc_equal_statistics,
        topk_value, recall, precisions, accuracy, f2_score
    ) VALUES (
        :question, :standard_answer, :rag_ddl, :rag_ddl_extracted_value, :rag_db_description, :rag_db_desc_extracted_value,
        :rag_ddl_statistics, :rag_db_desc_statistics,
        :standard_ddl, :standard_ddl_extracted_value, :standard_db_desc, :standard_db_desc_extracted_value,
        :standard_ddl_statistics, :standard_db_desc_statistics,
        :ddl_include_statistics, :db_desc_include_statistics,
        :ddl_equal_statistics, :db_desc_equal_statistics,
        :topk_value, :recall, :precisions, :accuracy, :f2_score
    )
    """
    
    try:
        with engine.connect() as conn:
            # 先测试插入第一条记录
            if comparison_results:
                print("🧪 测试插入第一条记录...")
                test_result = comparison_results[0]
                try:
                    conn.execute(text(insert_sql), {
                        'question': test_result['question'],
                        'standard_answer': test_result['standard_answer'],
                        'rag_ddl': test_result['rag_ddl'],
                        'rag_ddl_extracted_value': test_result['rag_ddl_extracted_value'],
                        'rag_db_description': test_result['rag_desc'],
                        'rag_db_desc_extracted_value': test_result['rag_desc_extracted_value'],
                        'rag_ddl_statistics': test_result['rag_ddl_statistics'],
                        'rag_db_desc_statistics': test_result['rag_desc_statistics'],
                        'standard_ddl': test_result['gold_ddl'],
                        'standard_ddl_extracted_value': test_result['gold_ddl_extracted_value'],
                        'standard_db_desc': test_result['gold_desc'],
                        'standard_db_desc_extracted_value': test_result['gold_desc_extracted_value'],
                        'standard_ddl_statistics': test_result['gold_ddl_statistics'],
                        'standard_db_desc_statistics': test_result['gold_desc_statistics'],
                        'ddl_include_statistics': test_result['ddl_include_statistics'],
                        'db_desc_include_statistics': test_result['db_desc_include_statistics'],
                        'ddl_equal_statistics': test_result['ddl_equal_statistics'],
                        'db_desc_equal_statistics': test_result['db_desc_equal_statistics'],
                        'topk_value': test_result['topk_value'],
                        'recall': test_result['recall_rate'],
                        'precisions': test_result['precision_rate'],
                        'accuracy': test_result['accuracy_rate'],
                        'f2_score': test_result['f2_score']
                    })
                    conn.commit()
                    print("✅ 测试插入成功！")
                except Exception as e:
                    print(f"❌ 测试插入失败: {e}")
                    print(f"   测试数据: {test_result}")
                    raise
            
            # 插入所有记录
            for i, result in enumerate(comparison_results):
                try:
                    conn.execute(text(insert_sql), {
                        'question': result['question'],
                        'standard_answer': result['standard_answer'],
                        'rag_ddl': result['rag_ddl'],
                        'rag_ddl_extracted_value': result['rag_ddl_extracted_value'],
                        'rag_db_description': result['rag_desc'],
                        'rag_db_desc_extracted_value': result['rag_desc_extracted_value'],
                        'rag_ddl_statistics': result['rag_ddl_statistics'],
                        'rag_db_desc_statistics': result['rag_desc_statistics'],
                        'standard_ddl': result['gold_ddl'],
                        'standard_ddl_extracted_value': result['gold_ddl_extracted_value'],
                        'standard_db_desc': result['gold_desc'],
                        'standard_db_desc_extracted_value': result['gold_desc_extracted_value'],
                        'standard_ddl_statistics': result['gold_ddl_statistics'],
                        'standard_db_desc_statistics': result['gold_desc_statistics'],
                        'ddl_include_statistics': result['ddl_include_statistics'],
                        'db_desc_include_statistics': result['db_desc_include_statistics'],
                        'ddl_equal_statistics': result['ddl_equal_statistics'],
                        'db_desc_equal_statistics': result['db_desc_equal_statistics'],
                        'topk_value': result['topk_value'],
                        'recall': result['recall_rate'],
                        'precisions': result['precision_rate'],
                        'accuracy': result['accuracy_rate'],
                        'f2_score': result['f2_score']
                    })
                    if (i + 1) % 10 == 0:
                        print(f"  📝 已处理 {i + 1}/{len(comparison_results)} 条记录")
                except Exception as e:
                    print(f"❌ 插入第 {i+1} 条记录失败: {e}")
                    print(f"   问题: {result.get('question', 'N/A')}")
                    print(f"   数据: {result}")
                    raise
            conn.commit()
            print(f"✅ 成功插入 {len(comparison_results)} 条记录到数据库")
        return True
    except Exception as e:
        print(f"❌ 插入数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def calculate_metrics(ddl_include_count, db_desc_include_count, 
                     gold_ddl_count, gold_desc_count, 
                     rag_ddl_count, rag_desc_count, 
                     ddl_total, db_desc_total, topk_value):
    """计算评估指标"""
    # 召回率：1/2*DDL语句-包含统计/黄金标准-DDL语句统计+1/2*数据库描述-包含统计/黄金标准-数据库描述统计
    recall_rate = 0.0
    if gold_ddl_count > 0 or gold_desc_count > 0:
        ddl_recall = ddl_include_count / gold_ddl_count if gold_ddl_count > 0 else 0
        desc_recall = db_desc_include_count / gold_desc_count if gold_desc_count > 0 else 0
        recall_rate = 0.5 * ddl_recall + 0.5 * desc_recall
    
    # 精确率：1/2*DDL语句-包含统计/TOPK值+1/2*数据库描述-包含统计/TOPK值
    precision_rate = 0.0
    if topk_value > 0:
        ddl_precision = ddl_include_count / topk_value
        desc_precision = db_desc_include_count / topk_value
        precision_rate = 0.5 * ddl_precision + 0.5 * desc_precision
    
    # 准确率：1/2*RAG检索-DDL语句统计/DDL语句总数+1/2*RAG检索-数据库描述统计/数据库描述总数
    accuracy_rate = 0.0
    if ddl_total > 0 or db_desc_total > 0:
        ddl_accuracy = rag_ddl_count / ddl_total if ddl_total > 0 else 0
        desc_accuracy = rag_desc_count / db_desc_total if db_desc_total > 0 else 0
        accuracy_rate = 0.5 * ddl_accuracy + 0.5 * desc_accuracy
    
    # F2值：5*精确率*召回率/(4*精确率+召回率)
    f2_score = 0.0
    if 4 * precision_rate + recall_rate > 0:
        f2_score = 5 * precision_rate * recall_rate / (4 * precision_rate + recall_rate)
    
    return recall_rate, precision_rate, accuracy_rate, f2_score

def compare_results():
    """主对比函数"""
    print("🚀 开始对比RAG检索结果和黄金标准...")
    
    # 数据库连接
    db_url = "mysql+pymysql://root:Rzx#1218@10.128.15.5:3306/rag_learn"
    
    # 文件路径
    rag_file = "F:\\llm\\code\\rag-new-project001\\data\\test_retrieval_results.txt"
    gold_file = "F:\\llm\\code\\rag-new-project001\\data\\question_analysis_results.txt"
    
    # 获取总数
    ddl_total = get_ddl_total_count()
    db_desc_total = get_db_desc_total_count()
    print(f"📊 DDL语句总数: {ddl_total}")
    print(f"📊 数据库描述总数: {db_desc_total}")
    
    # 初始化数据库连接
    print("🔗 连接数据库...")
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    # 创建表
    if not create_table_if_not_exists(engine):
        return
    
    # 检查表是否存在
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES LIKE 'compare_result'"))
            if result.fetchone():
                print("✅ 表 compare_result 存在")
            else:
                print("❌ 表 compare_result 不存在")
                return
    except Exception as e:
        print(f"❌ 检查表失败: {e}")
        return
    
    # 测试插入一条简单数据
    print("🧪 测试插入简单数据...")
    try:
        with engine.connect() as conn:
            test_sql = """
            INSERT INTO compare_result (
                question, standard_answer, rag_ddl, rag_ddl_extracted_value, rag_db_description, rag_db_desc_extracted_value,
                rag_ddl_statistics, rag_db_desc_statistics,
                standard_ddl, standard_ddl_extracted_value, standard_db_desc, standard_db_desc_extracted_value,
                standard_ddl_statistics, standard_db_desc_statistics,
                ddl_include_statistics, db_desc_include_statistics,
                ddl_equal_statistics, db_desc_equal_statistics,
                topk_value, recall, precisions, accuracy, f2_score
            ) VALUES (
                '测试问题', '测试答案', '测试DDL', 'test_table', '测试描述', 'test_table',
                1, 1, '测试标准DDL', 'test_table', '测试标准描述', 'test_table',
                1, 1, 1, 1, 1, 1, 3, 0.5, 0.5, 0.5, 0.5
            )
            """
            conn.execute(text(test_sql))
            conn.commit()
            print("✅ 测试插入成功！")
            
            # 验证插入
            result = conn.execute(text("SELECT COUNT(*) FROM compare_result"))
            count = result.fetchone()[0]
            print(f"📊 当前表中记录数: {count}")
            
    except Exception as e:
        print(f"❌ 测试插入失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
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
        
        # 提取表名
        rag_ddl_extracted_value = extract_table_names_from_ddl_as_string(rag_item["ddl_results"])
        rag_desc_extracted_value = extract_table_names_from_description_as_string(rag_item["desc_results"])
        gold_ddl_extracted_value = extract_table_names_from_ddl_as_string(gold_item["ddl_results"])
        gold_desc_extracted_value = extract_table_names_from_description_as_string(gold_item["desc_results"])
        
        # 统计逻辑：统计表名数量，但转换为TINYINT（0或1）
        rag_ddl_statistics = 1 if count_table_names_from_ddl(rag_item["ddl_results"]) > 0 else 0
        rag_desc_statistics = 1 if count_table_names_from_description(rag_item["desc_results"]) > 0 else 0
        gold_ddl_statistics = 1 if count_table_names_from_ddl(gold_item["ddl_results"]) > 0 else 0
        gold_desc_statistics = 1 if count_table_names_from_description(gold_item["desc_results"]) > 0 else 0
        
        # DDL内容对比
        ddl_comparison = compare_ddl_content(rag_item["ddl_results"], gold_item["ddl_results"])
        
        # 描述内容对比
        desc_comparison = compare_desc_content(rag_item["desc_results"], gold_item["desc_results"])
        
        # 计算评估指标
        recall_rate, precision_rate, accuracy_rate, f2_score = calculate_metrics(
            ddl_comparison["include_count"], desc_comparison["include_count"],
            gold_ddl_statistics, gold_desc_statistics,
            rag_ddl_statistics, rag_desc_statistics,
            ddl_total, db_desc_total, 3  # topk_value = 3
        )
        
        comparison_results.append({
            "question": rag_question,
            "standard_answer": rag_item["standard_answer"],
            "rag_ddl": rag_item["ddl_results"],
            "rag_ddl_extracted_value": rag_ddl_extracted_value,
            "rag_desc": rag_item["desc_results"],
            "rag_desc_extracted_value": rag_desc_extracted_value,
            "rag_ddl_statistics": rag_ddl_statistics,
            "rag_desc_statistics": rag_desc_statistics,
            "gold_ddl": gold_item["ddl_results"],
            "gold_ddl_extracted_value": gold_ddl_extracted_value,
            "gold_desc": gold_item["desc_results"],
            "gold_desc_extracted_value": gold_desc_extracted_value,
            "gold_ddl_statistics": gold_ddl_statistics,
            "gold_desc_statistics": gold_desc_statistics,
            "ddl_include_statistics": 1 if ddl_comparison["include_count"] > 0 else 0,
            "db_desc_include_statistics": 1 if desc_comparison["include_count"] > 0 else 0,
            "ddl_equal_statistics": ddl_comparison["equal_count"],
            "db_desc_equal_statistics": desc_comparison["equal_count"],
            "topk_value": 3,  # 固定为3，因为retriever.py中设置了top_k=3
            "recall_rate": recall_rate,
            "precision_rate": precision_rate,
            "accuracy_rate": accuracy_rate,
            "f2_score": f2_score
        })
        
        print(f"✅ 对比完成第 {i+1}/{len(rag_results)} 个问题")
    
    # 检查数据是否正确生成
    if comparison_results:
        print(f"📊 生成了 {len(comparison_results)} 条对比结果")
        print("🔍 第一条结果示例:")
        first_result = comparison_results[0]
        for key, value in first_result.items():
            print(f"  {key}: {value}")
    else:
        print("❌ 没有生成对比结果")
        return
    
    # 插入结果到数据库
    print("💾 将对比结果插入数据库...")
    if insert_comparison_results(engine, comparison_results):
        print("✅ 数据插入成功")
    else:
        print("❌ 数据插入失败")
    
    # 输出统计信息
    print(f"\n📊 对比统计:")
    print(f"总问题数: {len(comparison_results)}")
    
    if comparison_results:
        # 计算平均指标
        avg_recall = sum(r['recall_rate'] for r in comparison_results) / len(comparison_results)
        avg_precision = sum(r['precision_rate'] for r in comparison_results) / len(comparison_results)
        avg_accuracy = sum(r['accuracy_rate'] for r in comparison_results) / len(comparison_results)
        avg_f2 = sum(r['f2_score'] for r in comparison_results) / len(comparison_results)
        
        ddl_include_count = sum(1 for r in comparison_results if r['ddl_include_statistics'] > 0)
        desc_include_count = sum(1 for r in comparison_results if r['db_desc_include_statistics'] > 0)
        ddl_equal_count = sum(1 for r in comparison_results if r['ddl_equal_statistics'])
        desc_equal_count = sum(1 for r in comparison_results if r['db_desc_equal_statistics'])
        
        print(f"DDL语句包含匹配的问题数: {ddl_include_count}")
        print(f"数据库描述包含匹配的问题数: {desc_include_count}")
        print(f"DDL语句完全相等的问题数: {ddl_equal_count}")
        print(f"数据库描述完全相等的问题数: {desc_equal_count}")
        
        print(f"DDL语句包含匹配率: {ddl_include_count/len(comparison_results)*100:.1f}%")
        print(f"数据库描述包含匹配率: {desc_include_count/len(comparison_results)*100:.1f}%")
        print(f"DDL语句完全匹配率: {ddl_equal_count/len(comparison_results)*100:.1f}%")
        print(f"数据库描述完全匹配率: {desc_equal_count/len(comparison_results)*100:.1f}%")
        
        print(f"\n📈 平均评估指标:")
        print(f"平均召回率: {avg_recall:.4f}")
        print(f"平均精确率: {avg_precision:.4f}")
        print(f"平均准确率: {avg_accuracy:.4f}")
        print(f"平均F2值: {avg_f2:.4f}")
    
    print(f"✅ 对比完成！结果已保存到数据库表 compare_result")

if __name__ == "__main__":
    compare_results()
