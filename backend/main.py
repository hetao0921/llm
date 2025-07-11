from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import os
from pathlib import Path
from config.settings import (
    LOAD_DIR, CHUNK_DIR, PARSE_DIR, EMBEDDING_DIR, 
    INDEXING_DIR, GENERATION_DIR, METADATA_FILES
)

# 导入服务模块
from services import (
    loading_service, parsing_service, chunking_service, 
    embedding_service, indexing_service, generation_service
)

# 创建FastAPI应用
app = FastAPI(title="RAG Framework API")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

# 添加API路由
app.include_router(loading_service.router, prefix="/api/loading", tags=["文件加载"])
app.include_router(parsing_service.router, prefix="/api/parsing", tags=["文档解析"])
app.include_router(chunking_service.router, prefix="/api/chunking", tags=["文档分块"])
app.include_router(embedding_service.router, prefix="/api/embedding", tags=["向量嵌入"])
app.include_router(indexing_service.router, prefix="/api/indexing", tags=["向量索引"])
app.include_router(generation_service.router, prefix="/api/generation", tags=["文本生成"])

# 确保数据目录存在
@app.on_event("startup")
async def startup_event():
    # 创建所有必要的目录
    for dir_path in [LOAD_DIR, CHUNK_DIR, PARSE_DIR, EMBEDDING_DIR, INDEXING_DIR, GENERATION_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # 确保所有元数据文件所在的目录存在
    for metadata_file in METADATA_FILES.values():
        metadata_file.parent.mkdir(parents=True, exist_ok=True)

# 添加请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 根路由
@app.get("/")
async def root():
    return {
        "message": "Welcome to RAG Framework API",
        "endpoints": {
            "loading": "/api/loading",
            "parsing": "/api/parsing",
            "chunking": "/api/chunking",
            "embedding": "/api/embedding",
            "indexing": "/api/indexing",
            "generation": "/api/generation"
        }
    }

# 健康检查
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "loading": True,
            "parsing": True,
            "chunking": True,
            "embedding": True,
            "indexing": True,
            "generation": True
        }
    }

# 运行应用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 