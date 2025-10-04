# Implementation of _load_faiss_index with proper pickle loading for document content

import os
import logging
import faiss
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import pickle
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

@lru_cache(maxsize=16)
def load_faiss_index(index_path: Path) -> Tuple[Any, Dict[str, Any]]:
    """
    Load a FAISS index and its metadata from disk with proper error handling
    
    Args:
        index_path: Path to the index directory
        
    Returns:
        Tuple of (faiss_index, metadata)
    """
    try:
        # Expected file paths
        faiss_file = index_path / "index.faiss"
        
        # Check for different metadata file names
        metadata_candidates = [
            index_path / "index.pkl",
            index_path / "documents.pkl",
            index_path / "metadata.pkl"
        ]
        
        metadata_file = None
        for candidate in metadata_candidates:
            if candidate.exists():
                metadata_file = candidate
                break
        
        if not faiss_file.exists():
            raise FileNotFoundError(f"FAISS index file not found at {faiss_file}")
        
        if not metadata_file:
            raise FileNotFoundError(f"No metadata file found in {index_path}")
        
        # Load FAISS index
        logger.info(f"Loading FAISS index from {faiss_file}")
        faiss_index = faiss.read_index(str(faiss_file))
        
        # Load metadata
        logger.info(f"Loading metadata from {metadata_file}")
        with open(metadata_file, 'rb') as f:
            metadata = pickle.load(f)
        
        # Ensure metadata is in expected format
        if isinstance(metadata, dict):
            # Validate the metadata structure
            if "documents" not in metadata and "texts" not in metadata:
                logger.warning(f"No document content found in metadata at {metadata_file}")
                
                # Try to get documents from other fields
                if "metadata" in metadata and isinstance(metadata["metadata"], list):
                    # Check if the metadata has document content
                    if any("content" in m for m in metadata["metadata"] if isinstance(m, dict)):
                        # Extract content from metadata
                        documents = [m.get("content", "") for m in metadata["metadata"] if isinstance(m, dict)]
                        metadata["documents"] = documents
                        logger.info(f"Extracted {len(documents)} document contents from metadata field")
            
            # Ensure there's at least an empty documents list
            if "documents" not in metadata:
                metadata["documents"] = []
            
            # Verify if documents match the index size
            index_size = faiss_index.ntotal
            doc_size = len(metadata.get("documents", []))
            
            if doc_size == 0 and index_size > 0:
                logger.warning(f"Index has {index_size} vectors but no document content")
            elif doc_size > 0 and doc_size != index_size:
                logger.warning(f"Index has {index_size} vectors but metadata has {doc_size} documents")
        else:
            # Convert non-dict metadata to dict format
            logger.warning(f"Converting non-dict metadata to dict format")
            if isinstance(metadata, list):
                converted_metadata = {"documents": metadata}
                metadata = converted_metadata
            else:
                metadata = {"documents": [str(metadata)]}
        
        logger.info(f"Successfully loaded FAISS index with {faiss_index.ntotal} vectors")
        return faiss_index, metadata
        
    except Exception as e:
        logger.error(f"Error loading FAISS index: {e}")
        # Return a minimal valid result for graceful degradation
        empty_index = faiss.IndexFlatL2(1)  # 1-dimensional placeholder
        empty_metadata = {"documents": [], "metadatas": []}
        return empty_index, empty_metadata
