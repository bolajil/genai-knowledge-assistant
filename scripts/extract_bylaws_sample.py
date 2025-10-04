import PyPDF2
import pdfplumber
import os

def extract_with_all_methods(pdf_path):
    """Try multiple PDF extraction methods and show samples"""
    results = {}
    
    print(f"🔍 Extracting from: {pdf_path}")
    
    # Method 1: PyPDF2
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            print(f"📄 PDF has {len(reader.pages)} pages")
            for page in reader.pages:
                text += page.extract_text() + "\n"
        results['pypdf2'] = text
        print(f"✓ PyPDF2: {len(text):,} characters")
    except Exception as e:
        results['pypdf2_error'] = str(e)
        print(f"❌ PyPDF2 failed: {e}")
    
    # Method 2: pdfplumber
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        results['pdfplumber'] = text
        print(f"✓ pdfplumber: {len(text):,} characters")
    except Exception as e:
        results['pdfplumber_error'] = str(e)
        print(f"❌ pdfplumber failed: {e}")
    
    return results

def search_for_board_content(text, method_name):
    """Search for board-related content and show samples"""
    board_terms = [
        "powers of the board",
        "duties of directors", 
        "responsibilities of the board",
        "board shall have power",
        "authority of the board",
        "powers and duties",
        "board of directors shall"
    ]
    
    print(f"\n🔍 SEARCHING IN {method_name.upper()} EXTRACTION:")
    print("="*60)
    
    found_terms = []
    samples = []
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        for term in board_terms:
            if term.lower() in line.lower():
                found_terms.append(term)
                # Get context around the match
                start = max(0, i-3)
                end = min(len(lines), i+6)
                context = '\n'.join(lines[start:end])
                samples.append({
                    'term': term,
                    'context': context,
                    'line_num': i
                })
                break
    
    print(f"Found {len(found_terms)} board-related terms: {found_terms}")
    
    # Show first few samples
    for i, sample in enumerate(samples[:3]):
        print(f"\n📝 SAMPLE {i+1} - Found '{sample['term']}' at line {sample['line_num']}:")
        print("-" * 40)
        print(sample['context'])
        print("-" * 40)
    
    return len(found_terms), samples

def show_text_structure(text, method_name):
    """Show the structure of extracted text"""
    print(f"\n📊 TEXT STRUCTURE ANALYSIS - {method_name.upper()}:")
    print("="*60)
    
    lines = text.split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    print(f"Total lines: {len(lines):,}")
    print(f"Non-empty lines: {len(non_empty_lines):,}")
    print(f"Average line length: {sum(len(line) for line in non_empty_lines) / len(non_empty_lines):.1f} chars")
    
    # Show first 20 non-empty lines to see structure
    print(f"\n📄 FIRST 20 LINES PREVIEW:")
    print("-" * 40)
    for i, line in enumerate(non_empty_lines[:20]):
        print(f"{i+1:2d}: {line}")
    print("-" * 40)
    
    # Look for potential section headers (all caps, short lines)
    headers = [line for line in non_empty_lines if len(line) > 5 and len(line) < 100 and line.isupper()]
    print(f"\n📋 POTENTIAL SECTION HEADERS ({len(headers)} found):")
    for header in headers[:10]:  # Show first 10
        print(f"  • {header}")
    if len(headers) > 10:
        print(f"  ... and {len(headers)-10} more")

if __name__ == "__main__":
    # Extract from the Bylaws PDF
    pdf_path = r"c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\uploads\Bylaws.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at: {pdf_path}")
        exit()
    
    # Run extraction with all methods
    extraction_results = extract_with_all_methods(pdf_path)
    
    # Analyze each successful extraction
    best_method = None
    best_score = 0
    
    for method, text in extraction_results.items():
        if 'error' not in method and text:
            print(f"\n{'='*80}")
            print(f"ANALYZING {method.upper()} EXTRACTION")
            print('='*80)
            
            # Show text structure
            show_text_structure(text, method)
            
            # Search for board content
            score, samples = search_for_board_content(text, method)
            
            # Save extraction to file
            output_file = f"extracted_{method}_sample.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"💾 Full extraction saved to: {output_file}")
            
            if score > best_score:
                best_score = score
                best_method = method
    
    print(f"\n🏆 BEST EXTRACTION METHOD: {best_method} (found {best_score} board terms)")
    
    if best_method:
        print(f"✅ Ready to create semantic index with {best_method} extraction")
    else:
        print(f"❌ No method found board content - PDF might be scanned or use different terminology")
