# PowerShell script to start RAG application with chunking features

# Set console colors
$host.UI.RawUI.BackgroundColor = "Black"
$host.UI.RawUI.ForegroundColor = "White"
Clear-Host

# Display welcome message
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "        RAG Document Chunking System" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Display instructions
Write-Host "Instructions:" -ForegroundColor Yellow
Write-Host "1. This script will start backend and frontend services" -ForegroundColor White
Write-Host "2. Backend service will run at http://localhost:8000" -ForegroundColor White
Write-Host "3. Frontend service will run at http://localhost:5173" -ForegroundColor White
Write-Host "4. Chunked data will be saved in backend/data/processed/chunks directory" -ForegroundColor White
Write-Host ""

Write-Host "Document Chunking Steps:" -ForegroundColor Yellow
Write-Host "1. First upload and process documents in the File Loading page" -ForegroundColor White
Write-Host "2. Then select processed documents in the Document Chunking page" -ForegroundColor White
Write-Host "3. Choose a chunking strategy:" -ForegroundColor White
Write-Host "   - Fixed Size (Characters): Chunk by character count" -ForegroundColor White
Write-Host "   - By Sentence Length: Chunk by number of sentences" -ForegroundColor White
Write-Host "   - By Paragraph: Chunk by number of paragraphs" -ForegroundColor White
Write-Host "   - By Page: Chunk by document pages" -ForegroundColor White
Write-Host "4. Set chunking parameters and click 'Process Chunking'" -ForegroundColor White
Write-Host "5. View, preview, and manage chunk content" -ForegroundColor White
Write-Host ""

# Confirm starting services
$confirmation = Read-Host "Start services now? (y/n)"
if ($confirmation -ne 'y') {
    Write-Host "Startup cancelled." -ForegroundColor Red
    exit
}

# Kill processes that might be already running
Write-Host "Stopping any services that might be running..." -ForegroundColor Yellow
try {
    Stop-Process -Name "node" -ErrorAction SilentlyContinue
    Stop-Process -Name "python" -ErrorAction SilentlyContinue
} catch {
    # Ignore errors
}

# Start backend service
Write-Host "Starting backend service..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; .\start-backend.ps1"

# Wait for backend to start
Start-Sleep -Seconds 3

# Start frontend service
Write-Host "Starting frontend service..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; .\start-frontend.ps1"

Write-Host ""
Write-Host "Services are starting, please wait..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
Write-Host "Done! Visit http://localhost:5173 in your browser" -ForegroundColor Green 