"""
Test script for VaultMIND Agent multi-source search functionality.
This script tests the search functionality and agent response generation directly.
"""
import sys
import os
import logging
from pprint import pprint

# Add the root directory to the path so we can import the utils modules
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_search_functionality():
    """Test the multi-source search functionality"""
    try:
        from utils.multi_source_search import perform_multi_source_search, format_search_results_for_agent
        
        # Test 1: AWS Security Query
        print("\n== TEST 1: AWS Security Query ==")
        query = "What are the best practices for AWS security?"
        sources = ["Indexed Documents", "Web Search (External)"]
        
        print(f"Searching for: {query}")
        print(f"Sources: {sources}")
        
        # Perform the search with use_placeholders=False to ensure real results
        results = perform_multi_source_search(query, sources, max_results=5, use_placeholders=False)
        
        print(f"Found {len(results)} results")
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"Source: {result.source_name} ({result.source_type})")
            print(f"Relevance: {result.relevance_score:.2f}")
            print(f"Content: {result.content[:100]}...")
        
        # Format the results for agent display
        formatted_results = format_search_results_for_agent(results)
        print("\n== Formatted Results for Agent ==")
        print(formatted_results[:500] + "...\n")
        
        # Test 2: Azure Security Query
        print("\n== TEST 2: Azure Security Query ==")
        query = "What are the latest Azure security features?"
        
        print(f"Searching for: {query}")
        print(f"Sources: {sources}")
        
        # Perform the search with use_placeholders=False to ensure real results
        results = perform_multi_source_search(query, sources, max_results=5, use_placeholders=False)
        
        print(f"Found {len(results)} results")
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"Source: {result.source_name} ({result.source_type})")
            print(f"Relevance: {result.relevance_score:.2f}")
            print(f"Content: {result.content[:100]}...")
        
        # Format the results for agent display
        formatted_results = format_search_results_for_agent(results)
        print("\n== Formatted Results for Agent ==")
        print(formatted_results[:500] + "...\n")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing search functionality: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_response():
    """Test the agent response generation with search results"""
    try:
        from tabs.agent_assistant_enhanced import generate_agent_response
        
        # Test AWS Security Query
        print("\n== TEST: Agent Response for AWS Security Query ==")
        task = "What are the best practices for AWS security in 2025?"
        category = "Analysis & Research"
        operation = "Research Topic"
        mode = "Advanced"
        output_format = "Markdown"
        platform = "General"
        tone = "Professional"
        knowledge_sources = ["Indexed Documents", "Web Search (External)"]
        
        print(f"Generating agent response for: {task}")
        print(f"Category: {category}, Operation: {operation}")
        
        # Generate response with search functionality enabled
        response = generate_agent_response(
            task, category, operation, mode, 
            output_format, platform, tone, knowledge_sources
        )
        
        print("\n== Agent Response ==")
        print(response[:1000] + "...\n")
        
        # Test Azure Security Query
        print("\n== TEST: Agent Response for Azure Security Query ==")
        task = "What are the latest Azure security features in 2025?"
        
        print(f"Generating agent response for: {task}")
        print(f"Category: {category}, Operation: {operation}")
        
        # Generate response with search functionality enabled
        response = generate_agent_response(
            task, category, operation, mode, 
            output_format, platform, tone, knowledge_sources
        )
        
        print("\n== Agent Response ==")
        print(response[:1000] + "...\n")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing agent response: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== VaultMIND Agent Search and Response Test ===")
    
    print("\n1. Testing Search Functionality")
    search_success = test_search_functionality()
    
    if search_success:
        print("\n✅ Search functionality test completed successfully")
    else:
        print("\n❌ Search functionality test failed")
    
    print("\n2. Testing Agent Response Generation")
    agent_success = test_agent_response()
    
    if agent_success:
        print("\n✅ Agent response generation test completed successfully")
    else:
        print("\n❌ Agent response generation test failed")
    
    if search_success and agent_success:
        print("\n✅ All tests completed successfully!")
    else:
        print("\n❌ Some tests failed. Please check the logs.")
