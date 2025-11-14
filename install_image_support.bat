@echo off
echo ========================================
echo Image Ingestion Setup Script
echo ========================================
echo.

echo Step 1: Installing Python dependencies...
pip install pillow pytesseract easyocr numpy
echo.

echo Step 2: Checking Tesseract installation...
tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Tesseract not found!
    echo.
    echo Please install Tesseract OCR:
    echo 1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo 2. Or run: choco install tesseract
    echo 3. Add to PATH: C:\Program Files\Tesseract-OCR
    echo.
) else (
    echo [OK] Tesseract is installed
    tesseract --version
    echo.
)

echo Step 3: Testing imports...
python -c "import PIL; print('[OK] Pillow installed')" 2>nul || echo [ERROR] Pillow not installed
python -c "import pytesseract; print('[OK] Pytesseract installed')" 2>nul || echo [ERROR] Pytesseract not installed
python -c "import easyocr; print('[OK] EasyOCR installed')" 2>nul || echo [ERROR] EasyOCR not installed
python -c "import numpy; print('[OK] NumPy installed')" 2>nul || echo [ERROR] NumPy not installed
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To run the demo:
echo   streamlit run demo_image_ingestion.py
echo.
echo To test image extraction:
echo   python -c "from utils.image_text_extractor import ImageTextExtractor; print('Image extractor ready!')"
echo.

pause
