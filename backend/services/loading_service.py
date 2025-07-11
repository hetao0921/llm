import os
import json
import uuid
import datetime
import mimetypes
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Optional, Union, Any
import shutil
import logging
from config.settings import LOAD_DIR, METADATA_FILES, FILE_NAMING
import re
import pandas as pd
from io import BytesIO
import hashlib

# Initialize optional dependencies
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from unstructured.partition.auto import partition
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# Initialize MIME types
mimetypes.init()

# 初始化路由
router = APIRouter()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义支持的文件扩展名和其对应的加载器
SUPPORTED_EXTENSIONS = {
    # PDF files
    '.pdf': ['pymupdf', 'pypdf', 'unstructured'],
    
    # Microsoft Office documents
    '.docx': ['docx', 'unstructured'],
    '.doc': ['unstructured'],
    '.pptx': ['pptx', 'unstructured'],
    '.ppt': ['unstructured'],
    '.xlsx': ['unstructured'],
    '.xls': ['unstructured'],
    
    # Text files
    '.txt': ['text', 'unstructured'],
    '.md': ['text', 'unstructured'],
    '.csv': ['text', 'unstructured'],
    '.json': ['text', 'unstructured'],
    
    # Web content
    '.html': ['html', 'unstructured'],
    '.htm': ['html', 'unstructured'],
    '.xml': ['text', 'unstructured'],
}

def detect_file_type(file_path: str, file_extension: str = None) -> str:
    """
    Detect file type based on extension and content.
    Returns the file format as a string.
    """
    if file_extension is None:
        file_extension = os.path.splitext(file_path)[1].lower()
    
    # Check if the extension is directly supported
    if file_extension in SUPPORTED_EXTENSIONS:
        return file_extension[1:]  # Remove the dot
    
    # Try to determine MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        if 'pdf' in mime_type:
            return 'pdf'
        elif 'msword' in mime_type or 'officedocument.wordprocessing' in mime_type:
            return 'doc'
        elif 'officedocument.presentation' in mime_type:
            return 'ppt'
        elif 'officedocument.spreadsheet' in mime_type:
            return 'xls'
        elif 'text/' in mime_type:
            return 'txt'
        elif 'html' in mime_type:
            return 'html'
    
    # Default to generic text
    return 'txt'

def get_recommended_loader(file_extension: str) -> str:
    """
    Get the recommended loader for the file type based on available loaders.
    """
    loaders = SUPPORTED_EXTENSIONS.get(file_extension.lower(), ['unstructured'])
    
    # Check if the recommended loaders are available
    for loader in loaders:
        if loader == 'pymupdf' and PYMUPDF_AVAILABLE:
            return 'pymupdf'
        elif loader == 'pypdf' and PYPDF_AVAILABLE:
            return 'pypdf'
        elif loader == 'docx' and DOCX_AVAILABLE:
            return 'docx'
        elif loader == 'pptx' and PPTX_AVAILABLE:
            return 'pptx'
        elif loader == 'html' and BS4_AVAILABLE:
            return 'html'
        elif loader == 'text':
            return 'text'
    
    # Fallback to unstructured if available
    if UNSTRUCTURED_AVAILABLE:
        return 'unstructured'
    
    # If nothing else works, use simple text extraction
    return 'text'

def load_metadata() -> Dict:
    """加载元数据"""
    if METADATA_FILES["load"].exists():
        try:
            with open(METADATA_FILES["load"], "r", encoding="utf-8") as f:
                metadata = json.load(f)
                # 修复路径格式
                for doc_id, doc_info in metadata.get("documents", {}).items():
                    if "input_path" not in doc_info and "original_file" in doc_info:
                        doc_info["input_path"] = doc_info["original_file"]
                    if "output_path" not in doc_info and "text_file" in doc_info:
                        doc_info["output_path"] = doc_info["text_file"]
                return metadata
        except json.JSONDecodeError:
            logger.error("Invalid JSON in metadata file. Creating new metadata.")
        return {"documents": {}}

def save_metadata(metadata: Dict) -> None:
    """保存元数据"""
    # 确保目录存在
    METADATA_FILES["load"].parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILES["load"], "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

def extract_text_pymupdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF is not installed. Please install it with 'pip install pymupdf'")
    
    doc = fitz.open(file_path)
    text = ""
    
    try:
        for page in doc:
            text += page.get_text()
    except Exception as e:
        logger.warning(f"Error extracting text with PyMuPDF: {str(e)}")
        # Fallback approach
        for page in doc:
            try:
                text += page.get_text("text")
            except Exception as e2:
                logger.warning(f"Fallback text extraction failed: {str(e2)}")
                continue
    
    return text

def extract_text_pypdf(file_path: str) -> str:
    """Extract text from PDF using PyPDF."""
    if not PYPDF_AVAILABLE:
        raise ImportError("PyPDF is not installed. Please install it with 'pip install pypdf'")
    
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_text_unstructured(file_path: str) -> str:
    """Extract text using Unstructured."""
    if not UNSTRUCTURED_AVAILABLE:
        raise ImportError("Unstructured is not installed. Please install it with 'pip install unstructured'")
    
    elements = partition(filename=file_path)
    text = "\n\n".join([str(element) for element in elements])
    return text

def extract_text_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx is not installed. Please install it with 'pip install python-docx'")
    
    doc = Document(file_path)
    text = "\n\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text

def extract_text_pptx(file_path: str) -> str:
    """Extract text from PPTX using python-pptx."""
    if not PPTX_AVAILABLE:
        raise ImportError("python-pptx is not installed. Please install it with 'pip install python-pptx'")
    
    pres = Presentation(file_path)
    text_parts = []
    
    for slide in pres.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text_parts.append(shape.text)
    
    return "\n\n".join(text_parts)

def extract_text_html(file_path: str) -> str:
    """Extract text from HTML using BeautifulSoup."""
    if not BS4_AVAILABLE:
        raise ImportError("BeautifulSoup is not installed. Please install it with 'pip install beautifulsoup4'")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        # Get text
        text = soup.get_text(separator='\n')
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def extract_text_plain(file_path: str) -> str:
    """Extract text from plain text files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with a different encoding if utf-8 fails
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()

def extract_document_text(file_path: str, loader_type: str = "auto", file_extension: str = None) -> str:
    """Extract text from a document using the specified loader."""
    if loader_type == "auto":
        if file_extension is None:
            file_extension = os.path.splitext(file_path)[1]
        loader_type = get_recommended_loader(file_extension)
    
    try:
        if loader_type == "pymupdf":
            return extract_text_pymupdf(file_path)
        elif loader_type == "pypdf":
            return extract_text_pypdf(file_path)
        elif loader_type == "docx":
            return extract_text_docx(file_path)
        elif loader_type == "pptx":
            return extract_text_pptx(file_path)
        elif loader_type == "html":
            return extract_text_html(file_path)
        elif loader_type == "unstructured":
            return extract_text_unstructured(file_path)
        else:  # text
            return extract_text_plain(file_path)
    except Exception as e:
        logger.error(f"Error extracting text with {loader_type}: {str(e)}")
        if loader_type != "text":
            logger.info("Falling back to plain text extraction")
            return extract_text_plain(file_path)
        raise

@router.get("/available-loaders")
async def get_available_loaders():
    """获取可用的加载器列表"""
    loaders = {
        "auto": "自动选择最佳加载器",
        "text": "纯文本加载器（适用于所有文本文件）"
    }
    
    if PYMUPDF_AVAILABLE:
        loaders["pymupdf"] = "PyMuPDF加载器（适用于PDF文件）"
    if PYPDF_AVAILABLE:
        loaders["pypdf"] = "PyPDF加载器（适用于PDF文件）"
    if DOCX_AVAILABLE:
        loaders["docx"] = "DOCX加载器（适用于Word文档）"
    if PPTX_AVAILABLE:
        loaders["pptx"] = "PPTX加载器（适用于PowerPoint文档）"
    if BS4_AVAILABLE:
        loaders["html"] = "HTML加载器（适用于网页文件）"
    if UNSTRUCTURED_AVAILABLE:
        loaders["unstructured"] = "Unstructured加载器（通用文档加载器）"
    
    return loaders

@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    loader: str = Form("auto")
) -> Dict[str, Any]:
    """上传文件"""
    try:
        # 生成文件ID和时间戳
        file_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建文件名
        original_filename = file.filename
        new_filename = FILE_NAMING["load"].format(
            original_name=Path(original_filename).stem,
            file_id=file_id,
            timestamp=timestamp,
            ext=Path(original_filename).suffix
        )
        
        # 构建文件路径
        file_path = LOAD_DIR / new_filename
        
        # 保存文件
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            file_size = len(content)
        
        # 更新元数据
        metadata = load_metadata()
        metadata["documents"][file_id] = {
            "id": file_id,
            "original_filename": original_filename,
            "original_file": str(file_path),
            "input_path": str(file_path),  # 添加input_path字段
            "text_file": str(LOAD_DIR / f"{new_filename}_loaded.txt"),
            "file_type": detect_file_type(original_filename),
            "loader_used": loader,
            "upload_time": datetime.datetime.now().isoformat(),
            "file_size": file_size,
            "size_bytes": file_size  # 添加size_bytes字段以保持一致性
        }
        
        save_metadata(metadata)
        
        return {
            "file_id": file_id,
            "filename": new_filename,
            "size": file_size,
            "status": "uploaded"
        }
        
    except Exception as e:
        # 如果上传失败，清理已创建的文件
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=500,
            content={
                "detail": f"文件上传失败: {str(e)}",
                "error_code": "upload_failed"
            }
        )

@router.get("/files")
async def get_files():
    """获取已上传的文件列表"""
    try:
        files = []
        # 确保目录存在
        LOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # 直接从LOAD_DIR读取文件
        for file_path in LOAD_DIR.glob("*"):
            try:
                if file_path.is_file() and not file_path.name.endswith("_loaded.txt"):
                    # 从文件名中提取UUID
                    uuid_match = re.search(r'_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_', file_path.name)
                    if uuid_match:
                        file_id = uuid_match.group(1)
                    else:
                        # 如果找不到UUID，则使用文件名生成一个稳定的ID
                        file_id = hashlib.md5(f"{file_path.name}_{file_path.stat().st_mtime}".encode()).hexdigest()
                    
                    file_info = {
                        "file_id": file_id,
                        "original_filename": file_path.name,
                        "original_file": str(file_path),
                        "input_path": str(file_path),
                        "file_type": detect_file_type(str(file_path)),
                        "size_bytes": file_path.stat().st_size,
                        "upload_time": datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                    files.append(file_info)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue
        
        # 按上传时间倒序排序
        files.sort(key=lambda x: x["upload_time"], reverse=True)
        return {"files": files}
    except Exception as e:
        logger.error(f"Error getting file list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@router.get("/files/{file_id}")
async def get_file_details(file_id: str):
    """获取文件详细信息"""
    metadata = load_metadata()
    if file_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文件不存在")
    return metadata["documents"][file_id]

@router.get("/files/{file_id}/download")
async def download_original_file(file_id: str):
    """下载原始文件"""
    metadata = load_metadata()
    if file_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_path = Path(metadata["documents"][file_id]["original_file"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        file_path,
        filename=metadata["documents"][file_id]["original_filename"],
        media_type="application/octet-stream"
    )

@router.get("/files/{file_id}/preview")
async def preview_document(
    file_id: str,
    page: int = Query(1, description="Page number to preview (for paginated documents like PDFs)")
):
    """预览文档内容"""
    try:
        # 加载元数据
        metadata = load_metadata()
        
        if file_id not in metadata["documents"]:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        document_info = metadata["documents"][file_id]
        file_path = document_info.get("original_file") or document_info.get("input_path", "")
        
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="原始文件不存在")
        
        # 获取文件扩展名
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # 对于PDF文件，尝试使用PyMuPDF生成预览
        if file_extension == ".pdf":
            try:
                import fitz
                doc = fitz.Document(file_path)  # Use Document instead of open
                if page < 1 or page > doc.page_count:
                    raise HTTPException(status_code=400, detail=f"页码超出范围 (1-{doc.page_count})")
                
                # 获取指定页面的文本
                text = doc[page-1].get_text()
                doc.close()
                
                return {
                    "content": text[:1000],  # 返回前1000个字符
                    "format": "text",
                    "total_pages": doc.page_count,
                    "current_page": page
                }
            except ImportError:
                # 如果PyMuPDF不可用，返回文本预览
                text_path = Path(document_info.get("text_file") or document_info.get("text_path", ""))
                if text_path.exists():
                    with open(text_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    return {
                        "content": text[:1000],  # 返回前1000个字符
                        "format": "text"
                    }
                else:
                    raise HTTPException(status_code=404, detail="预览文件不存在")
        else:
            # 对于其他类型的文件，返回文本预览
            text_path = Path(document_info.get("text_file") or document_info.get("text_path", ""))
            if text_path.exists():
                with open(text_path, "r", encoding="utf-8") as f:
                    text = f.read()
                return {
                    "content": text[:1000],  # 返回前1000个字符
                    "format": "text"
                }
            else:
                raise HTTPException(status_code=404, detail="预览文件不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预览文件失败: {str(e)}")
    
    raise HTTPException(status_code=400, detail="不支持的文件类型")

@router.post("/load")
async def load_document(request: Dict = Body(...)):
    """加载文档并提取文本内容"""
    try:
        file_id = request.get("file_id")
        loader_type = request.get("loader_type", "auto")
        additional_params = request.get("additional_params", {})
        
        if not file_id:
            raise HTTPException(status_code=400, detail="需要提供文件ID")
        
        logger.info(f"加载文档: file_id={file_id}, loader_type={loader_type}")
        
        # 加载元数据
        metadata = load_metadata()
        
        # 检查文件是否存在
        if file_id not in metadata["documents"]:
            logger.error(f"找不到文件ID: {file_id}")
            raise HTTPException(status_code=404, detail=f"找不到文件: {file_id}")
        
        # 获取文件信息
        file_info = metadata["documents"][file_id]
        input_path = Path(file_info["input_path"])
        
        # 确保文件存在
        if not input_path.exists():
            logger.error(f"文件不存在: {input_path}")
            raise HTTPException(status_code=404, detail=f"文件不存在: {input_path}")
        
        # 生成输出文件路径
        output_path = input_path.parent / f"{input_path.stem.replace('_loaded', '')}_text.txt"
        
        # 更新文件信息
        file_info["text_file"] = str(output_path)
        file_info["output_path"] = str(output_path)
        file_info["text_path"] = str(output_path)  # 添加text_path字段
        file_info["loader_used"] = loader_type
        file_info["load_time"] = datetime.datetime.now().isoformat()
        
        # 提取文本
        text_content = extract_document_text(
            file_path=str(input_path),  # 修改参数名
            loader_type=loader_type,
            file_extension=input_path.suffix[1:]  # 添加文件扩展名
        )
        
        # 保存提取的文本
        output_path.write_text(text_content, encoding='utf-8')
        
        # 更新文件大小信息
        file_info["text_size"] = len(text_content)
        file_info["loaded"] = True
        
        # 保存元数据
        save_metadata(metadata)
        
        return {"status": "success", "message": "文档加载成功"}
        
    except Exception as e:
        logger.error(f"加载文档时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"加载文档时出错: {str(e)}")

async def get_text_preview(document_id: str, max_chars: int = 1000) -> str:
    """Get a preview of the document's text."""
    metadata = load_metadata()
    
    if document_id not in metadata["documents"]:
        return ""
    
    document_info = metadata["documents"][document_id]
    text_path = document_info.get("text_path")
    
    if not text_path or not os.path.exists(text_path):
        return ""
    
    with open(text_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read(max_chars)
    
    return text

@router.get("/documents")
async def list_documents():
    """Get a list of all processed documents."""
    metadata = load_metadata()
    return {"documents": list(metadata["documents"].values())}

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get information about a specific document."""
    metadata = load_metadata()
    
    if document_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return metadata["documents"][document_id]

@router.get("/documents/{document_id}/text")
async def get_document_text(
    document_id: str, 
    start: Optional[int] = Query(None, description="Start position for text slice"),
    end: Optional[int] = Query(None, description="End position for text slice")
):
    """Get the extracted text of a document, optionally specifying a range."""
    metadata = load_metadata()
    
    if document_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    document_info = metadata["documents"][document_id]
    text_path = document_info["text_path"]
    
    if not os.path.exists(text_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Return a slice of the text if start and end are specified
    if start is not None:
        if end is not None:
            text = text[start:end]
        else:
            text = text[start:]
    elif end is not None:
        text = text[:end]
    
    return {"document_id": document_id, "text": text}

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, delete_files: bool = Query(True)):
    """Delete a document and optionally its associated files."""
    metadata = load_metadata()
    
    if document_id not in metadata["documents"]:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    document_info = metadata["documents"][document_id]
    
    if delete_files:
        # Delete the original file
        input_path = Path(document_info["input_path"])
        if input_path.exists():
            input_path.unlink()
        
        # Delete the text file
        text_path = Path(document_info["text_path"])
        if text_path.exists():
            text_path.unlink()
    
    # Remove from metadata
    del metadata["documents"][document_id]
    save_metadata(metadata)
    
    return {"status": "success", "message": "文件已删除"}

@router.delete("/files/{file_id}")
async def delete_file(file_id: str, delete_files: bool = Query(True)):
    """删除文件"""
    try:
        # 获取文件列表
        files = []
        for file_path in LOAD_DIR.glob("*"):
            if file_path.is_file() and not file_path.name.endswith("_loaded.txt"):
                # Extract UUID from filename
                uuid_match = re.search(r'_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_', file_path.name)
                if uuid_match:
                    current_file_id = uuid_match.group(1)
                else:
                    # If no UUID found, generate a stable ID from filename and modification time
                    current_file_id = hashlib.md5(f"{file_path.name}_{file_path.stat().st_mtime}".encode()).hexdigest()
                
                file_info = {
                    "file_id": current_file_id,
                    "original_file": str(file_path),
                    "input_path": str(file_path)
                }
                files.append(file_info)
        
        # 查找要删除的文件
        file_to_delete = None
        for file_info in files:
            if file_info["file_id"] == file_id:
                file_to_delete = Path(file_info["original_file"])
                break
        
        if not file_to_delete:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        deleted_files = []
        errors = []
        
        # 删除原始文件
        if file_to_delete.exists():
            try:
                file_to_delete.unlink()
                deleted_files.append(str(file_to_delete))
            except Exception as e:
                errors.append(f"删除原始文件失败: {str(e)}")
        
        # 删除对应的_loaded.txt文件
        loaded_file = file_to_delete.parent / f"{file_id}_loaded.txt"
        if loaded_file.exists():
            try:
                loaded_file.unlink()
                deleted_files.append(str(loaded_file))
            except Exception as e:
                errors.append(f"删除加载文件失败: {str(e)}")
        
        if errors:
            raise HTTPException(status_code=500, detail={"errors": errors})
        
        return {
            "status": "success",
            "message": "文件删除成功",
            "deleted_files": deleted_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除操作失败: {str(e)}")

@router.get("/uploads")
async def get_uploaded_files():
    """Get a list of all uploaded files from the uploads directory."""
    uploaded_files = []
    
    try:
        # List all files in the upload directory
        for file_path in LOAD_DIR.glob("*"):
            if file_path.is_file() and not file_path.name.endswith("_loaded.txt"):
                # Extract UUID from filename
                uuid_match = re.search(r'_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_', file_path.name)
                if uuid_match:
                    file_id = uuid_match.group(1)
                else:
                    # If no UUID found, generate a stable ID from filename and modification time
                    file_id = hashlib.md5(f"{file_path.name}_{file_path.stat().st_mtime}".encode()).hexdigest()
                
                file_extension = file_path.suffix.lower()
                file_size = file_path.stat().st_size
                
                # Extract timestamp
                timestamp = datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                
                file_info = {
                    "file_id": file_id,
                    "filename": file_path.name,
                    "size": file_size,
                    "file_extension": file_extension,
                    "upload_time": timestamp,
                    "file_path": str(file_path),
                    "status": "uploaded",  # Since these are raw uploaded files
                }
                
                uploaded_files.append(file_info)
                
        logger.info(f"Found {len(uploaded_files)} uploaded files")
    except Exception as e:
        logger.error(f"Error listing uploaded files: {str(e)}")
        
    return {"files": uploaded_files} 