"""
Enhanced Document Search Demo

This script demonstrates the enhanced document search capabilities:
1. Searching by metadata (file type, date, size, author)
2. Hybrid search combining vector search and metadata
3. Advanced query preprocessing with expansion
"""

import argparse
import logging
import json
from typing import Dict, List, Any
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import enhanced search components
try:
    from utils.enhanced_search import get_enhanced_search
    enhanced_search = get_enhanced_search()
    ENHANCED_SEARCH_AVAILABLE = True
except ImportError:
    logger.error("Enhanced search not available.")
    ENHANCED_SEARCH_AVAILABLE = False
    enhanced_search = None

def pretty_print_results(results, show_metadata=False):
    """Print search results in a readable format"""
    if not results:
        print("\n❌ No results found.")
        return
    
    print(f"\n✅ Found {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        print(f"Result {i} (Relevance: {result.relevance:.2f}) - Source: {result.source}")
        print("-" * 50)
        
        # Print a preview of the content
        preview = result.content[:200] + "..." if len(result.content) > 200 else result.content
        print(preview)
        
        # Show metadata if requested
        if show_metadata and result.metadata:
            print("\nMetadata:")
            for key, value in result.metadata.items():
                print(f"  {key}: {value}")
        
        print("\n")

def run_demo_search(query, search_type="hybrid", max_results=5, show_metadata=False):
    """Run a demonstration search"""
    if not ENHANCED_SEARCH_AVAILABLE:
        print("❌ Enhanced search not available.")
        return
    
    print(f"\n🔍 Searching for: '{query}' using {search_type} search")
    print("-" * 60)
    
    start_time = time.time()
    
    # Perform the search
    results = enhanced_search.search(
        query=query,
        max_results=max_results,
        search_type=search_type
    )
    
    # Print timing
    end_time = time.time()
    duration = end_time - start_time
    print(f"Search completed in {duration:.2f} seconds")
    
    # Print results
    pretty_print_results(results, show_metadata)
    
    return results

def demo_metadata_search():
    """Demonstrate metadata search capabilities"""
    print("\n===== Metadata Search Demonstration =====")
    
    # Search by file type
    run_demo_search("type:pdf cloud computing", "metadata", show_metadata=True)
    
    # Search by date range
    run_demo_search("date:2022-01-01..2023-12-31 security", "metadata", show_metadata=True)
    
    # Search by file type and keyword
    run_demo_search("type:txt database", "metadata", show_metadata=True)

def demo_hybrid_search():
    """Demonstrate hybrid search capabilities"""
    print("\n===== Hybrid Search Demonstration =====")
    
    # Basic hybrid search
    run_demo_search("cloud computing benefits", "hybrid")
    
    # Hybrid search with metadata
    run_demo_search("type:pdf cloud computing benefits", "hybrid", show_metadata=True)
    
    # Hybrid search with specific question
    run_demo_search("What are the cost benefits of cloud computing?", "hybrid")

def demo_vector_search():
    """Demonstrate vector search capabilities"""
    print("\n===== Vector Search Demonstration =====")
    
    # Basic vector search
    run_demo_search("cloud computing benefits", "vector")
    
    # Vector search with specific question
    run_demo_search("What are the security concerns with public cloud?", "vector")

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="Enhanced Document Search Demo")
    
    # Add arguments
    parser.add_argument("--query", type=str, help="Search query to run")
    parser.add_argument("--type", type=str, default="hybrid", 
                        choices=["hybrid", "vector", "metadata"],
                        help="Type of search to perform")
    parser.add_argument("--max-results", type=int, default=5, 
                        help="Maximum number of results to return")
    parser.add_argument("--show-metadata", action="store_true", 
                        help="Show document metadata in results")
    parser.add_argument("--demo", type=str, choices=["all", "metadata", "hybrid", "vector"],
                        help="Run a predefined demo")
    
    args = parser.parse_args()
    
    # Check if enhanced search is available
    if not ENHANCED_SEARCH_AVAILABLE:
        print("❌ Enhanced search not available. Please check your installation.")
        return
    
    # Run the appropriate demo or search
    if args.demo:
        if args.demo == "all":
            demo_metadata_search()
            demo_hybrid_search()
            demo_vector_search()
        elif args.demo == "metadata":
            demo_metadata_search()
        elif args.demo == "hybrid":
            demo_hybrid_search()
        elif args.demo == "vector":
            demo_vector_search()
    elif args.query:
        run_demo_search(
            query=args.query,
            search_type=args.type,
            max_results=args.max_results,
            show_metadata=args.show_metadata
        )
    else:
        # Default to running all demos
        demo_metadata_search()
        demo_hybrid_search()
        demo_vector_search()

if __name__ == "__main__":
    main()
