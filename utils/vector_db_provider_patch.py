"""
Enhanced Vector DB Provider Patch

This module patches the existing VectorDBProvider class with improved 
FAISS index loading capabilities to ensure document content is properly retrieved.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Tuple

# Import the enhanced FAISS loader
from utils.faiss_loader import load_faiss_index

# Configure logging
logger = logging.getLogger(__name__)

# Import the original vector DB provider
try:
    from utils.vector_db_provider import VectorDBProvider, get_vector_db_provider
    
    # Save the original function if it exists
    if hasattr(VectorDBProvider, '_load_faiss_index'):
        original_load_faiss_index = VectorDBProvider._load_faiss_index
    else:
        # Create a new method using our enhanced loader
        @lru_cache(maxsize=16)
        def enhanced_load_faiss_index(self, index_path: Path) -> Tuple[Any, Dict[str, Any]]:
            """
            Enhanced method to load a FAISS index and its metadata from disk with proper error handling
            
            Args:
                index_path: Path to the index directory
                
            Returns:
                Tuple of (faiss_index, metadata)
            """
            try:
                # Use our enhanced loader
                return load_faiss_index(index_path)
            except Exception as e:
                logger.error(f"Error in enhanced_load_faiss_index: {e}")
                # If our loader fails, return minimal valid data
                import faiss
                empty_index = faiss.IndexFlatL2(1)
                empty_metadata = {"documents": [], "metadatas": []}
                return empty_index, empty_metadata
        
        # Patch the VectorDBProvider class with our enhanced method
        VectorDBProvider._load_faiss_index = enhanced_load_faiss_index
        logger.info("VectorDBProvider patched with enhanced FAISS loader")
        
    # Initialize the patched provider
    get_vector_db_provider()
    logger.info("Vector DB provider initialized with enhanced FAISS loader")
    
except ImportError as e:
    logger.error(f"Could not import VectorDBProvider: {e}")
except Exception as e:
    logger.error(f"Error patching VectorDBProvider: {e}")
