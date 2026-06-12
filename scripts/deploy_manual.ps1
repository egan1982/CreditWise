# =============================================================================
# CreditWise 非 Docker 部署脚本（Windows）
#
# 用法：.\scripts\deploy_manual.ps1
#
# 前置条件：
#   - Python ≥ 3.10（推荐 .venv）
#   - Node.js ≥ 18（如需构建前端）
#   - Visual C++ 运行时
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host " CreditWise 非 Docker 手动部署 (Windows)"
Write-Host "============================================================"
Write-Host ""

# [0] 部署模式
Write-Host "[0] 选择部署模式"
Write-Host "  [1] 单用户模式"
Write-Host "  [2] 内网多用户（Basic Auth）"
$mode = Read-Host "请选择 [1/2] (默认: 1)"
if (-not $mode) { $mode = "1" }

if ($mode -eq "2") { $ENABLE_AUTH = "true" } else { $ENABLE_AUTH = "false" }
Write-Host "ENABLE_AUTH=$ENABLE_AUTH"
Write-Host ""

# [1] 依赖检查
Write-Host "[1] 依赖检查"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Host "ERROR: Python 3 未安装" -ForegroundColor Red
    exit 1
}
$pyVer = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "  Python $pyVer" -ForegroundColor Green

# Node
$node = Get-Command node -ErrorAction SilentlyContinue
$hasNode = $false
if ($node) {
    $nodeVer = & node -v
    $nodeMajor = [int]($nodeVer -replace 'v','' -split '\.')[0]
    if ($nodeMajor -ge 18) {
        $hasNode = $true
        Write-Host "  Node.js $nodeVer" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Node.js $nodeVer (need >=18), skip frontend build" -ForegroundColor Yellow
    }
} else {
    Write-Host "  WARNING: Node.js 未安装，将跳过前端构建" -ForegroundColor Yellow
}

# Port check
foreach ($port in @(8200, 8100)) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object State -eq Listen
    if ($conn) {
        Write-Host "ERROR: 端口 $port 已被占用" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  端口 8200, 8100 可用" -ForegroundColor Green

# Disk
$disk = Get-PSDrive -Name (Get-Location).Drive.Name
if ($disk.Free -lt 2GB) {
    Write-Host "ERROR: 磁盘空间不足 2GB" -ForegroundColor Red
    exit 1
}
Write-Host ""

# [2] 虚拟环境
Write-Host "[2] 创建虚拟环境"
$venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $python -m venv .venv
}
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
Write-Host "  Python 依赖安装完成" -ForegroundColor Green
Write-Host ""

# [3] 前端构建
Write-Host "[3] 构建前端"
if ($hasNode) {
    if (Test-Path "demo/chat/package.json") {
        Write-Host "  构建主前端..."
        Push-Location "demo/chat"
        npm install
        npm run build
        Pop-Location
    }
} else {
    Write-Host "  跳过前端构建" -ForegroundColor Yellow
}
Write-Host ""

# [4] 环境配置
Write-Host "[4] 配置环境"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$envContent = Get-Content .env -Raw
if ($envContent -match 'ENABLE_AUTH=') {
    $envContent = $envContent -replace 'ENABLE_AUTH=.*', "ENABLE_AUTH=$ENABLE_AUTH"
} else {
    $envContent += "`nENABLE_AUTH=$ENABLE_AUTH"
}

if (-not ($envContent -match 'LLM_MANAGER_ENCRYPTION_KEY=.+')) {
    Write-Host "  自动生成加密密钥..." -ForegroundColor Yellow
    $key = & $venvPython -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    $envContent += "`nLLM_MANAGER_ENCRYPTION_KEY=$key"
}
Set-Content .env $envContent -NoNewline

if ($ENABLE_AUTH -eq "true") {
    if (-not (Test-Path "config/users.yaml")) {
        Copy-Item "config/users.yaml.example" "config/users.yaml"
    }
}

New-Item -ItemType Directory -Force workspace,execution_states,task_results,logs | Out-Null
Write-Host ""

# [5] 启动
Write-Host "[5] 启动服务"
Write-Host "  启动后端 (端口 8200)..."
Start-Process -FilePath $venvPython -ArgumentList "API/main.py" -NoNewWindow -WorkingDirectory (Get-Location)

Start-Sleep 3
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8200/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "  服务启动成功！" -ForegroundColor Green
} catch {
    Write-Host "  警告: 健康检查失败，请手动验证" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================"
Write-Host " 部署完成！" -ForegroundColor Green
Write-Host "============================================================"
Write-Host ""
Write-Host " 访问地址: http://localhost:8200"
Write-Host ""
