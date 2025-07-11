from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Optional, Union, Any
from enum import Enum


class FileStatus(str, Enum):
    """Enum for file processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LoaderType(str, Enum):
    """Enum for document loader types"""
    PYMUPDF = "pymupdf"
    PYPDF = "pypdf"
    UNSTRUCTURED = "unstructured"


class ChunkingStrategy(str, Enum):
    """Enum for document chunking strategies"""
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    RECURSIVE = "recursive"


class ParsingMethod(str, Enum):
    """Enum for document parsing methods"""
    FULL_TEXT = "full_text"
    BY_PAGE = "by_page"
    BY_HEADING = "by_heading"
    TABLE_EXTRACT = "table_extract"


class EmbeddingProvider(str, Enum):
    """Enum for embedding providers"""
    OPENAI = "openai"
    BEDROCK = "bedrock"
    HUGGINGFACE = "huggingface"


class VectorDBType(str, Enum):
    """Enum for vector database types"""
    MEMORY = "memory"
    MILVUS = "milvus"
    PINECONE = "pinecone"
    FAISS = "faiss"


class FileUploadResponse(BaseModel):
    """Response model for file upload"""
    file_id: str
    filename: str
    file_size: int
    content_type: str
    status: FileStatus
    message: Optional[str] = None


class DocumentLoadRequest(BaseModel):
    """Request model for loading a document"""
    file_id: str
    loader_type: LoaderType
    additional_params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DocumentChunkRequest(BaseModel):
    """Request model for chunking a document"""
    file_id: str
    strategy: ChunkingStrategy
    chunk_size: int = 1000
    chunk_overlap: int = 200
    additional_params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Model for a document chunk"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    page_number: Optional[int] = None
    chunk_index: int


class ChunkingResult(BaseModel):
    """Response model for document chunking"""
    file_id: str
    total_chunks: int
    strategy: ChunkingStrategy
    chunk_size: int
    chunk_overlap: int
    chunks: List[DocumentChunk]


class LoadingResult(BaseModel):
    """Response model for document loading"""
    file_id: str
    filename: str
    loader_type: LoaderType
    num_pages: Optional[int] = None
    content_preview: str
    metadata: Dict[str, Any]


class ApiError(BaseModel):
    """Error response model"""
    detail: str
    status_code: int = 400
    error_type: str = "BadRequest" 