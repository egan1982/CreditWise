# DeepAnalyze 环境初始化脚本
# 用于初始化项目虚拟环境并安装依赖

param(
    [switch]$Force = $false,
    [switch]$NoActivate = $false
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$pipExe = Join-Path $venvPath "Scripts\pip.exe"
$requirementsFile = Join-Path $projectRoot "requirements.txt"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze 环境初始化" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 检查虚拟环境是否已存在
if (Test-Path $venvPath) {
    if ($Force) {
        Write-Host "删除现有虚拟环境..." -ForegroundColor Yellow
        Remove-Item -Path $venvPath -Recurse -Force
    } else {
        Write-Host "虚拟环境已存在: $venvPath" -ForegroundColor Green
        if (-not $NoActivate) {
            Write-Host "激活虚拟环境..." -ForegroundColor Green
            & "$venvPath\Scripts\Activate.ps1"
        }
        exit 0
    }
}

# 创建虚拟环境
Write-Host "创建虚拟环境..." -ForegroundColor Green
$portablePython = "C:\Users\fjzheng\portable-dev-env\tools\python\python.exe"

if (Test-Path $portablePython) {
    & $portablePython -m venv $venvPath
} else {
    python -m venv $venvPath
}

if (-not (Test-Path $pythonExe)) {
    Write-Host "虚拟环境创建失败" -ForegroundColor Red
    exit 1
}

Write-Host "虚拟环境创建成功: $venvPath" -ForegroundColor Green

# 升级 pip
Write-Host "升级 pip..." -ForegroundColor Green
& $pythonExe -m pip install --upgrade pip -q

# 安装依赖
if (Test-Path $requirementsFile) {
    Write-Host "安装依赖包..." -ForegroundColor Green
    & $pipExe install -r $requirementsFile -q
    Write-Host "依赖包安装完成" -ForegroundColor Green
} else {
    Write-Host "requirements.txt 不存在，跳过依赖安装" -ForegroundColor Yellow
}

# 激活虚拟环境
if (-not $NoActivate) {
    Write-Host "激活虚拟环境..." -ForegroundColor Green
    & "$venvPath\Scripts\Activate.ps1"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "环境初始化完成" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
