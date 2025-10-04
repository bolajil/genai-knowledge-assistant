"""
Vector Search with Embeddings

Enhanced vector search functionality that uses proper embeddings
for accurate document retrieval.
"""

import logging
import numpy as np
import faiss
import pickle
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorSearchEngine:
    """
    Enhanced vector search engine using embeddings
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the vector search engine
        
        Args:
            model_name: Name of the sentence transformer model
        """
        self.model_name = model_name
        self.model = None
        self._initialize_model()
        self.loaded_indexes = {}
    
    def _initialize_model(self):
        """Initialize the embedding model"""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Initialized embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def load_index(self, index_path: Path) -> bool:
        """
        Load a FAISS index with metadata
        
        Args:
            index_path: Path to the index directory
            
        Returns:
            True if loaded successfully
        """
        try:
            faiss_file = index_path / "index.faiss"
            metadata_file = index_path / "index.pkl"
            
            if not faiss_file.exists() or not metadata_file.exists():
                logger.error(f"Index files not found in {index_path}")
                return False
            
            # Load FAISS index
            faiss_index = faiss.read_index(str(faiss_file))
            
            # Load metadata
            with open(metadata_file, 'rb') as f:
                metadata = pickle.load(f)
            
            # Store in cache
            index_name = index_path.name
            self.loaded_indexes[index_name] = {
                'faiss_index': faiss_index,
                'metadata': metadata,
                'path': index_path
            }
            
            logger.info(f"Loaded index: {index_name} ({faiss_index.ntotal} vectors)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load index from {index_path}: {e}")
            return False
    
    def search(self, query: str, index_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search an index using vector similarity
        
        Args:
            query: Search query
            index_name: Name of the index to search
            top_k: Number of results to return
            
        Returns:
            List of search results with content and metadata
        """
        try:
            # Check if index is loaded
            if index_name not in self.loaded_indexes:
                # Try to find and load the index
                index_paths = [
                    Path(__file__).parent.parent / "data" / "indexes" / index_name,
                    Path(__file__).parent.parent / "data" / "faiss_index" / index_name
                ]
                
                loaded = False
                for path in index_paths:
                    if path.exists():
                        if self.load_index(path):
                            loaded = True
                            break
                
                if not loaded:
                    logger.error(f"Could not load index: {index_name}")
                    return []
            
            # Get the loaded index
            index_data = self.loaded_indexes[index_name]
            faiss_index = index_data['faiss_index']
            metadata = index_data['metadata']
            
            # Generate query embedding
            query_embedding = self.model.encode([query])
            query_embedding = query_embedding.astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Search the index
            scores, indices = faiss_index.search(query_embedding, top_k)
            
            # Format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # No more results
                    break
                
                # Get document content and metadata
                content = ""
                doc_metadata = {}
                
                if 'documents' in metadata and idx < len(metadata['documents']):
                    content = metadata['documents'][idx]
                
                if 'metadatas' in metadata and idx < len(metadata['metadatas']):
                    doc_metadata = metadata['metadatas'][idx]
                
                # Create result
                result = {
                    'content': content,
                    'source': doc_metadata.get('source', 'Unknown'),
                    'page': doc_metadata.get('page', 'N/A'),
                    'section': f"Chunk {doc_metadata.get('chunk_id', idx)}",
                    'confidence_score': float(score),
                    'chunk_id': doc_metadata.get('chunk_id', idx),
                    'metadata': {
                        'embedding_model': metadata.get('embedding_model', self.model_name),
                        'chunk_start': doc_metadata.get('start_pos', 0),
                        'chunk_end': doc_metadata.get('end_pos', 0),
                        'chunk_length': doc_metadata.get('length', len(content))
                    }
                }
                
                results.append(result)
            
            logger.info(f"Vector search returned {len(results)} results for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed for {index_name}: {e}")
            return []
    
    def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """
        Get information about a loaded index
        
        Args:
            index_name: Name of the index
            
        Returns:
            Index information dictionary
        """
        if index_name not in self.loaded_indexes:
            return {'error': 'Index not loaded'}
        
        index_data = self.loaded_indexes[index_name]
        metadata = index_data['metadata']
        faiss_index = index_data['faiss_index']
        
        return {
            'name': index_name,
            'total_vectors': faiss_index.ntotal,
            'dimension': faiss_index.d,
            'embedding_model': metadata.get('embedding_model', 'unknown'),
            'total_chunks': metadata.get('total_chunks', 0),
            'source_file': metadata.get('source_file', 'unknown'),
            'created_at': metadata.get('created_at', 'unknown'),
            'chunk_size': metadata.get('chunk_size', 0),
            'chunk_overlap': metadata.get('chunk_overlap', 0)
        }

# Global instance
_vector_search_engine = None

def get_vector_search_engine() -> VectorSearchEngine:
    """Get the global vector search engine instance"""
    global _vector_search_engine
    if _vector_search_engine is None:
        _vector_search_engine = VectorSearchEngine()
    return _vector_search_engine

def search_with_embeddings(query: str, index_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Convenience function for vector search with embeddings
    
    Args:
        query: Search query
        index_name: Name of the index to search
        top_k: Number of results to return
        
    Returns:
        List of search results
    """
    engine = get_vector_search_engine()
    return engine.search(query, index_name, top_k)

def validate_embeddings_available(index_name: str) -> Tuple[bool, str]:
    """
    Check if embeddings are available for an index
    
    Args:
        index_name: Name of the index to check
        
    Returns:
        Tuple of (available, message)
    """
    # Check common index locations
    index_paths = [
        Path(__file__).parent.parent / "data" / "indexes" / index_name,
        Path(__file__).parent.parent / "data" / "faiss_index" / index_name
    ]
    
    for path in index_paths:
        if path.exists():
            faiss_file = path / "index.faiss"
            metadata_file = path / "index.pkl"
            
            if faiss_file.exists() and metadata_file.exists():
                try:
                    # Try to load and validate
                    faiss_index = faiss.read_index(str(faiss_file))
                    if faiss_index.ntotal > 0:
                        return True, f"Embeddings available ({faiss_index.ntotal} vectors)"
                    else:
                        return False, "FAISS index is empty"
                except Exception as e:
                    return False, f"Error loading index: {str(e)}"
            else:
                return False, "FAISS index files not found"
    
    return False, f"Index directory not found: {index_name}"
