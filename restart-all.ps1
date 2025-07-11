# PowerShell重启所有服务脚本
Write-Host "重启RAG框架所有服务..." -ForegroundColor Green

# 关闭可能正在运行的进程（可选）
# Write-Host "关闭现有服务..." -ForegroundColor Yellow
# Stop-Process -Name "node" -ErrorAction SilentlyContinue
# Stop-Process -Name "python" -ErrorAction SilentlyContinue

# 打开新的终端窗口启动后端
Write-Host "在新窗口中启动后端..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start-backend.ps1"

# 等待几秒，确保后端有时间启动
Start-Sleep -Seconds 2

# 打开新的终端窗口启动前端
Write-Host "在新窗口中启动前端..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start-frontend.ps1"

Write-Host "所有服务启动完毕！" -ForegroundColor Green 