# RAG Framework

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

MIT 