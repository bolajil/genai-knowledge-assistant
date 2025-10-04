@echo off
REM Launch script for VaultMind GenAI Knowledge Assistant
REM This script ensures proper environment activation and application launch

echo Starting VaultMind GenAI Knowledge Assistant...
echo.

REM Activate the Anaconda environment
call C:\Users\bolaf\anaconda3\Scripts\activate.bat genai_project2

REM Check if the environment was activated successfully
if %ERRORLEVEL% NEQ 0 (
    echo Failed to activate Anaconda environment.
    echo Please make sure your Anaconda installation is working correctly.
    pause
    exit /b 1
)

echo Environment activated successfully.
echo.

REM Install required packages if they don't exist
pip install streamlit langchain pandas beautifulsoup4 pypdf -q

echo Starting application...
echo.

REM Launch the dashboard
python -m streamlit run genai_dashboard_modular.py --server.port=8515

echo Application closed.
pause
