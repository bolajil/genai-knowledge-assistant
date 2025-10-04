"""
Vector Database Integration Test Utility

This script tests the integration of the centralized vector database solution
by running various operations and validating the responses.
"""

import os
import sys
import logging
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

def test_vector_db_config():
    """Test loading the vector database configuration"""
    logger.info("Testing vector database configuration...")
    
    try:
        from config.vector_db_config import get_vector_db_config
        
        # Get the configuration
        config = get_vector_db_config()
        logger.info(f"Vector DB Config loaded successfully")
        logger.info(f"Default index path: {config.default_index_path}")
        logger.info(f"Available engines: {config.available_engines}")
        
        return True, config
    except Exception as e:
        logger.error(f"Failed to load vector database configuration: {e}")
        return False, None

def test_vector_db_provider():
    """Test the vector database provider initialization"""
    logger.info("Testing vector database provider...")
    
    try:
        from utils.vector_db_provider import get_vector_db_provider
        
        # Get the provider
        provider = get_vector_db_provider()
        logger.info(f"Vector DB Provider initialized successfully")
        
        # Check provider status
        status, message = provider.get_vector_db_status()
        logger.info(f"Provider status: {status}")
        logger.info(f"Provider message: {message}")
        
        # Get available indexes
        indexes = provider.get_available_indexes()
        logger.info(f"Available indexes: {indexes}")
        
        return True, provider
    except Exception as e:
        logger.error(f"Failed to initialize vector database provider: {e}")
        return False, None

def test_search_operations(provider, query="cloud security best practices"):
    """Test search operations using the provider"""
    logger.info(f"Testing search operations with query: '{query}'...")
    
    if not provider:
        logger.error("Cannot test search operations: Provider not available")
        return False, None
    
    try:
        # Perform a basic search
        results = provider.search(query, max_results=5)
        logger.info(f"Search returned {len(results)} results")
        
        # Print the first result
        if results:
            logger.info(f"First result: {results[0].content[:100]}...")
        
        return True, results
    except Exception as e:
        logger.error(f"Search operation failed: {e}")
        return False, None

def test_enhanced_research_integration(query="AWS security benefits"):
    """Test the enhanced research integration"""
    logger.info(f"Testing enhanced research integration with query: '{query}'...")
    
    try:
        from utils.enhanced_research_integration import generate_enhanced_research_content
        
        # Generate research content
        content = generate_enhanced_research_content(
            task=query,
            operation="Research Topic",
            knowledge_sources=["Indexed Documents", "Web Search (External)"]
        )
        
        logger.info(f"Research content generated successfully")
        logger.info(f"Content preview: {content[:200]}...")
        
        return True, content
    except Exception as e:
        logger.error(f"Enhanced research integration failed: {e}")
        return False, None

def test_tab_implementation():
    """Test the updated tab implementation"""
    logger.info("Testing enhanced research tab implementation...")
    
    try:
        # Import the updated tab module
        sys.path.append(str(parent_dir / "tabs"))
        from enhanced_research_updated import ENHANCED_RESEARCH_AVAILABLE, db_provider
        
        logger.info(f"Enhanced research tab loaded successfully")
        logger.info(f"Enhanced research available: {ENHANCED_RESEARCH_AVAILABLE}")
        
        if db_provider:
            status, message = db_provider.get_vector_db_status()
            logger.info(f"Tab vector DB status: {status}")
            logger.info(f"Tab vector DB message: {message}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to test tab implementation: {e}")
        return False

def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test vector database integration")
    parser.add_argument("--query", default="cloud security", help="Query to use for testing search")
    args = parser.parse_args()
    
    logger.info("Starting vector database integration tests...")
    
    # Test configuration
    config_success, config = test_vector_db_config()
    
    # Test provider
    provider_success, provider = test_vector_db_provider()
    
    # Test search if provider is available
    if provider_success:
        search_success, results = test_search_operations(provider, args.query)
    else:
        search_success = False
    
    # Test enhanced research integration
    research_success, _ = test_enhanced_research_integration(args.query)
    
    # Test tab implementation
    tab_success = test_tab_implementation()
    
    # Summary
    logger.info("\n--- Test Summary ---")
    logger.info(f"Vector DB Config: {'✅ PASS' if config_success else '❌ FAIL'}")
    logger.info(f"Vector DB Provider: {'✅ PASS' if provider_success else '❌ FAIL'}")
    logger.info(f"Search Operations: {'✅ PASS' if search_success else '❌ FAIL'}")
    logger.info(f"Enhanced Research: {'✅ PASS' if research_success else '❌ FAIL'}")
    logger.info(f"Tab Implementation: {'✅ PASS' if tab_success else '❌ FAIL'}")
    
    # Overall result
    all_passed = all([config_success, provider_success, search_success, research_success, tab_success])
    logger.info(f"Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
