"""
Test OCR Setup - Diagnose Tesseract and EasyOCR installation
"""

import sys
import os

print("=" * 60)
print("OCR Setup Diagnostic Tool")
print("=" * 60)
print()

# Test 1: Check Python packages
print("1. Checking Python packages...")
print("-" * 60)

try:
    from PIL import Image
    print("✅ PIL/Pillow: INSTALLED")
except ImportError as e:
    print(f"❌ PIL/Pillow: NOT INSTALLED - {e}")

try:
    import pytesseract
    print("✅ pytesseract: INSTALLED")
    
    # Try to get Tesseract version
    try:
        version = pytesseract.get_tesseract_version()
        print(f"   Version: {version}")
    except Exception as e:
        print(f"   ⚠️ Warning: Cannot get version - {e}")
        
except ImportError as e:
    print(f"❌ pytesseract: NOT INSTALLED - {e}")

try:
    import easyocr
    print("✅ easyocr: INSTALLED")
except ImportError as e:
    print(f"❌ easyocr: NOT INSTALLED - {e}")

try:
    import numpy
    print("✅ numpy: INSTALLED")
except ImportError as e:
    print(f"❌ numpy: NOT INSTALLED - {e}")

print()

# Test 2: Check Tesseract executable
print("2. Checking Tesseract OCR executable...")
print("-" * 60)

try:
    import pytesseract
    
    # Try to find Tesseract
    tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
    print(f"Tesseract path: {tesseract_cmd}")
    
    # Check if file exists
    if os.path.exists(tesseract_cmd):
        print("✅ Tesseract executable: FOUND")
    else:
        print("❌ Tesseract executable: NOT FOUND at specified path")
        print()
        print("   Common installation paths:")
        print("   - C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        print("   - C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe")
        print()
        print("   To install Tesseract:")
        print("   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   2. Or run: choco install tesseract")
        
except Exception as e:
    print(f"❌ Error checking Tesseract: {e}")

print()

# Test 3: Try actual OCR on a test image
print("3. Testing OCR functionality...")
print("-" * 60)

try:
    from PIL import Image, ImageDraw, ImageFont
    import pytesseract
    
    # Create a simple test image with text
    print("Creating test image...")
    img = Image.new('RGB', (400, 100), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fallback to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    draw.text((10, 30), "Hello World 123", fill='black', font=font)
    
    # Try OCR
    print("Running OCR...")
    text = pytesseract.image_to_string(img)
    
    if text.strip():
        print(f"✅ OCR SUCCESS! Extracted: '{text.strip()}'")
    else:
        print("⚠️ OCR ran but extracted no text")
        
except Exception as e:
    print(f"❌ OCR TEST FAILED: {e}")
    import traceback
    print()
    print("Error details:")
    print(traceback.format_exc())

print()

# Test 4: Check image extractor
print("4. Testing image_text_extractor module...")
print("-" * 60)

try:
    from utils.image_text_extractor import ImageTextExtractor, PIL_AVAILABLE, TESSERACT_AVAILABLE, EASYOCR_AVAILABLE
    
    print(f"PIL Available: {PIL_AVAILABLE}")
    print(f"Tesseract Available: {TESSERACT_AVAILABLE}")
    print(f"EasyOCR Available: {EASYOCR_AVAILABLE}")
    
    if PIL_AVAILABLE and TESSERACT_AVAILABLE:
        print()
        print("Testing ImageTextExtractor...")
        
        # Create test image
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        draw.text((10, 30), "Test Image 456", fill='black', font=font)
        
        # Convert to bytes
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # Extract text
        extractor = ImageTextExtractor(preferred_engine="tesseract")
        text, method, metadata = extractor.extract_text_from_image(img_bytes, "test.png")
        
        print(f"✅ ImageTextExtractor SUCCESS!")
        print(f"   Method: {method}")
        print(f"   Confidence: {metadata.get('confidence', 0):.1f}%")
        print(f"   Words: {metadata.get('word_count', 0)}")
        print(f"   Extracted: '{text[:100]}'")
    else:
        print("⚠️ Cannot test - missing dependencies")
        
except Exception as e:
    print(f"❌ ImageTextExtractor TEST FAILED: {e}")
    import traceback
    print()
    print("Error details:")
    print(traceback.format_exc())

print()
print("=" * 60)
print("Diagnostic Complete!")
print("=" * 60)
print()

# Summary
print("SUMMARY:")
print("-" * 60)

all_ok = True

try:
    from PIL import Image
    import pytesseract
    import numpy
    
    # Check if Tesseract works
    test_img = Image.new('RGB', (100, 50), color='white')
    pytesseract.image_to_string(test_img)
    
    print("✅ OCR system is ready to use!")
    print()
    print("You can now run:")
    print("  streamlit run demo_image_ingestion.py")
    
except Exception as e:
    all_ok = False
    print("❌ OCR system has issues")
    print()
    print("RECOMMENDED ACTIONS:")
    print("1. Install missing packages:")
    print("   pip install pillow pytesseract easyocr numpy")
    print()
    print("2. Install Tesseract OCR:")
    print("   Download: https://github.com/UB-Mannheim/tesseract/wiki")
    print("   Or run: choco install tesseract")
    print()
    print("3. Add Tesseract to PATH:")
    print("   C:\\Program Files\\Tesseract-OCR")

print()
