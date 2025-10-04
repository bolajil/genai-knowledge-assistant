"""
Test the ByLaw content fix to ensure it doesn't encounter the AttributeError issue.
"""

import importlib
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_bylaw_enhanced_response():
    """Test the bylaw enhanced response function directly"""
    try:
        # Make sure utils is in sys.path
        import os
        utils_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils')
        if utils_dir not in sys.path:
            sys.path.insert(0, utils_dir)
        
        # Import the function
        from utils.enhanced_llm_bylaw_patch import get_bylaw_enhanced_response
        
        # Create mock comprehensive_results
        mock_results = [
            {
                'content': 'This is a test document about board meetings',
                'source': 'test.pdf',
                'metadata': {'source': 'test.pdf'}
            }
        ]
        
        # Call the function
        result = get_bylaw_enhanced_response("Tell me about board meetings", mock_results)
        
        # Check the result
        if isinstance(result, dict) and 'result' in result:
            logger.info("✅ get_bylaw_enhanced_response returned a dictionary with 'result' key")
            logger.info(f"Result preview: {result['result'][:100]}...")
            return True
        else:
            logger.error(f"❌ get_bylaw_enhanced_response returned unexpected format: {type(result)}")
            return False
    except Exception as e:
        logger.error(f"❌ Error testing get_bylaw_enhanced_response: {e}")
        return False

def test_query_assistant_with_bylaw():
    """Test the query_assistant function with a ByLaw query"""
    try:
        # Import the function
        from tabs.query_assistant import query_index
        
        # Call the function
        result = query_index("Tell me about board meetings", "ByLawS2_index")
        
        # Check the result
        if result:
            logger.info(f"✅ query_index returned {len(result)} results")
            if isinstance(result[0], dict):
                logger.info("Result is a dictionary as expected")
                if 'enhanced_response' in result[0]:
                    logger.info("Enhanced response is present")
                    return True
            elif isinstance(result[0], str):
                logger.info("Result is a string")
                logger.info(f"Result preview: {result[0][:100]}...")
                return True
            else:
                logger.error(f"❌ Unexpected result type: {type(result[0])}")
                return False
        else:
            logger.error("❌ query_index returned no results")
            return False
    except Exception as e:
        logger.error(f"❌ Error testing query_index: {e}")
        return False

def main():
    """Main function"""
    logger.info("Testing ByLaw content fix...")
    
    # Reload modules to ensure latest changes are used
    if 'utils.enhanced_llm_bylaw_patch' in sys.modules:
        importlib.reload(sys.modules['utils.enhanced_llm_bylaw_patch'])
    if 'tabs.query_assistant' in sys.modules:
        importlib.reload(sys.modules['tabs.query_assistant'])
    
    # Test get_bylaw_enhanced_response
    bylaw_response_result = test_bylaw_enhanced_response()
    
    # Test query_assistant with ByLaw query
    query_assistant_result = test_query_assistant_with_bylaw()
    
    # Overall result
    if bylaw_response_result and query_assistant_result:
        logger.info("✅ All tests passed! The ByLaw content fix is working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
