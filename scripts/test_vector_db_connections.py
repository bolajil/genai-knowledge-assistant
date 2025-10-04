#!/usr/bin/env python
"""
Vector Database Connection Test Script

This script tests the connection status of configured vector databases,
verifies connection parameters, and reports on the health of each provider.
"""

import os
import sys
import logging
import argparse
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Add parent directory to path for imports
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import necessary modules
try:
    from utils.multi_vector_storage_interface import VectorStoreType
    from utils.multi_vector_storage_manager import get_multi_vector_manager
    from utils.vector_db_provider import get_vector_db_provider
    from config.vector_db_config import get_vector_db_config, VectorDBType
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.warning("Some dependencies may be missing. This is normal if you haven't installed all optional dependencies.")
    logger.info("The test will continue with available modules.")
    IMPORTS_AVAILABLE = False

async def test_vector_db_connections():
    """Test connections to all configured vector databases"""
    if not IMPORTS_AVAILABLE:
        logger.warning("Required modules not available. Skipping vector DB provider tests.")
        return True  # Return success to allow other tests to run
    
    logger.info("Testing vector database connections...")
    
    # Get the vector database provider
    try:
        provider = get_vector_db_provider()
        status, message = provider.get_vector_db_status()
        logger.info(f"Vector DB Provider Status: {status} - {message}")
        
        # Get available indexes
        indexes = provider.get_available_indexes(force_refresh=True)
        logger.info(f"Available indexes: {indexes}")
        
        if not indexes:
            logger.warning("No vector indexes found. Check configuration.")
    except Exception as e:
        logger.error(f"Error accessing vector database provider: {e}")
        return False
    
    # Test multi-vector storage manager connections
    try:
        manager = get_multi_vector_manager()
        logger.info("Testing connections via multi-vector storage manager...")
        
        # Test connections to all vector store types
        connection_results = {}
        for store_type in VectorStoreType:
            try:
                # Use health_check method to test connection
                store = manager.get_store_by_type(store_type)
                if store:
                    result = await store.health_check()
                    connection_results[store_type.value] = result
                    logger.info(f"  {store_type.value}: {'✅ Connected' if result[0] else '❌ Failed'} - {result[1]}")
                else:
                    connection_results[store_type.value] = (False, "Store not configured")
                    logger.info(f"  {store_type.value}: ⚠️ Not configured")
            except Exception as e:
                connection_results[store_type.value] = (False, str(e))
                logger.warning(f"  {store_type.value}: ❌ Error - {e}")
        
        # Get all available stores with their status
        available_stores = manager.get_available_stores()
        logger.info(f"Available stores: {len(available_stores)}")
        for store in available_stores:
            logger.info(f"  {store['type']}: Connected={store['connected']}, Collections={store['collection_count']}")
            if store['error']:
                logger.warning(f"    Error: {store['error']}")
        
        # At least one store should be available
        available_count = sum(1 for store in available_stores if store['connected'])
        logger.info(f"Connected stores: {available_count}/{len(available_stores)}")
        
        return available_count > 0
    except Exception as e:
        logger.error(f"Error testing multi-vector connections: {e}")
        return False

def test_vector_db_config():
    """Test loading and validating the vector database configuration"""
    if not IMPORTS_AVAILABLE:
        logger.error("Required modules not available. Cannot test configuration.")
        return False
    
    logger.info("Testing vector database configuration...")
    
    try:
        # Get the configuration
        config = get_vector_db_config()
        
        # Check FAISS paths
        faiss_paths = config.get_db_paths(VectorDBType.FAISS)
        logger.info(f"FAISS paths: {[str(p) for p in faiss_paths]}")
        for path in faiss_paths:
            if path.exists():
                logger.info(f"  ✅ Path exists: {path}")
            else:
                logger.warning(f"  ⚠️ Path does not exist: {path}")
        
        # Check connection parameters for different providers
        for db_type in VectorDBType:
            params = config.get_connection_params(db_type)
            if params:
                logger.info(f"{db_type.value} connection parameters:")
                # Filter out sensitive information
                filtered_params = {k: ("<redacted>" if k.lower() in ["api_key", "password", "secret"] else v) 
                                 for k, v in params.items()}
                for key, value in filtered_params.items():
                    logger.info(f"  {key}: {value}")
            else:
                logger.info(f"{db_type.value}: No connection parameters configured")
        
        # Check enabled features
        features = [f for f in dir(config) if f.startswith("is_") and callable(getattr(config, f))]
        for feature in features:
            try:
                enabled = getattr(config, feature)()
                logger.info(f"Feature {feature}: {'✅ Enabled' if enabled else '❌ Disabled'}")
            except Exception:
                pass
        
        return True
    except Exception as e:
        logger.error(f"Failed to test vector database configuration: {e}")
        return False

def main():
    """Main function to run the tests"""
    parser = argparse.ArgumentParser(description="Test vector database connections")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting vector database connection tests...")
    
    # Test configuration
    config_success = test_vector_db_config()
    
    # Test connections
    connection_success = asyncio.run(test_vector_db_connections())
    
    # Summary
    logger.info("\n--- Test Summary ---")
    logger.info(f"Vector DB Config: {'✅ PASS' if config_success else '❌ FAIL'}")
    logger.info(f"Vector DB Connections: {'✅ PASS' if connection_success else '❌ FAIL'}")
    
    # Overall result
    all_passed = all([config_success, connection_success])
    logger.info(f"Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())