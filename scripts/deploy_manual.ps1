# =============================================================================
# CreditWise 非 Docker 部署脚本（Windows）
#
# 用法：.\scripts\deploy_manual.ps1
#
# 前置条件：
#   - Python ≥ 3.10（系统 PATH 或 portable-dev-env 便携式路径均可）
#   - Node.js ≥ 18（系统 PATH 或 portable-dev-env 便携式路径均可）
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

# --- Python：优先 PATH，其次 portable-dev-env ---
$portablePython = "$env:USERPROFILE\portable-dev-env\tools\python\python.exe"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python -and (Test-Path $portablePython)) {
    $python = $portablePython
    Write-Host "  使用便携式 Python: $portablePython" -ForegroundColor Cyan
} elseif (-not $python) {
    Write-Host "ERROR: Python 3 未找到（PATH 和 portable-dev-env 均未检测到）" -ForegroundColor Red
    exit 1
}
$pyExe = if ($python -is [string]) { $python } else { $python.Source }
$pyVer = & $pyExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "  Python $pyVer  ($pyExe)" -ForegroundColor Green

# --- Node.js：优先 PATH，其次 portable-dev-env ---
$portableNode = "$env:USERPROFILE\portable-dev-env\tools\nodejs\node.exe"
$portableNpm  = "$env:USERPROFILE\portable-dev-env\tools\nodejs\npm.cmd"
$node = Get-Command node -ErrorAction SilentlyContinue
$hasNode = $false
$npmCmd = "npm"
if ($node) {
    $nodeVer = & node -v
    $nodeMajor = [int]($nodeVer -replace 'v','' -split '\.')[0]
    if ($nodeMajor -ge 18) {
        $hasNode = $true
        Write-Host "  Node.js $nodeVer" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Node.js $nodeVer (需要 >=18)，跳过前端构建" -ForegroundColor Yellow
    }
} elseif (Test-Path $portableNode) {
    $nodeVer = & $portableNode -v
    $nodeMajor = [int]($nodeVer -replace 'v','' -split '\.')[0]
    if ($nodeMajor -ge 18) {
        $hasNode = $true
        $npmCmd = $portableNpm
        Write-Host "  Node.js $nodeVer (便携式)  ($portableNode)" -ForegroundColor Cyan
    } else {
        Write-Host "  WARNING: 便携式 Node.js $nodeVer (需要 >=18)，跳过前端构建" -ForegroundColor Yellow
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
    & $pyExe -m venv .venv
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
        & $npmCmd install
        & $npmCmd run build
        Pop-Location
        if (Test-Path "demo/chat/dist/index.html") {
            Write-Host "  前端构建成功" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: 构建产物未找到，请检查构建日志" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  跳过前端构建（Node.js 不可用）" -ForegroundColor Yellow
    Write-Host "  ⚠️  生产模式下需要前端构建产物，服务启动后主界面可能无法访问" -ForegroundColor Yellow
}
Write-Host ""

# [4] 环境配置
Write-Host "[4] 配置环境"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$envContent = Get-Content .env -Raw -Encoding UTF8
if ($envContent -match 'ENABLE_AUTH=') {
    $envContent = $envContent -replace 'ENABLE_AUTH=.*', "ENABLE_AUTH=$ENABLE_AUTH"
} else {
    $envContent += "`nENABLE_AUTH=$ENABLE_AUTH"
}

if (-not ($envContent -match 'LLM_MANAGER_ENCRYPTION_KEY=.+')) {
    Write-Host "  自动生成加密密钥..." -ForegroundColor Yellow
    $key = & $venvPython -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    $envContent = $envContent -replace 'LLM_MANAGER_ENCRYPTION_KEY=', "LLM_MANAGER_ENCRYPTION_KEY=$key"
    if (-not ($envContent -match 'LLM_MANAGER_ENCRYPTION_KEY=')) {
        $envContent += "`nLLM_MANAGER_ENCRYPTION_KEY=$key"
    }
    Write-Host "  加密密钥已生成（请妥善保存 .env 文件，重新部署时需保持一致）" -ForegroundColor Yellow
}
[System.IO.File]::WriteAllText((Resolve-Path ".env").Path, $envContent, [System.Text.Encoding]::UTF8)

if ($ENABLE_AUTH -eq "true") {
    if (-not (Test-Path "config/users.yaml")) {
        Copy-Item "config/users.yaml.example" "config/users.yaml"
        Write-Host "  已创建 config/users.yaml，请编辑后添加用户" -ForegroundColor Yellow
    }
}

New-Item -ItemType Directory -Force workspace, execution_states, task_results, logs, config | Out-Null
Write-Host "  环境配置完成" -ForegroundColor Green
Write-Host ""

# [5] 启动
Write-Host "[5] 启动服务"
Write-Host "  启动后端 (端口 8200)..."

$projectRoot = (Get-Location).Path
$apiDir = Join-Path $projectRoot "API"
$env:DEV_MODE = "false"
$env:API_HOST = "0.0.0.0"
$env:API_PORT = "8200"
$env:PYTHONPATH = "$projectRoot;$apiDir"
$env:PYTHONUNBUFFERED = "1"

Start-Process -FilePath $venvPython -ArgumentList (Join-Path $projectRoot "API\main.py") `
    -NoNewWindow -WorkingDirectory $projectRoot

Start-Sleep 5
$ok = $false
for ($i = 1; $i -le 6; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8200/health" -UseBasicParsing -TimeoutSec 3
        $ok = $true
        break
    } catch {
        Start-Sleep 2
    }
}

if ($ok) {
    Write-Host "  服务启动成功！" -ForegroundColor Green
} else {
    Write-Host "  警告: 健康检查未通过，请查看终端输出或 logs\server.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================"
Write-Host " 部署完成！" -ForegroundColor Green
Write-Host "============================================================"
Write-Host ""
Write-Host " 访问地址:    http://localhost:8200"
Write-Host " LLM Manager: http://localhost:8200/llm-manager"
Write-Host " API 文档:    http://localhost:8200/docs"
Write-Host " 停止服务:    .\scripts\stop_prod.ps1"
Write-Host " 查看日志:    Get-Content logs\server.log -Tail 50 -Wait"
Write-Host ""
Write-Host " 首次使用请先在 LLM Manager 中添加并激活一个 LLM 渠道。"
Write-Host ""

