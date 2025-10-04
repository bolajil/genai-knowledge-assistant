"""
Vector Database Centralization Quick Start

This script helps initialize and validate the centralized vector database solution.
Run this script to:
1. Configure the vector database paths
2. Validate that the database is accessible
3. Run a test search query

Usage:
    python vector_db_quickstart.py --index-path [path] --query [search query]
"""

import os
import sys
import argparse
import logging
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

def setup_environment(index_path=None, embedding_model=None, engine=None):
    """Set up environment variables for the vector database configuration"""
    if index_path:
        os.environ['VAULTMIND_INDEX_PATH'] = index_path
        logger.info(f"Set VAULTMIND_INDEX_PATH to {index_path}")
    
    if embedding_model:
        os.environ['VAULTMIND_EMBEDDING_MODEL'] = embedding_model
        logger.info(f"Set VAULTMIND_EMBEDDING_MODEL to {embedding_model}")
    
    if engine:
        os.environ['VAULTMIND_VECTOR_ENGINE'] = engine
        logger.info(f"Set VAULTMIND_VECTOR_ENGINE to {engine}")
    
    return True

def validate_configuration():
    """Validate the vector database configuration"""
    try:
        from config.vector_db_config import get_vector_db_config
        
        config = get_vector_db_config()
        logger.info(f"Vector DB Configuration loaded successfully")
        logger.info(f"Default index path: {config.default_index_path}")
        logger.info(f"Default embedding model: {config.embedding_model}")
        logger.info(f"Available engines: {config.available_engines}")
        
        # Check if the index path exists
        if os.path.exists(config.default_index_path):
            logger.info(f"Index path exists: {config.default_index_path}")
        else:
            logger.warning(f"Index path does not exist: {config.default_index_path}")
            logger.warning("You may need to create the index first")
        
        return True
    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}")
        return False

def test_vector_db_provider():
    """Test the vector database provider"""
    try:
        from utils.vector_db_provider import get_vector_db_provider
        
        provider = get_vector_db_provider()
        logger.info(f"Vector DB Provider initialized successfully")
        
        # Check provider status
        status, message = provider.get_vector_db_status()
        logger.info(f"Provider status: {status}")
        logger.info(f"Provider message: {message}")
        
        return True, provider
    except Exception as e:
        logger.error(f"Failed to initialize vector database provider: {e}")
        return False, None

def run_test_search(provider, query):
    """Run a test search using the provider"""
    if not provider:
        logger.error("Cannot run test search: Provider not available")
        return False
    
    try:
        results = provider.search(query, max_results=3)
        
        logger.info(f"Search for '{query}' returned {len(results)} results")
        
        if results:
            logger.info("\nSearch Results:")
            for i, result in enumerate(results, 1):
                logger.info(f"\n--- Result {i} ---")
                logger.info(f"Relevance: {result.relevance:.2f}")
                logger.info(f"Source: {result.source}")
                logger.info(f"Content: {result.content[:200]}...")
        else:
            logger.warning("No results found. This could be normal if no matching documents exist")
        
        return True
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Vector Database Centralization Quick Start")
    parser.add_argument("--index-path", help="Path to the vector database index")
    parser.add_argument("--embedding-model", default="all-minLM-L6-v2", 
                       help="Name of the embedding model to use")
    parser.add_argument("--engine", default="faiss",
                       help="Vector database engine to use (faiss or weaviate)")
    parser.add_argument("--query", default="cloud security",
                       help="Test query to run")
    args = parser.parse_args()
    
    logger.info("Starting Vector Database Centralization Quick Start")
    
    # Set up environment variables
    setup_environment(
        index_path=args.index_path,
        embedding_model=args.embedding_model,
        engine=args.engine
    )
    
    # Validate configuration
    if not validate_configuration():
        logger.error("Configuration validation failed")
        return 1
    
    # Test vector database provider
    provider_success, provider = test_vector_db_provider()
    if not provider_success:
        logger.error("Vector database provider initialization failed")
        return 1
    
    # Run test search
    if not run_test_search(provider, args.query):
        logger.error("Test search failed")
        return 1
    
    logger.info("\n✅ Vector Database Centralization Quick Start completed successfully")
    logger.info("\nNext steps:")
    logger.info("1. Review the centralization guide: docs/vector_db_centralization_guide.md")
    logger.info("2. Update tabs to use the centralized solution: python scripts/migrate_tabs.py")
    logger.info("3. Test tab implementations")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
