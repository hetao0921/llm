# PowerShell前端启动脚本
Write-Host "启动RAG框架前端..." -ForegroundColor Green

# 进入前端目录
Set-Location -Path ".\frontend"

# 安装依赖（如果需要）
# Write-Host "安装依赖..." -ForegroundColor Yellow
# npm install

# 启动开发服务器
Write-Host "启动Vue开发服务器..." -ForegroundColor Yellow
npm run dev

# 返回上一级目录
Set-Location -Path ".." 