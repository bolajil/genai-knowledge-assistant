def extract_with_ocr(pdf_path):
    """Use OCR for scanned PDFs"""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        import os
        from pathlib import Path
        
        print(f"🔍 Attempting OCR extraction on: {pdf_path}")
        
        # Convert PDF to images
        print("📄 Converting PDF pages to images...")
        images = convert_from_path(pdf_path)
        full_text = ""
        
        print(f"📊 Processing {len(images)} pages...")
        
        for i, image in enumerate(images):
            print(f"   Processing page {i+1}/{len(images)}...")
            
            # Save temporary image
            temp_dir = Path("temp_ocr")
            temp_dir.mkdir(exist_ok=True)
            image_path = temp_dir / f"temp_page_{i}.jpg"
            image.save(image_path, 'JPEG')
            
            # OCR the image
            text = pytesseract.image_to_string(image_path, config='--psm 6')
            full_text += f"--- Page {i+1} ---\n" + text + "\n\n"
            
            # Clean up
            os.remove(image_path)
        
        # Clean up temp directory
        temp_dir.rmdir()
        
        print(f"✅ OCR completed: {len(full_text):,} characters extracted")
        return full_text
        
    except ImportError as e:
        print(f"❌ Missing dependencies for OCR:")
        print(f"   Install: pip install pdf2image pytesseract")
        print(f"   Also install Tesseract: https://github.com/tesseract-ocr/tesseract")
        return None
    except Exception as e:
        print(f"❌ OCR error: {e}")
        return None

def test_ocr_quality(text):
    """Test the quality of OCR extracted text"""
    if not text:
        return False
    
    # Check for common OCR issues
    issues = []
    
    # Check character density (OCR often produces sparse text)
    words = text.split()
    if len(words) < 100:
        issues.append("Too few words extracted")
    
    # Check for excessive special characters (OCR artifacts)
    special_chars = sum(1 for c in text if not c.isalnum() and c not in ' \n\t.,;:!?-')
    if special_chars > len(text) * 0.1:
        issues.append("Too many special characters (OCR artifacts)")
    
    # Check for reasonable sentence structure
    sentences = text.split('.')
    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
    if avg_sentence_length < 3:
        issues.append("Sentences too short (poor OCR quality)")
    
    # Look for expected legal document terms
    legal_terms = ["shall", "board", "director", "power", "authority", "responsibility"]
    found_terms = sum(1 for term in legal_terms if term.lower() in text.lower())
    
    print(f"📊 OCR Quality Assessment:")
    print(f"   • Words extracted: {len(words):,}")
    print(f"   • Special character ratio: {special_chars/len(text)*100:.1f}%")
    print(f"   • Average sentence length: {avg_sentence_length:.1f} words")
    print(f"   • Legal terms found: {found_terms}/{len(legal_terms)}")
    
    if issues:
        print(f"⚠️  Quality issues detected:")
        for issue in issues:
            print(f"     - {issue}")
    
    # Return True if quality seems acceptable
    return len(issues) <= 1 and found_terms >= 3

if __name__ == "__main__":
    from pathlib import Path
    
    # Find PDF files
    search_paths = [Path("data"), Path("data/backups"), Path(".")]
    pdf_files = []
    
    for path in search_paths:
        if path.exists():
            for pdf_file in path.rglob("*.pdf"):
                if any(term in pdf_file.name.lower() for term in ["bylaw", "board", "director"]):
                    pdf_files.append(pdf_file)
    
    if not pdf_files:
        print("No PDF files found. Please specify the path manually.")
        exit()
    
    # Test OCR on the first PDF
    pdf_path = str(pdf_files[0])
    print(f"Testing OCR extraction on: {pdf_path}")
    
    # Run OCR extraction
    ocr_text = extract_with_ocr(pdf_path)
    
    if ocr_text:
        # Test quality
        quality_ok = test_ocr_quality(ocr_text)
        
        # Save OCR results
        with open("extracted_ocr.txt", "w", encoding="utf-8") as f:
            f.write(ocr_text)
        print(f"💾 OCR results saved to 'extracted_ocr.txt'")
        
        if quality_ok:
            print(f"✅ OCR quality acceptable - ready to create semantic index")
            
            # Create semantic index with OCR text
            from create_proper_semantic_index import create_proper_semantic_index
            index_path = create_proper_semantic_index(ocr_text, "Bylaws_OCR_Index")
            print(f"🚀 OCR-based semantic index created!")
        else:
            print(f"⚠️  OCR quality poor - manual review recommended")
    else:
        print(f"❌ OCR extraction failed")
