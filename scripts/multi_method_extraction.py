def extract_with_all_methods(pdf_path):
    """Try multiple PDF extraction methods"""
    results = {}
    
    # Method 1: PyPDF2 (basic)
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        results['pypdf2'] = text
        print(f"✓ PyPDF2: Extracted {len(text)} characters")
    except Exception as e:
        results['pypdf2_error'] = str(e)
        print(f"❌ PyPDF2 failed: {e}")
    
    # Method 2: pdfplumber (better for many PDFs)
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        results['pdfplumber'] = text
        print(f"✓ pdfplumber: Extracted {len(text)} characters")
    except Exception as e:
        results['pdfplumber_error'] = str(e)
        print(f"❌ pdfplumber failed: {e}")
    
    # Method 3: pymupdf (excellent for text extraction)
    try:
        import fitz  # pymupdf
        text = ""
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text() + "\n"
        results['pymupdf'] = text
        doc.close()
        print(f"✓ pymupdf: Extracted {len(text)} characters")
    except Exception as e:
        results['pymupdf_error'] = str(e)
        print(f"❌ pymupdf failed: {e}")
    
    return results

def analyze_extraction_quality(extraction_results):
    """Analyze which extraction method worked best"""
    board_terms = [
        "powers of the board",
        "duties of directors", 
        "responsibilities of the board",
        "board shall have power",
        "authority of the board"
    ]
    
    best_method = None
    best_score = 0
    
    print("\n" + "="*60)
    print("EXTRACTION QUALITY ANALYSIS")
    print("="*60)
    
    for method, text in extraction_results.items():
        if 'error' not in method:
            # Count how many board-related terms we found
            score = 0
            found_terms = []
            
            for term in board_terms:
                if term.lower() in text.lower():
                    score += 1
                    found_terms.append(term)
            
            print(f"\n{method.upper()}:")
            print(f"  Length: {len(text):,} characters")
            print(f"  Board terms found: {score}/{len(board_terms)}")
            print(f"  Found terms: {found_terms}")
            
            # Show a sample of content around "board" or "power"
            lines = text.split('\n')
            sample_lines = []
            for i, line in enumerate(lines):
                if any(word in line.lower() for word in ['board', 'power', 'director']):
                    start = max(0, i-1)
                    end = min(len(lines), i+2)
                    sample_lines.extend(lines[start:end])
                    if len(sample_lines) > 10:  # Limit sample size
                        break
            
            if sample_lines:
                print(f"  Sample content:")
                for line in sample_lines[:5]:
                    if line.strip():
                        print(f"    {line.strip()[:100]}...")
            
            if score > best_score:
                best_score = score
                best_method = method
    
    print(f"\n🏆 BEST METHOD: {best_method} (found {best_score}/{len(board_terms)} terms)")
    return best_method, extraction_results.get(best_method, "")

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
    
    # Test the first PDF found
    pdf_path = str(pdf_files[0])
    print(f"Testing extraction methods on: {pdf_path}")
    
    # Run all extraction methods
    extraction_results = extract_with_all_methods(pdf_path)
    
    # Save all results to examine
    for method, text in extraction_results.items():
        if 'error' not in method:
            output_file = f"extracted_{method}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Saved {method} results to {output_file}")
    
    # Analyze quality
    best_method, best_text = analyze_extraction_quality(extraction_results)
    
    if best_text:
        # Save the best extraction
        with open("best_extraction.txt", "w", encoding="utf-8") as f:
            f.write(best_text)
        print(f"\n✅ Best extraction saved to 'best_extraction.txt'")
        print(f"Ready to create semantic index with {best_method} method")
    else:
        print("\n❌ No extraction method found the expected content")
        print("The PDF might be scanned images requiring OCR")
