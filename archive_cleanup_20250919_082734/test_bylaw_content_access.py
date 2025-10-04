#!/usr/bin/env python
"""
ByLaw Content Access Test Script

This script specifically tests the ByLaw content access functionality,
which has been identified as a critical component with known issues.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to the path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

def test_direct_bylaw_retrieval():
    """Test the direct ByLaw retrieval functionality"""
    logger.info("\n=== Testing Direct ByLaw Retrieval ===\n")
    
    try:
        # Import the direct ByLaw retrieval module
        from utils.direct_bylaws_retriever import search_bylaws
        
        # Test queries
        test_queries = [
            "board meeting",
            "action outside of meeting",
            "directors vote electronically",
            "quorum for board meetings",
            "executive sessions"
        ]
        
        success_count = 0
        
        for query in test_queries:
            logger.info(f"Testing query: '{query}'")
            
            # Search for ByLaw content
            results = search_bylaws(query, max_results=3)
            
            if results and len(results) > 0:
                logger.info(f"✅ Found {len(results)} results for '{query}'")
                logger.info(f"Top result score: {results[0].get('score', 'N/A')}")
                logger.info(f"Content preview: {results[0]['content'][:100]}...\n")
                success_count += 1
            else:
                logger.error(f"❌ No results found for '{query}'\n")
        
        # Report overall success
        if success_count == len(test_queries):
            logger.info(f"✅ All {success_count}/{len(test_queries)} queries returned results")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️ {success_count}/{len(test_queries)} queries returned results")
            return True
        else:
            logger.error(f"❌ No queries returned results")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.direct_bylaws_retriever module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing direct ByLaw retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bylaw_query_detection():
    """Test the ByLaw query detection functionality"""
    logger.info("\n=== Testing ByLaw Query Detection ===\n")
    
    try:
        # Import the ByLaw query detection module
        from utils.bylaw_query_patch import is_bylaw_query
        
        # Test cases (query, expected result)
        test_cases = [
            ("Tell me about board meetings", True),
            ("How do directors vote electronically?", True),
            ("What is the quorum for board meetings?", True),
            ("Can board members take action outside of meetings?", True),
            ("Explain the rules for executive sessions", True),
            ("What is cloud computing?", False),
            ("How does AWS S3 work?", False),
            ("Tell me about machine learning", False)
        ]
        
        success_count = 0
        
        for query, expected_result in test_cases:
            # Test with ByLawS2_index
            result = is_bylaw_query(query, "ByLawS2_index")
            
            if result == expected_result:
                logger.info(f"✅ Query '{query}' correctly {'detected' if expected_result else 'not detected'} as ByLaw query")
                success_count += 1
            else:
                logger.error(f"❌ Query '{query}' incorrectly {'not detected' if expected_result else 'detected'} as ByLaw query")
        
        # Report overall success
        if success_count == len(test_cases):
            logger.info(f"✅ All {success_count}/{len(test_cases)} detection tests passed")
            return True
        elif success_count > len(test_cases) / 2:
            logger.warning(f"⚠️ {success_count}/{len(test_cases)} detection tests passed")
            return True
        else:
            logger.error(f"❌ Only {success_count}/{len(test_cases)} detection tests passed")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.bylaw_query_patch module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing ByLaw query detection: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_llm_bylaw_patch():
    """Test the enhanced LLM ByLaw patch functionality"""
    logger.info("\n=== Testing Enhanced LLM ByLaw Patch ===\n")
    
    try:
        # Import the enhanced LLM ByLaw patch module
        from utils.enhanced_llm_bylaw_patch import get_bylaw_enhanced_response
        
        # Create mock search results
        mock_results = [
            {
                'content': 'Board meetings shall be held at least quarterly. A quorum consists of a majority of directors.',
                'source': 'ByLaws.pdf',
                'metadata': {'source': 'ByLaws.pdf'}
            },
            {
                'content': 'Directors may participate in meetings remotely via teleconference or video conference.',
                'source': 'ByLaws.pdf',
                'metadata': {'source': 'ByLaws.pdf'}
            }
        ]
        
        # Test the enhanced response generation
        query = "Tell me about board meetings"
        logger.info(f"Testing query: '{query}'")
        
        response = get_bylaw_enhanced_response(query, mock_results)
        
        if response and isinstance(response, dict) and 'result' in response:
            logger.info(f"✅ Enhanced response generated successfully")
            logger.info(f"Response preview: {response['result'][:100]}...\n")
            return True
        else:
            logger.error(f"❌ Failed to generate enhanced response")
            logger.error(f"Response: {response}\n")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.enhanced_llm_bylaw_patch module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing enhanced LLM ByLaw patch: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bylaw_search_integration():
    """Test the integration of ByLaw search with the query assistant"""
    logger.info("\n=== Testing ByLaw Search Integration ===\n")
    
    try:
        # Import the query assistant module
        from tabs.query_assistant import query_index
        
        # Test query
        query = "provide statement about Board Meetings; Action Outside of Meeting"
        index_name = "ByLawS2_index"
        
        logger.info(f"Testing query: '{query}' with index: '{index_name}'")
        
        # Query the index
        results = query_index(query, index_name, top_k=3)
        
        if results and len(results) > 0:
            logger.info(f"✅ Query returned {len(results)} results")
            
            # Check result format
            if isinstance(results[0], dict):
                logger.info("✅ Result is in dictionary format as expected")
                
                # Check for enhanced response
                if 'enhanced_response' in results[0]:
                    logger.info("✅ Enhanced response is present")
                    logger.info(f"Response preview: {results[0]['enhanced_response'][:100]}...\n")
                else:
                    logger.warning("⚠️ Enhanced response is not present")
                    
                # Check for content
                if 'content' in results[0]:
                    logger.info("✅ Content is present")
                    logger.info(f"Content preview: {results[0]['content'][:100]}...\n")
                else:
                    logger.warning("⚠️ Content is not present")
                
                return True
            else:
                logger.warning(f"⚠️ Result is not in dictionary format: {type(results[0])}")
                logger.info(f"Result preview: {str(results[0])[:100]}...\n")
                return True
        else:
            logger.error(f"❌ Query returned no results")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import tabs.query_assistant module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing ByLaw search integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    logger.info("\n" + "*" * 80)
    logger.info("* BYLAW CONTENT ACCESS TEST SCRIPT *".center(78))
    logger.info("*" * 80 + "\n")
    
    # Run all tests
    tests = [
        ("Direct ByLaw Retrieval", test_direct_bylaw_retrieval),
        ("ByLaw Query Detection", test_bylaw_query_detection),
        ("Enhanced LLM ByLaw Patch", test_enhanced_llm_bylaw_patch),
        ("ByLaw Search Integration", test_bylaw_search_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning test: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            results[test_name] = False
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY".center(80))
    logger.info("=" * 80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("\n" + "-" * 80)
    logger.info(f"OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✅ ALL TESTS PASSED")
    elif passed > 0:
        logger.info("⚠️ SOME TESTS FAILED")
    else:
        logger.info("❌ ALL TESTS FAILED")
    
    logger.info("-" * 80)
    
    # Return success if all tests passed
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)