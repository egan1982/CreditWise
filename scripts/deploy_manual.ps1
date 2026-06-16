# =============================================================================
# CreditWise Windows 一键部署
# 用法: .\scripts\deploy_manual.ps1
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

# Python (所有 Python 内联代码用变量存储，避免单引号)
$PY_CHK = "import sys; print(sys.version_info.major * 100 + sys.version_info.minor)"
$PY_VER_CODE = "import sys; v=sys.version_info; print(str(v.major)+'.'+str(v.minor)+'.'+str(v.micro))"
$pyExe = $null
foreach ($cmd in @("python", "python3")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if (-not $found) { continue }
    # 跳过 Microsoft Store 占位符（实际没有安装 Python 的假入口）
    if ($found.Source -match "WindowsApps") { continue }
    try {
        $verCheck = & $found.Source -c $PY_CHK 2>$null
        if ($LASTEXITCODE -eq 0 -and [int]$verCheck -ge 310) {
            $pyExe = $found.Source
            break
        }
    } catch {}
}
if (-not $pyExe) {
    Write-Host "ERROR: 未找到 Python 3.10+。请安装 Python 并确保其已加入系统 PATH。" -ForegroundColor Red
    Write-Host "       下载地址: https://www.python.org/downloads/" -ForegroundColor Gray
    exit 1
}
$pyVer = & $pyExe -c $PY_VER_CODE
Write-Host "  Python $pyVer  ($pyExe)" -ForegroundColor Green

# Node.js
$hasNode = $false
$npmCmd = $null
$nodeFound = Get-Command node -ErrorAction SilentlyContinue
if ($nodeFound) {
    $nodeVer = & node -v
    $nodeMajor = [int]($nodeVer -replace "v","" -split "\.")[0]
    if ($nodeMajor -ge 18) {
        $hasNode = $true
        $npmExe = Get-Command npm -ErrorAction SilentlyContinue
        if ($npmExe) { $npmCmd = $npmExe.Source } else { $npmCmd = "npm" }
        Write-Host "  Node.js $nodeVer" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Node.js $nodeVer 版本过低(需要>=18), 将跳过前端构建" -ForegroundColor Yellow
    }
} else {
    Write-Host "  WARNING: 未在 PATH 中找到 Node.js, 将跳过前端构建" -ForegroundColor Yellow
}

# 端口检查
$portBlocked = $false
foreach ($port in @(8200, 8100)) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object State -eq Listen
    if ($conn) {
        $blockPid = $conn.OwningProcess
        Write-Host "  端口 $port 已被 PID $blockPid 占用" -ForegroundColor Yellow
        $portBlocked = $true
    }
}
if ($portBlocked) {
    $choice = Read-Host "  是否强制结束占用进程? [y/N]"
    if ($choice -eq "y" -or $choice -eq "Y") {
        foreach ($port in @(8200, 8100)) {
            $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object State -eq Listen
            if ($conn) {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                Write-Host "  已终止 PID $($conn.OwningProcess) (端口 $port)" -ForegroundColor Green
            }
        }
        Start-Sleep 1
    } else {
        Write-Host "  请手动释放端口后重试" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  端口 8200, 8100 可用" -ForegroundColor Green

# 磁盘
$disk = Get-PSDrive -Name (Get-Location).Drive.Name
if ($disk.Free -lt 2GB) {
    $freeGB = [math]::Round($disk.Free / 1GB, 1)
    Write-Host "ERROR: 磁盘可用空间不足 2GB（当前 ${freeGB} GB）" -ForegroundColor Red
    exit 1
}
Write-Host ""

# [2] 虚拟环境
Write-Host "[2] 创建虚拟环境"
$projectRoot = (Get-Location).Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  创建 .venv ..."
    # 尝试 venv (Python 3.3+)，失败则回退到 virtualenv
    $venvOk = $false
    try {
        & $pyExe -m venv .venv 2>$null
        if ($LASTEXITCODE -eq 0) { $venvOk = $true }
    } catch {}
    if (-not $venvOk) {
        Write-Host "  venv 不可用，尝试 virtualenv ..."
        try {
            & $pyExe -m pip install virtualenv -q 2>$null
            & $pyExe -m virtualenv .venv 2>$null
            if ($LASTEXITCODE -eq 0) { $venvOk = $true }
        } catch {}
    }
    if (-not $venvOk) {
        Write-Host "ERROR: 无法创建虚拟环境 (venv/virtualenv 均失败)" -ForegroundColor Red
        Write-Host "       请确保 Python 安装完整或手动创建 .venv" -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path $venvPython)) {
        Write-Host "ERROR: .venv 创建后未找到 python.exe" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  安装 Python 依赖（首次约需 3-5 分钟）..."
& $venvPython -m pip install --upgrade pip -q
& $venvPython -m pip install -r requirements.txt
Write-Host "  Python 依赖安装完成" -ForegroundColor Green
Write-Host ""

# [3] 前端构建
Write-Host "[3] 构建前端"
if ($hasNode) {
    if (Test-Path "demo\chat\package.json") {
        Write-Host "  npm install ..."
        Push-Location "demo\chat"
        & $npmCmd install
        Write-Host "  npm run build ..."
        & $npmCmd run build
        Pop-Location
        if (Test-Path "demo\chat\dist\index.html") {
            Write-Host "  前端构建成功" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: 构建产物未找到" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  跳过前端构建（Node.js 不可用）" -ForegroundColor Yellow
}
Write-Host ""


# [4] 环境配置
Write-Host "[4] 配置环境"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

# 逐行读写 .env — 不用任何单引号字符串，全用双引号变量规避编码问题
$envPath = (Resolve-Path ".env").Path
$envLines = [System.IO.File]::ReadAllLines($envPath, [System.Text.Encoding]::UTF8)
$CK_AUTH = "ENABLE_AUTH="
$CK_ENCR = "LLM_MANAGER_ENCRYPTION_KEY="

$needKey = $true
foreach ($line in $envLines) {
    $t = $line.Trim()
    if ($t.StartsWith($CK_ENCR) -and $t.Length -gt $CK_ENCR.Length) {
        $needKey = $false
        break
    }
}
$newKey = $null
if ($needKey) {
    Write-Host "  自动生成加密密钥..." -ForegroundColor Yellow
    $FK_CODE = "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    $newKey = & $venvPython -c $FK_CODE
    Write-Host "  [注意] 加密密钥已写入 .env，重新部署时请保留此文件" -ForegroundColor Yellow
}

$newLines = [System.Collections.Generic.List[string]]::new()
$authSet = $false
$keySet = $false
foreach ($line in $envLines) {
    $t = $line.Trim()
    if ($t.StartsWith($CK_AUTH)) {
        $newLines.Add($CK_AUTH + $ENABLE_AUTH)
        $authSet = $true
    } elseif ($t.StartsWith($CK_ENCR) -and $newKey) {
        $newLines.Add($CK_ENCR + $newKey)
        $keySet = $true
    } else {
        $newLines.Add($line)
    }
}
if (-not $authSet) { $newLines.Add($CK_AUTH + $ENABLE_AUTH) }
if ($newKey -and -not $keySet) { $newLines.Add($CK_ENCR + $newKey) }

[System.IO.File]::WriteAllLines($envPath, $newLines, [System.Text.Encoding]::UTF8)

if ($ENABLE_AUTH -eq "true") {
    if (-not (Test-Path "config\users.yaml")) {
        Copy-Item "config\users.yaml.example" "config\users.yaml"
        Write-Host "  已创建 config/users.yaml，请编辑并添加用户账号" -ForegroundColor Yellow
    }
}

New-Item -ItemType Directory -Force workspace, execution_states, task_results, logs, config | Out-Null
Write-Host "  环境配置完成" -ForegroundColor Green
Write-Host ""

# [5] 启动
Write-Host "[5] 启动服务"
$apiDir = Join-Path $projectRoot "API"
$env:DEV_MODE = "false"
$env:API_HOST = "0.0.0.0"
$env:API_PORT = "8200"
$env:ENABLE_AUTH = $ENABLE_AUTH
$env:PYTHONPATH = "$projectRoot;$apiDir"
$env:PYTHONUNBUFFERED = "1"

Start-Process -FilePath $venvPython -ArgumentList (Join-Path $projectRoot "API\main.py") -NoNewWindow -WorkingDirectory $projectRoot

Write-Host "  等待服务就绪..."
$ok = $false
for ($i = 1; $i -le 10; $i++) {
    Start-Sleep 3
    try {
        Invoke-WebRequest -Uri "http://localhost:8200/health" -UseBasicParsing -TimeoutSec 3 | Out-Null
        $ok = $true
        break
    } catch {}
}

if ($ok) {
    Write-Host "  服务启动成功！" -ForegroundColor Green
} else {
    Write-Host "  WARNING: 健康检查未通过，请查看终端输出排查问题" -ForegroundColor Yellow
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
