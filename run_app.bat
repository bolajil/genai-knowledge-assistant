@echo off
ECHO ===================================================
ECHO VaultMind Query Assistant Test Runner
ECHO ===================================================

ECHO Activating conda environment...
CALL conda activate genai_project2

ECHO Running the main application...
ECHO.
ECHO Important: Check the Query Assistant tab to verify it works properly
ECHO.

streamlit run main.py

PAUSE
