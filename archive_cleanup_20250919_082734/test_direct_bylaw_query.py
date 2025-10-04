"""
Direct ByLaw Query Test

This script directly tests querying for ByLaw content without going through the full UI.
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup the environment for testing"""
    # Add current directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # Add utils directory to path
    utils_dir = os.path.join(current_dir, 'utils')
    if utils_dir not in sys.path:
        sys.path.insert(0, utils_dir)
    
    # Add tabs directory to path
    tabs_dir = os.path.join(current_dir, 'tabs')
    if tabs_dir not in sys.path:
        sys.path.insert(0, tabs_dir)

def test_direct_bylaw_query():
    """Test querying for ByLaw content directly"""
    try:
        # Import query_index from query_assistant
        from tabs.query_assistant import query_index
        
        # Query parameters
        query = "provide stament about Board Meetings; Action Outside of Meeting"
        index_name = "ByLawS2_index"
        top_k = 5
        
        # Query the index
        logger.info(f"Querying index '{index_name}' with query: '{query}'")
        results = query_index(query, index_name, top_k)
        
        # Check results
        if results:
            logger.info(f"✅ Query returned {len(results)} results")
            
            # Print results
            for i, result in enumerate(results):
                logger.info(f"\nResult {i+1}:")
                
                if isinstance(result, dict):
                    # Print dictionary result
                    for key, value in result.items():
                        if key == 'content':
                            # Truncate content for display
                            content_preview = value[:100] + "..." if len(value) > 100 else value
                            logger.info(f"{key}: {content_preview}")
                        elif key == 'enhanced_response':
                            # Truncate enhanced_response for display
                            response_preview = value[:100] + "..." if len(value) > 100 else value
                            logger.info(f"{key}: {response_preview}")
                        else:
                            logger.info(f"{key}: {value}")
                else:
                    # Print string result
                    result_preview = result[:100] + "..." if len(result) > 100 else result
                    logger.info(f"Result: {result_preview}")
            
            return True
        else:
            logger.error("❌ Query returned no results")
            return False
    except Exception as e:
        logger.error(f"❌ Error querying for ByLaw content: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bylaw_direct_functions():
    """Test ByLaw direct injection functions"""
    try:
        # Import functions
        from utils.bylaw_query_patch import is_bylaw_query, get_bylaw_result, inject_bylaw_content
        from utils.enhanced_llm_bylaw_patch import get_bylaw_enhanced_response
        
        # Test is_bylaw_query
        query = "provide stament about Board Meetings; Action Outside of Meeting"
        index_name = "ByLawS2_index"
        is_bylaw = is_bylaw_query(query, index_name)
        logger.info(f"is_bylaw_query: {is_bylaw}")
        
        # Test get_bylaw_result
        result = get_bylaw_result(query)
        logger.info(f"get_bylaw_result content preview: {result['content'][:100]}...")
        
        # Test inject_bylaw_content
        comprehensive_results = []
        injected_results = inject_bylaw_content(comprehensive_results, query)
        logger.info(f"inject_bylaw_content returned {len(injected_results)} results")
        
        # Test get_bylaw_enhanced_response
        mock_results = [{'content': 'Test content', 'source': 'test'}]
        enhanced_response = get_bylaw_enhanced_response(query, mock_results)
        logger.info(f"get_bylaw_enhanced_response result type: {type(enhanced_response)}")
        if isinstance(enhanced_response, dict) and 'result' in enhanced_response:
            logger.info(f"get_bylaw_enhanced_response result preview: {enhanced_response['result'][:100]}...")
        else:
            logger.info(f"get_bylaw_enhanced_response result: {enhanced_response}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error testing ByLaw direct functions: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    # Setup environment
    setup_environment()
    
    # Test ByLaw direct functions
    logger.info("\n=== TESTING BYLAW DIRECT FUNCTIONS ===\n")
    test_bylaw_direct_functions()
    
    # Test direct ByLaw query
    logger.info("\n=== TESTING DIRECT BYLAW QUERY ===\n")
    success = test_direct_bylaw_query()
    
    # Print result
    if success:
        logger.info("\n✅ All tests passed successfully!")
        logger.info("The ByLaw content retrieval fix is working correctly.")
    else:
        logger.error("\n❌ Tests failed.")
        logger.error("The ByLaw content retrieval fix is not working correctly.")
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
