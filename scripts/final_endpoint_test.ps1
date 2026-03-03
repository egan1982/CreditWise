# Final endpoint testing with correct paths
param(
    [string]$BaseURL = "http://localhost",
    [int]$BackendPort = 8200,
    [int]$FrontendPort = 3000,
    [int]$VitePort = 3001
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze Endpoint Availability Test" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$tests = @(
    @{Name="Backend Root"; URL="$BaseURL`:$BackendPort/"}, 
    @{Name="Backend API Docs"; URL="$BaseURL`:$BackendPort/docs"}, 
    @{Name="Backend Health"; URL="$BaseURL`:$BackendPort/health"}, 
    @{Name="Workspace Files"; URL="$BaseURL`:$BackendPort/workspace/files?session_id=default"}, 
    @{Name="Frontend (3000)"; URL="$BaseURL`:$FrontendPort"}, 
    @{Name="LLM Manager API Docs"; URL="$BaseURL`:$BackendPort/llm-manager/docs"}, 
    @{Name="LLM Manager Channels"; URL="$BaseURL`:$BackendPort/llm-manager/api/manage/channels"}, 
    @{Name="LLM Manager Logs"; URL="$BaseURL`:$BackendPort/llm-manager/api/logs"}, 
    @{Name="LLM Manager Stats"; URL="$BaseURL`:$BackendPort/llm-manager/api/stats"}, 
    @{Name="LLM Manager (Vite)"; URL="$BaseURL`:$VitePort"}
)

$available = 0
$total = $tests.Count

Write-Host "Testing endpoints..." -ForegroundColor Yellow
foreach ($test in $tests) {
    try {
        $response = curl.exe -s -o nul -w "%{http_code}" $test.URL 2>$null
        if ($response -eq "200" -or $response -eq "302") {
            Write-Host "[OK] $($test.Name)" -ForegroundColor Green
            $available++
        } else {
            Write-Host "[FAIL] $($test.Name) - Status: $response" -ForegroundColor Red
        }
    } catch {
        Write-Host "[ERROR] $($test.Name) - Connection failed" -ForegroundColor Red
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Availability Report" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Available: $available/$total endpoints" -ForegroundColor $(if($available -eq $total) {"Green"} else {"Yellow"})

if ($available -lt $total) {
    Write-Host "`nIssues and Solutions:" -ForegroundColor Red
    Write-Host "1. Backend issues (.e.g., connection failed)" -ForegroundColor Yellow
    Write-Host "   - Run: .\start_dev.ps1" -ForegroundColor Gray
    Write-Host "   - Check: .app_pids.txt to see if PIDs are valid" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Frontend issues (.e.g., port not responding)" -ForegroundColor Yellow
    Write-Host "   - Check if Node.js is installed: node --version" -ForegroundColor Gray
    Write-Host "   - Check if dependencies are installed: npm list" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. LLM Manager API issues (.e.g., 404)" -ForegroundColor Yellow
    Write-Host "   - This is normal in DEV_MODE=true (frontend served by Vite)" -ForegroundColor Gray
    Write-Host "   - Only API endpoints are available at 8200/llm-manager/api/*" -ForegroundColor Gray
    Write-Host "   - UI is served by Vite at 3001" -ForegroundColor Gray
} else {
    Write-Host "`nAll endpoints are accessible!" -ForegroundColor Green
}

Write-Host "`nAccess URLs:" -ForegroundColor Cyan
Write-Host "- Main App: http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host "- LLM Manager: http://localhost:$VitePort" -ForegroundColor Green
Write-Host "- API Docs: http://localhost:$BackendPort/docs" -ForegroundColor Green
Write-Host "- LLM Manager API: http://localhost:$BackendPort/llm-manager/docs" -ForegroundColor Gray