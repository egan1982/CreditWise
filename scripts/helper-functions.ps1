# DeepAnalyze 启动辅助函数
# 提供端口管理、虚拟环境检测等功能

function Test-PortInUse {
    param (
        [int]$Port
    )
    
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $true
    } catch {
        return $false
    }
}

function Get-ProcessUsingPort {
    param (
        [int]$Port
    )
    
    try {
        $process = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($process) {
            $processId = $process.OwningProcess
            $processName = Get-Process -Id $processId -ErrorAction SilentlyContinue
            return @{
                ProcessId = $processId
                ProcessName = $processName.ProcessName
            }
        }
        return $null
    } catch {
        return $null
    }
}

function Stop-ProcessUsingPort {
    param (
        [int]$Port,
        [switch]$Force
    )
    
    $processInfo = Get-ProcessUsingPort -Port $Port
    if ($processInfo) {
        Write-Host "端口 $Port 被进程 $($processInfo.ProcessName) (PID: $($processInfo.ProcessId)) 占用" -ForegroundColor Yellow
        
        if ($Force) {
            try {
                Stop-Process -Id $processInfo.ProcessId -Force
                Write-Host "已强制终止进程 $($processInfo.ProcessName)" -ForegroundColor Green
                Start-Sleep -Seconds 2
                return $true
            } catch {
                Write-Host "无法终止进程: $($_.Exception.Message)" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "请手动终止进程或使用 -Force 参数强制终止" -ForegroundColor Yellow
            return $false
        }
    }
    return $true
}

function Ensure-PortAvailable {
    param (
        [int]$Port,
        [switch]$Force
    )
    
    if (Test-PortInUse -Port $Port) {
        Write-Host "警告: 端口 $Port 已被占用" -ForegroundColor Yellow
        return Stop-ProcessUsingPort -Port $Port -Force:$Force
    }
    return $true
}

function Test-VirtualEnvironment {
    param (
        [string]$VenvPath = ".\.venv"
    )
    
    # 检查虚拟环境目录是否存在
    if (-not (Test-Path $VenvPath)) {
        return @{
            Exists = $false
            Valid = $false
            Reason = "虚拟环境目录不存在"
        }
    }
    
    # 检查Python可执行文件是否存在
    $pythonExe = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        return @{
            Exists = $true
            Valid = $false
            Reason = "虚拟环境Python可执行文件不存在"
        }
    }
    
    # 检查虚拟环境是否可以激活
    try {
        $result = & $pythonExe -c "import sys; print(sys.prefix)" 2>$null
        if ($result -eq (Get-Item $VenvPath).FullName) {
            return @{
                Exists = $true
                Valid = $true
                Reason = "虚拟环境有效"
            }
        }
    } catch {
        # 忽略错误，继续检查
    }
    
    return @{
        Exists = $true
        Valid = $false
        Reason = "虚拟环境可能损坏"
    }
}

function Install-VirtualEnvironment {
    param (
        [string]$VenvPath = ".\.venv",
        [string]$PythonPath = "python"
    )
    
    try {
        Write-Host "正在创建虚拟环境: $VenvPath" -ForegroundColor Yellow
        
        # 尝试使用指定的Python创建虚拟环境
        $result = & $PythonPath -m venv $VenvPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "创建虚拟环境失败: $result" -ForegroundColor Red
            return $false
        }
        
        Write-Host "虚拟环境创建成功" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "创建虚拟环境时出错: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Ensure-VirtualEnvironment {
    param (
        [string]$VenvPath = ".\.venv",
        [string]$RequirementsPath = "requirements.txt",
        [string]$PythonPath = "python"
    )
    
    $venvCheck = Test-VirtualEnvironment -VenvPath $VenvPath
    if (-not $venvCheck.Valid) {
        Write-Host "虚拟环境检查失败: $($venvCheck.Reason)" -ForegroundColor Yellow
        Write-Host "尝试创建虚拟环境..." -ForegroundColor Yellow
        
        if (-not (Install-VirtualEnvironment -VenvPath $VenvPath -PythonPath $PythonPath)) {
            Write-Host "无法创建虚拟环境" -ForegroundColor Red
            return $false
        }
        
        # 检查requirements.txt是否存在
        if (Test-Path $RequirementsPath) {
            Write-Host "安装依赖包..." -ForegroundColor Yellow
            try {
                & "$VenvPath\Scripts\Activate.ps1"
                pip install -r $RequirementsPath
                Write-Host "依赖包安装完成" -ForegroundColor Green
            } catch {
                Write-Host "安装依赖包失败: $($_.Exception.Message)" -ForegroundColor Red
                return $false
            }
        }
    }
    
    return $true
}

function Open-FrontendBrowser {
    param (
        [string]$FrontendUrl = "http://localhost:3000",
        [switch]$Delay
    )
    
    if ($Delay) {
        Start-Sleep -Seconds 5
    }
    
    try {
        Write-Host "正在打开前端页面: $FrontendUrl" -ForegroundColor Cyan
        Start-Process $FrontendUrl
        return $true
    } catch {
        Write-Host "无法自动打开浏览器: $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

# 导出所有函数
Export-ModuleMember -Function *