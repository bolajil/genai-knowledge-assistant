"""
ByLaw Query Test Script

This script tests the enhanced search capability for ByLaw content.
It will send queries that should trigger the direct ByLaw content retrieval.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the root directory to the path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Try to import the search manager
try:
    from tabs.agent_assistant_enhanced import SearchManager, is_bylaw_query
    from utils.direct_bylaws_retriever import search_bylaws
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    sys.exit(1)

def test_bylaw_query_detection():
    """Test the is_bylaw_query function"""
    print("\n=== Testing ByLaw Query Detection ===")
    
    test_queries = [
        "Tell me about board meetings",
        "How do directors vote electronically?",
        "What is the quorum for board meetings?",
        "Can a board take action outside of a meeting?",
        "Explain the rules for executive sessions",
        "This is an unrelated query about cloud computing"
    ]
    
    for query in test_queries:
        is_bylaw = is_bylaw_query(query)
        status = "✅ Detected as ByLaw query" if is_bylaw else "❌ Not detected as ByLaw query"
        print(f"Query: '{query}' -> {status}")

def test_direct_bylaw_retrieval():
    """Test the direct ByLaw retrieval function"""
    print("\n=== Testing Direct ByLaw Retrieval ===")
    
    test_queries = [
        "Tell me about board meetings",
        "How do directors vote electronically?",
        "This is an unrelated query about cloud computing"
    ]
    
    for query in test_queries:
        results = search_bylaws(query, max_results=2)
        
        if results:
            print(f"Query: '{query}'")
            print(f"  ✅ Found {len(results)} results")
            print(f"  Relevance score: {results[0]['score']}")
            print(f"  Content preview: {results[0]['content'][:50]}...")
        else:
            print(f"Query: '{query}'")
            print(f"  ❌ No results found")

def test_search_manager():
    """Test the SearchManager with ByLaw queries"""
    print("\n=== Testing SearchManager ===")
    
    try:
        # Initialize the search manager
        search_manager = SearchManager()
        
        test_queries = [
            ("Tell me about board meetings", ["ByLawS2_index"]),
            ("How do directors vote electronically?", ["General"]),
        ]
        
        for query, sources in test_queries:
            print(f"\nQuery: '{query}' with sources {sources}")
            
            try:
                results = search_manager.search(query, sources)
                
                if results:
                    print(f"  ✅ Found {len(results)} results")
                    for i, result in enumerate(results):
                        print(f"  Result {i+1}:")
                        print(f"    Source: {result.source_name}")
                        print(f"    Score: {result.relevance_score}")
                        print(f"    Content preview: {result.content[:50]}...")
                else:
                    print(f"  ❌ No results found")
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"Error initializing SearchManager: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("BYLAW QUERY TEST SCRIPT")
    print("======================\n")
    
    # Test ByLaw query detection
    test_bylaw_query_detection()
    
    # Test direct ByLaw retrieval
    test_direct_bylaw_retrieval()
    
    # Test SearchManager (optional, might fail due to dependencies)
    try:
        test_search_manager()
    except Exception as e:
        print(f"\nSearchManager test skipped: {str(e)}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
