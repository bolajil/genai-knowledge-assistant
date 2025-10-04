@echo off
ECHO ===================================================
ECHO VaultMind Query Assistant Debug Utility
ECHO ===================================================

ECHO Activating conda environment...
CALL conda activate genai_project2

ECHO Running query assistant debug tool...
streamlit run debug_query_assistant.py

PAUSE
