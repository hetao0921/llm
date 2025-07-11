@echo off
echo Starting RAG Framework Backend...
cd backend
uvicorn main:app --reload --port 8000 