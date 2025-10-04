@echo off
echo ============================================
echo Installing Vertex AI with Compatible Versions
echo ============================================
echo.

echo This installs pre-built wheels that don't require Rust compilation
echo.

echo Step 1: Installing google-auth...
py -m pip install google-auth==2.23.4
echo.

echo Step 2: Installing pydantic with pre-built wheel...
py -m pip install "pydantic>=2.0,<2.10"
echo.

echo Step 3: Installing google-cloud-aiplatform with constraints...
py -m pip install "google-cloud-aiplatform>=1.38.0,<1.60" --no-deps
echo.

echo Step 4: Installing remaining dependencies...
py -m pip install google-api-core[grpc] proto-plus protobuf packaging google-cloud-storage google-cloud-bigquery google-cloud-resource-manager shapely docstring_parser
echo.

echo Step 5: Verifying installation...
py -c "import google.cloud.aiplatform; print('SUCCESS: Vertex AI installed, version:', google.cloud.aiplatform.__version__)"
echo.

echo ============================================
echo Installation Complete
echo ============================================
pause
