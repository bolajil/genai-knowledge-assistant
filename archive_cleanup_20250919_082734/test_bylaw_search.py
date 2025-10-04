"""
ByLaw Search Tester

This script provides a simple way to test the ByLaw search functionality
without running the full VaultMIND system.
"""

import sys
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_bylaw_search(query):
    """Test the ByLaw search functionality"""
    logger.info(f"Testing ByLaw search with query: '{query}'")
    
    # Import the direct bylaws retriever
    try:
        from utils.direct_bylaws_retriever import search_bylaws
        
        # Search for ByLaw content
        results = search_bylaws(query, 5)
        
        if results:
            logger.info(f"Found {len(results)} results:")
            
            for i, result in enumerate(results):
                logger.info(f"\nResult {i+1} (Score: {result['score']:.4f}):")
                logger.info(f"Source: {result['source']}")
                logger.info(f"Content:\n{result['content']}")
                
                if "metadata" in result and result["metadata"]:
                    logger.info(f"Metadata: {result['metadata']}")
        else:
            logger.info("No results found.")
        
        return True
    except ImportError as e:
        logger.error(f"Error importing direct_bylaws_retriever: {e}")
        return False
    except Exception as e:
        logger.error(f"Error testing ByLaw search: {e}")
        return False

def main():
    """Main function"""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Test ByLaw search functionality")
    parser.add_argument("query", nargs="?", default="board meeting", help="The query to search for")
    args = parser.parse_args()
    
    # Test ByLaw search
    if test_bylaw_search(args.query):
        logger.info("✅ ByLaw search test completed successfully")
    else:
        logger.error("❌ ByLaw search test failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
