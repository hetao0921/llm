# PowerShell后端启动脚本
Write-Host "启动RAG框架后端..." -ForegroundColor Green

# 激活虚拟环境（如果存在）
if (Test-Path "venv/Scripts/Activate.ps1") {
    . ./venv/Scripts/Activate.ps1
} elseif (Test-Path ".venv/Scripts/Activate.ps1") {
    . ./.venv/Scripts/Activate.ps1
}

# 安装或更新依赖
Write-Host "Installing/updating dependencies..."
pip install -r backend/requirements.txt

# 创建必要的目录
$directories = @(
    "data",
    "data/load",
    "data/metadata",
    "data/chunks",
    "data/embeddings",
    "data/indexes"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir
        Write-Host "Created directory: $dir"
    }
}

# 启动后端服务
Write-Host "Starting backend service..."
try {
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
} catch {
    Write-Host "Error starting backend service: $_"
    exit 1
} 