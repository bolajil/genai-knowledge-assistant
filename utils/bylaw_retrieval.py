"""
Direct ByLaw Document Retrieval

This module provides direct document retrieval for the ByLawS2 index
to ensure the system properly reads and returns document content.
"""

import os
import logging
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import pickle
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths to look for the ByLawS2 index
SEARCH_PATHS = [
    Path("data/faiss_index/ByLawS2_index"),
    Path("data/indexes/ByLawS2_index"),
    Path("data/faiss_index/ByLawS2"),
    Path("vector_store/ByLawS2_index")
]

class ByLawDocumentRetriever:
    """Specialized retriever for ByLaw documents"""
    
    def __init__(self):
        self.embedding_model = None
        self.faiss_index = None
        self.documents = []
        self.metadata = {}
        self.index_loaded = False
        self._initialize()
    
    def _initialize(self):
        """Initialize the retriever and load the index"""
        try:
            # Load the embedding model
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded embedding model successfully")
            
            # Find and load the index
            for path in SEARCH_PATHS:
                if self._load_index(path):
                    break
            
            if not self.index_loaded:
                logger.error("Failed to load ByLawS2 index from any of the search paths")
        except Exception as e:
            logger.error(f"Error initializing ByLaw document retriever: {e}")
    
    def _load_index(self, index_path: Path) -> bool:
        """Load the FAISS index and documents from the specified path"""
        try:
            # Check if path exists
            if not index_path.exists():
                return False
            
            # Check for index files
            faiss_file = index_path / "index.faiss"
            if not faiss_file.exists():
                return False
            
            # Check for metadata/document files (try different names)
            metadata_file = None
            for filename in ["index.pkl", "documents.pkl", "metadata.pkl"]:
                if (index_path / filename).exists():
                    metadata_file = index_path / filename
                    break
            
            if not metadata_file:
                return False
            
            # Load FAISS index
            self.faiss_index = faiss.read_index(str(faiss_file))
            logger.info(f"Loaded FAISS index from {faiss_file} with {self.faiss_index.ntotal} vectors")
            
            # Load documents
            with open(metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
            
            # Extract documents based on metadata format
            if isinstance(self.metadata, dict):
                if "documents" in self.metadata:
                    self.documents = self.metadata["documents"]
                elif "texts" in self.metadata:
                    self.documents = self.metadata["texts"]
                else:
                    # Try to find documents in other fields
                    for key, value in self.metadata.items():
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], str):
                            self.documents = value
                            break
            elif isinstance(self.metadata, list):
                self.documents = self.metadata
            
            logger.info(f"Loaded {len(self.documents)} documents from {metadata_file}")
            self.index_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading index from {index_path}: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the ByLaw documents for relevant content
        
        Args:
            query: The search query
            top_k: Maximum number of results to return
            
        Returns:
            List of search results with content and metadata
        """
        if not self.index_loaded or not self.faiss_index or not self.embedding_model:
            logger.error("ByLaw index not properly loaded")
            return [{"content": "ByLaw index not properly loaded", "score": 0.0}]
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]
            query_embedding = np.array([query_embedding]).astype('float32')
            
            # Search the index
            distances, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Format results
            results = []
            for i, doc_idx in enumerate(indices[0]):
                if doc_idx == -1:  # No more results
                    continue
                    
                # Get document content
                content = "No content available"
                if 0 <= doc_idx < len(self.documents):
                    content = self.documents[doc_idx]
                
                # Get metadata
                doc_metadata = {}
                if isinstance(self.metadata, dict) and "metadatas" in self.metadata:
                    if 0 <= doc_idx < len(self.metadata["metadatas"]):
                        doc_metadata = self.metadata["metadatas"][doc_idx]
                
                # Create result
                score = float(1.0 - distances[0][i])  # Convert distance to similarity score
                result = {
                    "content": content,
                    "score": score,
                    "metadata": doc_metadata,
                    "index": "ByLawS2_index",
                    "doc_idx": int(doc_idx)
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching ByLaw index: {e}")
            return [{"content": f"Error searching ByLaw index: {str(e)}", "score": 0.0}]

# Create singleton instance
_bylaw_retriever = None

def get_bylaw_retriever() -> ByLawDocumentRetriever:
    """Get the singleton ByLawDocumentRetriever instance"""
    global _bylaw_retriever
    if _bylaw_retriever is None:
        _bylaw_retriever = ByLawDocumentRetriever()
    return _bylaw_retriever

def search_bylaw_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search the ByLaw documents directly
    
    Args:
        query: The search query
        top_k: Maximum number of results to return
        
    Returns:
        List of search results with content and metadata
    """
    retriever = get_bylaw_retriever()
    return retriever.search(query, top_k)
