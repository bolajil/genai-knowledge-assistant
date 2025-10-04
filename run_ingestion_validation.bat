@echo off
echo ========================================
echo Ingestion Tab Validation Test Suite
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Running validation tests...
echo.

REM Run the test suite
python tests/test_ingestion_tab_validation.py

echo.
echo ========================================
echo Test execution completed
echo ========================================
echo.
echo Review the output above for test results
echo Refer to INGESTION_TAB_REVIEW.md for recommendations
echo.

pause
