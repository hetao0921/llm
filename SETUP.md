# RAG Framework Setup Guide

This guide will help you set up and run both the backend and frontend components of the RAG Framework.

## Backend Setup

1. Create a Python virtual environment:

   ```bash
   # For Windows
   python -m venv venv
   venv\Scripts\activate

   # For macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

2. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following content:

   ```
   OPENAI_API_KEY=your_openai_api_key_here
   # Uncomment and configure these if you want to use a specific vector database
   # VECTOR_DB_TYPE=milvus
   # MILVUS_URI=http://localhost:19530
   # VECTOR_DB_TYPE=pinecone
   # PINECONE_API_KEY=your_pinecone_api_key_here
   # PINECONE_ENVIRONMENT=your_pinecone_environment_here
   ```

4. Run the FastAPI backend:

   ```bash
   # From the project root
   cd backend
   uvicorn main:app --reload
   ```

   The backend API will be available at http://localhost:8000 and the API documentation at http://localhost:8000/docs

## Frontend Setup

1. Install Node.js dependencies:

   ```bash
   cd frontend
   npm install
   ```

2. Run the development server:

   ```bash
   npm run dev
   ```

   The frontend will be available at http://localhost:5173

## Using the RAG Framework

1. Open the frontend in your browser
2. Use the File Loading module to upload and process documents
3. Use the Document Chunking module to split documents into chunks
4. More features coming soon!

## Troubleshooting

### Backend Issues

- Make sure you've set the correct OPENAI_API_KEY in your .env file
- Check the Python version (3.8+ recommended)
- Verify all required packages are installed with `pip list`

### Frontend Issues

- Make sure Node.js is installed (v14+ recommended)
- Clear browser cache if you're seeing outdated content
- Check browser console for any JavaScript errors

If you encounter any issues, please report them in the issues section of the repository. 