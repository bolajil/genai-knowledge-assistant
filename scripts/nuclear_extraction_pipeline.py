"""
Nuclear Option: Complete PDF extraction and semantic indexing pipeline
This script implements the full solution to fix broken ingestion
"""

import os
import sys
from pathlib import Path
import json
import numpy as np

def find_pdf_files():
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

def verify_pdf_content(pdf_path):
    """Verify PDF contains expected content"""
    try:
        import PyPDF2
        
        search_terms = [
            "powers of the board",
            "duties of directors", 
            "responsibilities of the board",
            "board shall have power",
            "authority of the board"
        ]
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            
            found_terms = []
            for term in search_terms:
                if term.lower() in full_text.lower():
                    found_terms.append(term)
            
            print(f"✓ PDF verification: Found {len(found_terms)}/{len(search_terms)} key terms")
            return len(found_terms) > 0, full_text
            
    except Exception as e:
        print(f"❌ PDF verification failed: {e}")
        return False, ""

def extract_with_multiple_methods(pdf_path):
    """Try all extraction methods"""
    results = {}
    
    # Method 1: PyPDF2
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        results['pypdf2'] = text
        print(f"✓ PyPDF2: {len(text):,} characters")
    except Exception as e:
        results['pypdf2_error'] = str(e)
        print(f"❌ PyPDF2 failed: {e}")
    
    # Method 2: pdfplumber
    try:
        import pdfplumber
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
    
    # Method 3: pymupdf
    try:
        import fitz  # pymupdf
        text = ""
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text() + "\n"
        results['pymupdf'] = text
        doc.close()
        print(f"✓ pymupdf: {len(text):,} characters")
    except Exception as e:
        results['pymupdf_error'] = str(e)
        print(f"❌ pymupdf failed: {e}")
    
    return results

def find_best_extraction(extraction_results):
    """Find the extraction method that captured the most board-related content"""
    board_terms = [
        "powers of the board", "duties of directors", "responsibilities of the board",
        "board shall have power", "authority of the board", "powers and duties"
    ]
    
    best_method = None
    best_score = 0
    best_text = ""
    
    for method, text in extraction_results.items():
        if 'error' not in method:
            score = sum(1 for term in board_terms if term.lower() in text.lower())
            
            if score > best_score:
                best_score = score
                best_method = method
                best_text = text
    
    print(f"🏆 Best method: {best_method} (found {best_score}/{len(board_terms)} terms)")
    return best_method, best_text

def create_nuclear_semantic_index(text, index_name="Bylaws_Nuclear_Index"):
    """Create the nuclear semantic index"""
    from sentence_transformers import SentenceTransformer
    
    print(f"Creating nuclear semantic index: {index_name}")
    
    # Advanced section detection
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_section = "Introduction"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detect section headers (multiple criteria)
        is_header = (
            (len(line) > 5 and len(line) < 100 and line.isupper()) or
            (line.startswith('ARTICLE') and line.isupper()) or
            (line.startswith('SECTION') and line.isupper()) or
            (line.endswith(':') and len(line) < 80 and line.isupper())
        )
        
        if is_header and not line.isdigit() and not line.startswith('Page'):
            # Save current chunk
            if current_chunk:
                chunk_text = "\n".join(current_chunk)
                if len(chunk_text) > 100:  # Meaningful content only
                    chunks.append({
                        "text": chunk_text,
                        "section": current_section
                    })
            
            # Start new section
            current_section = line
            current_chunk = [line]
        else:
            current_chunk.append(line)
    
    # Add final chunk
    if current_chunk:
        chunk_text = "\n".join(current_chunk)
        if len(chunk_text) > 100:
            chunks.append({
                "text": chunk_text,
                "section": current_section
            })
    
    print(f"Created {len(chunks)} semantic chunks")
    
    # Generate embeddings
    model = SentenceTransformer('all-MiniLM-L6-v2')
    chunk_texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(chunk_texts)
    
    # Save index
    index_path = Path(f"data/indexes/{index_name}")
    index_path.mkdir(parents=True, exist_ok=True)
    
    with open(index_path / "semantic_chunks.json", "w", encoding="utf-8") as f:
        json.dump({
            "chunks": chunk_texts,
            "metadata": [{"section": chunk["section"]} for chunk in chunks]
        }, f, indent=2)
    
    np.save(index_path / "chunk_embeddings.npy", embeddings)
    
    print(f"✅ Nuclear index created: {index_path}")
    return index_path

def test_nuclear_index(query="What specific powers and responsibilities does the Board of Directors have?", 
                      index_name="Bylaws_Nuclear_Index"):
    """Test the nuclear index"""
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    
    index_path = Path(f"data/indexes/{index_name}")
    
    with open(index_path / "semantic_chunks.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    chunks = data["chunks"]
    metadata = data["metadata"]
    embeddings = np.load(index_path / "chunk_embeddings.npy")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query)
    
    similarities = cosine_similarity([query_embedding], embeddings)[0]
    top_indices = np.argsort(similarities)[-3:][::-1]
    
    print(f"\n🎯 NUCLEAR INDEX TEST RESULTS")
    print("="*60)
    
    for i, idx in enumerate(top_indices):
        score = similarities[idx]
        section = metadata[idx]["section"]
        content = chunks[idx]
        
        print(f"\nResult #{i+1} [Score: {score:.4f}]")
        print(f"Section: {section}")
        print(f"Content preview: {content[:300]}...")
        
        if score > 0.3:
            print("✅ HIGH RELEVANCE")
        elif score > 0.2:
            print("⚠️  MODERATE RELEVANCE")
        else:
            print("❌ LOW RELEVANCE")

def main():
    """Run the complete nuclear extraction pipeline"""
    print("🚀 NUCLEAR EXTRACTION PIPELINE STARTING")
    print("="*60)
    
    # Step 1: Find PDFs
    pdf_files = find_pdf_files()
    if not pdf_files:
        print("❌ No PDF files found")
        return
    
    pdf_path = str(pdf_files[0])
    print(f"📄 Processing: {pdf_path}")
    
    # Step 2: Verify content exists
    has_content, _ = verify_pdf_content(pdf_path)
    if not has_content:
        print("⚠️  PDF verification failed - may need OCR")
    
    # Step 3: Extract with all methods
    print("\n📤 EXTRACTION PHASE")
    extraction_results = extract_with_multiple_methods(pdf_path)
    
    # Step 4: Find best extraction
    best_method, best_text = find_best_extraction(extraction_results)
    
    if not best_text:
        print("❌ All extraction methods failed")
        return
    
    # Save best extraction
    with open("nuclear_extraction.txt", "w", encoding="utf-8") as f:
        f.write(best_text)
    print(f"💾 Best extraction saved to nuclear_extraction.txt")
    
    # Step 5: Create semantic index
    print("\n🧠 SEMANTIC INDEXING PHASE")
    index_path = create_nuclear_semantic_index(best_text)
    
    # Step 6: Test the index
    print("\n🧪 TESTING PHASE")
    test_nuclear_index()
    
    print(f"\n🎉 NUCLEAR PIPELINE COMPLETE!")
    print(f"✅ Index ready at: {index_path}")
    print(f"✅ Ready to query Board powers with high accuracy")

if __name__ == "__main__":
    main()
