@echo off
echo ============================================
echo Installing Vertex AI for Python 3.14
echo ============================================
echo.

echo Python 3.14 is in beta and some packages need special handling
echo.

echo Step 1: Upgrade pip and setuptools...
py -m pip install --upgrade pip setuptools wheel
echo.

echo Step 2: Install google-auth (no compilation needed)...
py -m pip install google-auth
echo.

echo Step 3: Try installing with pre-built binaries only...
py -m pip install --only-binary=:all: google-cloud-aiplatform 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Pre-built binaries not available, trying alternative approach...
    echo.
    
    echo Step 4: Install older compatible version...
    py -m pip install "google-cloud-aiplatform==1.38.0"
)
echo.

echo Step 5: Verifying installation...
py -c "import google.cloud.aiplatform; print('SUCCESS: Vertex AI installed'); print('Version:', google.cloud.aiplatform.__version__)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================
    echo INSTALLATION FAILED
    echo ============================================
    echo.
    echo Python 3.14 beta has compatibility issues with some packages.
    echo.
    echo RECOMMENDED SOLUTIONS:
    echo.
    echo Option 1: Use Python 3.11 or 3.12 (stable versions^)
    echo   - Download from: https://www.python.org/downloads/
    echo   - Install Python 3.12.x
    echo   - Use: py -3.12 -m pip install google-cloud-aiplatform
    echo.
    echo Option 2: Use Conda environment with Python 3.11
    echo   - conda create -n vaultmind python=3.11
    echo   - conda activate vaultmind
    echo   - pip install google-cloud-aiplatform
    echo.
    echo Option 3: Use other vector stores (already working^)
    echo   - Pinecone (already connected^)
    echo   - Weaviate (already connected^)
    echo   - FAISS (local, no setup needed^)
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Installation Successful!
echo ============================================
echo.
echo Next steps:
echo 1. Restart Streamlit: streamlit run genai_dashboard_modular.py
echo 2. Go to Multi-Vector Ingestion tab
echo 3. Click "Reload Manager" button
echo 4. Vertex AI should show as connected (green^)
echo.
pause
