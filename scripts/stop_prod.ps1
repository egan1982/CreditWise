# =============================================================================
# CreditWise 生产环境停止（Windows）
#
# 用法：.\scripts\stop_prod.ps1
# =============================================================================

$ErrorActionPreference = "SilentlyContinue"
$projectRoot = $PSScriptRoot | Split-Path -Parent
$pidFile = Join-Path $projectRoot ".app_pids.txt"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " CreditWise 停止服务" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 从 PID 文件停止
if (Test-Path $pidFile) {
    Write-Host "从 PID 文件停止进程..." -ForegroundColor Yellow
    $pids = Get-Content $pidFile
    foreach ($id in $pids) {
        try {
            $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "  停止 PID $id ($($proc.ProcessName))" -ForegroundColor Gray
                $proc.Kill() | Out-Null
                Write-Host "  PID $id 已停止" -ForegroundColor Green
            } else {
                Write-Host "  PID $id 已不存在" -ForegroundColor Gray
            }
        } catch {
            Write-Host "  PID $id 停止失败: $_" -ForegroundColor Yellow
        }
    }
    Remove-Item $pidFile -Force
    Write-Host "  PID 文件已清理" -ForegroundColor Gray
} else {
    Write-Host "PID 文件不存在，尝试通过端口扫描..." -ForegroundColor Yellow
}

# 兜底：端口扫描强制清理
foreach ($port in @(8200, 8100)) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object State -eq Listen
    if ($conn) {
        $existingPid = $conn.OwningProcess
        Write-Host "  端口 $port 仍被 PID $existingPid 占用，强制终止..." -ForegroundColor Yellow
        taskkill /PID $existingPid /F /T 2>$null | Out-Null
    }
}

Start-Sleep 1
Write-Host "服务已停止" -ForegroundColor Green
