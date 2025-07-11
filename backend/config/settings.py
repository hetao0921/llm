import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# 基础数据目录 - 使用绝对路径
BACKEND_DIR = Path(__file__).parent.parent
BASE_DATA_DIR = BACKEND_DIR / "data"

# 各功能的目录
# 文件加载：输入来自用户上传，输出到 load 目录
LOAD_DIR = BASE_DATA_DIR / "load"

# 文档分块：输入从 load 目录读取，输出到 chunk 目录
CHUNK_DIR = BASE_DATA_DIR / "chunk"

# 文档解析：输入来自用户上传，输出到 parse 目录
PARSE_DIR = BASE_DATA_DIR / "parse"

# 向量嵌入：输入从 chunk 目录读取，输出到 embedding 目录
EMBEDDING_DIR = BASE_DATA_DIR / "embedding"

# 向量索引：输入从 embedding 目录读取，输出到 indexing 目录
INDEXING_DIR = BASE_DATA_DIR / "indexing"

# 文本生成：输入从 indexing 目录读取，输出到 generation 目录
GENERATION_DIR = BASE_DATA_DIR / "generation"

# 元数据文件
METADATA_FILES = {
    "load": LOAD_DIR / "metadata.json",
    "chunk": CHUNK_DIR / "metadata.json",
    "parse": PARSE_DIR / "metadata.json",
    "embedding": EMBEDDING_DIR / "metadata.json",
    "indexing": INDEXING_DIR / "metadata.json",
    "generation": GENERATION_DIR / "metadata.json"
}

# 文件命名格式
FILE_NAMING = {
    "load": "{original_name}_{file_id}_{timestamp}_loaded{ext}",
    "chunk": "{original_name}_{file_id}_{timestamp}_chunked{ext}",
    "parse": "{original_name}_{file_id}_{timestamp}_parsed{ext}",
    "embedding": "{original_name}_{file_id}_{timestamp}_embedded{ext}",
    "indexing": "{original_name}_{file_id}_{timestamp}_indexed{ext}",
    "generation": "{original_name}_{file_id}_{timestamp}_generated{ext}"
}

# 确保所有目录存在
for dir_path in [LOAD_DIR, CHUNK_DIR, PARSE_DIR, EMBEDDING_DIR, INDEXING_DIR, GENERATION_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 确保所有元数据文件所在的目录存在
for metadata_file in METADATA_FILES.values():
    metadata_file.parent.mkdir(parents=True, exist_ok=True)

# OpenAI API settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_GENERATION_MODEL = "gpt-3.5-turbo"

# Document processing settings
CHUNK_SIZE_DEFAULT = 1000
CHUNK_OVERLAP_DEFAULT = 200
MAX_FILE_SIZE_MB = 50  # Maximum file size in MB

# Vector database settings
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "memory")  # Options: memory, milvus, pinecone
MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "") 