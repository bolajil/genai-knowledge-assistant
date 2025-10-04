#!/usr/bin/env python
"""
Vector Database Functionality Test Script

This script tests the vector database functionality, including:
- Connection to vector database providers
- Fallback mechanisms when primary provider is unavailable
- Search capabilities and result quality
- Index management
"""

import os
import sys
import logging
import time
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

def test_vector_db_initialization():
    """Test the initialization of vector database providers"""
    logger.info("\n=== Testing Vector Database Initialization ===\n")
    
    try:
        # Import the vector database initialization module
        from utils.vector_db_enhanced_init import get_vector_db_provider
        
        # Test initialization with default provider
        logger.info("Testing initialization with default provider")
        provider = get_vector_db_provider()
        
        if provider is not None:
            logger.info(f"✅ Successfully initialized vector database provider: {provider.__class__.__name__}")
            
            # Check available indexes
            indexes = provider.available_indexes()
            if indexes and len(indexes) > 0:
                logger.info(f"✅ Provider has {len(indexes)} available indexes: {', '.join(indexes)}")
            else:
                logger.warning("⚠️ Provider has no available indexes")
            
            return True
        else:
            logger.error("❌ Failed to initialize vector database provider")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.vector_db_enhanced_init module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing vector database initialization: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mock_vector_db_fallback():
    """Test the fallback to mock vector database when primary provider is unavailable"""
    logger.info("\n=== Testing Mock Vector DB Fallback ===\n")
    
    try:
        # Import the vector database initialization and mock provider modules
        from utils.vector_db_enhanced_init import get_vector_db_provider
        from utils.vector_db_fix import MockVectorDBProvider
        
        # Temporarily modify environment to force fallback
        original_env = {}
        for key in ['PINECONE_API_KEY', 'WEAVIATE_API_KEY', 'QDRANT_API_KEY']:
            if key in os.environ:
                original_env[key] = os.environ[key]
                del os.environ[key]
        
        try:
            # Test initialization with fallback
            logger.info("Testing initialization with fallback to mock provider")
            provider = get_vector_db_provider()
            
            if provider is not None:
                if isinstance(provider, MockVectorDBProvider):
                    logger.info("✅ Successfully fell back to MockVectorDBProvider")
                    
                    # Check available indexes
                    indexes = provider.available_indexes()
                    if indexes and len(indexes) > 0:
                        logger.info(f"✅ Mock provider has {len(indexes)} available indexes: {', '.join(indexes)}")
                    else:
                        logger.warning("⚠️ Mock provider has no available indexes")
                    
                    # Test search functionality
                    results = provider.search("test query", "mock_index", top_k=3)
                    if results and len(results) > 0:
                        logger.info(f"✅ Mock provider returned {len(results)} search results")
                    else:
                        logger.warning("⚠️ Mock provider returned no search results")
                    
                    return True
                else:
                    logger.warning(f"⚠️ Did not fall back to MockVectorDBProvider, got {provider.__class__.__name__} instead")
                    return False
            else:
                logger.error("❌ Failed to initialize vector database provider with fallback")
                return False
        
        finally:
            # Restore original environment
            for key, value in original_env.items():
                os.environ[key] = value
    
    except ImportError:
        logger.error("❌ Failed to import required modules")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing mock vector DB fallback: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_db_search():
    """Test the vector database search functionality"""
    logger.info("\n=== Testing Vector Database Search ===\n")
    
    try:
        # Import the vector database initialization module
        from utils.vector_db_enhanced_init import get_vector_db_provider
        
        # Get the vector database provider
        provider = get_vector_db_provider()
        
        if provider is None:
            logger.error("❌ Failed to initialize vector database provider")
            return False
        
        # Get available indexes
        indexes = provider.available_indexes()
        
        if not indexes or len(indexes) == 0:
            logger.warning("⚠️ No indexes available for testing")
            return False
        
        # Select an index for testing (prefer non-ByLaw index if available)
        test_index = next((idx for idx in indexes if 'bylaw' not in idx.lower()), indexes[0])
        
        # Test queries
        test_queries = [
            "cloud computing",
            "machine learning",
            "data security",
            "artificial intelligence",
            "digital transformation"
        ]
        
        success_count = 0
        
        for query in test_queries:
            logger.info(f"Testing query: '{query}' on index: '{test_index}'")
            
            # Search the index
            start_time = time.time()
            results = provider.search(query, test_index, top_k=3)
            elapsed_time = time.time() - start_time
            
            if results and len(results) > 0:
                logger.info(f"✅ Found {len(results)} results for '{query}' in {elapsed_time:.2f} seconds")
                
                # Check result format
                if hasattr(results[0], 'content') or (isinstance(results[0], dict) and 'content' in results[0]):
                    content = results[0].content if hasattr(results[0], 'content') else results[0]['content']
                    logger.info(f"Content preview: {content[:100]}...\n")
                else:
                    logger.warning(f"⚠️ Unexpected result format: {type(results[0])}")
                    logger.info(f"Result preview: {str(results[0])[:100]}...\n")
                
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
        logger.error("❌ Failed to import utils.vector_db_enhanced_init module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing vector database search: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multi_vector_integration():
    """Test the multi-vector integration functionality"""
    logger.info("\n=== Testing Multi-Vector Integration ===\n")
    
    try:
        # Import the multi-vector integration module
        from utils.multi_vector_integration import MultiVectorIntegration
        
        # Initialize the multi-vector integration
        logger.info("Initializing MultiVectorIntegration")
        integration = MultiVectorIntegration()
        
        if integration is not None:
            logger.info("✅ Successfully initialized MultiVectorIntegration")
            
            # Test getting available providers
            providers = integration.get_available_providers()
            if providers and len(providers) > 0:
                logger.info(f"✅ Found {len(providers)} available providers: {', '.join(providers)}")
            else:
                logger.warning("⚠️ No available providers found")
            
            # Test getting available indexes
            indexes = integration.get_available_indexes()
            if indexes and len(indexes) > 0:
                logger.info(f"✅ Found {len(indexes)} available indexes: {', '.join(indexes)}")
                
                # Select an index for testing
                test_index = indexes[0]
                
                # Test search functionality
                query = "cloud computing"
                logger.info(f"Testing search with query: '{query}' on index: '{test_index}'")
                
                results = integration.search(query, test_index, top_k=3)
                if results and len(results) > 0:
                    logger.info(f"✅ Search returned {len(results)} results")
                    return True
                else:
                    logger.warning("⚠️ Search returned no results")
                    return False
            else:
                logger.warning("⚠️ No available indexes found")
                return False
        else:
            logger.error("❌ Failed to initialize MultiVectorIntegration")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.multi_vector_integration module")
        return False
    except AttributeError:
        logger.error("❌ MultiVectorIntegration class does not have the expected methods")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing multi-vector integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    logger.info("\n" + "*" * 80)
    logger.info("* VECTOR DATABASE FUNCTIONALITY TEST SCRIPT *".center(78))
    logger.info("*" * 80 + "\n")
    
    # Run all tests
    tests = [
        ("Vector DB Initialization", test_vector_db_initialization),
        ("Mock Vector DB Fallback", test_mock_vector_db_fallback),
        ("Vector DB Search", test_vector_db_search),
        ("Multi-Vector Integration", test_multi_vector_integration)
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