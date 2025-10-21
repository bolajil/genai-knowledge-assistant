"""
Simple Vector Manager - Direct Implementation

This module provides a straightforward vector database manager that works
with the actual directory structure without complex dependencies.
"""

import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_simple_indexes():
    """Get available indexes by directly scanning directories"""
    indexes = []
    
    # Check data/faiss_index directory
    faiss_dir = Path("data/faiss_index")
    if faiss_dir.exists():
        # Check for direct index files
        if (faiss_dir / "index.faiss").exists() and (faiss_dir / "index.pkl").exists():
            indexes.append("default_faiss")
        
        # Check subdirectories
        for item in faiss_dir.iterdir():
            if item.is_dir():
                indexes.append(item.name)
    
    # Check data/indexes directory
    indexes_dir = Path("data/indexes")
    if indexes_dir.exists():
        for item in indexes_dir.iterdir():
            if item.is_dir():
                indexes.append(item.name)
    
    # Remove duplicates and sort
    indexes = sorted(list(set(indexes)))
    
    logger.info(f"Simple vector manager found indexes: {indexes}")
    return indexes

def get_simple_vector_status():
    """Get simple vector database status"""
    indexes = get_simple_indexes()
    
    if indexes:
        return ("Ready", f"{len(indexes)} Index(es) Available")
    else:
        return ("Error", "No Indexes Found")

def get_simple_index_path(index_name):
    """Get path for a specific index.
    Preference order:
    1) data/indexes/<name> if it contains extracted_text.txt (best for text/real-time retrieval)
    2) data/faiss_index/<name> if it exists (vector-only directory)
    3) data/indexes/<name> if it exists (even without extracted_text)
    4) default_faiss fallback
    """
    # Prefer text-friendly directory when available
    indexes_path = Path("data/indexes") / index_name
    if indexes_path.exists():
        try:
            if (indexes_path / "extracted_text.txt").exists():
                return str(indexes_path)
            # Or any readable text-like files
            for p in indexes_path.glob("*"):
                if p.is_file() and p.suffix.lower() in {".txt", ".md", ".html", ".json"}:
                    return str(indexes_path)
        except Exception:
            # If checks fail, still allow returning the path
            return str(indexes_path)

    # Next, faiss vector directory
    faiss_path = Path("data/faiss_index") / index_name
    if faiss_path.exists():
        return str(faiss_path)

    # Finally, if text directory exists but no detectable files, still return it
    if indexes_path.exists():
        return str(indexes_path)

    # default faiss
    if index_name == "default_faiss":
        faiss_dir = Path("data/faiss_index")
        if (faiss_dir / "index.faiss").exists():
            return str(faiss_dir)
    
    return None
