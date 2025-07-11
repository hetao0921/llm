<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
# llm
=======
# llm
=======
# 手工制作一个RAG框架
>>>>>>> bce0580 (提交本地)
=======
# RAG Framework
>>>>>>> ff13d8e (20250711)

A comprehensive Retrieval-Augmented Generation (RAG) framework for document processing and AI-powered knowledge retrieval.

## Features

- **File Loading**: Support for multiple document formats and loading methods (PyMuPDF, PyPDF, Unstructured)
- **Document Chunking**: Various text splitting strategies for optimal context segmentation
- **Document Parsing**: Multiple parsing options for different document structures
- **Vector Embedding**: Support for multiple embedding providers (OpenAI, Bedrock, HuggingFace)
- **Vector Indexing**: Integration with multiple vector databases (Milvus, Pinecone, etc.)
- **Text Generation**: AI-powered text generation with context awareness

## Project Structure

```
rag-framework/
├── backend/                # FastAPI backend
│   ├── config/             # Configuration settings
│   ├── models/             # Pydantic data models
│   ├── services/           # Service modules
│   └── main.py             # FastAPI application entry point
├── frontend/               # Vue.js frontend
│   └── src/                # Frontend source code
└── requirements.txt        # Python dependencies
```

## Setup & Installation

### Backend Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 
   ```

3. Create a `.env` file in the project root with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   # Add other API keys as needed
   ```

4. Run the FastAPI server:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

5. Access the API documentation at http://localhost:8000/docs

### Frontend Setup (coming soon)

The Vue.js frontend is under development and will be available soon.

## API Endpoints

### Document Loading

- `POST /api/loading/upload`: Upload a new document
- `POST /api/loading/load`: Load and process an uploaded document
- `GET /api/loading/files`: Get a list of all uploaded files
- `GET /api/loading/files/{file_id}`: Get details about a specific file
- `DELETE /api/loading/files/{file_id}`: Delete a file

### Document Chunking

- `POST /api/chunking/chunk`: Split a document into chunks
- `GET /api/chunking/chunks/{file_id}`: Get chunks for a specific document
- `DELETE /api/chunking/chunks/{file_id}`: Delete chunks for a document

## License

<<<<<<< HEAD
<<<<<<< HEAD
1.  使用 Readme\_XXX.md 来支持不同的语言，例如 Readme\_en.md, Readme\_zh.md
2.  Gitee 官方博客 [blog.gitee.com](https://blog.gitee.com)
3.  你可以 [https://gitee.com/explore](https://gitee.com/explore) 这个地址来了解 Gitee 上的优秀开源项目
4.  [GVP](https://gitee.com/gvp) 全称是 Gitee 最有价值开源项目，是综合评定出的优秀开源项目
5.  Gitee 官方提供的使用手册 [https://gitee.com/help](https://gitee.com/help)
6.  Gitee 封面人物是一档用来展示 Gitee 会员风采的栏目 [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)
>>>>>>> 8b81175 (Initial commit)
=======
>>>>>>> bce0580 (提交本地)
=======
MIT 
>>>>>>> ff13d8e (20250711)
