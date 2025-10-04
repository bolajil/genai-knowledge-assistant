"""
Implementation script to initialize and set up the centralized index management
This is the first step in standardizing index storage across the application
"""
import os
import logging
import time
from pathlib import Path
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_search_system():
    """
    Initialize the centralized search system
    - Migrates existing indexes to standard location
    - Ensures all required directories exist
    - Returns stats about the system setup
    """
    from utils.index_manager import IndexManager
    
    start_time = time.time()
    logger.info("Initializing centralized search system...")
    
    # Ensure standard index path exists
    standard_path = IndexManager.get_standard_index_path()
    os.makedirs(standard_path, exist_ok=True)
    logger.info(f"Standard index path: {standard_path}")
    
    # Get initial count of indexes
    initial_indexes = IndexManager.list_available_indexes(force_refresh=True)
    logger.info(f"Found {len(initial_indexes)} indexes before migration")
    
    # Migrate legacy indexes
    migration_results = IndexManager.migrate_legacy_indexes()
    logger.info(f"Migrated {len(migration_results)} indexes to standard location")
    
    # Get final count of indexes
    final_indexes = IndexManager.list_available_indexes(force_refresh=True)
    logger.info(f"Found {len(final_indexes)} indexes after migration")
    
    # Log all available indexes
    logger.info("Available indexes:")
    for idx in final_indexes:
        logger.info(f"  - {idx}")
    
    # Calculate stats
    elapsed_time = time.time() - start_time
    stats = {
        "initial_index_count": len(initial_indexes),
        "migrated_index_count": len(migration_results),
        "final_index_count": len(final_indexes),
        "standard_path": standard_path,
        "elapsed_time": elapsed_time
    }
    
    logger.info(f"Search system initialization completed in {elapsed_time:.2f} seconds")
    return stats

if __name__ == "__main__":
    """Run the initialization directly when executed as a script"""
    stats = init_search_system()
    print("\nSearch System Initialization Results:")
    print(f"Standard path: {stats['standard_path']}")
    print(f"Initial index count: {stats['initial_index_count']}")
    print(f"Migrated indexes: {stats['migrated_index_count']}")
    print(f"Final index count: {stats['final_index_count']}")
    print(f"Completed in: {stats['elapsed_time']:.2f} seconds")
