param(
    [switch]$Force
)

$projectRoot = $PSScriptRoot
$pidFile = Join-Path $projectRoot ".app_pids.txt"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze Application Stop Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 优雅停止进程的函数
function Stop-ProcessGracefully {
    param(
        [int]$ProcessId,
        [int]$GracePeriod = 3
    )
    
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if (-not $process) {
            Write-Host "Process no longer exists: PID: $ProcessId" -ForegroundColor Gray
            return $true
        }
        
        Write-Host "Stopping process PID: $ProcessId ($($process.ProcessName))..." -ForegroundColor Yellow
        
        # 尝试优雅关闭（发送关闭信号）
        try {
            $process.CloseMainWindow() | Out-Null
        } catch {
            # 忽略没有主窗口的进程
        }
        
        # 等待进程自行退出
        $waited = 0
        while (-not $process.HasExited -and $waited -lt $GracePeriod) {
            Start-Sleep -Milliseconds 500
            $waited += 0.5
            $process.Refresh()
        }
        
        # 如果进程仍在运行，强制终止
        if (-not $process.HasExited) {
            Write-Host "  Grace period expired, force killing..." -ForegroundColor Yellow
            $process.Kill()
            Start-Sleep -Milliseconds 500
        }
        
        Write-Host "Process stopped: PID: $ProcessId" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "Unable to stop process PID: $ProcessId - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile
    
    if ($pids.Count -gt 0) {
        Write-Host "Found the following process PIDs to stop:" -ForegroundColor Yellow
        $pids | ForEach-Object { Write-Host "  PID: $_" -ForegroundColor Gray }
        Write-Host ""
        
        foreach ($processId in $pids) {
            Stop-ProcessGracefully -ProcessId $processId -GracePeriod 3
        }
    } else {
        Write-Host "PID file is empty, no processes to stop" -ForegroundColor Yellow
    }
    
    # Delete PID file
    Remove-Item $pidFile -Force
    Write-Host "PID file deleted" -ForegroundColor Green
} else {
    Write-Host "PID file not found, trying to stop processes by port..." -ForegroundColor Yellow
    
    # Stop processes by common ports
    $ports = @(3000, 3001, 8200)
    
    foreach ($port in $ports) {
        $portInUse = netstat -ano 2>$null | Select-String ":$port " | Select-String "LISTENING"
        if ($portInUse) {
            $pidMatch = [regex]::Match($portInUse, '\s+(\d+)\s*$')
            if ($pidMatch.Success) {
                $processId = [int]$pidMatch.Groups[1].Value
                Write-Host "Found process on port $port with PID: $processId" -ForegroundColor Yellow
                Stop-ProcessGracefully -ProcessId $processId -GracePeriod 3
            }
        } else {
            Write-Host "Port $port is not in use" -ForegroundColor Green
        }
    }
}

# 等待文件系统释放锁定
Write-Host "`nWaiting for file system to release locks..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

Write-Host "`nStop operation completed" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan