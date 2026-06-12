# =============================================================================
# CreditWise 生产环境启动（Windows）
#
# 用法：.\scripts\start_prod.ps1
#
# 与 start_dev.ps1 的区别：
#   - DEV_MODE=false，后端直接提供前端静态文件（无需 3000/3001）
#   - API_HOST=0.0.0.0，允许内网其他机器访问
#   - 不启动前端 dev server，不打开浏览器
#   - 日志写入 logs/server.log
# =============================================================================
param(
    [int]$Port = 8200,
    [string]$HostAddr = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot | Split-Path -Parent
$venvPath = Join-Path $projectRoot ".venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$apiMain = Join-Path $projectRoot "API\main.py"
$logDir = Join-Path $projectRoot "logs"
$pidFile = Join-Path $projectRoot ".app_pids.txt"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " CreditWise 生产模式启动" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# [1] 端口占用检查
Write-Host "[1] 端口占用检查" -ForegroundColor Yellow
foreach ($p in @($Port, 8100)) {
    $conn = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | Where-Object State -eq Listen
    if ($conn) {
        $existingPid = $conn.OwningProcess
        Write-Host "  端口 $p 已被 PID $existingPid 占用，尝试终止..." -ForegroundColor Yellow
        taskkill /PID $existingPid /F /T 2>$null | Out-Null
        Start-Sleep 1
    }
}
Write-Host "  端口 $Port, 8100 可用" -ForegroundColor Green

# [2] Python 环境
Write-Host "[2] 检查 Python 环境" -ForegroundColor Yellow
if (-not (Test-Path $pythonExe)) {
    Write-Host "  虚拟环境不存在，尝试使用系统 Python..." -ForegroundColor Yellow
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonExe) {
        Write-Host "ERROR: Python 未找到" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  Python: $pythonExe" -ForegroundColor Green

if (-not (Test-Path $apiMain)) {
    Write-Host "ERROR: API 主文件不存在: $apiMain" -ForegroundColor Red
    exit 1
}

# [3] 日志目录
New-Item -ItemType Directory -Force $logDir | Out-Null

# [4] 设置环境变量
Write-Host "[3] 设置环境变量" -ForegroundColor Yellow
$env:API_PORT = $Port
$env:API_HOST = $HostAddr
$env:DEV_MODE = "false"
$env:PYTHONUNBUFFERED = 1
Write-Host "  API_PORT=$Port, API_HOST=$HostAddr, DEV_MODE=false" -ForegroundColor Green

# [5] 启动
Write-Host "[4] 启动服务" -ForegroundColor Green
Set-Location $projectRoot

$apiDir = Join-Path $projectRoot "API"
$logFile = Join-Path $logDir "server.log"

$procInfo = New-Object System.Diagnostics.ProcessStartInfo
$procInfo.FileName = $pythonExe
$procInfo.Arguments = $apiMain
$procInfo.UseShellExecute = $false
$procInfo.RedirectStandardOutput = $true
$procInfo.RedirectStandardError = $true
$procInfo.WorkingDirectory = $projectRoot
$procInfo.EnvironmentVariables["PYTHONPATH"] = "$projectRoot;$apiDir"

$proc = [System.Diagnostics.Process]::Start($procInfo)
$pid = $proc.Id

# 记录 PID
$pid | Out-File -FilePath $pidFile

Write-Host "  进程 PID: $pid" -ForegroundColor Green
Write-Host "  日志文件: $logFile" -ForegroundColor Gray

# [6] 健康检查
Write-Host "[5] 健康检查" -ForegroundColor Yellow
for ($i = 1; $i -le 10; $i++) {
    Start-Sleep 3
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 3
        Write-Host "  服务就绪 (尝试 $i/10)" -ForegroundColor Green
        break
    } catch {
        if ($i -eq 10) {
            Write-Host "  WARNING: 健康检查失败，请查看日志" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " 启动完成！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host " 访问地址: http://$(hostname):$Port"
Write-Host " 停止服务: .\scripts\stop_prod.ps1"
Write-Host " 查看日志: Get-Content logs\server.log -Tail 50"
Write-Host ""
