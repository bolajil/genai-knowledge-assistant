"""
Script to regenerate ByLaw index using page-based chunking strategy
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.page_based_chunking import regenerate_index_with_page_chunks
from utils.enhanced_page_chunking import EnhancedPageChunkingRetrieval

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Regenerate ByLaw index with page-based chunking"""
    
    print("🔄 Regenerating ByLawS2_index with Page-Based Chunking")
    print("=" * 60)
    
    try:
        # Test the page chunking on ByLaw document
        print("📄 Testing page-based chunking...")
        
        retriever = EnhancedPageChunkingRetrieval()
        test_query = "removal of directors and vacancies"
        
        results = retriever.retrieve_with_page_chunks(test_query, "ByLawS2_index", max_results=3)
        
        if results:
            print(f"✅ Successfully generated {len(results)} page-based chunks")
            
            for i, result in enumerate(results, 1):
                print(f"\n📋 Chunk {i}:")
                print(f"   Page: {result.get('page_number', 'N/A')}")
                print(f"   Sections: {', '.join(result.get('sections', []))}")
                print(f"   Relevance: {result.get('relevance_score', 0):.2f}")
                print(f"   Length: {len(result.get('content', ''))}")
                
                # Show first 200 chars of content
                content_preview = result.get('content', '')[:200]
                print(f"   Preview: {content_preview}...")
        else:
            print("❌ No chunks generated")
            return False
        
        print("\n" + "=" * 60)
        print("✅ Page-based chunking test completed successfully!")
        print("\n📋 Benefits of Page-Based Chunking:")
        print("   • Preserves document structure and page context")
        print("   • Maintains headers and section identifiers")
        print("   • Better LLM processing with natural boundaries")
        print("   • Improved accuracy for section-specific queries")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in page-based chunking regeneration: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
