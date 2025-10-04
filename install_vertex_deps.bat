@echo off
echo ============================================
echo Installing Vertex AI Dependencies
echo ============================================
echo.

echo Step 1: Upgrading pip...
py -m pip install --upgrade pip
echo.

echo Step 2: Installing google-auth...
py -m pip install google-auth
echo.

echo Step 3: Installing google-cloud-aiplatform...
py -m pip install google-cloud-aiplatform
echo.

echo Step 4: Verifying installation...
py -c "import google.cloud.aiplatform; print('SUCCESS: Vertex AI package installed, version:', google.cloud.aiplatform.__version__)"
echo.

echo ============================================
echo Installation Complete
echo ============================================
pause
