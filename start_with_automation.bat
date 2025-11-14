@echo off
echo ========================================
echo VaultMind with Automation System
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/4] Installing automation dependencies...
pip install -q -r requirements-automation.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
)

echo.
echo [2/4] Creating logs directory...
if not exist logs mkdir logs

echo.
echo [3/4] Starting automation system in background...
start "VaultMind Automation" python run_automation_system.py

echo.
echo Waiting for automation system to initialize...
timeout /t 5 /nobreak >nul

echo.
echo [4/4] Starting Streamlit dashboard...
echo.
echo ========================================
echo System URLs:
echo   Dashboard: http://localhost:8501
echo   Metrics:   http://localhost:8000/metrics
echo ========================================
echo.
echo Press Ctrl+C to stop the dashboard
echo (Automation system will continue running in background)
echo.

streamlit run genai_dashboard_modular.py

echo.
echo Dashboard stopped. Automation system is still running.
echo To stop automation, close the "VaultMind Automation" window.
pause
