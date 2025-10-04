"""
Test Query with Current System
=============================
Test the exact query that was returning table of contents to see current behavior.
"""

import sys
import os
sys.path.append(os.getcwd())

def test_current_query():
    """Test the current system with the problematic query."""
    
    print("Testing Current Query System")
    print("=" * 40)
    
    try:
        # Import the query function from tabs
        from tabs.query_assistant import query_index
        
        query = "Procedures for Board meetings and actions outside of meetings"
        index_name = "ByLawS2_index"
        
        print(f"Query: {query}")
        print(f"Index: {index_name}")
        print("-" * 40)
        
        # Execute the query
        results = query_index(query, index_name, top_k=3)
        
        if results:
            print(f"SUCCESS: Got {len(results)} results")
            
            for i, result in enumerate(results, 1):
                print(f"\n--- RESULT {i} ---")
                
                # Check if it's a dict or string
                if isinstance(result, dict):
                    content = result.get('content', str(result))
                    section = result.get('section', 'N/A')
                    source = result.get('source', 'N/A')
                    score = result.get('relevance_score', 0.0)
                    
                    print(f"Section: {section}")
                    print(f"Source: {source}")
                    print(f"Score: {score}")
                else:
                    content = str(result)
                    print(f"Raw result: {type(result)}")
                
                # Show content preview
                if len(content) > 300:
                    print(f"Content: {content[:300]}...")
                else:
                    print(f"Content: {content}")
                
                # Check if this is TOC vs actual content
                content_lower = content.lower()
                if ('table of contents' in content_lower or 
                    content.count('.') > len(content) * 0.2 or
                    'page' in content_lower and content.count('page') > 3):
                    print("❌ ISSUE: Still looks like table of contents")
                else:
                    print("✅ SUCCESS: Appears to be actual content")
                    
                # Check for board meeting procedures
                if ('board' in content_lower and 'meeting' in content_lower and 
                    ('action' in content_lower or 'procedure' in content_lower)):
                    print("✅ RELEVANT: Contains board meeting procedures")
                else:
                    print("⚠️  RELEVANCE: May not contain specific procedures")
        else:
            print("❌ FAILED: No results returned")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def check_pdf_direct():
    """Check if PDF direct extraction works."""
    
    print("\n" + "=" * 40)
    print("Testing PDF Direct Access")
    print("=" * 40)
    
    try:
        from pathlib import Path
        
        pdf_path = Path("data/indexes/ByLawS2_index/source_document.pdf")
        
        if pdf_path.exists():
            print(f"✅ PDF exists: {pdf_path}")
            print(f"   Size: {pdf_path.stat().st_size / 1024:.1f} KB")
            
            # Try PyPDF2 extraction
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    print(f"   Pages: {len(pdf_reader.pages)}")
                    
                    # Extract first few pages
                    sample_text = ""
                    for i, page in enumerate(pdf_reader.pages[:3]):
                        page_text = page.extract_text()
                        sample_text += page_text
                    
                    print(f"   Sample extraction: {len(sample_text)} characters")
                    
                    # Check for board meeting content
                    if 'board meeting' in sample_text.lower():
                        print("✅ PDF contains board meeting content")
                    else:
                        print("⚠️  Board meeting content not in first 3 pages")
                        
            except Exception as e:
                print(f"❌ PDF extraction failed: {e}")
        else:
            print(f"❌ PDF not found: {pdf_path}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_current_query()
    check_pdf_direct()
    
    print("\n" + "=" * 40)
    print("NEXT STEPS:")
    print("1. If still showing TOC, the PDF needs to be re-extracted")
    print("2. If PDF extraction works, integration needs fixing")
    print("3. Try the query in the web interface to compare")
    print("=" * 40)
