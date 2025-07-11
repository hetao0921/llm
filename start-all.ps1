Write-Host "Starting RAG Framework..." -ForegroundColor Yellow

# Start the backend in a new PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-File", "$(Get-Location)\start-backend.ps1"

# Wait a moment for the backend to initialize
Start-Sleep -Seconds 2

# Start the frontend in a new PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-File", "$(Get-Location)\start-frontend.ps1"

Write-Host "RAG Framework started successfully!" -ForegroundColor Green
Write-Host "- Backend is running at: http://localhost:8000" -ForegroundColor Green
Write-Host "- Frontend is running at: http://localhost:5173" -ForegroundColor Green 