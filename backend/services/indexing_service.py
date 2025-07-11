from pathlib import Path
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, List, Any
import json
from datetime import datetime
import logging
import numpy as np
from config.settings import INDEXING_DIR, METADATA_FILES, FILE_NAMING, EMBEDDING_DIR

# 初始化路由
router = APIRouter()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_metadata() -> Dict[str, Dict[str, Any]]:
    """加载元数据"""
    metadata: Dict[str, Dict[str, Any]] = {"documents": {}}
    if METADATA_FILES["indexing"].exists():
        try:
            with open(METADATA_FILES["indexing"], "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, dict) and "documents" in loaded_data:
                    metadata = loaded_data
                else:
                    logger.error("Metadata file contains invalid data structure")
        except json.JSONDecodeError:
            logger.error("Invalid JSON in metadata file. Creating new metadata.")
    return metadata

def save_metadata(metadata: Dict) -> None:
    """保存元数据"""
    with open(METADATA_FILES["indexing"], "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

@router.post("/documents/{file_id}/index")
async def index_document(
    file_id: str,
    request: Dict = Body(...)
):
    """对文档进行向量索引"""
    # 加载元数据
    metadata = load_metadata()
    
    # 从embedding目录读取嵌入文件
    matching_files = list(EMBEDDING_DIR.glob(f"*{file_id}*_embedded.json"))
    if not matching_files:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "文档不存在，请先进行向量嵌入",
                "error_code": "document_not_found",
                "file_id": file_id
            }
        )
    
    input_file = matching_files[0]
    
    # 读取嵌入数据
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            embedding_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")
    
    # 获取索引参数
    index_type = request.get("index_type", "faiss")  # 默认使用FAISS
    params = request.get("params", {})
    
    # 从嵌入数据中提取向量
    vectors = []
    texts = []
    metadata_list = []
    for item in embedding_data["embeddings"]:
        vectors.append(item["embedding"])
        texts.append(item["text"])
        metadata_list.append(item["metadata"])
    
    # 构建索引（这里使用示例数据）
    index_data = {
        "vectors": vectors,
        "texts": texts,
        "metadata": metadata_list
    }
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 获取原始文件名（不含扩展名）
    original_filename = input_file.stem.split("_embedded")[0]
    
    # 构建新的文件名
    output_filename = FILE_NAMING["indexing"].format(
        original_name=original_filename,
        file_id=file_id,
        timestamp=timestamp
    )
    
    # 创建索引结果数据
    index_result = {
        "file_id": file_id,
        "filename": output_filename,
        "index_type": index_type,
        "params": params,
        "vector_count": len(vectors),
        "index_data": index_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # 保存索引结果
    output_file = INDEXING_DIR / output_filename
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(index_result, f, ensure_ascii=False, indent=2)
    
    # 更新元数据
    if file_id not in metadata["documents"]:
        metadata["documents"][file_id] = {
            "id": file_id,
            "original_filename": original_filename,
            "input_file": str(input_file),
            "indices": []
        }
    
    # 添加新的索引信息
    index_info = {
        "index_type": index_type,
        "vector_count": len(vectors),
        "timestamp": index_result["timestamp"],
        "output_file": str(output_file)
    }
    metadata["documents"][file_id]["indices"].append(index_info)
    save_metadata(metadata)
    
    return index_result

@router.get("/documents/{file_id}/indices")
async def get_document_indices(file_id: str):
    """获取文档的索引信息"""
    # 加载元数据
    metadata = load_metadata()
    
    # 检查文档是否存在
    if file_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    document_info = metadata["documents"][file_id]
    
    # 检查是否有索引
    if not document_info["indices"]:
        raise HTTPException(status_code=404, detail="文档还未建立索引")
    
    # 获取最新的索引文件
    latest_index = document_info["indices"][-1]
    index_file = Path(latest_index["output_file"])
    
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="索引文件不存在")
    
    # 读取索引数据
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)
    
    return index_data

@router.delete("/documents/{file_id}/indices")
async def delete_document_indices(file_id: str):
    """删除文档的所有索引"""
    # 加载元数据
    metadata = load_metadata()
    
    # 检查文档是否存在
    if file_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    document_info = metadata["documents"][file_id]
    
    # 删除所有索引文件
    for index_info in document_info["indices"]:
        index_file = Path(index_info["output_file"])
        if index_file.exists():
            index_file.unlink()
    
    # 清空索引记录
    document_info["indices"] = []
    save_metadata(metadata)
    
    return {"status": "success", "message": "索引已删除"} 