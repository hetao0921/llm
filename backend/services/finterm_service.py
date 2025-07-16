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

def get_embedding(model_name: str, text: str, provider: str = 'siliconflow'):
    """调用向量化API，返回embedding，支持多provider扩展"""
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
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            return resp.json().get('data', [{}])[0].get('embedding', [])
        else:
            return []
    # 可扩展其他provider
    return []

def read_csv_auto_encoding(file_path, **kwargs):
    import pandas as pd
    try:
        return pd.read_csv(file_path, encoding='utf-8', **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding='gbk', **kwargs)

@router.post("/load")
async def load_finterm(
    request: Dict = Body(...)
) -> Dict[str, Any]:
    """根据 file_id 分批处理本地文件，向量化C列并入库到chromadb，封装元数据"""
    try:
        file_id = request.get('file_id')
        db_type = request.get('db_type')
        index_type = request.get('index_type')
        provider = request.get('provider')
        model_name = request.get('model_name')
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
                # D列向量化
                embedding = get_embedding(model_name or '', finterm_normalization, provider or '')
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
                # 入库到chromadb
                collection.add(
                    documents=[finterm_normalization],
                    metadatas=[metadata],
                    ids=[finterm_id]
                )
                results.append({
                    "id": finterm_id,
                    "name": finterm_original,
                    "insert_time": now_str,
                    "update_time": now_str,
                    "status": "有效"
                })
        return {"status": "success", "count": len(results), "files": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}") 