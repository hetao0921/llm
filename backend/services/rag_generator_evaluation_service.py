#!/usr/bin/env python3
"""
RAG系统生成器评估服务
"""

import os
import logging
import requests
import json
import re
import sqlite3
from typing import List, Dict, Any, Set, Tuple
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 尝试导入 PyMySQL
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError as e:
    logging.error("缺少 pymysql 包，请执行：pip install pymysql")
    raise e

# 尝试导入 PyMilvus
try:
    from pymilvus import connections, Collection, utility
except ImportError as e:
    logging.error("缺少 pymilvus 包，请执行：pip install pymilvus")
    raise e

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Silicon Flow 配置
SILICON_FLOW_API_URL = "https://api.siliconflow.cn/v1"
SILICON_FLOW_API_TOKEN = os.getenv("SILICON_FLOW_API_TOKEN", "sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn")
SILICON_FLOW_EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
SILICON_FLOW_CHAT_MODEL = os.getenv("SILICON_FLOW_CHAT_MODEL", "Qwen/QwQ-32B")

# Milvus 连接配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "10.128.15.221")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
DATABASE_NAME = os.getenv("MILVUS_DB_NAME", "text2sql_milvus_sakila_hetao")

# 集合名称
COLLECTION_DDL = "ddl_knowledge"
COLLECTION_Q2SQL = "q2sql_knowledge" 
COLLECTION_DBDESC = "dbdesc_knowledge"

# 数据库连接配置
DB_URL = "mysql+pymysql://root:Rzx#1218@10.128.15.5:3306/rag_learn"

# 创建路由器
router = APIRouter()

# 请求模型
class GeneratorEvaluationRequest(BaseModel):
    system_type: str
    generation_sub_type: str
    question: str

class GeneratorEvaluationResponse(BaseModel):
    success: bool
    message: str
    generation_results: str
    evaluation_metrics: Dict[str, float]

# 初始化 Milvus 连接
def init_milvus_connection():
    """初始化 Milvus 连接"""
    try:
        connections.connect(
            host=MILVUS_HOST,
            port=MILVUS_PORT,
            db_name=DATABASE_NAME
        )
        logging.info(f"✅ 成功连接到 Milvus 服务器 {MILVUS_HOST}:{MILVUS_PORT}")
        logging.info(f"✅ 正在使用数据库: '{DATABASE_NAME}'")
        return True
    except Exception as e:
        logging.error(f"❌ Milvus 连接失败: {e}")
        return False

# Silicon Flow 嵌入函数
def get_silicon_flow_embedding(text: str) -> list:
    """使用 Silicon Flow API 获取文本嵌入向量"""
    try:
        url = f"{SILICON_FLOW_API_URL}/embeddings"
        headers = {
            "Authorization": f"Bearer {SILICON_FLOW_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": SILICON_FLOW_EMBEDDING_MODEL,
            "input": text
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            embedding = result['data'][0]['embedding']
            logging.info(f"✅ 嵌入向量生成成功，维度: {len(embedding)}")
            return embedding
        else:
            logging.error(f"❌ Silicon Flow 嵌入 API 请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"❌ 嵌入生成异常: {e}")
        return None

# Silicon Flow 聊天补全函数
def siliconflow_chat_completion(messages: list, temperature: float = 0.1) -> str:
    """使用 Silicon Flow 聊天补全接口"""
    try:
        url = f"{SILICON_FLOW_API_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {SILICON_FLOW_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": SILICON_FLOW_CHAT_MODEL,
            "messages": messages,
            "temperature": temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0]['message']
                content = message['content'].strip()
                logging.info("✅ Silicon Flow 聊天补全调用成功")
                return content
            else:
                logging.error("❌ 响应中没有找到有效的回复内容")
                return None
        else:
            logging.error(f"❌ Silicon Flow 聊天 API 请求失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"❌ 聊天补全异常: {e}")
        return None

# 动态检测向量字段名称
def get_vector_field_name(collection):
    """动态检测集合中的向量字段名称"""
    try:
        schema = collection.schema
        for field in schema.fields:
            if hasattr(field, 'dtype') and 'FLOAT_VECTOR' in str(field.dtype):
                return field.name
            if any(keyword in field.name.lower() for keyword in ['vector', 'embedding', 'vec']):
                return field.name
        return "vector"
    except Exception as e:
        logging.warning(f"无法检测向量字段名称，使用默认值: {e}")
        return "vector"

# 检索函数
def retrieve(collection_name: str, query_emb: list, top_k: int = 3, output_fields: list = None):
    """从指定集合中检索相似内容"""
    try:
        if not utility.has_collection(collection_name):
            logging.warning(f"集合 '{collection_name}' 不存在")
            return []
            
        collection = Collection(collection_name)
        vector_field = get_vector_field_name(collection)
        
        # 加载集合
        try:
            collection.load()
        except Exception as load_error:
            logging.warning(f"集合加载失败: {load_error}")
            return []
        
        # 搜索参数
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        # 执行搜索
        results = collection.search(
            data=[query_emb],
            anns_field=vector_field,
            param=search_params,
            limit=top_k,
            output_fields=output_fields
        )
        
        # 处理结果
        hits = []
        if results and len(results) > 0:
            for result in results[0]:
                hit_data = {
                    "id": result.id,
                    "distance": result.distance,
                    "entity": {}
                }
                
                # 添加输出字段
                if output_fields:
                    for field in output_fields:
                        try:
                            if hasattr(result, 'entity') and hasattr(result.entity, field):
                                hit_data["entity"][field] = getattr(result.entity, field)
                            elif hasattr(result, field):
                                hit_data["entity"][field] = getattr(result, field)
                            else:
                                hit_data["entity"][field] = None
                        except Exception as e:
                            logging.warning(f"获取字段 {field} 失败: {e}")
                            hit_data["entity"][field] = None
                
                hits.append(hit_data)
        
        logging.info(f"[检索] {collection_name} 检索到 {len(hits)} 条结果")
        return hits
        
    except Exception as e:
        logging.error(f"[检索] {collection_name} 检索失败: {e}")
        return []

# SQL 提取函数
def extract_sql(text: str) -> str:
    """从文本中提取 SQL 语句"""
    if not text:
        return ""
    
    # 尝试匹配 SQL 代码块
    sql_blocks = re.findall(r'```sql\n(.*?)\n```', text, re.DOTALL)
    if sql_blocks:
        return sql_blocks[0].strip()
    
    # 如果没有找到代码块，尝试匹配 SELECT 语句
    select_match = re.search(r'SELECT.*?;', text, re.DOTALL)
    if select_match:
        return select_match.group(0).strip()
    
    # 尝试匹配 UPDATE 语句
    update_match = re.search(r'UPDATE.*?;', text, re.DOTALL)
    if update_match:
        return update_match.group(0).strip()
    
    # 尝试匹配 INSERT 语句  
    insert_match = re.search(r'INSERT.*?;', text, re.DOTALL)
    if insert_match:
        return insert_match.group(0).strip()
        
    # 尝试匹配 DELETE 语句
    delete_match = re.search(r'DELETE.*?;', text, re.DOTALL)
    if delete_match:
        return delete_match.group(0).strip()
    
    # 如果都没有找到，返回原始文本
    return text.strip()

# 解析上传的标准化生成列表
def parse_standard_list(file_content: str, question: str = "") -> Dict[str, str]:
    """解析标准化生成列表文件，并根据问题匹配对应的SQL"""
    try:
        # 尝试解析为JSON
        try:
            data = json.loads(file_content)
            logging.info(f"JSON解析结果类型: {type(data)}")
            
            if isinstance(data, dict):
                # 如果是单个字典，直接返回
                return data
            elif isinstance(data, list) and len(data) > 0:
                # 如果是列表，需要根据问题匹配
                if question:
                    # 根据问题内容匹配对应的条目
                    matched_item = find_matching_question(data, question)
                    if matched_item:
                        logging.info(f"✅ 找到匹配的问题: {matched_item.get('question', '')}")
                        return matched_item
                    else:
                        logging.warning(f"⚠️ 未找到匹配的问题，使用第一个条目")
                        return data[0] if isinstance(data[0], dict) else {}
                else:
                    # 没有提供问题，取第一个元素
                    return data[0] if isinstance(data[0], dict) else {}
            else:
                logging.warning(f"JSON解析结果不是字典或列表: {type(data)}")
                return {}
        except json.JSONDecodeError:
            pass
        
        # 尝试解析为YAML
        try:
            import yaml
            data = yaml.safe_load(file_content)
            logging.info(f"YAML解析结果类型: {type(data)}")
            
            if isinstance(data, dict):
                return data
            elif isinstance(data, list) and len(data) > 0:
                if question:
                    matched_item = find_matching_question(data, question)
                    if matched_item:
                        logging.info(f"✅ 找到匹配的问题: {matched_item.get('question', '')}")
                        return matched_item
                    else:
                        logging.warning(f"⚠️ 未找到匹配的问题，使用第一个条目")
                        return data[0] if isinstance(data[0], dict) else {}
                else:
                    return data[0] if isinstance(data[0], dict) else {}
            else:
                logging.warning(f"YAML解析结果不是字典或列表: {type(data)}")
                return {}
        except yaml.YAMLError:
            pass
        
        # 尝试解析为简单的键值对格式
        lines = file_content.strip().split('\n')
        result = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        logging.info(f"键值对解析结果: {result}")
        return result
        
    except Exception as e:
        logging.error(f"解析标准化生成列表失败: {e}")
        return {}

def find_matching_question(data_list: List[Dict], question: str) -> Dict:
    """在数据列表中查找匹配的问题"""
    if not question or not data_list:
        return {}
    
    question_lower = question.lower().strip()
    
    # 1. 精确匹配
    for item in data_list:
        if isinstance(item, dict) and 'question' in item:
            item_question = item['question'].lower().strip()
            if item_question == question_lower:
                logging.info(f"🎯 精确匹配: {item['question']}")
                return item
    
    # 2. 包含匹配
    for item in data_list:
        if isinstance(item, dict) and 'question' in item:
            item_question = item['question'].lower().strip()
            if question_lower in item_question or item_question in question_lower:
                logging.info(f"🔍 包含匹配: {item['question']}")
                return item
    
    # 3. 关键词匹配
    question_words = set(re.findall(r'\b\w+\b', question_lower))
    best_match = None
    best_score = 0
    
    for item in data_list:
        if isinstance(item, dict) and 'question' in item:
            item_question = item['question'].lower().strip()
            item_words = set(re.findall(r'\b\w+\b', item_question))
            
            # 计算词汇重叠度
            intersection = question_words.intersection(item_words)
            if intersection:
                score = len(intersection) / len(question_words.union(item_words))
                if score > best_score:
                    best_score = score
                    best_match = item
    
    if best_match and best_score > 0.3:  # 至少30%的词汇重叠
        logging.info(f"🔗 关键词匹配 (相似度: {best_score:.2f}): {best_match['question']}")
        return best_match
    
    logging.warning(f"❌ 未找到匹配的问题: {question}")
    return {}

# 创建SQLite测试数据库
def create_sakila_test_db():
    """创建Sakila测试数据库"""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # 创建actor表
    cursor.execute('''
        CREATE TABLE actor (
            actor_id INTEGER PRIMARY KEY,
            first_name VARCHAR(45),
            last_name VARCHAR(45),
            last_update TIMESTAMP
        )
    ''')
    
    # 创建customer表
    cursor.execute('''
        CREATE TABLE customer (
            customer_id INTEGER PRIMARY KEY,
            store_id INTEGER,
            first_name VARCHAR(45),
            last_name VARCHAR(45),
            create_date TIMESTAMP,
            address_id INTEGER,
            active INTEGER
        )
    ''')
    
    # 创建category表
    cursor.execute('''
        CREATE TABLE category (
            category_id INTEGER PRIMARY KEY,
            name VARCHAR(25),
            last_update TIMESTAMP
        )
    ''')
    
    # 插入actor测试数据
    actor_data = [
        (1, 'PENELOPE', 'GUINESS', '2020-01-01 00:00:00'),
        (2, 'NICK', 'WAHLBERG', '2020-01-01 00:00:00'),
        (3, 'ED', 'CHASE', '2020-01-01 00:00:00'),
        (4, 'JENNIFER', 'DAVIS', '2020-01-01 00:00:00'),
        (5, 'JOHNNY', 'LOLLOBRIGIDA', '2020-01-01 00:00:00')
    ]
    cursor.executemany('INSERT INTO actor VALUES (?, ?, ?, ?)', actor_data)
    
    # 插入category测试数据
    category_data = [
        (1, 'Action', '2020-01-01 00:00:00'),
        (2, 'Animation', '2020-01-01 00:00:00'),
        (3, 'Children', '2020-01-01 00:00:00'),
        (4, 'Classics', '2020-01-01 00:00:00'),
        (5, 'Comedy', '2020-01-01 00:00:00')
    ]
    cursor.executemany('INSERT INTO category VALUES (?, ?, ?)', category_data)
    
    conn.commit()
    
    return conn

# SQL转换函数
def convert_mysql_to_sqlite(sql: str) -> str:
    """将MySQL SQL转换为SQLite兼容的SQL"""
    if not sql:
        return sql
    
    # 替换NOW()为datetime('now')
    sql = re.sub(r'\bNOW\(\)', "datetime('now')", sql, flags=re.IGNORECASE)
    
    # 替换其他MySQL特定函数
    sql = re.sub(r'\bCURDATE\(\)', "date('now')", sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bCURTIME\(\)', "time('now')", sql, flags=re.IGNORECASE)
    
    return sql

# 执行SQL并获取结果
def execute_sql_and_get_results(sql: str, conn) -> List[Tuple]:
    """执行SQL并获取结果"""
    try:
        # 转换SQL为SQLite兼容格式
        converted_sql = convert_mysql_to_sqlite(sql)
        logging.info(f"🔍 原始SQL: {sql}")
        logging.info(f"🔍 转换后SQL: {converted_sql}")
        
        cursor = conn.cursor()
        cursor.execute(converted_sql)
        results = cursor.fetchall()
        logging.info(f"✅ SQL执行成功，返回 {len(results)} 行结果")
        return results
    except Exception as e:
        logging.error(f"❌ 执行SQL失败: {e}")
        logging.error(f"❌ 失败SQL: {converted_sql}")
        return None

# 计算执行准确率
def calculate_execution_accuracy(generated_sql: str, standard_sql: str) -> float:
    """计算执行准确率"""
    try:
        logging.info(f"🧪 开始计算执行准确率")
        logging.info(f"🔍 生成的SQL: {generated_sql}")
        logging.info(f"🔍 标准SQL: {standard_sql}")
        
        # 创建测试数据库
        conn = create_sakila_test_db()
        logging.info("✅ 测试数据库创建成功")
        
        # 执行生成的SQL
        generated_results = execute_sql_and_get_results(generated_sql, conn)
        if generated_results is None:
            logging.error("❌ 生成的SQL执行失败")
            return 0.0
        
        # 执行标准SQL
        standard_results = execute_sql_and_get_results(standard_sql, conn)
        if standard_results is None:
            logging.error("❌ 标准SQL执行失败")
            return 0.0
        
        # 比较结果集
        logging.info(f"🔍 生成SQL结果: {generated_results}")
        logging.info(f"🔍 标准SQL结果: {standard_results}")
        
        if generated_results == standard_results:
            logging.info("✅ 执行准确率: 1.0 (结果完全匹配)")
            return 1.0
        else:
            logging.info("❌ 执行准确率: 0.0 (结果不匹配)")
            return 0.0
            
    except Exception as e:
        logging.error(f"❌ 计算执行准确率失败: {e}")
        import traceback
        traceback.print_exc()
        return 0.0
    finally:
        if 'conn' in locals():
            conn.close()

# 计算精确匹配率
def calculate_exact_match_rate(generated_sql: str, standard_sql: str) -> float:
    """计算精确匹配率"""
    if not generated_sql or not standard_sql:
        logging.warning("❌ 精确匹配率计算失败：SQL为空")
        return 0.0
    
    # 标准化SQL：移除多余空格，转换为小写
    normalized_generated = re.sub(r'\s+', ' ', generated_sql.strip().lower())
    normalized_standard = re.sub(r'\s+', ' ', standard_sql.strip().lower())
    
    logging.info(f"🔍 标准化生成SQL: {normalized_generated}")
    logging.info(f"🔍 标准化标准SQL: {normalized_standard}")
    
    if normalized_generated == normalized_standard:
        logging.info("✅ 精确匹配率: 1.0 (SQL完全匹配)")
        return 1.0
    else:
        logging.info("❌ 精确匹配率: 0.0 (SQL不匹配)")
        return 0.0

# 解析SQL组件
def parse_sql_components(sql: str) -> Dict[str, Set[str]]:
    """解析SQL组件"""
    if not sql:
        return {}
    
    components = {
        'select': set(),
        'from': set(),
        'where': set(),
        'group_by': set(),
        'order_by': set(),
        'join': set()
    }
    
    sql_upper = sql.upper()
    
    # 解析SELECT子句
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_upper, re.DOTALL)
    if select_match:
        select_clause = select_match.group(1)
        # 提取列名
        columns = re.findall(r'\b\w+\b', select_clause)
        components['select'] = set(columns)
    
    # 解析FROM子句
    from_match = re.search(r'FROM\s+(\w+)', sql_upper)
    if from_match:
        components['from'].add(from_match.group(1))
    
    # 解析WHERE子句
    where_match = re.search(r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s*$)', sql_upper, re.DOTALL)
    if where_match:
        where_clause = where_match.group(1)
        # 提取条件中的列名和值
        conditions = re.findall(r'\b\w+\b', where_clause)
        components['where'] = set(conditions)
    
    # 解析JOIN子句
    join_matches = re.findall(r'JOIN\s+(\w+)', sql_upper)
    components['join'] = set(join_matches)
    
    return components

# 计算组件匹配率/SQL-F1值
def calculate_component_match_rate(generated_sql: str, standard_sql: str) -> float:
    """计算组件匹配率/SQL-F1值"""
    if not generated_sql or not standard_sql:
        logging.warning("❌ 组件匹配率计算失败：SQL为空")
        return 0.0
    
    logging.info(f"🧪 开始计算组件匹配率")
    logging.info(f"🔍 生成SQL: {generated_sql}")
    logging.info(f"🔍 标准SQL: {standard_sql}")
    
    generated_components = parse_sql_components(generated_sql)
    standard_components = parse_sql_components(standard_sql)
    
    logging.info(f"🔍 生成SQL组件: {generated_components}")
    logging.info(f"🔍 标准SQL组件: {standard_components}")
    
    total_precision = 0
    total_recall = 0
    component_count = 0
    
    for component_type in generated_components:
        if component_type in standard_components:
            generated_set = generated_components[component_type]
            standard_set = standard_components[component_type]
            
            if generated_set or standard_set:  # 至少有一个不为空
                intersection = generated_set.intersection(standard_set)
                
                # 计算精确率
                precision = len(intersection) / len(generated_set) if generated_set else 0
                
                # 计算召回率
                recall = len(intersection) / len(standard_set) if standard_set else 0
                
                logging.info(f"🔍 {component_type} - 生成集: {generated_set}, 标准集: {standard_set}, 交集: {intersection}")
                logging.info(f"🔍 {component_type} - 精确率: {precision:.3f}, 召回率: {recall:.3f}")
                
                # 计算F1值
                if precision + recall > 0:
                    f1 = 2 * precision * recall / (precision + recall)
                    total_precision += precision
                    total_recall += recall
                    component_count += 1
                    logging.info(f"🔍 {component_type} - F1值: {f1:.3f}")
    
    if component_count == 0:
        logging.warning("❌ 组件匹配率: 0.0 (没有可比较的组件)")
        return 0.0
    
    avg_precision = total_precision / component_count
    avg_recall = total_recall / component_count
    
    if avg_precision + avg_recall > 0:
        final_f1 = 2 * avg_precision * avg_recall / (avg_precision + avg_recall)
        logging.info(f"✅ 组件匹配率: {final_f1:.3f} (平均精确率: {avg_precision:.3f}, 平均召回率: {avg_recall:.3f})")
        return final_f1
    else:
        logging.warning("❌ 组件匹配率: 0.0 (平均精确率和召回率都为0)")
        return 0.0

# 计算检索相关性
def calculate_retrieval_relevance(question: str, retrieval_data: Dict) -> float:
    """计算检索相关性"""
    if not retrieval_data:
        return 0.0
    
    # 简单的关键词匹配方法
    question_lower = question.lower()
    relevance_score = 0.0
    total_items = 0
    
    # 检查DDL相关性
    if 'ddl_context' in retrieval_data:
        ddl_context = retrieval_data['ddl_context'].lower()
        # 提取问题中的关键词
        question_words = set(re.findall(r'\b\w+\b', question_lower))
        ddl_words = set(re.findall(r'\b\w+\b', ddl_context))
        
        if question_words and ddl_words:
            intersection = question_words.intersection(ddl_words)
            relevance_score += len(intersection) / len(question_words)
            total_items += 1
    
    # 检查描述相关性
    if 'desc_context' in retrieval_data:
        desc_context = retrieval_data['desc_context'].lower()
        question_words = set(re.findall(r'\b\w+\b', question_lower))
        desc_words = set(re.findall(r'\b\w+\b', desc_context))
        
        if question_words and desc_words:
            intersection = question_words.intersection(desc_words)
            relevance_score += len(intersection) / len(question_words)
            total_items += 1
    
    return relevance_score / total_items if total_items > 0 else 0.0

# 计算生成器上下文利用度
def calculate_context_utilization(generated_sql: str, retrieval_data: Dict) -> float:
    """计算生成器上下文利用度"""
    if not generated_sql or not retrieval_data:
        return 0.0
    
    sql_lower = generated_sql.lower()
    utilization_score = 0.0
    total_context = 0
    
    # 检查是否使用了DDL中的表名
    if 'ddl_context' in retrieval_data:
        ddl_context = retrieval_data['ddl_context'].lower()
        # 提取DDL中的表名
        table_names = re.findall(r'create\s+table\s+(\w+)', ddl_context)
        used_tables = 0
        
        for table_name in table_names:
            if table_name in sql_lower:
                used_tables += 1
        
        if table_names:
            utilization_score += used_tables / len(table_names)
            total_context += 1
    
    # 检查是否使用了描述中的列名
    if 'desc_context' in retrieval_data:
        desc_context = retrieval_data['desc_context'].lower()
        # 提取列名
        column_names = re.findall(r'(\w+):', desc_context)
        used_columns = 0
        
        for column_name in column_names:
            if column_name in sql_lower:
                used_columns += 1
        
        if column_names:
            utilization_score += used_columns / len(column_names)
            total_context += 1
    
    return utilization_score / total_context if total_context > 0 else 0.0

# 创建表（如果不存在）
def create_table_if_not_exists(engine):
    """创建evaluation_metrics表（如果不存在）"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS evaluation_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        question TEXT NOT NULL COMMENT '问题内容',
        rag_retrieval_data JSON COMMENT 'RAG检索结果数据',
        gold_standard_data JSON COMMENT '黄金标准数据',
        execution_accuracy DECIMAL(5,4) COMMENT '执行准确率',
        exact_match_rate DECIMAL(5,4) COMMENT '精确匹配率',
        component_match_rate DECIMAL(5,4) COMMENT '组件匹配率 / SQL-F1值',
        retrieval_relevance DECIMAL(5,4) COMMENT '检索相关性',
        context_utilization DECIMAL(5,4) COMMENT '生成器上下文利用度',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG系统评估指标表'
    """
    
    try:
        logging.info("🔧 开始创建表...")
        with engine.connect() as conn:
            # 先测试数据库连接
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            logging.info(f"🔗 数据库连接测试成功: {test_value}")
            
            # 检查当前数据库
            result = conn.execute(text("SELECT DATABASE()"))
            db_name = result.fetchone()[0]
            logging.info(f"📊 当前数据库: {db_name}")
            
            # 检查表是否已存在
            result = conn.execute(text("SHOW TABLES LIKE 'evaluation_metrics'"))
            table_exists = result.fetchone()
            if table_exists:
                logging.info("✅ 表 evaluation_metrics 已存在")
                
                # 查看现有表结构
                result = conn.execute(text("DESCRIBE evaluation_metrics"))
                columns = result.fetchall()
                logging.info("📋 现有表结构:")
                for col in columns:
                    logging.info(f"  - {col[0]}: {col[1]} {col[2] if col[2] else ''}")
            else:
                logging.info("📝 表 evaluation_metrics 不存在，开始创建...")
                
                # 创建表
                conn.execute(text(create_table_sql))
                conn.commit()
                logging.info("✅ 表创建成功")
                
                # 验证表是否创建成功
                result = conn.execute(text("SHOW TABLES LIKE 'evaluation_metrics'"))
                if result.fetchone():
                    logging.info("✅ 表 evaluation_metrics 创建确认成功")
                    
                    # 查看新创建的表结构
                    result = conn.execute(text("DESCRIBE evaluation_metrics"))
                    columns = result.fetchall()
                    logging.info("📋 新创建的表结构:")
                    for col in columns:
                        logging.info(f"  - {col[0]}: {col[1]} {col[2] if col[2] else ''}")
                else:
                    logging.error("❌ 表 evaluation_metrics 创建失败")
                    return False
                
        return True
    except Exception as e:
        logging.error(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# 保存结果到数据库
def save_to_database(question: str, rag_retrieval_data: str, gold_standard_data: str,
                    exact_match_rate: float, retrieval_relevance: float, 
                    context_utilization: float):
    """保存评估结果到数据库"""
    try:
        logging.info("🚀 开始保存数据到数据库...")
        logging.info(f"📊 数据库URL: {DB_URL}")
        
        # 创建数据库引擎
        engine = create_engine(DB_URL, echo=True)  # 开启SQL日志
        
        # 确保表存在
        logging.info("🔧 检查并创建表...")
        if not create_table_if_not_exists(engine):
            logging.error("❌ 无法创建或验证表")
            return False
        
        # 准备插入数据
        insert_data = {
            'question': question,
            'rag_retrieval_data': json.dumps(rag_retrieval_data, ensure_ascii=False),  # 始终序列化为JSON
            'gold_standard_data': json.dumps(gold_standard_data, ensure_ascii=False),  # 始终序列化为JSON
            'execution_accuracy': 0.0,  # 设置为0，不再计算
            'exact_match_rate': float(exact_match_rate),
            'component_match_rate': 0.0,  # 设置为0，不再计算
            'retrieval_relevance': float(retrieval_relevance),
            'context_utilization': float(context_utilization)
        }
        
        logging.info(f"📊 准备插入的数据:")
        for key, value in insert_data.items():
            if key in ['rag_retrieval_data', 'gold_standard_data']:
                logging.info(f"  {key}: {type(value)} (长度: {len(str(value))})")
            else:
                logging.info(f"  {key}: {value} ({type(value)})")
        
        # 插入数据
        insert_sql = """
        INSERT INTO evaluation_metrics (
            question, rag_retrieval_data, gold_standard_data,
            execution_accuracy, exact_match_rate, component_match_rate,
            retrieval_relevance, context_utilization
        ) VALUES (
            :question, :rag_retrieval_data, :gold_standard_data,
            :execution_accuracy, :exact_match_rate, :component_match_rate,
            :retrieval_relevance, :context_utilization
        )
        """
        
        with engine.connect() as conn:
            logging.info("🧪 开始执行插入操作...")
            
            try:
                # 执行插入
                logging.info(f"🔍 执行SQL: {insert_sql}")
                logging.info(f"🔍 插入数据: {insert_data}")
                
                result = conn.execute(text(insert_sql), insert_data)
                conn.commit()
                
                # 获取插入的ID
                inserted_id = result.lastrowid
                logging.info(f"✅ 数据插入成功，ID: {inserted_id}")
                
                # 验证插入
                result = conn.execute(text("SELECT COUNT(*) FROM evaluation_metrics"))
                count = result.fetchone()[0]
                logging.info(f"📊 当前表中总记录数: {count}")
                
                # 查看刚插入的记录
                result = conn.execute(text("SELECT * FROM evaluation_metrics WHERE id = :id"), {"id": inserted_id})
                inserted_record = result.fetchone()
                if inserted_record:
                    logging.info(f"📋 插入的记录: {inserted_record}")
                else:
                    logging.warning("⚠️ 无法找到刚插入的记录")
                    
            except Exception as insert_error:
                logging.error(f"❌ 插入操作失败: {insert_error}")
                logging.error(f"❌ 插入SQL: {insert_sql}")
                logging.error(f"❌ 插入数据: {insert_data}")
                conn.rollback()
                raise insert_error
        
        logging.info("✅ 评估结果已成功保存到数据库")
        return True
        
    except Exception as e:
        logging.error(f"❌ 保存到数据库失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 尝试更详细的错误信息
        try:
            engine = create_engine(DB_URL)
            with engine.connect() as conn:
                # 检查表是否存在
                result = conn.execute(text("SHOW TABLES LIKE 'evaluation_metrics'"))
                if not result.fetchone():
                    logging.error("❌ 表 evaluation_metrics 不存在")
                else:
                    logging.info("✅ 表 evaluation_metrics 存在")
                    
                    # 检查表结构
                    result = conn.execute(text("DESCRIBE evaluation_metrics"))
                    columns = result.fetchall()
                    logging.info("📋 表结构:")
                    for col in columns:
                        logging.info(f"  - {col[0]}: {col[1]} {col[2] if col[2] else ''}")
        except Exception as debug_e:
            logging.error(f"❌ 调试信息获取失败: {debug_e}")
        
        return False

# API端点
@router.post("/submit", response_model=GeneratorEvaluationResponse)
async def submit_generator_evaluation(
    system_type: str = Form(...),
    generation_sub_type: str = Form(...),
    question: str = Form(...),
    standard_list: UploadFile = File(...)
):
    """提交RAG生成器评估"""
    try:
        # 验证参数
        if not question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        if generation_sub_type != "txt2sql":
            raise HTTPException(status_code=400, detail="目前只支持txt2SQL生成子类型")
        
        # 读取上传的标准化生成列表
        file_content = await standard_list.read()
        standard_data = parse_standard_list(file_content.decode('utf-8'), question)
        
        logging.info(f"解析的标准化数据: {type(standard_data)} - {standard_data}")
        
        if not standard_data:
            raise HTTPException(status_code=400, detail="无法解析标准化生成列表文件")
        
        # 初始化Milvus连接
        if not init_milvus_connection():
            raise HTTPException(status_code=500, detail="无法连接到向量数据库")
        
        # 生成问题嵌入
        query_embedding = get_silicon_flow_embedding(question)
        if query_embedding is None:
            raise HTTPException(status_code=500, detail="生成问题嵌入失败")
        
        # 检索DDL信息
        ddl_hits = retrieve(COLLECTION_DDL, query_embedding, top_k=3, output_fields=["ddl_text"])
        logging.info(f"DDL检索结果: {len(ddl_hits)} 条")
        ddl_results = []
        for i, hit in enumerate(ddl_hits):
            logging.info(f"DDL hit {i}: {type(hit)} - {hit}")
            entity = hit.get("entity", {})
            logging.info(f"DDL entity {i}: {type(entity)} - {entity}")
            if isinstance(entity, dict) and entity.get("ddl_text"):
                ddl_results.append(entity["ddl_text"])
        ddl_context = "\n".join(ddl_results)
        
        # 检索问答示例
        q2sql_hits = retrieve(COLLECTION_Q2SQL, query_embedding, top_k=3, output_fields=["question", "sql_text"])
        logging.info(f"Q2SQL检索结果: {len(q2sql_hits)} 条")
        example_results = []
        for i, hit in enumerate(q2sql_hits):
            logging.info(f"Q2SQL hit {i}: {type(hit)} - {hit}")
            entity = hit.get("entity", {})
            logging.info(f"Q2SQL entity {i}: {type(entity)} - {entity}")
            if isinstance(entity, dict) and entity.get("question") and entity.get("sql_text"):
                example_results.append(f"NL: \"{entity['question']}\"\nSQL: \"{entity['sql_text']}\"")
        example_context = "\n".join(example_results)
        
        # 检索数据库描述信息
        desc_hits = retrieve(COLLECTION_DBDESC, query_embedding, top_k=8, output_fields=["table_name", "column_name", "description"])
        logging.info(f"描述检索结果: {len(desc_hits)} 条")
        desc_results = []
        for i, hit in enumerate(desc_hits):
            logging.info(f"描述 hit {i}: {type(hit)} - {hit}")
            entity = hit.get("entity", {})
            logging.info(f"描述 entity {i}: {type(entity)} - {entity}")
            if isinstance(entity, dict) and entity.get("table_name"):
                desc_results.append(f"{entity['table_name']}.{entity.get('column_name', '')}: {entity.get('description', '')}")
        desc_context = "\n".join(desc_results)
        
        # 构建检索上下文数据（用于计算检索相关性和上下文利用度）
        retrieval_context_data = {
            "ddl_context": ddl_context,
            "example_context": example_context,
            "desc_context": desc_context,
            "ddl_hits_count": len(ddl_hits),
            "q2sql_hits_count": len(q2sql_hits),
            "desc_hits_count": len(desc_hits)
        }
        
        # 构建生成器输出结果
        generation_output = f"""生成问题: {question}

检索到的上下文:
DDL结构信息:
{ddl_context}

问答示例:
{example_context}

字段描述信息:
{desc_context}

检索到的文档数量: DDL={len(ddl_hits)}, 示例={len(q2sql_hits)}, 描述={len(desc_hits)}"""
        
        # 组装提示词并生成SQL
        system_prompt = """你是一个专业的SQL生成助手。请根据提供的数据库结构、字段描述和示例，将自然语言查询转换为准确的SQL语句。

请严格遵循以下要求：
1. 只返回SQL语句，不要包含任何解释或说明
2. 确保SQL语法正确
3. 使用提供的表名和字段名
4. 如果问题涉及日期范围，请使用合适的日期函数
5. 如果需要连接多个表，请确保连接条件正确
6. 注意：Sakila数据库中的演员表是actor，不是actors"""

        user_prompt = (
            f"### 数据库结构定义:\n{ddl_context}\n\n"
            f"### 字段描述:\n{desc_context}\n\n"
            f"### 示例查询:\n{example_context}\n\n"
            f"### 用户查询:\n{question}\n\n"
            f"请生成对应的SQL查询语句："
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 调用大模型生成SQL
        raw_sql = siliconflow_chat_completion(messages, temperature=0.1)
        if raw_sql is None:
            raise HTTPException(status_code=500, detail="SQL生成失败")
        
        generated_sql = extract_sql(raw_sql)
        if not generated_sql:
            raise HTTPException(status_code=500, detail="未能提取到有效的SQL语句")
        
        # rag_retrieval_data 只存储生成的SQL语句
        rag_retrieval_data = generated_sql
        
        # 更新生成器输出结果
        generation_output += f"""

生成的SQL语句:
{generated_sql}

执行结果: 成功生成SQL语句"""
        
        # 从标准化列表中获取黄金标准数据
        logging.info(f"获取黄金标准数据，standard_data类型: {type(standard_data)}")
        if isinstance(standard_data, dict):
            gold_standard_sql = standard_data.get("sql", "")
        else:
            logging.error(f"standard_data不是字典类型: {type(standard_data)}")
            gold_standard_sql = ""
        
        # gold_standard_data 只存储SQL语句本身
        gold_standard_data = gold_standard_sql
        
        # 计算评估指标（去掉执行准确率和SQL-F1值）
        exact_match_rate = calculate_exact_match_rate(generated_sql, gold_standard_sql)
        retrieval_relevance = calculate_retrieval_relevance(question, retrieval_context_data)
        context_utilization = calculate_context_utilization(generated_sql, retrieval_context_data)
        
        # 保存到数据库
        save_success = save_to_database(
            question, rag_retrieval_data, gold_standard_data,
            exact_match_rate, retrieval_relevance, context_utilization
        )
        
        if not save_success:
            logging.error("❌ 数据库保存失败")
            raise HTTPException(status_code=500, detail="数据库保存失败")
        
        # 返回结果
        return GeneratorEvaluationResponse(
            success=True,
            message="评估完成",
            generation_results=generation_output,
            evaluation_metrics={
                "exact_match_rate": exact_match_rate,
                "retrieval_relevance": retrieval_relevance,
                "context_utilization": context_utilization
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"评估过程中发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")
    finally:
        # 断开Milvus连接
        try:
            connections.disconnect("default")
        except:
            pass
