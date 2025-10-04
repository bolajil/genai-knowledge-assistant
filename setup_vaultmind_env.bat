@echo off
echo ============================================
echo VaultMind Conda Environment Setup
echo ============================================
echo.
echo This creates an ISOLATED environment that won't affect your base conda or main project.
echo.
pause

echo Step 1: Creating conda environment 'vaultmind' with Python 3.11...
echo.
conda create -n vaultmind python=3.11 -y
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create conda environment
    pause
    exit /b 1
)
echo.

echo Step 2: Activating vaultmind environment...
echo.
call conda activate vaultmind
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate environment
    pause
    exit /b 1
)
echo.

echo Step 3: Upgrading pip in isolated environment...
echo.
python -m pip install --upgrade pip
echo.

echo Step 4: Installing core dependencies from requirements.txt...
echo.
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo WARNING: requirements.txt not found, installing essential packages...
    pip install streamlit pandas numpy python-dotenv pyyaml
)
echo.

echo Step 5: Installing Vertex AI packages...
echo.
pip install google-cloud-aiplatform google-auth
echo.

echo Step 6: Verifying installation...
echo.
python -c "import google.cloud.aiplatform; print('✅ Vertex AI installed, version:', google.cloud.aiplatform.__version__)"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Vertex AI installation verification failed
    pause
    exit /b 1
)
echo.

echo Step 7: Verifying Streamlit...
echo.
python -c "import streamlit; print('✅ Streamlit installed, version:', streamlit.__version__)"
echo.

echo ============================================
echo SUCCESS: Environment Setup Complete!
echo ============================================
echo.
echo Your 'vaultmind' environment is ready and ISOLATED from base conda.
echo.
echo IMPORTANT NOTES:
echo ----------------
echo 1. Your base conda environment is UNCHANGED
echo 2. Your main project files are UNCHANGED
echo 3. Only Python packages are in the new environment
echo.
echo TO USE THIS ENVIRONMENT:
echo ------------------------
echo 1. Open new terminal/command prompt
echo 2. Run: conda activate vaultmind
echo 3. Run: streamlit run genai_dashboard_modular.py
echo.
echo TO SWITCH BACK TO BASE:
echo -----------------------
echo Run: conda deactivate
echo.
echo TO DELETE THIS ENVIRONMENT (if needed):
echo ---------------------------------------
echo Run: conda deactivate
echo Run: conda env remove -n vaultmind
echo.
pause
