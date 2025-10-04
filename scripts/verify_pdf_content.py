import PyPDF2
from pathlib import Path

def search_in_pdf(pdf_path, search_terms):
    """Search for specific terms in PDF to verify content exists"""
    print(f"Searching in: {pdf_path}")
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            found_content = False
            
            print(f"PDF has {len(reader.pages)} pages")
            
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text = page.extract_text()
                
                for term in search_terms:
                    if term.lower() in text.lower():
                        print(f"✓ FOUND '{term}' on page {page_num + 1}")
                        # Show some context
                        lines = text.split('\n')
                        for i, line in enumerate(lines):
                            if term.lower() in line.lower():
                                start = max(0, i-2)
                                end = min(len(lines), i+5)
                                context = '\n'.join(lines[start:end])
                                print(f"Context:\n{context}\n" + "="*50)
                                found_content = True
                                break
                        
            if not found_content:
                print("❌ None of the search terms were found in the PDF")
                print("This suggests the PDF might be:")
                print("1. Scanned images (needs OCR)")
                print("2. Using different terminology")
                print("3. Has encoding issues")
            
            return found_content
            
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return False

# Find PDF files in common locations
def find_bylaw_pdfs():
    """Find potential bylaw PDF files"""
    search_paths = [
        Path("data"),
        Path("data/backups"),
        Path("."),
    ]
    
    pdf_files = []
    for path in search_paths:
        if path.exists():
            for pdf_file in path.rglob("*.pdf"):
                if any(term in pdf_file.name.lower() for term in ["bylaw", "board", "director"]):
                    pdf_files.append(pdf_file)
    
    return pdf_files

if __name__ == "__main__":
    # Search terms to verify content exists
    search_terms = [
        "powers of the board",
        "duties of directors", 
        "responsibilities of the board",
        "board shall have power",
        "authority of the board",
        "powers and duties",
        "board of directors shall"
    ]
    
    # Find potential PDF files
    pdf_files = find_bylaw_pdfs()
    
    if pdf_files:
        print(f"Found {len(pdf_files)} potential PDF files:")
        for pdf in pdf_files:
            print(f"  - {pdf}")
        
        # Test each PDF
        for pdf_path in pdf_files:
            print(f"\n{'='*60}")
            print(f"Testing: {pdf_path.name}")
            print('='*60)
            found = search_in_pdf(str(pdf_path), search_terms)
            if found:
                print(f"✓ {pdf_path.name} contains the target content!")
            else:
                print(f"❌ {pdf_path.name} does not contain expected content")
    else:
        print("No PDF files found. Please check the file path.")
        print("Common locations to check:")
        print("  - data/")
        print("  - data/backups/")
        print("  - Current directory")
