# VaultMind App Restart Script
# Stops Streamlit, clears cache, and restarts

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VaultMind App Restart Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop all Streamlit processes
Write-Host "[1/4] Stopping Streamlit processes..." -ForegroundColor Yellow
$streamlitProcesses = Get-Process streamlit -ErrorAction SilentlyContinue
if ($streamlitProcesses) {
    $streamlitProcesses | Stop-Process -Force
    Write-Host "  ✓ Stopped $($streamlitProcesses.Count) Streamlit process(es)" -ForegroundColor Green
} else {
    Write-Host "  ℹ No Streamlit processes found" -ForegroundColor Gray
}

Start-Sleep -Seconds 1

# Clear Python cache
Write-Host "[2/4] Clearing Python cache..." -ForegroundColor Yellow
$cacheDirs = @("tabs\__pycache__", "utils\__pycache__", "app\__pycache__")
foreach ($dir in $cacheDirs) {
    if (Test-Path $dir) {
        Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
        Write-Host "  ✓ Cleared $dir" -ForegroundColor Green
    }
}

# Verify .env file exists
Write-Host "[3/4] Checking configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  ✓ .env file found" -ForegroundColor Green
} else {
    Write-Host "  ⚠ .env file not found - copy .env.example to .env" -ForegroundColor Red
}

# Restart Streamlit
Write-Host "[4/4] Starting Streamlit..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  App is starting..." -ForegroundColor Cyan
Write-Host "  URL: http://localhost:8501" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

streamlit run genai_dashboard_modular.py
