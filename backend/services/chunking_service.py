import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import logging
import re
from fastapi import APIRouter, HTTPException, Body, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from config.settings import CHUNK_DIR, LOAD_DIR, METADATA_FILES, FILE_NAMING

# 初始化路由
router = APIRouter()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 分块配置
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

def load_metadata() -> Dict[str, Dict[str, Any]]:
    """加载元数据"""
    metadata: Dict[str, Dict[str, Any]] = {"documents": {}}
    if METADATA_FILES["chunk"].exists():
        try:
            with open(METADATA_FILES["chunk"], "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, dict) and "documents" in loaded_data:
                    return loaded_data
                else:
                    logger.error("Metadata file contains invalid data structure")
        except json.JSONDecodeError:
            logger.error("Invalid JSON in metadata file. Creating new metadata.")
    return metadata

def save_metadata(metadata: Dict) -> None:
    """保存元数据"""
    # 确保目录存在
    METADATA_FILES["chunk"].parent.mkdir(parents=True, exist_ok=True)

    with open(METADATA_FILES["chunk"], "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

def find_loaded_text_file(file_id: str) -> Optional[Path]:
    """查找已加载的文本文件，支持多种可能的文件名格式"""
    logger.info(f"正在查找文件ID: {file_id}")
    
    # 首先检查file_id是否本身就是UUID格式
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    is_uuid = bool(uuid_pattern.match(file_id))
    
    # 如果file_id是UUID，直接查找对应的文件
    if is_uuid:
        # 在目录中查找包含此UUID的文件
        for file_path in LOAD_DIR.glob("*"):
            if file_id in str(file_path):
                if str(file_path).endswith("_text.txt"):
                    logger.info(f"找到匹配的已加载文本文件: {file_path}")
                    return file_path
                else:
                    # 如果找到原始文件但没有找到_text.txt，检查是否存在对应的text文件
                    base_name = file_path.stem
                    if base_name.endswith("_loaded"):
                        base_name = base_name[:-7]  # 移除 _loaded 后缀
                    text_file = file_path.parent / f"{base_name}_text.txt"
                    if text_file.exists():
                        logger.info(f"找到对应的已加载文本文件: {text_file}")
                        return text_file
    
    # 尝试直接匹配简单格式
    simple_path = LOAD_DIR / f"{file_id}_text.txt"
    if simple_path.exists():
        logger.info(f"找到文件 {simple_path}")
        return simple_path
    
    # 尝试从元数据中查找
    try:
        loading_metadata_path = METADATA_FILES["load"]
        if loading_metadata_path.exists():
            with open(loading_metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                logger.info(f"元数据中的文档: {list(metadata.get('documents', {}).keys())}")
                if file_id in metadata.get("documents", {}):
                    text_file = metadata["documents"][file_id].get("text_file")
                    if text_file:
                        text_path = Path(text_file)
                        if text_path.exists():
                            logger.info(f"从元数据找到文件 {text_path}")
                            return text_path
    except Exception as e:
        logger.error(f"从元数据中查找文件时出错: {str(e)}")
    
    # 在所有文件中查找UUID
    try:
        logger.info(f"在目录中查找所有可能的文件...")
        for file_path in LOAD_DIR.glob("*"):
            # 从文件名中提取UUID
            uuid_match = re.search(r'_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_', str(file_path))
            if uuid_match and uuid_match.group(1) == file_id:
                if str(file_path).endswith("_text.txt"):
                    logger.info(f"通过UUID匹配找到已加载文本文件: {file_path}")
                    return file_path
                else:
                    # 如果找到原始文件，检查对应的text文件
                    base_name = file_path.stem
                    if base_name.endswith("_loaded"):
                        base_name = base_name[:-7]  # 移除 _loaded 后缀
                    text_file = file_path.parent / f"{base_name}_text.txt"
                    if text_file.exists():
                        logger.info(f"找到对应的已加载文本文件: {text_file}")
                        return text_file
    except Exception as e:
        logger.error(f"在目录中查找文件时出错: {str(e)}")
    
    # 如果所有方法都失败，返回None
    logger.warning(f"未找到文件: {file_id}")
    return None

def detect_page_markers(text: str) -> List[int]:
    """检测文本中的页面标记"""
    # 常见的页面标记模式
    patterns = [
        r'\f',  # Form feed character
        r'(?m)^Page\s+\d+$',  # "Page X" at start of line
        r'(?m)^\[\d+\]$',  # [X] at start of line
        r'(?m)^-\s*\d+\s*-$',  # -X- at start of line
    ]

    page_breaks = []
    current_pos = 0

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            page_breaks.append(match.start())

    # 如果没有找到页面标记，尝试通过连续两个换行符来判断
    if not page_breaks:
        for match in re.finditer(r'\n\n+', text):
            page_breaks.append(match.start())

    return sorted(list(set(page_breaks)))

def chunk_text(text: str, strategy: str = "fixed_size", params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """根据策略对文本进行分块"""
    if params is None:
        params = {}

    chunk_size = params.get("chunk_size", DEFAULT_CHUNK_SIZE)
    chunk_overlap = params.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)
    include_page_markers = params.get("include_page_markers", True)
    
    chunks = []

    if strategy == "fixed_size":
        # 固定大小分块
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append({
                "text": chunk_text,
                "start": start,
                "end": end,
                "size": len(chunk_text)
            })
            start = end - chunk_overlap

    elif strategy == "paragraph":
        # 按段落分块
        paragraphs = text.split("\n\n")
        current_chunk = ""
        current_size = 0
        start = 0

        for paragraph in paragraphs:
            if current_size + len(paragraph) > chunk_size and current_chunk:
                # 保存当前块
                chunks.append({
                    "text": current_chunk,
                    "start": start,
                    "end": start + len(current_chunk),
                    "size": len(current_chunk)
                })
                # 开始新的块，保留重叠的段落
                overlap_paragraphs = current_chunk.split("\n\n")[-chunk_overlap:] if chunk_overlap > 0 else []
                current_chunk = "\n\n".join(overlap_paragraphs + [paragraph])
                current_size = len(current_chunk)
                start = start + len(current_chunk) - sum(len(p) + 2 for p in overlap_paragraphs[:-1]) if overlap_paragraphs else start + len(current_chunk)
            else:
                # 添加到当前块
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
                current_size = len(current_chunk)

        # 保存最后一个块
        if current_chunk:
            chunks.append({
                "text": current_chunk,
                "start": start,
                "end": start + len(current_chunk),
                "size": len(current_chunk)
            })

    elif strategy == "sentence":
        # 按句子分块
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""
        current_size = 0
        start = 0
        sentence_count = 0
        max_sentences = params.get("chunk_size", 5)  # 每块最大句子数
        overlap_sentences = params.get("chunk_overlap", 1)  # 重叠句子数

        for sentence in sentences:
            sentence_count += 1

            if sentence_count > max_sentences and current_chunk:
                # 保存当前块
                chunks.append({
                    "text": current_chunk,
                    "start": start,
                    "end": start + len(current_chunk),
                    "size": len(current_chunk)
                })
                # 开始新的块，保留重叠的句子
                overlap_text = ". ".join(current_chunk.split(". ")[-overlap_sentences:])
                current_chunk = overlap_text + ". " + sentence if overlap_text else sentence
                current_size = len(current_chunk)
                sentence_count = overlap_sentences + 1
                start = start + len(current_chunk) - len(overlap_text) if overlap_text else start + len(current_chunk)
        else:
                # 添加到当前块
                if current_chunk:
                    current_chunk += " "
                current_chunk += sentence
                current_size = len(current_chunk)

        # 保存最后一个块
        if current_chunk:
            chunks.append({
                "text": current_chunk,
                "start": start,
                "end": start + len(current_chunk),
                "size": len(current_chunk)
            })

    elif strategy == "page":
        # 按页面分块
        page_breaks = detect_page_markers(text)
        if not page_breaks:
            # 如果没有检测到页面标记，使用固定大小分块
            return chunk_text(text, "fixed_size", params)

        # 添加文本结束位置
        page_breaks.append(len(text))

        start = 0
        for end in page_breaks:
            chunk_text = text[start:end].strip()
            if chunk_text:
                # 如果需要包含页面标记
                if include_page_markers:
                    page_num = page_breaks.index(end) + 1
                    chunk_text = f"[Page {page_num}]\n{chunk_text}"

                chunks.append({
                    "text": chunk_text,
                    "start": start,
                    "end": end,
                    "size": len(chunk_text),
                    "page": page_breaks.index(end) + 1
                })
            start = end

    # 为每个块添加唯一ID和时间戳
    for i, chunk in enumerate(chunks):
        chunk["id"] = f"chunk_{i+1}"
        chunk["timestamp"] = datetime.now().isoformat()
    
    return chunks

def validate_chunking_params(strategy: str, params: Dict[str, Any]) -> Tuple[bool, str]:
    """验证分块参数"""
    if strategy not in ["fixed_size", "sentence", "paragraph", "page"]:
        return False, f"不支持的分块策略: {strategy}"

    chunk_size = params.get("chunk_size")
    chunk_overlap = params.get("chunk_overlap")

    if strategy == "fixed_size":
        if not chunk_size or not isinstance(chunk_size, (int, float)) or chunk_size < 100 or chunk_size > 10000:
            return False, "块大小必须在100-10000字符之间"
        if chunk_overlap is not None and (not isinstance(chunk_overlap, (int, float)) or chunk_overlap < 0 or chunk_overlap >= chunk_size):
            return False, "重叠部分必须小于块大小且不能为负"

    elif strategy == "sentence":
        if not chunk_size or not isinstance(chunk_size, int) or chunk_size < 1 or chunk_size > 30:
            return False, "每块句子数必须在1-30之间"
        if chunk_overlap is not None and (not isinstance(chunk_overlap, int) or chunk_overlap < 0 or chunk_overlap > 5):
            return False, "句子重叠必须在0-5之间"

    elif strategy == "paragraph":
        if not chunk_size or not isinstance(chunk_size, int) or chunk_size < 1 or chunk_size > 20:
            return False, "每块段落数必须在1-20之间"
        if chunk_overlap is not None and (not isinstance(chunk_overlap, int) or chunk_overlap < 0 or chunk_overlap > 3):
            return False, "段落重叠必须在0-3之间"

    elif strategy == "page":
        include_page_markers = params.get("include_page_markers")
        if include_page_markers is not None and not isinstance(include_page_markers, bool):
            return False, "include_page_markers必须是布尔值"

    return True, ""

# API路由
@router.get("/strategies")
async def get_chunking_strategies():
    """获取可用的分块策略"""
    strategies = [
        {
            "id": "fixed_size",
            "name": "固定大小",
            "description": "将文本按固定大小分块，并可设置重叠部分",
            "parameters": [
                {"name": "chunk_size", "type": "number", "default": 1000, "min": 100, "max": 10000, "description": "每个块的大小（字符数）"},
                {"name": "chunk_overlap", "type": "number", "default": 200, "min": 0, "max": 5000, "description": "块之间重叠的字符数"}
            ]
        },
        {
            "id": "paragraph",
            "name": "段落分块",
            "description": "根据段落（以空行分隔）进行分块",
            "parameters": [
                {"name": "chunk_size", "type": "number", "default": 3, "min": 1, "max": 20, "description": "每块包含的段落数"},
                {"name": "chunk_overlap", "type": "number", "default": 1, "min": 0, "max": 3, "description": "块之间重叠的段落数"}
            ]
        },
        {
            "id": "sentence",
            "name": "句子分块",
            "description": "根据句子（以句号、感叹号、问号等结尾）进行分块",
            "parameters": [
                {"name": "chunk_size", "type": "number", "default": 5, "min": 1, "max": 30, "description": "每块包含的句子数"},
                {"name": "chunk_overlap", "type": "number", "default": 1, "min": 0, "max": 5, "description": "块之间重叠的句子数"}
            ]
        },
        {
            "id": "page",
            "name": "页面分块",
            "description": "根据页面标记或分页符进行分块",
            "parameters": [
                {"name": "include_page_markers", "type": "boolean", "default": True, "description": "在块中包含页码标记"}
            ]
        }
    ]

    return strategies

@router.post("/documents/{file_id}/chunk")
async def chunk_document(
    file_id: str,
    request: Dict = Body(...)
):
    """对文档进行分块"""
    logger.info(f"开始处理文件ID: {file_id} 的分块请求")
    
    # 查找文件
    file_path = find_loaded_text_file(file_id)
    if not file_path:
        # 添加额外的文件检查逻辑
        original_files = list(LOAD_DIR.glob(f"*{file_id}*"))
        original_files.extend(list(LOAD_DIR.glob("*")))
        
        if original_files:
            logger.info(f"找到 {len(original_files)} 个可能相关的文件")
            # 检查是否有其他已加载的文件可用
            loaded_files = [f for f in original_files if str(f).endswith("_text.txt")]
            
            if loaded_files:
                # 如果有可用的已加载文件，使用第一个
                selected_file = loaded_files[0]
                logger.info(f"将使用找到的已加载文件: {selected_file}")
                file_path = selected_file
            else:
                # 检查文件是否存在但未加载
                for orig_path in original_files:
                    if orig_path.exists() and not str(orig_path).endswith("_text.txt"):
                        logger.warning(f"文件存在但未加载: {orig_path}")
                        raise HTTPException(status_code=400, detail=f"文件 {file_id} 尚未加载。请先在文件加载页面上传并加载文档。")
        
        if not file_path:  # 如果上述逻辑没有找到文件
            logger.error(f"找不到文件: {file_id}")
            raise HTTPException(status_code=404, detail=f"找不到文件: {file_id}。请确保文件已上传并加载。")
    
    logger.info(f"已找到要分块的文件: {file_path}")
    
    # 获取分块策略和参数
    strategy = request.get("strategy", "fixed_size")
    params = request.get("params", {})
    
    # 验证参数
    is_valid, error_msg = validate_chunking_params(strategy, params)
    if not is_valid:
        logger.warning(f"分块参数验证失败: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # 读取文件内容
        logger.info(f"正在读取文件内容: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        if not text or len(text.strip()) == 0:
            logger.warning(f"文件内容为空: {file_path}")
            raise HTTPException(status_code=400, detail=f"文件内容为空，无法进行分块")
        
        logger.info(f"文件内容读取成功，长度: {len(text)} 字符")
        
        # 执行分块
        logger.info(f"开始执行分块，策略: {strategy}, 参数: {params}")
        chunks = chunk_text(text, strategy, params)
        
        # 保存分块结果
        chunk_file = CHUNK_DIR / f"{file_id}_chunks.json"
        chunk_data = {
            "file_id": file_id,
            "strategy": strategy,
            "params": params,
            "chunks": chunks,
            "timestamp": datetime.now().isoformat(),
            "original_size": len(text)
        }
        
        # 确保目录存在
        CHUNK_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(chunk_file, "w", encoding="utf-8") as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
        
        # 更新元数据
        metadata = load_metadata()
        metadata["documents"][file_id] = {
            "strategy": strategy,
            "params": params,
            "timestamp": chunk_data["timestamp"],
            "chunk_file": str(chunk_file)
        }
        save_metadata(metadata)
        
        logger.info(f"文档分块完成，共 {len(chunks)} 个块")
        
        # 返回分块结果
        return JSONResponse(content={"chunks": chunks})
    
    except Exception as e:
        logger.error(f"分块失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分块失败: {str(e)}")

@router.get("/documents/{file_id}/chunks")
async def get_document_chunks(file_id: str):
    """获取文档的分块"""
    chunk_file = CHUNK_DIR / f"{file_id}_chunks.json"
    if not chunk_file.exists():
        return JSONResponse(content={"chunks": []})

    try:
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunk_data = json.load(f)
            return JSONResponse(content={"chunks": chunk_data.get("chunks", [])})
    except Exception as e:
        logger.error(f"读取分块失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"读取分块失败: {str(e)}")

@router.get("/documents/{file_id}/chunks/json")
async def get_chunks_json(file_id: str):
    """获取JSON格式的分块数据"""
    chunk_file = CHUNK_DIR / f"{file_id}_chunks.json"
    if not chunk_file.exists():
        raise HTTPException(status_code=404, detail=f"找不到文件的分块数据: {file_id}")

    try:
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunk_data = json.load(f)
            return JSONResponse(content={"chunks": chunk_data.get("chunks", [])})
    except Exception as e:
        logger.error(f"读取JSON数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"读取JSON数据失败: {str(e)}")

@router.delete("/documents/{file_id}/chunks")
async def delete_document_chunks(file_id: str):
    """删除文档的分块"""
    chunk_file = CHUNK_DIR / f"{file_id}_chunks.json"
    if not chunk_file.exists():
        return JSONResponse(content={"message": "分块数据不存在"})

    try:
        # 删除分块文件
        chunk_file.unlink()

        # 更新元数据
        metadata = load_metadata()
        if file_id in metadata["documents"]:
            del metadata["documents"][file_id]
            save_metadata(metadata)

        return JSONResponse(content={"message": "分块数据已删除"})
    except Exception as e:
        logger.error(f"删除分块失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除分块失败: {str(e)}") 