"""
Test Document-Aware Chunking System
===================================
Test the new chunking system with the actual ByLawS2_index to verify it returns content instead of TOC.
"""

import sys
import os
sys.path.append(os.getcwd())

def test_bylaws_query():
    """Test the specific query that was returning table of contents."""
    
    print("Testing Document-Aware Chunking System")
    print("="*50)
    
    try:
        # Test the comprehensive retrieval with the actual query
        from utils.comprehensive_document_retrieval import retrieve_comprehensive_information
        
        query = "Procedures for Board meetings and actions outside of meetings"
        index_name = "ByLawS2_index"
        
        print(f"Query: {query}")
        print(f"Index: {index_name}")
        print("-" * 50)
        
        # Get results using the enhanced system
        results = retrieve_comprehensive_information(query, index_name, max_results=3)
        
        if results:
            print(f"SUCCESS: Retrieved {len(results)} results")
            
            for i, result in enumerate(results, 1):
                print(f"\n--- RESULT {i} ---")
                print(f"Section: {result.get('section', 'N/A')}")
                print(f"Source: {result.get('source', 'N/A')}")
                print(f"Confidence: {result.get('confidence_score', 0.0):.2f}")
                print(f"Word Count: {result.get('word_count', 0)}")
                
                content = result.get('content', '')
                if len(content) > 300:
                    print(f"Content Preview: {content[:300]}...")
                else:
                    print(f"Content: {content}")
                
                # Check if this looks like TOC vs actual content
                if 'TABLE OF CONTENTS' in content.upper() or content.count('.') > len(content) * 0.3:
                    print("⚠️  WARNING: This looks like table of contents!")
                else:
                    print("✅ SUCCESS: This appears to be actual section content!")
        else:
            print("❌ FAILED: No results returned")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_pdf_extraction():
    """Test direct PDF extraction."""
    
    print("\n" + "="*50)
    print("Testing PDF Direct Extraction")
    print("="*50)
    
    try:
        from utils.pdf_section_extractor import PDFSectionExtractor
        from pathlib import Path
        
        pdf_path = Path("data/indexes/ByLawS2_index/source_document.pdf")
        
        if pdf_path.exists():
            print(f"PDF found: {pdf_path}")
            
            extractor = PDFSectionExtractor()
            sections = extractor.find_section_content(str(pdf_path), "board meetings action outside")
            
            print(f"Found {len(sections)} relevant sections")
            
            for i, section in enumerate(sections[:2], 1):
                print(f"\n--- SECTION {i} ---")
                print(f"Title: {section['section_title']}")
                print(f"Relevance: {section['relevance_score']:.2f}")
                print(f"Word Count: {section['word_count']}")
                
                content = section['content']
                if len(content) > 200:
                    print(f"Content Preview: {content[:200]}...")
                else:
                    print(f"Content: {content}")
        else:
            print(f"❌ PDF not found: {pdf_path}")
            
    except Exception as e:
        print(f"❌ ERROR in PDF extraction: {e}")

def test_document_aware_chunking():
    """Test document-aware chunking directly."""
    
    print("\n" + "="*50)
    print("Testing Document-Aware Chunking")
    print("="*50)
    
    try:
        from utils.document_aware_chunking import chunk_document_intelligently
        
        # Sample bylaws content
        test_content = """
        ARTICLE III. BOARD OF DIRECTORS: NUMBER, POWERS, MEETINGS
        
        Section 2. BOARD MEETINGS; Action Outside of Meeting
        Regular meetings of the Board of Directors may be held at such time and place as shall be determined, from time to time, by a majority of the directors, but at least four (4) times per year. Special meetings of the Board of Directors may be called by the president or by any two (2) directors. 
        
        The Board may take action outside of a meeting if all Directors consent in writing to the action. Such written consent shall be filed with the minutes of the proceedings of the Board and shall have the same force and effect as a unanimous vote at a meeting.
        
        Section 3. Notice of MEETINGS
        Notice of each meeting of the Board of Directors shall be given to each director by the secretary or president at least ten (10) days prior to the date of such meeting.
        """
        
        chunks = chunk_document_intelligently(test_content, "test_bylaws.pdf")
        
        print(f"Generated {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n--- CHUNK {i} ---")
            print(f"Section: {chunk['section']}")
            print(f"Word Count: {chunk['word_count']}")
            print(f"Document Type: {chunk['metadata'].get('document_type', 'N/A')}")
            
            content = chunk['content']
            if len(content) > 200:
                print(f"Content Preview: {content[:200]}...")
            else:
                print(f"Content: {content}")
                
    except Exception as e:
        print(f"❌ ERROR in document-aware chunking: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bylaws_query()
    test_pdf_extraction()
    test_document_aware_chunking()
    
    print("\n" + "="*50)
    print("Test Complete")
    print("="*50)
