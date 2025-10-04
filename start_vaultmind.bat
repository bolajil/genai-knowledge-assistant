@echo off
ECHO Starting VaultMind GenAI Knowledge Assistant...
ECHO ===========================================
ECHO Using Anaconda Python with genai_project2 environment

REM Activate conda environment and run the app
C:\Users\bolaf\anaconda3\Scripts\activate.bat genai_project2 && C:\Users\bolaf\anaconda3\python.exe run_app.py

REM If the app failed to start, pause so the user can see the error
if ERRORLEVEL 1 (
    ECHO.
    ECHO *** Error starting application ***
    ECHO Please check the error message above
    pause
)
