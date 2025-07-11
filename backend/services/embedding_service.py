from pathlib import Path
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, List, Any
import json
from datetime import datetime
import logging
import numpy as np
from config.settings import EMBEDDING_DIR, METADATA_FILES, FILE_NAMING, CHUNK_DIR

# 初始化路由
router = APIRouter()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_metadata() -> Dict[str, Dict[str, Any]]:
    """加载元数据"""
    metadata: Dict[str, Dict[str, Any]] = {"documents": {}}
    if METADATA_FILES["embedding"].exists():
        try:
            with open(METADATA_FILES["embedding"], "r", encoding="utf-8") as f:
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
    with open(METADATA_FILES["embedding"], "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

@router.post("/documents/{file_id}/embed")
async def embed_document(
    file_id: str,
    request: Dict = Body(...)
):
    """对文档进行向量嵌入"""
    # 加载元数据
    metadata = load_metadata()
    
    # 从chunk目录读取分块文件
    matching_files = list(CHUNK_DIR.glob(f"*{file_id}*_chunked.json"))
    if not matching_files:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "文档不存在，请先进行分块",
                "error_code": "document_not_found",
                "file_id": file_id
            }
        )
    
    input_file = matching_files[0]
    
    # 读取分块数据
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")
    
    # 获取嵌入参数
    model = request.get("model", "default")
    params = request.get("params", {})
    
    # 对每个块进行向量嵌入
    embeddings = []
    for chunk in chunks_data["chunks"]:
        # 这里应该调用实际的嵌入模型
        # 目前使用随机向量作为示例
        embedding = np.random.rand(768).tolist()  # 假设使用768维向量
        embeddings.append({
            "text": chunk["text"],
            "embedding": embedding,
            "metadata": {
                "start": chunk["start"],
                "end": chunk["end"],
                "size": chunk["size"]
            }
        })
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 获取原始文件名（不含扩展名）
    original_filename = input_file.stem.split("_chunked")[0]
    
    # 构建新的文件名
    output_filename = FILE_NAMING["embedding"].format(
        original_name=original_filename,
        file_id=file_id,
        timestamp=timestamp
    )
    
    # 创建嵌入结果数据
    embedding_result = {
        "file_id": file_id,
        "filename": output_filename,
        "model": model,
        "params": params,
        "embedding_count": len(embeddings),
        "embeddings": embeddings,
        "timestamp": datetime.now().isoformat()
    }
    
    # 保存嵌入结果
    output_file = EMBEDDING_DIR / output_filename
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(embedding_result, f, ensure_ascii=False, indent=2)
    
    # 更新元数据
    if file_id not in metadata["documents"]:
        metadata["documents"][file_id] = {
            "id": file_id,
            "original_filename": original_filename,
            "input_file": str(input_file),
            "embeddings": []
        }
    
    # 添加新的嵌入信息
    embedding_info = {
        "model": model,
        "embedding_count": len(embeddings),
        "timestamp": embedding_result["timestamp"],
        "output_file": str(output_file)
    }
    metadata["documents"][file_id]["embeddings"].append(embedding_info)
    save_metadata(metadata)
    
    return embedding_result

@router.get("/documents/{file_id}/embeddings")
async def get_document_embeddings(file_id: str):
    """获取文档的嵌入向量"""
    # 加载元数据
    metadata = load_metadata()
    
    # 检查文档是否存在
    if file_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    document_info = metadata["documents"][file_id]
    
    # 检查是否有嵌入向量
    if not document_info["embeddings"]:
        raise HTTPException(status_code=404, detail="文档还未进行向量嵌入")
    
    # 获取最新的嵌入文件
    latest_embedding = document_info["embeddings"][-1]
    embedding_file = Path(latest_embedding["output_file"])
    
    if not embedding_file.exists():
        raise HTTPException(status_code=404, detail="嵌入文件不存在")
    
    # 读取嵌入数据
    with open(embedding_file, "r", encoding="utf-8") as f:
        embedding_data = json.load(f)
    
    return embedding_data

@router.delete("/documents/{file_id}/embeddings")
async def delete_document_embeddings(file_id: str):
    """删除文档的所有嵌入向量"""
    # 加载元数据
    metadata = load_metadata()
    
    # 检查文档是否存在
    if file_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    document_info = metadata["documents"][file_id]
    
    # 删除所有嵌入文件
    for embedding_info in document_info["embeddings"]:
        embedding_file = Path(embedding_info["output_file"])
        if embedding_file.exists():
            embedding_file.unlink()
    
    # 清空嵌入记录
    document_info["embeddings"] = []
    save_metadata(metadata)
    
    return {"status": "success", "message": "嵌入向量已删除"} 