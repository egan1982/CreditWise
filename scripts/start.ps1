# DeepAnalyze 启动脚本 - 私有化部署
param(
    [int]$Port = 8200,
    [string]$HostAddr = "0.0.0.0"
)

$ErrorActionPreference = "Stop"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze v1.0.0 - 私有化部署" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# 设置环境变量
$env:API_PORT = $Port
$env:API_HOST = $HostAddr
$env:DEV_MODE = "false"           # 生产模式
$env:DATA_DIR = "$PSScriptRoot\data"
$env:WORKSPACE_BASE_DIR = "$PSScriptRoot\data\workspace"
$env:PYTHONUNBUFFERED = 1

# 创建必要目录
$dataDir = $env:DATA_DIR
$workspaceDir = $env:WORKSPACE_BASE_DIR

if (!(Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    Write-Host "✓ 创建数据目录: $dataDir" -ForegroundColor Green
}

if (!(Test-Path $workspaceDir)) {
    New-Item -ItemType Directory -Path $workspaceDir -Force | Out-Null
    Write-Host "✓ 创建工作区目录: $workspaceDir" -ForegroundColor Green
}

# 检查数据库（提示用户是初始状态）
$dbPath = Join-Path $dataDir "llm_manager.db"
if (!(Test-Path $dbPath)) {
    Write-Host ""
    Write-Host "ℹ️  首次启动：LLM Manager 数据库将自动创建" -ForegroundColor Yellow
    Write-Host "   请启动后访问 http://localhost:$Port/llm-manager 添加 LLM 配置" -ForegroundColor Yellow
}

# 查找 Python
$pythonExe = "python"
if (Test-Path "$PSScriptRoot\runtime\python\python.exe") {
    $pythonExe = "$PSScriptRoot\runtime\python\python.exe"
}

# 检查 Python 环境
Write-Host ""
Write-Host "检查 Python 环境..." -ForegroundColor Yellow
try {
    $pyVersion = & $pythonExe --version 2>&1
    Write-Host "✓ Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 无法找到 Python，请确保已安装" -ForegroundColor Red
    exit 1
}

# 设置 PYTHONPATH
$env:PYTHONPATH = "$PSScriptRoot;$PSScriptRoot\API"

Write-Host ""
Write-Host "🚀 启动服务..." -ForegroundColor Green
Write-Host "   API 地址: http://$HostAddr`:$Port" -ForegroundColor Gray
Write-Host "   前端地址: http://$HostAddr`:$Port" -ForegroundColor Gray
Write-Host "   LLM Manager: http://$HostAddr`:$Port/llm-manager" -ForegroundColor Gray
Write-Host ""

# 启动服务
& $pythonExe -m API.main
