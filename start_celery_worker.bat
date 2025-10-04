@echo off
echo ========================================
echo Starting VaultMIND Celery Worker
echo ========================================
echo.

REM Resolve Python path explicitly
set PYTHON_EXE=C:\Users\bolaf\AppData\Local\Programs\Python\Python310\python.exe

REM Check if Python is available
%PYTHON_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python not found at %PYTHON_EXE%
    echo Please verify your Python installation and PATH
    pause
    exit /b 1
)

REM Check if Redis is running
echo Checking Redis connection...
%PYTHON_EXE% -c "from redis import Redis; r = Redis(host='localhost', port=6379); r.ping(); print('✅ Redis is running')" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ ERROR: Redis is not running!
    echo.
    echo Please start Redis first:
    echo   - Windows: redis-server.exe
    echo   - WSL: wsl sudo service redis-server start
    echo   - Docker: docker run -d -p 6379:6379 redis
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Redis connection successful
echo.
echo Starting Celery worker...
echo Press Ctrl+C to stop the worker
echo.

REM Start Celery worker
%PYTHON_EXE% -m celery -A celery_worker worker --loglevel=info --pool=solo

pause
