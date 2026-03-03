param(
    [int]$Port = 8200,
    [int]$FrontendPort = 3000,
    [int]$VitePort = 3001,
    [string]$HostAddr = "127.0.0.1",
    [switch]$NoFrontend = $false,
    [switch]$NoBackend = $false
)

$projectRoot = "C:\Users\fjzheng\portable-dev-env\workspace\DeepAnalyze"
$venvPath = Join-Path $projectRoot ".venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$apiMain = Join-Path $projectRoot "API\main.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze 应用启动脚本" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "参数说明:" -ForegroundColor White
Write-Host "  -Port: 后端API端口 (默认: 8200)" -ForegroundColor Gray
Write-Host "  -FrontendPort: 前端应用端口 (默认: 3000)" -ForegroundColor Gray
Write-Host "  -VitePort: Vite开发服务器端口 (默认: 3001)" -ForegroundColor Gray
Write-Host "  -HostAddr: 主机地址 (默认: 127.0.0.1)" -ForegroundColor Gray
Write-Host "  -NoFrontend: 不启动前端应用" -ForegroundColor Gray
    Write-Host "  -NoBackend: 不启动后端API" -ForegroundColor Gray
    Write-Host "示例:" -ForegroundColor White
    Write-Host "  .\start_dev.ps1                       # 默认启动所有服务(双前端)" -ForegroundColor Gray
    Write-Host "  .\start_dev.ps1 -Port 8201             # 指定后端端口" -ForegroundColor Gray
    Write-Host "  .\start_dev.ps1 -FrontendPort 3002      # 指定前端端口" -ForegroundColor Gray
    Write-Host "  .\start_dev.ps1 -VitePort 3002          # 指定Vite端口" -ForegroundColor Gray
    Write-Host "  .\start_dev.ps1 -NoFrontend             # 只启动后端" -ForegroundColor Gray
    Write-Host "  .\start_dev.ps1 -NoBackend              # 只启动前端" -ForegroundColor Gray

# 第一步：检查并停止现有进程（可选但推荐）
if (-not $NoBackend) {
    $pidFile = Join-Path $projectRoot ".app_pids.txt"
    if (Test-Path $pidFile) {
        Write-Host "`n[0] 发现现有服务进程，正在停止..." -ForegroundColor Yellow
        try {
            $pids = Get-Content $pidFile
            foreach ($pid in $pids) {
                try {
                    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                    if ($process) {
                        Write-Host "  停止进程 PID: $pid ($($process.ProcessName))" -ForegroundColor Gray
                        $process.Kill() | Out-Null
                    }
                } catch {
                    Write-Host "  进程已不存在: PID: $pid" -ForegroundColor Gray
                }
            }
            Remove-Item $pidFile -Force
            Start-Sleep -Seconds 1
        } catch {
            Write-Host "  停止现有进程时出现错误，继续执行..." -ForegroundColor Yellow
        }
    }
}

# 第二步：清理端口占用
Write-Host "`n[1] 清理端口占用..." -ForegroundColor Yellow

# 清理API端口 (8200)
Write-Host "  检查端口 $Port (API)..." -ForegroundColor Gray
$portInUse = netstat -ano 2>$null | Select-String ":$Port " | Select-String "LISTENING"
if ($portInUse) {
    $pidMatch = [regex]::Match($portInUse, '\s+(\d+)\s*$')
    if ($pidMatch.Success) {
        $processId = $pidMatch.Groups[1].Value
        Write-Host "  找到占用进程 PID: $processId，正在终止..." -ForegroundColor Yellow
        taskkill /PID $processId /F /T 2>$null | Out-Null
        Start-Sleep -Seconds 1
        Write-Host "  端口 $Port 已释放" -ForegroundColor Green
    }
} else {
    Write-Host "  端口 $Port 未被占用" -ForegroundColor Green
}

# 清理HTTP文件服务器端口 (8100)
$FileServerPort = 8100
Write-Host "  检查端口 $FileServerPort (文件服务器)..." -ForegroundColor Gray
$filePortInUse = netstat -ano 2>$null | Select-String ":$FileServerPort " | Select-String "LISTENING"
if ($filePortInUse) {
    $pidMatch = [regex]::Match($filePortInUse, '\s+(\d+)\s*$')
    if ($pidMatch.Success) {
        $processId = $pidMatch.Groups[1].Value
        Write-Host "  找到占用进程 PID: $processId，正在终止..." -ForegroundColor Yellow
        taskkill /PID $processId /F /T 2>$null | Out-Null
        Start-Sleep -Seconds 1
        Write-Host "  端口 $FileServerPort 已释放" -ForegroundColor Green
    }
} else {
    Write-Host "  端口 $FileServerPort 未被占用" -ForegroundColor Green
}

# 第三步：检查 Python 环境
Write-Host "`n[3] 检查 Python 环境..." -ForegroundColor Yellow
if (-not (Test-Path $pythonExe)) {
    Write-Host "虚拟环境不存在: $pythonExe" -ForegroundColor Red
    Write-Host "尝试使用便携式 Python..." -ForegroundColor Yellow
    $pythonExe = "C:\Users\fjzheng\portable-dev-env\tools\python\python.exe"
    
    if (-not (Test-Path $pythonExe)) {
        Write-Host "便携式 Python 也不存在，无法启动" -ForegroundColor Red
        exit 1
    }
}
Write-Host "Python 环境就绪: $pythonExe" -ForegroundColor Green

# 第四步：检查 API 主文件
Write-Host "`n[4] 检查 API 主文件..." -ForegroundColor Yellow
if (-not (Test-Path $apiMain)) {
    Write-Host "API 主文件不存在: $apiMain" -ForegroundColor Red
    exit 1
}
Write-Host "API 主文件就绪: $apiMain" -ForegroundColor Green

# 第五步：设置环境变量
Write-Host "`n[5] 设置环境变量..." -ForegroundColor Yellow
$env:API_PORT = $Port
$env:API_HOST = $HostAddr
$env:DEV_MODE = "true"  # 开发模式，禁用8200/llm-manager静态页面，避免与3001冲突
$env:PYTHONUNBUFFERED = 1
Write-Host "环境变量设置完成 (PORT=$Port, HOST=$HostAddr, DEV_MODE=true)" -ForegroundColor Green

# 第六步：启动应用
Write-Host "`n[6] 启动应用服务器..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "应用启动信息:" -ForegroundColor Cyan
Write-Host "  - 后端API: http://$HostAddr`:$Port" -ForegroundColor Green
Write-Host "  - 文件服务器: http://$HostAddr`:$FileServerPort" -ForegroundColor Green
Write-Host "  - API 文档: http://$HostAddr`:$Port/docs" -ForegroundColor Green
Write-Host "  - 前端应用(三列式): http://$HostAddr`:$FrontendPort" -ForegroundColor Green
Write-Host "  - LLM Manager (Vite): http://$HostAddr`:$VitePort" -ForegroundColor Green
Write-Host "  - LLM Manager API: http://$HostAddr`:$Port/llm-manager/api" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 在项目目录启动应用
Set-Location $projectRoot

# 启动 Python 进程
$apiDir = Join-Path $projectRoot "API"
$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = $pythonExe
$processInfo.Arguments = $apiMain
$processInfo.UseShellExecute = $false
$processInfo.RedirectStandardOutput = $false
$processInfo.RedirectStandardError = $false
$processInfo.WorkingDirectory = $projectRoot  # 工作目录设为项目根目录，确保数据库路径统一

# 确保环境变量正确设置（同时包含项目根目录和API目录）
$processInfo.EnvironmentVariables["PYTHONPATH"] = "$projectRoot;$apiDir"

$process = [System.Diagnostics.Process]::Start($processInfo)
$pid = $process.Id

Write-Host "应用已启动 (PID: $pid)" -ForegroundColor Green
Write-Host "等待应用完全启动..." -ForegroundColor Yellow

# 等待后端应用启动完成并检查健康状态
Write-Host "等待后端服务启动..." -ForegroundColor Yellow
$backendStarted = $false
# 进一步优化：减少最大尝试次数，只要服务响应就继续
$maxAttempts = 10
$attempt = 0

do {
    $attempt++
    try {
        # 使用curl.exe检查后端健康状态
        $response = curl.exe -s -o nul -w "%{http_code}" "http://$HostAddr`:$Port" 2>$null
        
        # 只要能连通（任何响应）就认为后端已启动
        if ($response -ne "000" -and $response -ne "timeout") {
            $backendStarted = $true
            Write-Host "后端服务已启动 (尝试 $attempt/$maxAttempts, 状态码: $response)" -ForegroundColor Green
            break
        } else {
            Write-Host "等待后端启动... (尝试 $attempt/$maxAttempts)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "检查后端状态... (尝试 $attempt/$maxAttempts)" -ForegroundColor Yellow
    }
    
    # 优化：更短的等待间隔
    $sleepTime = if ($attempt -le 3) { 0.5 } elseif ($attempt -le 6) { 0.8 } else { 1.2 }
    Start-Sleep -Seconds $sleepTime
} while ($attempt -lt $maxAttempts -and -not $backendStarted)

if (-not $backendStarted) {
    Write-Host "警告：后端服务可能未完全启动，但将继续启动前端" -ForegroundColor Yellow
}

# 第七步：启动前端应用
if (-not $NoFrontend) {
    Write-Host "`n[7] 检查前端环境..." -ForegroundColor Yellow
    
    # 检查Node.js环境
    $nodePath = "C:\Users\fjzheng\portable-dev-env\tools\nodejs\node.exe"
    $npmPath = "C:\Users\fjzheng\portable-dev-env\tools\nodejs\npm.cmd"
    
    # 1. 启动三列式前端应用 (3000端口)
    $frontendDir = Join-Path $projectRoot "demo\chat"
    Write-Host "准备启动三列式前端应用..." -ForegroundColor Gray
    
    if ((Test-Path $nodePath) -and (Test-Path $npmPath) -and (Test-Path $frontendDir)) {
        Write-Host "前端环境检查通过，启动三列式前端应用..." -ForegroundColor Green
        
        # 检查前端端口是否被占用，并彻底终止相关进程
        $frontendPortInUse = netstat -ano 2>$null | Select-String ":$FrontendPort " | Select-String "LISTENING"
        if ($frontendPortInUse) {
            $pidMatch = [regex]::Match($frontendPortInUse, '\s+(\d+)\s*$')
            if ($pidMatch.Success) {
                $processId = $pidMatch.Groups[1].Value
                Write-Host "前端端口 $FrontendPort 被占用，正在终止 PID: $processId..." -ForegroundColor Yellow
                # 使用 /T 终止整个进程树
                taskkill /PID $processId /F /T 2>$null | Out-Null
            }
        }
        
        # 【关键修复】无条件清理所有可能的 Next.js 相关 node 进程（防止缓存损坏）
        $nextProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
            try {
                $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                $cmdLine -match "next" -or $cmdLine -match "demo\\chat"
            } catch { $false }
        }
        if ($nextProcesses) {
            Write-Host "发现残留的 Next.js 进程，正在清理..." -ForegroundColor Yellow
            $nextProcesses | ForEach-Object {
                try {
                    taskkill /PID $_.Id /F /T 2>$null | Out-Null
                    Write-Host "  已终止 PID: $($_.Id)" -ForegroundColor Gray
                } catch {}
            }
        }
        
        # 等待进程完全退出并释放文件锁
        Start-Sleep -Seconds 3
        
        # 【关键修复】无条件清理 Next.js 缓存（每次启动都清理，彻底避免缓存损坏问题）
        $nextCacheDir = Join-Path $frontendDir ".next"
        Write-Host "清理 Next.js 缓存目录（防止缓存损坏）..." -ForegroundColor Yellow
        
        if (Test-Path $nextCacheDir) {
            # 多次尝试清理，处理文件锁定情况
            $cleanupSuccess = $false
            for ($cleanAttempt = 1; $cleanAttempt -le 3; $cleanAttempt++) {
                try {
                    Remove-Item -Recurse -Force $nextCacheDir -ErrorAction Stop
                    $cleanupSuccess = $true
                    Write-Host "Next.js 缓存已清理" -ForegroundColor Green
                    break
                } catch {
                    if ($cleanAttempt -lt 3) {
                        Write-Host "缓存清理尝试 $cleanAttempt/3 失败，等待后重试..." -ForegroundColor Yellow
                        Start-Sleep -Seconds 2
                    } else {
                        Write-Host "警告：PowerShell 清理失败，尝试使用 cmd..." -ForegroundColor Yellow
                        # 使用 cmd 的 rmdir 命令，通常更可靠
                        $cmdResult = cmd /c "rmdir /s /q `"$nextCacheDir`"" 2>&1
                        if (-not (Test-Path $nextCacheDir)) {
                            $cleanupSuccess = $true
                            Write-Host "Next.js 缓存已通过 cmd 清理" -ForegroundColor Green
                        }
                    }
                }
            }
            
            # 如果仍然失败，尝试重命名
            if (-not $cleanupSuccess -and (Test-Path $nextCacheDir)) {
                Write-Host "强制重命名旧缓存目录..." -ForegroundColor Yellow
                $backupDir = Join-Path $frontendDir ".next_old_$(Get-Date -Format 'yyyyMMddHHmmss')"
                try {
                    Rename-Item -Path $nextCacheDir -NewName $backupDir -ErrorAction SilentlyContinue
                    # 异步删除旧目录
                    Start-Job -ScriptBlock { param($dir) Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue } -ArgumentList $backupDir | Out-Null
                    $cleanupSuccess = $true
                    Write-Host "缓存已重命名，将异步删除" -ForegroundColor Green
                } catch {
                    Write-Host "错误：缓存清理完全失败，前端可能无法正常启动！" -ForegroundColor Red
                    Write-Host "请手动删除: $nextCacheDir" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "无缓存需要清理" -ForegroundColor Gray
        }
        
        # 检查前端依赖是否已安装
        $packageJson = Join-Path $frontendDir "package.json"
        $nodeModules = Join-Path $frontendDir "node_modules"
        
        if ((Test-Path $packageJson) -and -not (Test-Path $nodeModules)) {
            Write-Host "前端依赖未安装，正在安装..." -ForegroundColor Yellow
            Set-Location $frontendDir
            
            $installProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
            $installProcessInfo.FileName = $npmPath
            $installProcessInfo.Arguments = "install"
            $installProcessInfo.UseShellExecute = $false
            $installProcessInfo.RedirectStandardOutput = $true
            $installProcessInfo.RedirectStandardError = $true
            $installProcessInfo.EnvironmentVariables["PATH"] = "C:\Users\fjzheng\portable-dev-env\tools\nodejs;" + $installProcessInfo.EnvironmentVariables["PATH"]
            
            $installProcess = [System.Diagnostics.Process]::Start($installProcessInfo)
            $installProcess.WaitForExit()
            
            if ($installProcess.ExitCode -eq 0) {
                Write-Host "前端依赖安装完成" -ForegroundColor Green
            } else {
                Write-Host "前端依赖安装失败" -ForegroundColor Red
            }
        }
        
        # 启动三列式前端应用
        $frontendProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
        $frontendProcessInfo.FileName = $npmPath
        $frontendProcessInfo.Arguments = "run dev"
        $frontendProcessInfo.UseShellExecute = $false
        $frontendProcessInfo.RedirectStandardOutput = $false
        $frontendProcessInfo.RedirectStandardError = $false
        $frontendProcessInfo.WorkingDirectory = $frontendDir
        
        # 设置环境变量
        $frontendProcessInfo.EnvironmentVariables["PATH"] = "C:\Users\fjzheng\portable-dev-env\tools\nodejs;" + $frontendProcessInfo.EnvironmentVariables["PATH"]
        
        $frontendProcess = [System.Diagnostics.Process]::Start($frontendProcessInfo)
        Write-Host "三列式前端应用已启动 (PID: $($frontendProcess.Id))" -ForegroundColor Green
        Write-Host "三列式前端地址: http://$HostAddr`:$FrontendPort" -ForegroundColor Green
        
        # 等待三列式前端应用启动完成（增强健康检查）
        Write-Host "等待三列式前端服务启动（Next.js 编译中）..." -ForegroundColor Yellow
        $frontendStarted = $false
        $maxAttempts = 20  # 增加尝试次数，给 Next.js 更多编译时间
        $attempt = 0
        
        do {
            $attempt++
            try {
                # 检查端口是否响应
                $response = curl.exe -s -o nul -w "%{http_code}" "http://$HostAddr`:$FrontendPort" 2>$null
                
                if ($response -ne "000" -and $response -ne "timeout") {
                    # 端口响应后，进一步检查关键资源是否就绪
                    $cssCheck = curl.exe -s -o nul -w "%{http_code}" "http://$HostAddr`:$FrontendPort/_next/static/css/app/layout.css" 2>$null
                    
                    if ($cssCheck -eq "200") {
                        $frontendStarted = $true
                        Write-Host "三列式前端服务已完全启动 (尝试 $attempt/$maxAttempts)" -ForegroundColor Green
                        break
                    } else {
                        Write-Host "Next.js 编译中... (尝试 $attempt/$maxAttempts, 端口已响应，等待资源编译)" -ForegroundColor Yellow
                    }
                } else {
                    Write-Host "等待三列式前端应用... (尝试 $attempt/$maxAttempts)" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "检查三列式前端状态... (尝试 $attempt/$maxAttempts)" -ForegroundColor Yellow
            }
            
            # Next.js 首次编译需要更多时间
            $sleepTime = if ($attempt -le 5) { 1 } elseif ($attempt -le 10) { 1.5 } else { 2 }
            Start-Sleep -Seconds $sleepTime
        } while ($attempt -lt $maxAttempts -and -not $frontendStarted)
        
        if (-not $frontendStarted) {
            Write-Host "警告：三列式前端资源可能仍在编译中，建议等待几秒后刷新浏览器" -ForegroundColor Yellow
        }
    } else {
        Write-Host "三列式前端环境不完整，跳过三列式前端启动" -ForegroundColor Yellow
        if (-not (Test-Path $nodePath)) { Write-Host "  - 缺少 Node.js: $nodePath" -ForegroundColor Red }
        if (-not (Test-Path $npmPath)) { Write-Host "  - 缺少 npm: $npmPath" -ForegroundColor Red }
        if (-not (Test-Path $frontendDir)) { Write-Host "  - 缺少前端目录: $frontendDir" -ForegroundColor Red }
    }
    
    # 2. 启动Vite前端服务器 (3001端口) - LLM Manager
    $viteDir = Join-Path $projectRoot "llm_manager_integrated\frontend"
    Write-Host "准备启动Vite开发服务器..." -ForegroundColor Gray
    
    if ((Test-Path $nodePath) -and (Test-Path $npmPath) -and (Test-Path $viteDir)) {
        Write-Host "Vite环境检查通过，启动Vite开发服务器..." -ForegroundColor Green
        
        # 检查Vite端口是否被占用
        $vitePortInUse = netstat -ano 2>$null | Select-String ":$VitePort " | Select-String "LISTENING"
        if ($vitePortInUse) {
            $pidMatch = [regex]::Match($vitePortInUse, '\s+(\d+)\s*$')
            if ($pidMatch.Success) {
                $processId = $pidMatch.Groups[1].Value
                Write-Host "Vite端口 $VitePort 被占用，正在终止 PID: $processId..." -ForegroundColor Yellow
                taskkill /PID $processId /F 2>$null | Out-Null
                Start-Sleep -Seconds 1
            }
        }
        
        # 检查Vite依赖是否已安装
        $vitePackageJson = Join-Path $viteDir "package.json"
        $viteNodeModules = Join-Path $viteDir "node_modules"
        
        if ((Test-Path $vitePackageJson) -and -not (Test-Path $viteNodeModules)) {
            Write-Host "Vite依赖未安装，正在安装..." -ForegroundColor Yellow
            Set-Location $viteDir
            
            $viteInstallProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
            $viteInstallProcessInfo.FileName = $npmPath
            $viteInstallProcessInfo.Arguments = "install"
            $viteInstallProcessInfo.UseShellExecute = $false
            $viteInstallProcessInfo.RedirectStandardOutput = $true
            $viteInstallProcessInfo.RedirectStandardError = $true
            $viteInstallProcessInfo.EnvironmentVariables["PATH"] = "C:\Users\fjzheng\portable-dev-env\tools\nodejs;" + $viteInstallProcessInfo.EnvironmentVariables["PATH"]
            
            $viteInstallProcess = [System.Diagnostics.Process]::Start($viteInstallProcessInfo)
            $viteInstallProcess.WaitForExit()
            
            if ($viteInstallProcess.ExitCode -eq 0) {
                Write-Host "Vite依赖安装完成" -ForegroundColor Green
            } else {
                Write-Host "Vite依赖安装失败" -ForegroundColor Red
            }
        }
        
        # 启动Vite开发服务器
        $viteProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
        $viteProcessInfo.FileName = $npmPath
        $viteProcessInfo.Arguments = "run dev"
        $viteProcessInfo.UseShellExecute = $false
        $viteProcessInfo.RedirectStandardOutput = $false
        $viteProcessInfo.RedirectStandardError = $false
        $viteProcessInfo.WorkingDirectory = $viteDir
        
        # 设置环境变量
        $viteProcessInfo.EnvironmentVariables["PATH"] = "C:\Users\fjzheng\portable-dev-env\tools\nodejs;" + $viteProcessInfo.EnvironmentVariables["PATH"]
        
        $viteProcess = [System.Diagnostics.Process]::Start($viteProcessInfo)
        Write-Host "Vite开发服务器已启动 (PID: $($viteProcess.Id))" -ForegroundColor Green
        Write-Host "Vite开发服务器地址: http://$HostAddr`:$VitePort" -ForegroundColor Green
        
        # 等待Vite开发服务器启动完成
        Write-Host "等待Vite开发服务器启动..." -ForegroundColor Yellow
        $viteStarted = $false
        $maxViteAttempts = 8
        $viteAttempt = 0
        
        do {
            $viteAttempt++
            try {
                # 使用curl.exe检查Vite健康状态
                $viteResponse = curl.exe -s -o nul -w "%{http_code}" "http://$HostAddr`:$VitePort" 2>$null
                # 只要能连通（任何响应）就认为Vite已启动
                if ($viteResponse -ne "000" -and $viteResponse -ne "timeout") {
                    $viteStarted = $true
                    Write-Host "Vite开发服务器已启动 (尝试 $viteAttempt/$maxViteAttempts, 状态码: $viteResponse)" -ForegroundColor Green
                    break
                } else {
                    Write-Host "等待Vite开发服务器... (尝试 $viteAttempt/$maxViteAttempts)" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "检查Vite开发服务器状态... (尝试 $viteAttempt/$maxViteAttempts)" -ForegroundColor Yellow
            }
            
            # 优化：更短的等待间隔
            $sleepTime = if ($viteAttempt -le 3) { 0.5 } else { 0.8 }
            Start-Sleep -Seconds $sleepTime
        } while ($viteAttempt -lt $maxViteAttempts -and -not $viteStarted)
        
        if (-not $viteStarted) {
            Write-Host "警告：Vite开发服务器可能未完全启动，但将继续打开浏览器" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Vite环境不完整，跳过Vite开发服务器启动" -ForegroundColor Yellow
        if (-not (Test-Path $nodePath)) { Write-Host "  - 缺少 Node.js: $nodePath" -ForegroundColor Red }
        if (-not (Test-Path $npmPath)) { Write-Host "  - 缺少 npm: $npmPath" -ForegroundColor Red }
        if (-not (Test-Path $viteDir)) { Write-Host "  - 缺少Vite目录: $viteDir" -ForegroundColor Red }
    }
}

# 第八步：启动浏览器
if (-not $NoFrontend) {
    Write-Host "`n[8] 启动浏览器..." -ForegroundColor Yellow
    
    # 默认打开3000端口的三列式前端应用
    if (Test-Path (Join-Path $projectRoot "demo\chat")) {
        $frontendUrl = "http://$HostAddr`:$FrontendPort"
        $urlType = "三列式前端应用"
    } else {
        # 如果三列式前端不存在，则打开Vite服务器
        $frontendUrl = "http://$HostAddr`:$VitePort"
        $urlType = "LLM Manager (Vite)"
    }
    
    Write-Host "准备打开$urlType`: $frontendUrl" -ForegroundColor Cyan
    Write-Host "提示: 双前端环境已启动，可同时访问:" -ForegroundColor Cyan
    Write-Host "  - 三列式前端: http://$HostAddr`:$FrontendPort" -ForegroundColor Gray
    Write-Host "  - LLM Manager: http://$HostAddr`:$VitePort" -ForegroundColor Gray
    
    # 检查服务状态并准备打开浏览器
    if ($backendStarted) {
        Write-Host "后端服务已启动，正在打开浏览器..." -ForegroundColor Green
    } else {
        Write-Host "后端可能仍在启动中，但将继续打开浏览器..." -ForegroundColor Yellow
    }
    
    try {
        # 尝试方法1: 使用默认浏览器打开
        [System.Diagnostics.Process]::Start($frontendUrl)
        Write-Host "浏览器已打开: $frontendUrl" -ForegroundColor Green
    } catch {
        try {
            # 尝试方法2: 使用 explorer.exe 打开
            & explorer.exe $frontendUrl
            Write-Host "浏览器已打开: $frontendUrl" -ForegroundColor Green
        } catch {
            try {
                # 尝试方法3: 使用 cmd 打开
                cmd /c start $frontendUrl
                Write-Host "浏览器已打开: $frontendUrl" -ForegroundColor Green
            } catch {
                Write-Host "无法自动打开浏览器，请手动访问: $frontendUrl" -ForegroundColor Yellow
            }
        }
    }
}

# 添加短暂延迟确保服务真正开始处理请求
Start-Sleep -Seconds 1

Write-Host "`n应用启动完成，服务正在后台运行..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "服务信息:" -ForegroundColor Cyan
Write-Host "  - 后端API: http://$HostAddr`:$Port" -ForegroundColor Green
Write-Host "  - 文件服务器: http://$HostAddr`:$FileServerPort" -ForegroundColor Green
Write-Host "  - API 文档: http://$HostAddr`:$Port/docs" -ForegroundColor Green
Write-Host "  - LLM Manager API: http://$HostAddr`:$Port/llm-manager/api" -ForegroundColor Gray
if (-not $NoFrontend -and (Test-Path (Join-Path $projectRoot "demo\chat"))) {
    Write-Host "  - 三列式前端应用: http://$HostAddr`:$FrontendPort" -ForegroundColor Green
}
if (-not $NoFrontend -and (Test-Path (Join-Path $projectRoot "llm_manager_integrated\frontend"))) {
    Write-Host "  - LLM Manager (Vite): http://$HostAddr`:$VitePort" -ForegroundColor Green
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "注意: 开发模式下8200/llm-manager静态页面已禁用，请使用3001端口的Vite版本" -ForegroundColor Yellow

# 不再等待进程退出，让脚本完成执行
Write-Host "脚本执行完成，服务将在后台继续运行" -ForegroundColor Cyan
Write-Host "如需停止服务，请手动终止相关进程" -ForegroundColor Yellow

# 保存进程PID到文件，方便后续停止
$pidFile = Join-Path $projectRoot ".app_pids.txt"
"$($process.Id)" | Out-File -FilePath $pidFile -Encoding UTF8
if ($frontendProcess) {
    "$($frontendProcess.Id)" | Out-File -FilePath $pidFile -Encoding UTF8 -Append
}
if ($viteProcess) {
    "$($viteProcess.Id)" | Out-File -FilePath $pidFile -Encoding UTF8 -Append
}
Write-Host "进程PID已保存到: $pidFile" -ForegroundColor Gray
