import re
import os
import uuid
import hashlib
import requests
import chromadb
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from pathlib import Path
import torch
from .finterm_ner_service import get_recognizer, extract_entities_with_rule_engine, FINTERM_CATEGORIES

router = APIRouter()

# chromadb 本地持久化路径
CHROMA_DB_PATH = str((Path(__file__).parent.parent / 'data' / 'chromadb'/ 'finterm_db').resolve())

# 模型配置
DEFAULT_MODELS = {
    # 维度模型
    "dimension_1024": {
        "provider": "siliconflow",
        "model_name": "BAAI/bge-m3"  # 默认使用BAAI/bge-m3模型
    },
    # 384维模型（作为备选）
    "dimension_384": {
        "provider": "siliconflow",
        "model_name": "netease-youdao/bce-embedding-base_v1"  # 使用API支持的384维模型
    },
    # 1024维备选模型
    "dimension_1024_alt": {
        "provider": "siliconflow",
        "model_name": "BAAI/bge-large-zh-v1.5"
    }
}

def get_embedding(model_name: str, text: str, provider: str = 'siliconflow'):
    """调用向量化API，返回embedding，支持多provider扩展"""
    # 确保有默认值
    if not model_name:
        model_name = DEFAULT_MODELS["dimension_1024"]["model_name"]
    if not provider:
        provider = DEFAULT_MODELS["dimension_1024"]["provider"]
    
    try:
        if provider == 'siliconflow':
            url = "https://api.siliconflow.cn/v1/embeddings"
            headers = {
                "Authorization": "Bearer sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "input": text
            }
            print(f"正在使用模型 {model_name} 获取文本向量...")
            resp = requests.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                embedding = resp.json().get('data', [{}])[0].get('embedding', [])
                print(f"成功获取向量，维度: {len(embedding)}")
                return embedding
            else:
                print(f"API调用失败: {resp.status_code} {resp.text}")
                return []
        # 可扩展其他provider
        return []
    except Exception as e:
        print(f"获取向量失败: {e}")
        return []

def get_collection_dimension(collection_name):
    """获取集合中向量的维度"""
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
        # 检查集合是否存在
        collection_names = [c.name for c in chroma_client.list_collections()]
        if collection_name not in collection_names:
            print(f"集合不存在: {collection_name}")
            return None
        
        # 获取集合
        collection = chroma_client.get_collection(name=collection_name)
        
        # 获取集合中的条目数
        print("尝试获取集合数据，明确包含embeddings...")
        collection_data = collection.get(include=["embeddings", "metadatas", "documents"])
        
        # 打印调试信息
        print(f"集合数据获取结果:")
        print(f"- 获取的IDs数量: {len(collection_data['ids']) if 'ids' in collection_data else 0}")
        print(f"- 获取的documents数量: {len(collection_data['documents']) if 'documents' in collection_data else 0}")
        print(f"- 获取的metadatas数量: {len(collection_data['metadatas']) if 'metadatas' in collection_data else 0}")
        print(f"- 获取的embeddings数量: {len(collection_data['embeddings']) if 'embeddings' in collection_data else 0}")
        
        # 检查是否有嵌入向量
        if collection_data and 'embeddings' in collection_data and collection_data["embeddings"] and len(collection_data["embeddings"]) > 0:
            first_embedding = collection_data["embeddings"][0]
            dimension = len(first_embedding)
            print(f"集合 {collection_name} 中向量维度为: {dimension}")
            
            # 检查向量数量
            embedding_count = len(collection_data["embeddings"])
            print(f"集合中共有 {embedding_count} 个向量")
            
            return dimension
        else:
            if collection_data and 'ids' in collection_data and len(collection_data['ids']) > 0:
                print(f"警告: 集合中有 {len(collection_data['ids'])} 条记录，但没有embeddings数据")
                
                # 尝试使用其他方法获取维度信息
                try:
                    # 尝试使用peek方法
                    peek_data = collection.peek(10)
                    print(f"尝试使用peek方法检查: {peek_data}")
                    
                    # 尝试直接查询
                    query_result = collection.query(
                        query_texts=["test query"],
                        n_results=1
                    )
                    print(f"查询测试结果: {query_result}")
                except Exception as peek_error:
                    print(f"额外检查失败: {peek_error}")
            
            print(f"集合 {collection_name} 中没有向量数据")
            return None
    except Exception as e:
        print(f"检查集合维度时出错: {e}")
        return None

def find_similar_terms(text: str, model_name: str, provider: str, db_type: str, index_type: str, collection_name: str):
    """查找相似的标准术语"""
    try:
        # 如果模型名称为空，使用默认的BAAI/bge-m3模型
        if not model_name:
            print("未指定模型，使用默认BAAI/bge-m3模型")
            model_name = DEFAULT_MODELS["dimension_1024"]["model_name"]
            provider = DEFAULT_MODELS["dimension_1024"]["provider"]
            
        # 连接向量数据库
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
        # 检查集合是否存在
        collection_names = [c.name for c in chroma_client.list_collections()]
        if collection_name not in collection_names:
            print(f"集合不存在: {collection_name}")
            return None
        
        # 在获取向量前先检查集合维度
        collection_dimension = get_collection_dimension(collection_name)
        if collection_dimension:
            print(f"查询前检测到集合维度为: {collection_dimension}")
            
            # 根据集合维度选择合适的模型
            original_model = model_name
            if collection_dimension == 384:
                print(f"集合使用384维向量，尝试自动选择适配模型")
                if "bge-small" not in model_name.lower():
                    model_name = DEFAULT_MODELS["dimension_384"]["model_name"]
                    provider = DEFAULT_MODELS["dimension_384"]["provider"]
                    print(f"自动从 {original_model} 切换到适配模型: {model_name}")
            elif collection_dimension == 1024:
                print(f"集合使用1024维向量，尝试自动选择适配模型")
                if "bge-m3" not in model_name.lower() and "bge-large" not in model_name.lower():
                    model_name = DEFAULT_MODELS["dimension_1024"]["model_name"]
                    provider = DEFAULT_MODELS["dimension_1024"]["provider"]
                    print(f"自动从 {original_model} 切换到适配模型: {model_name}")
            else:
                print(f"集合使用 {collection_dimension} 维向量，无法确定适配模型")
            
        # 获取集合
        collection = chroma_client.get_collection(name=collection_name)
        
        # 获取文本的向量表示
        embedding = get_embedding(model_name, text, provider)
        if not embedding:
            print(f"无法获取文本的向量表示: {text}")
            return None
            
        # 处理维度不匹配问题
        try:
            # 查询相似度最高的记录
            results = collection.query(
                query_embeddings=[embedding],
                n_results=1
            )
            
            if not results or not results.get('metadatas') or not results['metadatas'][0]:
                return None
                
            # 返回最相似的记录
            return results['metadatas'][0][0]
        except Exception as vector_error:
            if "dimension" in str(vector_error).lower():
                print(f"向量维度不匹配: {vector_error}")
                print(f"当前模型 {model_name} 的向量维度与集合中的向量维度不一致")
                print("尝试使用匹配维度的模型重新查询...")
                
                # 智能切换模型维度：从错误消息中提取需要的维度
                error_msg = str(vector_error)
                try:
                    # 从错误信息中提取维度数字
                    import re
                    dimension_match = re.search(r'collection dimensionality (\d+)', error_msg)
                    if dimension_match:
                        required_dim = int(dimension_match.group(1))
                        print(f"检测到集合需要维度为 {required_dim} 的向量")
                        
                        # 选择匹配维度的模型
                        matching_model = None
                        matching_provider = None
                        
                        if required_dim == 384:
                            # 使用384维模型
                            print("尝试切换到384维模型")
                            matching_model = DEFAULT_MODELS["dimension_384"]["model_name"]
                            matching_provider = DEFAULT_MODELS["dimension_384"]["provider"]
                        elif required_dim == 1024:
                            # 使用1024维模型
                            print("尝试切换到1024维模型")
                            matching_model = DEFAULT_MODELS["dimension_1024"]["model_name"]
                            matching_provider = DEFAULT_MODELS["dimension_1024"]["provider"]
                        else:
                            # 未知维度，尝试所有可用模型
                            print(f"未知维度: {required_dim}，尝试可用的模型")
                            for model_key in DEFAULT_MODELS:
                                try:
                                    print(f"尝试模型: {DEFAULT_MODELS[model_key]['model_name']}")
                                    test_embedding = get_embedding(
                                        DEFAULT_MODELS[model_key]['model_name'],
                                        text,
                                        DEFAULT_MODELS[model_key]['provider']
                                    )
                                    if test_embedding and len(test_embedding) == required_dim:
                                        matching_model = DEFAULT_MODELS[model_key]['model_name']
                                        matching_provider = DEFAULT_MODELS[model_key]['provider']
                                        print(f"找到匹配维度的模型: {matching_model}")
                                        break
                                except Exception as model_error:
                                    print(f"尝试模型 {DEFAULT_MODELS[model_key]['model_name']} 失败: {model_error}")
                                    continue
                        
                        if matching_model:
                            print(f"自动切换到适配模型: {matching_model}")
                            # 重新获取向量并查询
                            embedding = get_embedding(matching_model, text, matching_provider)
                            if embedding and len(embedding) > 0:
                                # 确认获取的向量维度符合要求
                                if len(embedding) == required_dim:
                                    print(f"成功获取匹配维度的向量: {len(embedding)}")
                                    try:
                                        results = collection.query(
                                            query_embeddings=[embedding],
                                            n_results=1
                                        )
                                        
                                        if results and results.get('metadatas') and results['metadatas'][0]:
                                            return results['metadatas'][0][0]
                                    except Exception as query_error:
                                        print(f"使用匹配维度的向量查询失败: {query_error}")
                                else:
                                    print(f"获取的向量维度 {len(embedding)} 与所需维度 {required_dim} 不符")
                            else:
                                print(f"无法获取模型 {matching_model} 的向量")
                        else:
                            print(f"未找到匹配维度 {required_dim} 的模型")
                except Exception as parse_error:
                    print(f"解析维度失败: {parse_error}")
                
                print("尝试使用不依赖向量的方式查找...")
                
                # 退回到基于关键词的匹配方式
                # 这里使用一个简单的方法：检索所有文档并进行字符串匹配
                try:
                    # 获取集合中所有数据
                    all_data = collection.get()
                    if not all_data or not all_data.get('metadatas'):
                        return None
                        
                    # 简单字符串匹配 (在生产环境中应使用更复杂的算法)
                    best_match = None
                    best_score = -1
                    
                    for i, metadata in enumerate(all_data['metadatas']):
                        # 简单相似度计算 - 字符重叠率
                        norm_term = metadata.get('finterm_normalization', '').lower()
                        if not norm_term:
                            continue
                            
                        text_lower = text.lower()
                        # 计算简单的相似度分数
                        common = set(text_lower) & set(norm_term)
                        if not common:
                            continue
                            
                        score = len(common) / max(len(text_lower), len(norm_term))
                        if score > best_score:
                            best_score = score
                            best_match = metadata
                    
                    if best_score > 0.3:  # 设置一个最低相似度阈值
                        return best_match
                except Exception as fallback_error:
                    print(f"备用匹配方法也失败: {fallback_error}")
            else:
                print(f"查询失败: {vector_error}")
            return None
    except Exception as e:
        print(f"查询相似术语出错: {e}")
        return None

@router.post("/normalize")
async def normalize_finterm(
    request: Dict = Body(...)
) -> Dict[str, Any]:
    """
    执行金融术语标准化
    
    - text: 输入文本
    - classifications: 术语分类列表
    - model_provider: 嵌入式模型供应商
    - model_name: 嵌入式模型名称
    - db_type: 向量数据库类型
    - index_type: 索引类型
    - collection_name: 集合名称
    """
    try:
        # 获取请求参数
        text = request.get('text', '')
        classifications = request.get('classifications', [])
        model_provider = request.get('model_provider', DEFAULT_MODELS["dimension_1024"]["provider"])
        model_name = request.get('model_name', DEFAULT_MODELS["dimension_1024"]["model_name"])
        db_type = request.get('db_type', 'chromadb')
        index_type = request.get('index_type', 'hnsw')
        collection_name = request.get('collection_name', 'my_finterm_collection')
        
        # 打印选择的模型信息
        print(f"使用模型: {model_name}, 提供商: {model_provider}")
        print(f"向量数据库: {db_type}, 索引: {index_type}, 集合: {collection_name}")
        
        if not text:
            raise HTTPException(status_code=400, detail="请提供输入文本")
            
        # 实体识别结果
        identified_entities = []
        
        # 1. 使用NER模型识别实体
        recognizer = get_recognizer()
        if recognizer:
            # 使用NER模型识别实体
            predicted_terms = recognizer.predict(text, min_confidence=0.6)
            for term_info in predicted_terms:
                term = term_info["term"]
                confidence = term_info["confidence"]
                start_pos = term_info["start_pos"]
                end_pos = term_info["end_pos"]
                entity_type = term_info.get("label", "FIN")  # 默认为FIN类型
                
                # 判断是否在选择的分类中
                if classifications and entity_type not in classifications:
                    entity_type = classifications[0] if classifications else 'N/A'
                
                # 添加到识别实体列表
                identified_entities.append({
                    "识别实体": term,
                    "实体分类": entity_type,
                    "识别实体识别分数": round(float(confidence), 4),
                    "开始字符位置": start_pos,
                    "结束字符位置": end_pos,
                    # 初始化其他必要字段
                    "标准化术语": "",
                    "标准化术语中文": "",
                    "金融术语标准化编码": "",
                    "匹配的标准化术语准确度": 0.0
                })
        
        # 如果NER模型未识别到实体，使用规则引擎
        if not identified_entities:
            print("NER模型未识别到实体，使用规则引擎进行识别")
            rule_entities = extract_entities_with_rule_engine(text, classifications)
            for entity in rule_entities:
                identified_entities.append({
                    "识别实体": entity["识别实体"],
                    "实体分类": entity["实体分类"],
                    "识别实体识别分数": entity["识别分数"],
                    "开始字符位置": entity["开始字符位置"],
                    "结束字符位置": entity["结束字符位置"],
                    # 初始化其他必要字段
                    "标准化术语": "",
                    "标准化术语中文": "",
                    "金融术语标准化编码": "",
                    "匹配的标准化术语准确度": 0.0
                })
                
        print(f"识别到 {len(identified_entities)} 个实体")
        
        # 2. 对每个识别出的实体进行向量匹配和标准化
        successful_matches = 0
        for entity in identified_entities:
            # 获取实体文本
            entity_text = entity["识别实体"]
            print(f"处理实体: {entity_text}")
            
            # 使用向量搜索找到最相似的标准术语
            similar_term = find_similar_terms(
                entity_text,
                model_name,
                model_provider, 
                db_type, 
                index_type,
                collection_name
            )
            
            if similar_term:
                # 如果找到匹配的标准术语，填充详细信息
                entity["标准化术语"] = similar_term.get("finterm_normalization", entity_text)
                entity["标准化术语中文"] = similar_term.get("finterm_normalization_chinese", "")
                entity["金融术语标准化编码"] = similar_term.get("finterm_code", "")
                entity["匹配的标准化术语准确度"] = 0.85  # 模拟相似度得分，实际应从数据库结果中获取
                successful_matches += 1
                print(f"  ✓ 找到匹配: {entity['标准化术语']}")
            else:
                # 未找到匹配项，使用原始实体
                entity["标准化术语"] = entity_text
                entity["标准化术语中文"] = ""
                entity["金融术语标准化编码"] = hashlib.sha256(entity_text.encode('utf-8')).hexdigest()
                entity["匹配的标准化术语准确度"] = 0.5  # 默认较低的相似度
                print(f"  ✗ 未找到匹配，使用原始文本: {entity_text}")
                
        print(f"成功匹配 {successful_matches}/{len(identified_entities)} 个实体")
        
        # 3. 构建返回结果 - 确保符合指定的JSON结构
        result = {
            "用户输入内容": text,
            "选择分类": classifications,
            "识别实体数": len(identified_entities),
            "实体详情": identified_entities,
            "status": "success"  # 保留status字段用于前端检查操作状态
        }
        
        return result
        
    except Exception as e:
        print(f"标准化处理异常: {e}")
        raise HTTPException(status_code=500, detail=f"金融术语标准化处理失败: {str(e)}") 