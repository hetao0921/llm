@echo off
echo Starting RAG Framework...
echo.
echo Starting backend server...
start cmd /k "start-backend.bat"
timeout /t 5
echo Starting frontend server...
start cmd /k "start-frontend.bat"
echo.
echo RAG Framework is starting. You can access the application at http://localhost:5173
echo Press any key to close this window (the application will continue running)
pause > nul 