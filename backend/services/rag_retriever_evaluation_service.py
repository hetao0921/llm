#!/usr/bin/env python3
"""
RAG系统检索器评估服务
"""

import os
import logging
import requests
import json
import yaml
import re
from typing import List, Dict, Any, Set
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

# Milvus 连接配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "10.128.15.221")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
DATABASE_NAME = os.getenv("MILVUS_DB_NAME", "text2sql_milvus_sakila_hetao")

# 集合名称
COLLECTION_DDL = "ddl_knowledge"
COLLECTION_DBDESC = "dbdesc_knowledge"

# 数据库连接配置
DB_URL = "mysql+pymysql://root:Rzx#1218@10.128.15.5:3306/rag_learn"

# 创建路由器
router = APIRouter()

# 请求模型
class RetrieverEvaluationRequest(BaseModel):
    system_type: str
    retrieval_sub_type: str
    question: str

class RetrieverEvaluationResponse(BaseModel):
    success: bool
    message: str
    retrieval_results: str
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

# 表名提取函数
def extract_table_names_from_ddl(text: str) -> Set[str]:
    """从DDL语句中提取表名和视图名"""
    if not text:
        return set()
    
    found_tables = set()
    text_lower = text.lower()
    
    # 匹配CREATE TABLE语句中的表名
    table_pattern = r'create\s+table\s+(?:if\s+not\s+exists\s+)?`?(\w+)`?'
    table_matches = re.findall(table_pattern, text_lower)
    found_tables.update(table_matches)
    
    # 匹配所有VIEW语句中的视图名
    view_pattern = r'(?:definer\s+)?view\s+`?(\w+)`?'
    view_matches = re.findall(view_pattern, text_lower)
    found_tables.update(view_matches)
    
    return found_tables

def extract_table_names_from_description(text: str) -> Set[str]:
    """从数据库描述中提取表名"""
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

def extract_table_names_as_string(text: str, is_ddl: bool = True) -> str:
    """从文本中提取表名，返回逗号分隔的字符串"""
    if is_ddl:
        tables = extract_table_names_from_ddl(text)
    else:
        tables = extract_table_names_from_description(text)
    return ",".join(sorted(tables)) if tables else ""

def count_table_names(text: str, is_ddl: bool = True) -> int:
    """统计文本中的表名数量"""
    if is_ddl:
        return len(extract_table_names_from_ddl(text))
    else:
        return len(extract_table_names_from_description(text))

# 获取总数函数
def get_ddl_total_count():
    """获取DDL语句总数"""
    ddl_file = "F:\\llm\\code\\rag-new-project001\\data\\ddl_statements.yaml"
    try:
        with open(ddl_file, 'r', encoding='utf-8') as f:
            ddl_data = yaml.safe_load(f)
        return len(ddl_data) if ddl_data else 0
    except Exception as e:
        logging.error(f"❌ 读取DDL文件失败: {e}")
        return 0

def get_db_desc_total_count():
    """获取数据库描述总数"""
    db_desc_file = "F:\\llm\\code\\rag-new-project001\\data\\db_description.yaml"
    try:
        with open(db_desc_file, 'r', encoding='utf-8') as f:
            db_desc_data = yaml.safe_load(f)
        return len(db_desc_data) if db_desc_data else 0
    except Exception as e:
        logging.error(f"❌ 读取数据库描述文件失败: {e}")
        return 0

# 解析上传的标准化检索列表
def parse_standard_list(file_content: str) -> Dict[str, str]:
    """解析标准化检索列表文件"""
    try:
        # 尝试解析为JSON
        try:
            data = json.loads(file_content)
            return data
        except json.JSONDecodeError:
            pass
        
        # 尝试解析为YAML
        try:
            data = yaml.safe_load(file_content)
            return data
        except yaml.YAMLError:
            pass
        
        # 尝试解析为简单的键值对格式
        lines = file_content.strip().split('\n')
        result = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        return result
        
    except Exception as e:
        logging.error(f"解析标准化检索列表失败: {e}")
        return {}

# 计算评估指标
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

# 保存结果到数据库
def save_to_database(question: str, standard_answer: str, rag_ddl: str, rag_desc: str,
                    rag_ddl_extracted: str, rag_desc_extracted: str,
                    rag_ddl_stats: int, rag_desc_stats: int,
                    gold_ddl: str, gold_desc: str,
                    gold_ddl_extracted: str, gold_desc_extracted: str,
                    gold_ddl_stats: int, gold_desc_stats: int,
                    ddl_include_stats: int, desc_include_stats: int,
                    ddl_equal_stats: int, desc_equal_stats: int,
                    topk_value: int, recall: float, precision: float, 
                    accuracy: float, f2_score: float):
    """保存评估结果到数据库"""
    try:
        engine = create_engine(DB_URL)
        
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
        
        with engine.connect() as conn:
            conn.execute(text(insert_sql), {
                'question': question,
                'standard_answer': standard_answer,
                'rag_ddl': rag_ddl,
                'rag_ddl_extracted_value': rag_ddl_extracted,
                'rag_db_description': rag_desc,
                'rag_db_desc_extracted_value': rag_desc_extracted,
                'rag_ddl_statistics': rag_ddl_stats,
                'rag_db_desc_statistics': rag_desc_stats,
                'standard_ddl': gold_ddl,
                'standard_ddl_extracted_value': gold_ddl_extracted,
                'standard_db_desc': gold_desc,
                'standard_db_desc_extracted_value': gold_desc_extracted,
                'standard_ddl_statistics': gold_ddl_stats,
                'standard_db_desc_statistics': gold_desc_stats,
                'ddl_include_statistics': ddl_include_stats,
                'db_desc_include_statistics': desc_include_stats,
                'ddl_equal_statistics': ddl_equal_stats,
                'db_desc_equal_statistics': desc_equal_stats,
                'topk_value': topk_value,
                'recall': recall,
                'precisions': precision,
                'accuracy': accuracy,
                'f2_score': f2_score
            })
            conn.commit()
        
        logging.info("✅ 评估结果已保存到数据库")
        return True
        
    except Exception as e:
        logging.error(f"❌ 保存到数据库失败: {e}")
        return False

# API端点
@router.post("/submit", response_model=RetrieverEvaluationResponse)
async def submit_retriever_evaluation(
    system_type: str = Form(...),
    retrieval_sub_type: str = Form(...),
    question: str = Form(...),
    standard_list: UploadFile = File(...)
):
    """提交RAG检索器评估"""
    try:
        # 验证参数
        if not question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        if retrieval_sub_type != "txt2sql":
            raise HTTPException(status_code=400, detail="目前只支持txt2SQL检索子类型")
        
        # 读取上传的标准化检索列表
        file_content = await standard_list.read()
        standard_data = parse_standard_list(file_content.decode('utf-8'))
        
        if not standard_data:
            raise HTTPException(status_code=400, detail="无法解析标准化检索列表文件")
        
        # 初始化Milvus连接
        if not init_milvus_connection():
            raise HTTPException(status_code=500, detail="无法连接到向量数据库")
        
        # 生成问题嵌入
        query_embedding = get_silicon_flow_embedding(question)
        if query_embedding is None:
            raise HTTPException(status_code=500, detail="生成问题嵌入失败")
        
        # 检索DDL信息
        ddl_hits = retrieve(COLLECTION_DDL, query_embedding, top_k=3, output_fields=["ddl_text"])
        ddl_results = []
        for hit in ddl_hits:
            entity = hit.get("entity", {})
            if isinstance(entity, dict) and entity.get("ddl_text"):
                ddl_results.append(entity["ddl_text"])
        ddl_context = "\n".join(ddl_results)
        
        # 检索数据库描述信息
        desc_hits = retrieve(COLLECTION_DBDESC, query_embedding, top_k=3, output_fields=["table_name", "column_name", "description"])
        desc_results = []
        for hit in desc_hits:
            entity = hit.get("entity", {})
            if isinstance(entity, dict) and entity.get("table_name"):
                desc_results.append(f"{entity['table_name']}.{entity.get('column_name', '')}: {entity.get('description', '')}")
        desc_context = "\n".join(desc_results)
        
        # 构建检索结果输出
        retrieval_output = f"""检索问题: {question}

DDL结构信息:
{ddl_context}

数据库描述信息:
{desc_context}

检索到的文档数量: DDL={len(ddl_hits)}, 描述={len(desc_hits)}"""
        
        # 提取表名和统计
        rag_ddl_extracted = extract_table_names_as_string(ddl_context, is_ddl=True)
        rag_desc_extracted = extract_table_names_as_string(desc_context, is_ddl=False)
        rag_ddl_stats = 1 if count_table_names(ddl_context, is_ddl=True) > 0 else 0
        rag_desc_stats = 1 if count_table_names(desc_context, is_ddl=False) > 0 else 0
        
        # 从标准化列表中提取黄金标准数据
        gold_ddl = standard_data.get("ddl", "")
        gold_desc = standard_data.get("description", "")
        gold_ddl_extracted = extract_table_names_as_string(gold_ddl, is_ddl=True)
        gold_desc_extracted = extract_table_names_as_string(gold_desc, is_ddl=False)
        gold_ddl_stats = 1 if count_table_names(gold_ddl, is_ddl=True) > 0 else 0
        gold_desc_stats = 1 if count_table_names(gold_desc, is_ddl=False) > 0 else 0
        
        # 计算包含统计
        rag_ddl_tables = extract_table_names_from_ddl(ddl_context)
        rag_desc_tables = extract_table_names_from_description(desc_context)
        gold_ddl_tables = extract_table_names_from_ddl(gold_ddl)
        gold_desc_tables = extract_table_names_from_description(gold_desc)
        
        ddl_include_count = len(rag_ddl_tables.intersection(gold_ddl_tables)) if gold_ddl_tables else 0
        desc_include_count = len(rag_desc_tables.intersection(gold_desc_tables)) if gold_desc_tables else 0
        
        ddl_include_stats = 1 if ddl_include_count > 0 else 0
        desc_include_stats = 1 if desc_include_count > 0 else 0
        
        # 计算相等统计
        ddl_equal_stats = 1 if rag_ddl_tables == gold_ddl_tables and rag_ddl_tables else 0
        desc_equal_stats = 1 if rag_desc_tables == gold_desc_tables and rag_desc_tables else 0
        
        # 获取总数
        ddl_total = get_ddl_total_count()
        db_desc_total = get_db_desc_total_count()
        
        # 计算评估指标
        recall, precision, accuracy, f2_score = calculate_metrics(
            ddl_include_count, desc_include_count,
            gold_ddl_stats, gold_desc_stats,
            rag_ddl_stats, rag_desc_stats,
            ddl_total, db_desc_total, 3  # topk_value = 3
        )
        
        # 保存到数据库
        save_to_database(
            question, "", ddl_context, desc_context,
            rag_ddl_extracted, rag_desc_extracted,
            rag_ddl_stats, rag_desc_stats,
            gold_ddl, gold_desc,
            gold_ddl_extracted, gold_desc_extracted,
            gold_ddl_stats, gold_desc_stats,
            ddl_include_stats, desc_include_stats,
            ddl_equal_stats, desc_equal_stats,
            3, recall, precision, accuracy, f2_score
        )
        
        # 返回结果
        return RetrieverEvaluationResponse(
            success=True,
            message="评估完成",
            retrieval_results=retrieval_output,
            evaluation_metrics={
                "recall_rate": recall,
                "precision_rate": precision,
                "accuracy_rate": accuracy,
                "f2_score": f2_score
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
