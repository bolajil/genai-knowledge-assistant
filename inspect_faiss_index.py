"""
FAISS Index Inspector Tool

This utility helps diagnose issues with FAISS indexes by inspecting their contents,
verifying document loading, and validating index structures.
"""

import os
import sys
import logging
from pathlib import Path
import json
import time
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import faiss
    import numpy as np
    import pickle
    from sentence_transformers import SentenceTransformer
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    logger.error("Required dependencies not found. Please install: faiss-cpu, numpy, sentence-transformers")
    DEPENDENCIES_AVAILABLE = False

# Paths to look for indexes
DEFAULT_SEARCH_PATHS = [
    Path("data/faiss_index"),
    Path("data/indexes"),
    Path("vector_store"),
]

def find_indexes(search_paths=None):
    """Find all FAISS indexes in the specified paths"""
    if search_paths is None:
        search_paths = DEFAULT_SEARCH_PATHS
    
    indexes = []
    
    for base_path in search_paths:
        if not base_path.exists() or not base_path.is_dir():
            logger.warning(f"Path does not exist: {base_path}")
            continue
        
        # Check for direct index files
        if (base_path / "index.faiss").exists():
            indexes.append({
                "name": base_path.name,
                "path": base_path,
                "type": "direct"
            })
        
        # Check subdirectories
        for item in base_path.iterdir():
            if item.is_dir():
                if (item / "index.faiss").exists():
                    indexes.append({
                        "name": item.name,
                        "path": item,
                        "type": "directory"
                    })
    
    return indexes

def inspect_index(index_path, show_samples=True, sample_count=3):
    """Inspect a FAISS index and its metadata"""
    if not DEPENDENCIES_AVAILABLE:
        return {"error": "Required dependencies not available"}
    
    results = {
        "index_path": str(index_path),
        "index_exists": False,
        "metadata_exists": False,
        "index_size": 0,
        "document_count": 0,
        "metadata_format": "unknown",
        "samples": [],
        "errors": []
    }
    
    try:
        # Check index file
        faiss_file = index_path / "index.faiss"
        if faiss_file.exists():
            results["index_exists"] = True
            
            # Load FAISS index
            faiss_index = faiss.read_index(str(faiss_file))
            results["index_size"] = faiss_index.ntotal
            
            # Find metadata file
            metadata_file = None
            for candidate in ["index.pkl", "documents.pkl", "metadata.pkl"]:
                if (index_path / candidate).exists():
                    metadata_file = index_path / candidate
                    results["metadata_exists"] = True
                    results["metadata_file"] = str(metadata_file)
                    break
            
            if metadata_file:
                # Load metadata
                with open(metadata_file, 'rb') as f:
                    metadata = pickle.load(f)
                
                # Analyze metadata format
                if isinstance(metadata, dict):
                    results["metadata_format"] = "dict"
                    
                    # Check for common document keys
                    doc_key = None
                    for key in ["documents", "texts", "content"]:
                        if key in metadata and isinstance(metadata[key], list):
                            doc_key = key
                            results["document_key"] = key
                            results["document_count"] = len(metadata[key])
                            
                            # Get samples
                            if show_samples and sample_count > 0:
                                samples = []
                                for i in range(min(sample_count, len(metadata[key]))):
                                    sample_text = metadata[key][i]
                                    if isinstance(sample_text, str):
                                        # Truncate long text
                                        if len(sample_text) > 500:
                                            sample_text = sample_text[:500] + "..."
                                        samples.append(sample_text)
                                results["samples"] = samples
                            break
                    
                    # Check for metadata
                    if "metadatas" in metadata and isinstance(metadata["metadatas"], list):
                        results["has_document_metadata"] = True
                        results["metadata_count"] = len(metadata["metadatas"])
                        
                        # Get sample metadata
                        if show_samples and sample_count > 0 and results["metadata_count"] > 0:
                            results["metadata_samples"] = metadata["metadatas"][:sample_count]
                            
                elif isinstance(metadata, list):
                    results["metadata_format"] = "list"
                    results["document_count"] = len(metadata)
                    
                    # Get samples
                    if show_samples and sample_count > 0:
                        samples = []
                        for i in range(min(sample_count, len(metadata))):
                            sample = metadata[i]
                            if isinstance(sample, str):
                                # Truncate long text
                                if len(sample) > 500:
                                    sample = sample[:500] + "..."
                                samples.append(sample)
                        results["samples"] = samples
                else:
                    results["metadata_format"] = type(metadata).__name__
            else:
                results["errors"].append("No metadata file found")
        else:
            results["errors"].append("FAISS index file not found")
    
    except Exception as e:
        results["errors"].append(f"Error inspecting index: {str(e)}")
    
    return results

def test_search(index_path, query="meeting", top_k=3):
    """Test searching a FAISS index with a query"""
    if not DEPENDENCIES_AVAILABLE:
        return {"error": "Required dependencies not available"}
    
    results = {
        "index_path": str(index_path),
        "query": query,
        "top_k": top_k,
        "success": False,
        "search_results": [],
        "errors": []
    }
    
    try:
        # Check files
        faiss_file = index_path / "index.faiss"
        if not faiss_file.exists():
            results["errors"].append("FAISS index file not found")
            return results
            
        # Find metadata file
        metadata_file = None
        for candidate in ["index.pkl", "documents.pkl", "metadata.pkl"]:
            if (index_path / candidate).exists():
                metadata_file = index_path / candidate
                break
        
        if not metadata_file:
            results["errors"].append("No metadata file found")
            return results
        
        # Load FAISS index
        faiss_index = faiss.read_index(str(faiss_file))
        
        # Load metadata
        with open(metadata_file, 'rb') as f:
            metadata = pickle.load(f)
        
        # Load embedding model
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Generate query embedding
        query_embedding = model.encode([query])[0]
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search the index
        distances, indices = faiss_index.search(query_embedding, top_k)
        
        # Get results
        search_results = []
        
        for i, doc_idx in enumerate(indices[0]):
            if doc_idx == -1:  # No more results
                continue
                
            # Get document content
            content = "No content available"
            
            # Try to get content from different metadata formats
            if isinstance(metadata, dict):
                for key in ["documents", "texts", "content"]:
                    if key in metadata and isinstance(metadata[key], list) and 0 <= doc_idx < len(metadata[key]):
                        content = metadata[key][doc_idx]
                        if isinstance(content, str):
                            # Truncate long content
                            if len(content) > 500:
                                content = content[:500] + "..."
                        break
            elif isinstance(metadata, list) and 0 <= doc_idx < len(metadata):
                content = metadata[doc_idx]
                if isinstance(content, str):
                    # Truncate long content
                    if len(content) > 500:
                        content = content[:500] + "..."
            
            # Get metadata
            doc_metadata = {}
            if isinstance(metadata, dict) and "metadatas" in metadata:
                if 0 <= doc_idx < len(metadata["metadatas"]):
                    doc_metadata = metadata["metadatas"][doc_idx]
            
            # Add result
            search_results.append({
                "doc_idx": int(doc_idx),
                "score": float(1.0 - distances[0][i]),
                "content": content,
                "metadata": doc_metadata
            })
        
        results["search_results"] = search_results
        results["success"] = True
        
    except Exception as e:
        results["errors"].append(f"Error testing search: {str(e)}")
    
    return results

def main():
    """Main function"""
    # Parse arguments first so we can support --list without heavy deps
    parser = argparse.ArgumentParser(description="FAISS Index Inspector Tool")
    parser.add_argument("--index", type=str, help="Name of specific index to inspect")
    parser.add_argument("--search", type=str, help="Test search with the specified query")
    parser.add_argument("--list", action="store_true", help="List all available indexes")
    parser.add_argument("--sample-count", type=int, default=3, help="Number of document samples to show")
    parser.add_argument("--top-k", type=int, default=3, help="Number of search results to return")
    args = parser.parse_args()

    # If we're only listing indexes (no inspect or search), allow running without deps
    if args.list and not args.index and not args.search:
        indexes = find_indexes()
        if not indexes:
            logger.error("No FAISS indexes found")
            return
        logger.info(f"Found {len(indexes)} FAISS indexes:")
        for i, index_info in enumerate(indexes):
            logger.info(f"{i+1}. {index_info['name']} - {index_info['path']}")
        return

    # For inspect/search operations, ensure dependencies are available
    if not DEPENDENCIES_AVAILABLE:
        logger.error("Required dependencies not available. Please install: faiss-cpu, numpy, sentence-transformers")
        return

    # Find indexes
    indexes = find_indexes()
    
    if not indexes:
        logger.error("No FAISS indexes found")
        return
    
    # List indexes by default when neither index nor search is provided
    if args.list or not (args.index or args.search):
        logger.info(f"Found {len(indexes)} FAISS indexes:")
        for i, index_info in enumerate(indexes):
            logger.info(f"{i+1}. {index_info['name']} - {index_info['path']}")
        return
    
    # Inspect specific index
    if args.index:
        target_index = None
        for index_info in indexes:
            if index_info["name"] == args.index:
                target_index = index_info
                break
        
        if not target_index:
            logger.error(f"Index '{args.index}' not found")
            return
        
        logger.info(f"Inspecting index: {target_index['name']}")
        inspection = inspect_index(target_index["path"], sample_count=args.sample_count)
        
        logger.info(f"Index path: {inspection['index_path']}")
        logger.info(f"FAISS index exists: {inspection['index_exists']}")
        logger.info(f"Metadata file exists: {inspection['metadata_exists']}")
        
        if inspection['index_exists']:
            logger.info(f"Index size: {inspection['index_size']} vectors")
        
        if inspection['metadata_exists']:
            logger.info(f"Metadata format: {inspection['metadata_format']}")
            logger.info(f"Document count: {inspection['document_count']}")
            
            if "document_key" in inspection:
                logger.info(f"Document key: {inspection['document_key']}")
            
            if "has_document_metadata" in inspection:
                logger.info(f"Has document metadata: {inspection['has_document_metadata']}")
                logger.info(f"Metadata count: {inspection['metadata_count']}")
            
            if inspection["samples"]:
                logger.info(f"\nDocument samples ({len(inspection['samples'])}):")
                for i, sample in enumerate(inspection["samples"]):
                    logger.info(f"\nSample {i+1}:")
                    logger.info(f"{sample}")
        
        if inspection["errors"]:
            logger.error("\nErrors:")
            for error in inspection["errors"]:
                logger.error(f"- {error}")
    
    # Test search
    if args.search:
        query = args.search
        
        # Use specified index or search all
        if args.index:
            target_indexes = [index_info for index_info in indexes if index_info["name"] == args.index]
            if not target_indexes:
                logger.error(f"Index '{args.index}' not found")
                return
        else:
            target_indexes = indexes
        
        for index_info in target_indexes:
            logger.info(f"\nTesting search on index: {index_info['name']}")
            logger.info(f"Query: '{query}'")
            
            search_results = test_search(index_info["path"], query, args.top_k)
            
            if search_results["success"]:
                logger.info(f"Found {len(search_results['search_results'])} results:")
                
                for i, result in enumerate(search_results["search_results"]):
                    logger.info(f"\nResult {i+1} (Score: {result['score']:.4f}):")
                    logger.info(f"Content: {result['content']}")
                    
                    if result["metadata"]:
                        logger.info(f"Metadata: {json.dumps(result['metadata'], indent=2)}")
            
            if search_results["errors"]:
                logger.error("\nErrors:")
                for error in search_results["errors"]:
                    logger.error(f"- {error}")

if __name__ == "__main__":
    main()
