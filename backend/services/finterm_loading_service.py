import os
import uuid
import hashlib
import datetime
import pandas as pd
import requests
import io
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any
from pathlib import Path
from config.settings import LOAD_DIR
# chromadb
import chromadb

router = APIRouter()

# chromadb 本地持久化路径
CHROMA_DB_PATH = str((Path(__file__).parent.parent / 'data' / 'chromadb'/ 'finterm_db').resolve())

# 模型配置
DEFAULT_MODELS = {
    "dimension_1024": {
        "provider": "siliconflow",
        "model_name": "BAAI/bge-m3"  # 默认使用BAAI/bge-m3模型
    },
    "dimension_384": {
        "provider": "siliconflow",
        "model_name": "netease-youdao/bce-embedding-base_v1"  # 使用API支持的384维模型
    },
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

def check_collection_dimension(collection_name):
    """检查集合中向量的维度"""
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

def read_csv_auto_encoding(file_path, **kwargs):
    import pandas as pd
    try:
        return pd.read_csv(file_path, encoding='utf-8', **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding='gbk', **kwargs)

@router.get("/collection/dimension")
async def get_collection_dimension_api(collection_name: str = "my_finterm_collection"):
    """获取集合中向量的维度信息"""
    try:
        dimension = check_collection_dimension(collection_name)
        if dimension is not None:
            return {
                "status": "success",
                "collection_name": collection_name,
                "dimension": dimension,
                "message": f"集合 {collection_name} 中向量维度为: {dimension}"
            }
        else:
            return {
                "status": "error",
                "collection_name": collection_name,
                "dimension": None,
                "message": f"无法获取集合 {collection_name} 的维度信息"
            }
    except Exception as e:
        return {
            "status": "error",
            "collection_name": collection_name,
            "dimension": None,
            "message": f"获取集合维度时出错: {str(e)}"
        }

@router.post("/load")
async def load_finterm(
    request: Dict = Body(...)
) -> Dict[str, Any]:
    """根据 file_id 分批处理本地文件，向量化C列并入库到chromadb，封装元数据"""
    try:
        file_id = request.get('file_id')
        db_type = request.get('db_type')
        index_type = request.get('index_type')
        provider = request.get('provider', DEFAULT_MODELS["dimension_1024"]["provider"])
        model_name = request.get('model_name', DEFAULT_MODELS["dimension_1024"]["model_name"])
        
        print(f"使用模型: {model_name}, 提供商: {provider}")
        print(f"向量数据库: {db_type}, 索引: {index_type}")
        
        if not file_id:
            raise HTTPException(status_code=400, detail='缺少 file_id')
        # 查找本地文件
        file_path = None
        for f in LOAD_DIR.glob(f"*{file_id}*"):
            if f.suffix.lower() in ['.csv', '.txt']:
                file_path = f
                break
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail='文件未找到')
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        now_date = now.strftime("%Y-%m-%d")
        validate_start = "2025-07-15 19:00:00"
        validate_end = "2026-07-15 19:00:00"
        # chromadb
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection_name = request.get('collection_name') or "my_finterm_collection"
        if collection_name in [c.name for c in chroma_client.list_collections()]:
            chroma_client.delete_collection(collection_name)
        collection = chroma_client.create_collection(name=collection_name)
        results = []
        chunk_size = 1000
        for chunk in read_csv_auto_encoding(file_path, header=None, chunksize=chunk_size):
            for idx, row in chunk.iterrows():
                # 直接按列索引取前4列，并打印调试
                try:
                    finterm_original = str(row.iloc[0]) if len(row) > 0 else ''
                    finterm_original_denoise = str(row.iloc[1]) if len(row) > 1 else ''
                    finterm_classify = str(row.iloc[2]) if len(row) > 2 else ''
                    finterm_normalization = str(row.iloc[3]) if len(row) > 3 else ''
                    finterm_normalization_chinese = str(row.iloc[4]) if len(row) > 4 else ''
                    finterm_category = str(row.iloc[5]) if len(row) > 5 else ''
                    print(f"row debug: {finterm_original}, {finterm_original_denoise}, {finterm_classify}, {finterm_normalization}, {finterm_normalization_chinese}, {finterm_category}")
                except Exception as e:
                    print(f"row iloc error: {e}")
                    finterm_original = finterm_original_denoise = finterm_classify = finterm_normalization = finterm_normalization_chinese = finterm_category = ''
                # D列为空、nan、null、N/A等则跳过
                skip_values = {'', 'nan', 'null', 'NULL', 'N/A', 'none', None}
                norm_val = finterm_normalization.strip().lower() if isinstance(finterm_normalization, str) else str(finterm_normalization).strip().lower()
                if norm_val in skip_values:
                    continue
                # D列向量化
                embedding = get_embedding(model_name or '', finterm_normalization, provider or '')
                
                # 检查是否成功获取向量
                if not embedding:
                    print(f"警告: 术语 '{finterm_normalization}' 未成功获取向量，跳过")
                    continue
                    
                # 检查向量维度
                if len(embedding) == 0:
                    print(f"警告: 术语 '{finterm_normalization}' 获取到的向量维度为0，跳过")
                    continue
                    
                print(f"术语 '{finterm_normalization}' 向量维度: {len(embedding)}")
                
                # 生成元数据
                finterm_id = str(uuid.uuid4())
                finterm_code = hashlib.sha256(finterm_normalization.encode('utf-8')).hexdigest()
                metadata = {
                    "id": finterm_id,
                    "finterm_code": finterm_code,
                    "finterm_original": finterm_original,
                    "finterm_original_denoise": finterm_original_denoise,
                    "finterm_classify": finterm_classify,
                    "finterm_normalization": finterm_normalization,
                    "finterm_normalization_chinese": finterm_normalization_chinese,
                    "finterm_category": finterm_category,
                    "insert_time": now_str,
                    "update_time": now_str,
                    "validate_start_date": validate_start,
                    "validate_end_date": validate_end,
                    "data_version": now_date,
                    "isvalidate": "1"
                }
                # 入库到chromadb - 明确传入embeddings参数
                try:
                    collection.add(
                        documents=[finterm_normalization],
                        metadatas=[metadata],
                        ids=[finterm_id],
                        embeddings=[embedding]  # 明确传入embeddings参数
                    )
                    print(f"成功将术语 '{finterm_normalization}' 及其向量添加到集合")
                    results.append({
                        "id": finterm_id,
                        "name": finterm_original,
                        "insert_time": now_str,
                        "update_time": now_str,
                        "status": "有效"
                    })
                except Exception as add_error:
                    print(f"向集合添加术语 '{finterm_normalization}' 失败: {add_error}")
        
        # 添加一个测试术语以验证集合功能
        try:
            test_id = "test-" + str(uuid.uuid4())
            test_embedding = [0.1] * 1024  # 创建一个1024维的测试向量
            collection.add(
                documents=["测试术语"],
                metadatas=[{
                    "id": test_id,
                    "finterm_code": "test_code",
                    "finterm_normalization": "测试术语",
                    "finterm_normalization_chinese": "测试术语中文",
                    "test": "true"
                }],
                ids=[test_id],
                embeddings=[test_embedding]
            )
            print("成功添加测试术语到集合")
        except Exception as test_error:
            print(f"添加测试术语失败: {test_error}")
        
        # 加载完成后检查集合维度
        actual_dimension = check_collection_dimension(collection_name)
        print(f"加载完成后集合 {collection_name} 的实际向量维度: {actual_dimension}")
        
        return {"status": "success", "count": len(results), "files": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@router.post("/collection/reset")
async def reset_collection(
    request: Dict = Body(...)
) -> Dict[str, Any]:
    """重置并初始化集合，创建测试向量"""
    try:
        collection_name = request.get('collection_name', 'my_finterm_collection')
        
        # 连接ChromaDB
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
        # 检查集合是否存在
        collection_names = [c.name for c in chroma_client.list_collections()]
        if collection_name in collection_names:
            print(f"删除现有集合: {collection_name}")
            chroma_client.delete_collection(collection_name)
            
        # 创建新集合
        print(f"创建新集合: {collection_name}")
        collection = chroma_client.create_collection(name=collection_name)
        
        # 添加测试向量
        dimension = request.get('dimension', 1024)
        test_ids = []
        test_terms = ["测试术语1", "测试术语2", "金融术语测试"]
        
        for i, term in enumerate(test_terms):
            test_id = f"test-{i+1}"
            test_embedding = [0.1] * dimension
            
            # 增加一些随机性使向量不完全相同
            import random
            for j in range(min(10, dimension)):
                random_idx = random.randint(0, dimension-1)
                test_embedding[random_idx] = random.random()
                
            metadata = {
                "id": test_id,
                "finterm_code": f"test_code_{i+1}",
                "finterm_normalization": term,
                "finterm_normalization_chinese": f"{term}中文",
                "finterm_category": "TEST",
                "insert_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            try:
                collection.add(
                    documents=[term],
                    metadatas=[metadata],
                    ids=[test_id],
                    embeddings=[test_embedding]
                )
                test_ids.append(test_id)
                print(f"成功添加测试术语: {term}")
            except Exception as add_error:
                print(f"添加测试术语失败: {add_error}")
        
        # 验证集合维度
        actual_dimension = check_collection_dimension(collection_name)
        
        return {
            "status": "success",
            "collection_name": collection_name,
            "dimension": actual_dimension,
            "test_ids": test_ids,
            "message": f"成功重置集合 {collection_name}，维度: {actual_dimension}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"重置集合失败: {str(e)}"
        }

@router.post("/collection/diagnose")
async def diagnose_collection(
    request: Dict = Body(...)
) -> Dict[str, Any]:
    """全面诊断集合的向量存储和检索功能"""
    try:
        collection_name = request.get('collection_name', 'my_finterm_collection')
        dimension = request.get('dimension', 1024)
        term = request.get('term', '诊断测试术语')
        
        report = {
            "collection_name": collection_name,
            "tests": [],
            "suggestions": []
        }
        
        # 测试1: 检查ChromaDB客户端
        try:
            chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            report["tests"].append({
                "name": "ChromaDB客户端初始化",
                "status": "通过",
                "message": f"成功初始化ChromaDB客户端，路径: {CHROMA_DB_PATH}"
            })
        except Exception as e:
            report["tests"].append({
                "name": "ChromaDB客户端初始化",
                "status": "失败",
                "message": f"初始化ChromaDB客户端失败: {str(e)}"
            })
            report["suggestions"].append("检查ChromaDB路径是否正确，确认有足够的权限")
            return {"status": "error", "report": report}
            
        # 测试2: 检查集合存在性
        collection_names = [c.name for c in chroma_client.list_collections()]
        if collection_name in collection_names:
            report["tests"].append({
                "name": "集合存在性检查",
                "status": "通过",
                "message": f"集合 {collection_name} 存在"
            })
            
            # 删除集合准备重新测试
            if request.get('reset', True):
                chroma_client.delete_collection(collection_name)
                report["tests"].append({
                    "name": "集合重置",
                    "status": "通过",
                    "message": f"集合 {collection_name} 已删除，准备重新创建"
                })
        else:
            report["tests"].append({
                "name": "集合存在性检查",
                "status": "通过",
                "message": f"集合 {collection_name} 不存在，将创建新集合"
            })
            
        # 测试3: 创建集合
        try:
            collection = chroma_client.create_collection(name=collection_name)
            report["tests"].append({
                "name": "创建集合",
                "status": "通过", 
                "message": f"成功创建集合 {collection_name}"
            })
        except Exception as e:
            report["tests"].append({
                "name": "创建集合",
                "status": "失败",
                "message": f"创建集合失败: {str(e)}"
            })
            report["suggestions"].append("检查ChromaDB权限，确认集合名称合法")
            return {"status": "error", "report": report}
            
        # 测试4: 创建向量
        try:
            test_embedding = [0.1] * dimension
            test_id = f"test-{uuid.uuid4()}"
            metadata = {
                "id": test_id,
                "finterm_code": "test_code",
                "finterm_normalization": term,
                "finterm_normalization_chinese": f"{term}中文",
                "test": "true"
            }
            
            report["tests"].append({
                "name": "创建测试向量",
                "status": "通过",
                "message": f"成功创建{dimension}维测试向量"
            })
        except Exception as e:
            report["tests"].append({
                "name": "创建测试向量",
                "status": "失败", 
                "message": f"创建测试向量失败: {str(e)}"
            })
            return {"status": "error", "report": report}
            
        # 测试5: 添加向量到集合
        try:
            collection.add(
                documents=[term],
                metadatas=[metadata],
                ids=[test_id],
                embeddings=[test_embedding]
            )
            report["tests"].append({
                "name": "添加向量到集合",
                "status": "通过",
                "message": f"成功将向量添加到集合 {collection_name}"
            })
        except Exception as e:
            report["tests"].append({
                "name": "添加向量到集合",
                "status": "失败",
                "message": f"添加向量失败: {str(e)}"
            })
            report["suggestions"].append("检查向量维度是否在ChromaDB支持范围内")
            return {"status": "error", "report": report}
            
        # 测试6: 获取集合数据
        try:
            # 尝试不同的方式获取集合数据
            get_standard = collection.get()
            get_with_embeddings = collection.get(include=["embeddings"])
            
            # 检查是否返回了ID
            if len(get_standard["ids"]) > 0:
                report["tests"].append({
                    "name": "获取集合数据-标准方式",
                    "status": "通过",
                    "message": f"成功获取集合数据，包含 {len(get_standard['ids'])} 个ID"
                })
            else:
                report["tests"].append({
                    "name": "获取集合数据-标准方式",
                    "status": "失败",
                    "message": "获取集合数据失败，没有返回ID"
                })
                
            # 检查是否返回了embeddings
            if 'embeddings' in get_with_embeddings and len(get_with_embeddings["embeddings"]) > 0:
                report["tests"].append({
                    "name": "获取集合数据-包含embeddings",
                    "status": "通过",
                    "message": f"成功获取集合embeddings，维度: {len(get_with_embeddings['embeddings'][0])}"
                })
                
                # 记录实际维度
                report["dimension"] = len(get_with_embeddings['embeddings'][0])
            else:
                report["tests"].append({
                    "name": "获取集合数据-包含embeddings",
                    "status": "失败",
                    "message": "获取集合embeddings失败，没有返回向量数据"
                })
                report["suggestions"].append("检查ChromaDB版本是否支持embeddings存储和检索")
        except Exception as e:
            report["tests"].append({
                "name": "获取集合数据",
                "status": "失败",
                "message": f"获取集合数据失败: {str(e)}"
            })
            
        # 测试7: 进行向量查询
        try:
            query_result = collection.query(
                query_embeddings=[test_embedding],
                n_results=1
            )
            
            if query_result and len(query_result["ids"]) > 0:
                report["tests"].append({
                    "name": "向量查询",
                    "status": "通过",
                    "message": f"成功使用向量进行查询，找到 {len(query_result['ids'])} 个结果"
                })
            else:
                report["tests"].append({
                    "name": "向量查询",
                    "status": "失败",
                    "message": "向量查询失败，没有返回结果"
                })
        except Exception as e:
            report["tests"].append({
                "name": "向量查询",
                "status": "失败",
                "message": f"向量查询失败: {str(e)}"
            })
        
        # 最终检查集合维度
        actual_dimension = check_collection_dimension(collection_name)
        if actual_dimension is not None:
            report["tests"].append({
                "name": "检查集合维度",
                "status": "通过",
                "message": f"集合维度为: {actual_dimension}"
            })
            report["final_dimension"] = actual_dimension
        else:
            report["tests"].append({
                "name": "检查集合维度",
                "status": "失败",
                "message": "无法确定集合维度"
            })
            
        # 整体测试结果
        test_results = [t["status"] for t in report["tests"]]
        if all(result == "通过" for result in test_results):
            return {"status": "success", "report": report}
        else:
            failed_count = sum(1 for result in test_results if result == "失败")
            report["suggestions"].append(f"有 {failed_count} 项测试失败，请检查详细报告")
            return {"status": "partial", "report": report}
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"诊断失败: {str(e)}"
        } 

@router.post("/test")
async def test_finterm(
    request: Dict = Body(...)
) -> Dict[str, Any]:
    """
    测试金融术语向量匹配功能
    
    - text: 输入文本
    - collection_name: 集合名称
    - model_provider: 嵌入式模型供应商
    - model_name: 嵌入式模型名称
    - db_type: 向量数据库类型
    - index_type: 索引类型
    """
    try:
        # 获取请求参数
        text = request.get('text', '')
        collection_name = request.get('collection_name', 'my_finterm_collection')
        model_provider = request.get('model_provider', DEFAULT_MODELS["dimension_1024"]["provider"])
        model_name = request.get('model_name', DEFAULT_MODELS["dimension_1024"]["model_name"])
        db_type = request.get('db_type', 'chromadb')
        index_type = request.get('index_type', 'hnsw')
        
        if not text:
            raise HTTPException(status_code=400, detail="请提供测试文本")
        
        # 1. 向量化查询文本
        print(f"正在向量化查询文本: '{text}'")
        embedding = get_embedding(model_name, text, model_provider)
        
        if not embedding:
            return {
                "status": "error",
                "message": "向量化失败，无法继续查询"
            }
        
        # 2. 连接到持久化数据库
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
        # 检查集合是否存在
        collection_names = [c.name for c in chroma_client.list_collections()]
        if collection_name not in collection_names:
            return {
                "status": "error",
                "message": f"集合 '{collection_name}' 不存在"
            }
        
        collection = chroma_client.get_collection(name=collection_name)
        
        # 3. 获取集合中的总条目数
        count = collection.count()
        print(f"集合 '{collection_name}' 中共有 {count} 条数据")
        
        # 4. 执行向量查询
        try:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=3,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as query_error:
            print(f"查询失败: {query_error}")
            return {
                "status": "error",
                "message": f"查询失败: {str(query_error)}"
            }
        
        # 5. 处理查询结果
        matches = []
        
        for i, (doc_id, document, metadata, distance) in enumerate(zip(
            results["ids"][0] if len(results["ids"]) > 0 else [],
            results["documents"][0] if len(results["documents"]) > 0 else [],
            results["metadatas"][0] if len(results["metadatas"]) > 0 else [],
            results["distances"][0] if len(results["distances"]) > 0 else []
        )):
            # 计算置信度（相似度分数）
            confidence = max(0, 1 - distance)
            
            # 格式化时间
            insert_time = metadata.get("insert_time", "N/A")
            update_time = metadata.get("update_time", "N/A")
            validate_start = metadata.get("validate_start_date", "N/A")
            validate_end = metadata.get("validate_end_date", "N/A")
            
            matches.append({
                "排名": i + 1,
                "ID": doc_id,
                "相似度": {
                    "距离": round(distance, 4),
                    "置信度": round(confidence * 100, 1)
                },
                "核心信息": {
                    "原始术语": metadata.get("finterm_original", "N/A"),
                    "术语代码": metadata.get("finterm_code", "N/A"),
                    "类别": metadata.get("finterm_category", "N/A"),
                    "分类": metadata.get("finterm_classify", "N/A"),
                    "标准化形式": metadata.get("finterm_normalization", "N/A"),
                    "中文标准化": metadata.get("finterm_normalization_chinese", "N/A")
                },
                "验证信息": {
                    "状态": "有效" if metadata.get("isvalidate") == "1" else "无效",
                    "有效期开始": validate_start,
                    "有效期结束": validate_end
                },
                "时间信息": {
                    "创建时间": insert_time,
                    "更新时间": update_time,
                    "数据版本": metadata.get("data_version", "N/A")
                }
            })
        
        # 6. 构建返回结果
        return {
            "status": "success",
            "查询信息": {
                "查询文本": text,
                "集合名称": collection_name,
                "集合大小": count,
                "结果数量": len(matches)
            },
            "匹配结果": matches
        }
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}") 

@router.get("/collection/preview")
async def preview_collection(collection_name: str = 'my_finterm_collection'):
    """
    预览集合内容，返回总数和前10条数据
    """
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection_names = [c.name for c in chroma_client.list_collections()]
        if collection_name not in collection_names:
            return {
                "status": "error",
                "message": f"集合 '{collection_name}' 不存在"
            }
        collection = chroma_client.get_collection(name=collection_name)
        total = collection.count()
        # 获取前10条数据
        preview = collection.get(limit=10, include=["documents", "metadatas"])
        items = []
        for i in range(len(preview["ids"])):
            items.append({
                "id": preview["ids"][i],
                "document": preview["documents"][i] if i < len(preview["documents"]) else None,
                "metadata": preview["metadatas"][i] if i < len(preview["metadatas"]) else None
            })
        return {
            "status": "success",
            "collection_name": collection_name,
            "total": total,
            "items": items
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"集合预览失败: {str(e)}"
        } 