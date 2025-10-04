"""
Unified Index Manager

This module provides a centralized system for discovering, listing, and loading vector indexes
from various sources, including local FAISS indexes and Weaviate.

Key Features:
- Discovers FAISS indexes from multiple common directories.
- Integrates with Weaviate to list and access cloud-based indexes.
- Provides a single, unified list of all available indexes.
- Gracefully handles cases where Weaviate is unavailable, falling back to FAISS.
- Centralizes index path and configuration management.
"""

import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define all possible local directories where FAISS indexes might be stored
FAISS_INDEX_DIRS = [
    PROJECT_ROOT / "data" / "faiss_index",
    PROJECT_ROOT / "data" / "indexes",
    PROJECT_ROOT / "vector_store",
]

# --- Weaviate Integration --- 
# Weaviate integration is not yet implemented, so we'll use FAISS-only for now
WEAVIATE_AVAILABLE = False
logger.info("Using FAISS-only mode (Weaviate integration not implemented yet)")

def get_weaviate_client():
    return None

# --- Core Functions ---

def discover_faiss_indexes() -> list[str]:
    """Scans all configured FAISS directories and returns a list of valid index names."""
    found_indexes = set()
    for dir_path in FAISS_INDEX_DIRS:
        if not dir_path.exists() or not dir_path.is_dir():
            continue
        
        # Check for direct index files in the directory (like data/faiss_index/index.faiss)
        if (dir_path / "index.faiss").exists() and (dir_path / "index.pkl").exists():
            found_indexes.add("default_faiss")
        
        # Check subdirectories for index files or metadata
        for item in dir_path.iterdir():
            if item.is_dir():
                # Check if it's a valid FAISS index (contains index.faiss and index.pkl)
                if (item / "index.faiss").exists() and (item / "index.pkl").exists():
                    found_indexes.add(item.name)
                # Also check for directories with index.meta (alternative index format)
                elif (item / "index.meta").exists():
                    found_indexes.add(item.name)
    
    # If no indexes found, provide fallback based on known directory structure
    if not found_indexes:
        # Check for known index directories even without proper FAISS files
        for dir_path in FAISS_INDEX_DIRS:
            if dir_path.exists():
                for item in dir_path.iterdir():
                    if item.is_dir() and item.name.endswith('_index'):
                        found_indexes.add(item.name)
    
    logger.info(f"Discovered {len(found_indexes)} local FAISS indexes: {list(found_indexes)}")
    return sorted(list(found_indexes))

def list_weaviate_indexes() -> list[str]:
    """Returns a list of all available Weaviate collection (index) names."""
    if not WEAVIATE_AVAILABLE:
        return []
    
    try:
        client = get_weaviate_client()
        if not client:
            logger.warning("Could not get Weaviate client.")
            return []
            
        collections = client.collections.list_all()
        index_names = [collection.name for collection in collections]
        logger.info(f"Discovered {len(index_names)} Weaviate indexes: {index_names}")
        return index_names
    except Exception as e:
        logger.error(f"Failed to list Weaviate indexes: {e}")
        return []

def get_unified_indexes(force_refresh: bool = False) -> list[str]:
    """Provides a single, unified list of all available indexes from all sources."""
    # Note: force_refresh is kept for API compatibility but not used here yet.
    
    faiss_indexes = discover_faiss_indexes()
    weaviate_indexes = list_weaviate_indexes()
    
    # Combine and deduplicate
    unified_list = sorted(list(set(faiss_indexes + weaviate_indexes)))
    logger.info(f"Unified index list created with {len(unified_list)} indexes.")
    return unified_list

def get_index_path(index_name: str) -> Path | None:
    """Finds the absolute path for a given FAISS index name."""
    # Handle special case for default_faiss
    if index_name == "default_faiss":
        for dir_path in FAISS_INDEX_DIRS:
            if (dir_path / "index.faiss").exists() and (dir_path / "index.pkl").exists():
                logger.info(f"Found path for default index: {dir_path}")
                return dir_path
    
    # Look for named index directories
    for dir_path in FAISS_INDEX_DIRS:
        potential_path = dir_path / index_name
        if potential_path.exists() and potential_path.is_dir():
            logger.info(f"Found path for index '{index_name}': {potential_path}")
            return potential_path
    
    logger.warning(f"Could not find path for FAISS index '{index_name}'.")
    return None

def get_vector_db_status() -> tuple[str, str]:
    """Checks the status of the vector databases and returns a status and message."""
    if WEAVIATE_AVAILABLE:
        try:
            client = get_weaviate_client()
            if client and client.is_live():
                return ("Ready", "Weaviate Connected")
        except Exception as e:
            logger.error(f"Weaviate status check failed: {e}")
            # Fall through to check FAISS
    
    # Check for local FAISS indexes
    faiss_indexes = discover_faiss_indexes()
    if faiss_indexes:
        return ("Ready", f"{len(faiss_indexes)} FAISS Index(es) Available")
    
    # If no FAISS indexes found, try the mock provider as a fallback
    try:
        from utils.mock_vector_db_provider import get_mock_vector_db_provider
        mock_provider = get_mock_vector_db_provider()
        return mock_provider.get_vector_db_status()
    except Exception as e:
        logger.error(f"Mock provider failed: {e}")
    
    return ("Error", "No Vector DB Available")
