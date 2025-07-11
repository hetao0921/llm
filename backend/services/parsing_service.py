import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse

from config.settings import PARSE_DIR, METADATA_FILES, FILE_NAMING

router = APIRouter()
logger = logging.getLogger(__name__)

def load_metadata() -> Dict[str, Dict[str, Any]]:
    """加载元数据"""
    metadata: Dict[str, Dict[str, Any]] = {"documents": {}}
    if METADATA_FILES["parse"].exists():
        try:
            with open(METADATA_FILES["parse"], "r", encoding="utf-8") as f:
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
    with open(METADATA_FILES["parse"], "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

@router.post("/documents/{file_id}/parse")
async def parse_document(
    file_id: str,
    request: Dict = Body(...)
):
    """解析文档"""
    # 加载元数据
    metadata = load_metadata()
    
    # 从PARSE_DIR目录读取文件
    input_file = PARSE_DIR / f"{file_id}_loaded.txt"
    if not input_file.exists():
        # 尝试在目录中查找匹配的文件
        matching_files = list(PARSE_DIR.glob(f"*{file_id}*"))
        if matching_files:
            input_file = matching_files[0]
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "文档不存在，请先上传文档",
                    "error_code": "document_not_found",
                    "file_id": file_id
                }
            )
    
    # 读取文档内容
    try:
        with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")
    
    # 获取解析参数
    parser = request.get("parser", "default")
    params = request.get("params", {})
    
    # 根据不同的解析器进行解析
    parsed_data = None
    if parser == "default":
        # 默认解析器：简单的文本分析
        parsed_data = {
            "word_count": len(text.split()),
            "char_count": len(text),
            "line_count": len(text.splitlines()),
            "paragraphs": len([p for p in text.split("\n\n") if p.strip()]),
            "language": detect_language(text)
        }
    elif parser == "json":
        # JSON解析器
        try:
            parsed_data = json.loads(text)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON解析失败: {str(e)}")
    elif parser == "markdown":
        # Markdown解析器
        import markdown
        html = markdown.markdown(text)
        parsed_data = {
            "html": html,
            "metadata": extract_markdown_metadata(text)
        }
    else:
        raise HTTPException(status_code=400, detail=f"不支持的解析器: {parser}")
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 获取原始文件名（不含扩展名）
    original_filename = input_file.stem.split("_")[0]
    
    # 构建新的文件名
    output_filename = FILE_NAMING["parse"].format(
        original_name=original_filename,
        file_id=file_id,
        timestamp=timestamp,
        ext=".json"
    )
    
    # 创建解析结果数据
    parse_result = {
        "file_id": file_id,
        "filename": output_filename,
        "parser": parser,
        "params": params,
        "parsed_data": parsed_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # 保存解析结果
    output_file = PARSE_DIR / output_filename
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(parse_result, f, ensure_ascii=False, indent=2)
    
    # 更新元数据
    if file_id not in metadata["documents"]:
        metadata["documents"][file_id] = {
            "id": file_id,
            "original_filename": original_filename,
            "input_file": str(input_file),
            "parses": []
        }
    
    # 添加新的解析信息
    parse_info = {
        "parser": parser,
        "timestamp": parse_result["timestamp"],
        "output_file": str(output_file)
    }
    metadata["documents"][file_id]["parses"].append(parse_info)
    save_metadata(metadata)
    
    return parse_result

@router.get("/documents/{file_id}/parses")
async def get_document_parses(file_id: str):
    """获取文档的解析历史"""
    # 加载元数据
    metadata = load_metadata()
    
    # 检查文档是否存在
    if file_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    document_info = metadata["documents"][file_id]
    
    # 检查是否有解析历史
    if not document_info["parses"]:
        raise HTTPException(status_code=404, detail="文档还未解析")
    
    # 获取最新的解析文件
    latest_parse = document_info["parses"][-1]
    parse_file = Path(latest_parse["output_file"])
    
    if not parse_file.exists():
        raise HTTPException(status_code=404, detail="解析文件不存在")
    
    # 读取解析数据
    with open(parse_file, "r", encoding="utf-8") as f:
        parse_data = json.load(f)
    
    return parse_data

@router.delete("/documents/{file_id}/parses")
async def delete_document_parses(file_id: str):
    """删除文档的所有解析结果"""
    # 加载元数据
    metadata = load_metadata()
    
    # 检查文档是否存在
    if file_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    document_info = metadata["documents"][file_id]
    
    # 删除所有解析文件
    for parse_info in document_info["parses"]:
        parse_file = Path(parse_info["output_file"])
        if parse_file.exists():
            parse_file.unlink()
    
    # 清空解析记录
    document_info["parses"] = []
    save_metadata(metadata)
    
    return {"status": "success", "message": "解析结果已删除"}

def detect_language(text: str) -> str:
    """检测文本语言"""
    try:
        from langdetect import detect
        return detect(text)
    except:
        return "unknown"

def extract_markdown_metadata(text: str) -> Dict:
    """提取Markdown文本的元数据"""
    metadata = {}
    lines = text.split("\n")
    
    # 简单的YAML-like元数据提取
    if lines and lines[0].strip() == "---":
        meta_lines = []
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                break
            meta_lines.append(line)
        
        for line in meta_lines:
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
    
    return metadata 