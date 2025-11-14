@echo off
echo ========================================
echo Restarting VaultMind Streamlit (FULL CLEAN)
echo ========================================
echo.

echo [1/5] Stopping all Python and Streamlit processes...
taskkill /F /IM streamlit.exe 2>nul
taskkill /F /IM python.exe 2>nul
echo Waiting for processes to stop...
timeout /t 3 /nobreak >nul

echo.
echo [2/5] Clearing ALL Python cache files...
del /s /q *.pyc 2>nul
echo.

echo [3/5] Removing ALL __pycache__ directories...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
echo.

echo [4/5] Clearing Streamlit cache...
if exist .streamlit\cache rmdir /s /q .streamlit\cache 2>nul
echo.

echo [5/5] Verifying critical files exist...
if exist utils\monitoring\simple_health_checks.py (
    echo   ✓ simple_health_checks.py found
) else (
    echo   ✗ WARNING: simple_health_checks.py NOT FOUND!
    echo   This will cause errors. Check if file was created.
    pause
    exit /b 1
)

if exist tabs\system_monitoring.py (
    echo   ✓ system_monitoring.py found
) else (
    echo   ✗ WARNING: system_monitoring.py NOT FOUND!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Starting Streamlit (Fresh Instance)...
echo ========================================
echo.
echo Dashboard will open at: http://localhost:8501
echo.
echo After it starts:
echo 1. Go to System Monitoring tab
echo 2. Click "Clear Cache" button if needed
echo 3. Health checks should work!
echo.
echo Press Ctrl+C to stop Streamlit
echo ========================================
echo.

streamlit run genai_dashboard_modular.py --server.port 8501

pause
