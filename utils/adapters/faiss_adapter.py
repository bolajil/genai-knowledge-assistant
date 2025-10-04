"""
FAISS Vector Store Adapter
Wraps existing FAISS functionality to conform to the unified interface
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
import json
from pathlib import Path

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None
    np = None

try:
    import pickle
    PICKLE_AVAILABLE = True
except ImportError:
    PICKLE_AVAILABLE = False

logger = logging.getLogger(__name__)

class FAISSAdapter(BaseVectorStore):
    """FAISS vector store adapter using existing FAISS functionality"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not FAISS_AVAILABLE:
            raise ImportError("faiss-cpu package is required for FAISS adapter")
        
        # Extract connection parameters
        params = config.connection_params
        self.index_directory = params.get('index_directory', 'data/faiss_index')
        self.vector_dimension = params.get('vector_dimension', 384)
        self.index_type = params.get('index_type', 'IndexFlatIP')  # IndexFlatIP, IndexHNSWFlat, etc.
        
        # Create index directory if it doesn't exist
        Path(self.index_directory).mkdir(parents=True, exist_ok=True)
        
        self._indexes = {}
        self._metadata_stores = {}
    
    def _get_index_path(self, collection_name: str) -> Path:
        """Get path for FAISS index file"""
        return Path(self.index_directory) / collection_name / "index.faiss"
    
    def _get_metadata_path(self, collection_name: str) -> Path:
        """Get path for metadata file"""
        return Path(self.index_directory) / collection_name / "metadata.pkl"
    
    def _get_documents_path(self, collection_name: str) -> Path:
        """Get path for documents file"""
        return Path(self.index_directory) / collection_name / "documents.pkl"
    
    async def connect(self) -> bool:
        """Initialize FAISS (no actual connection needed)"""
        try:
            logger.info(f"FAISS adapter initialized with index directory: {self.index_directory}")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize FAISS adapter: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close FAISS resources"""
        self._indexes.clear()
        self._metadata_stores.clear()
        self._connected = False
    
    def _create_faiss_index(self, dimension: int) -> faiss.Index:
        """Create a new FAISS index"""
        if self.index_type == 'IndexFlatIP':
            return faiss.IndexFlatIP(dimension)
        elif self.index_type == 'IndexFlatL2':
            return faiss.IndexFlatL2(dimension)
        elif self.index_type == 'IndexHNSWFlat':
            return faiss.IndexHNSWFlat(dimension, 32)
        else:
            # Default to flat inner product
            return faiss.IndexFlatIP(dimension)
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new FAISS index"""
        try:
            collection_dir = Path(self.index_directory) / collection_name
            collection_dir.mkdir(parents=True, exist_ok=True)
            
            index_path = self._get_index_path(collection_name)
            
            # Check if index already exists
            if index_path.exists():
                logger.info(f"FAISS index {collection_name} already exists")
                return True
            
            # Create new FAISS index
            dimension = kwargs.get('dimension', self.vector_dimension)
            index = self._create_faiss_index(dimension)
            
            # Save empty index
            faiss.write_index(index, str(index_path))
            
            # Initialize empty metadata and documents
            metadata_path = self._get_metadata_path(collection_name)
            documents_path = self._get_documents_path(collection_name)
            
            with open(metadata_path, 'wb') as f:
                pickle.dump([], f)
            
            with open(documents_path, 'wb') as f:
                pickle.dump([], f)
            
            logger.info(f"Created FAISS index: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create FAISS index {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a FAISS index"""
        try:
            collection_dir = Path(self.index_directory) / collection_name
            
            if collection_dir.exists():
                import shutil
                shutil.rmtree(collection_dir)
                
                # Remove from memory
                if collection_name in self._indexes:
                    del self._indexes[collection_name]
                if collection_name in self._metadata_stores:
                    del self._metadata_stores[collection_name]
                
                logger.info(f"Deleted FAISS index: {collection_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete FAISS index {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available FAISS indexes"""
        try:
            index_dir = Path(self.index_directory)
            if not index_dir.exists():
                return []
            
            collections = []
            for item in index_dir.iterdir():
                if item.is_dir() and (item / "index.faiss").exists():
                    collections.append(item.name)
            
            return collections
            
        except Exception as e:
            logger.error(f"Failed to list FAISS indexes: {e}")
            return []
    
    def _load_index(self, collection_name: str) -> Tuple[Optional[faiss.Index], List[Dict], List[str]]:
        """Load FAISS index and associated metadata"""
        try:
            if collection_name in self._indexes:
                return (
                    self._indexes[collection_name],
                    self._metadata_stores.get(collection_name, []),
                    []
                )
            
            index_path = self._get_index_path(collection_name)
            metadata_path = self._get_metadata_path(collection_name)
            documents_path = self._get_documents_path(collection_name)
            
            if not index_path.exists():
                return None, [], []
            
            # Load FAISS index
            index = faiss.read_index(str(index_path))
            
            # Load metadata
            metadata = []
            if metadata_path.exists():
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
            
            # Load documents
            documents = []
            if documents_path.exists():
                with open(documents_path, 'rb') as f:
                    documents = pickle.load(f)
            
            # Cache in memory
            self._indexes[collection_name] = index
            self._metadata_stores[collection_name] = metadata
            
            return index, metadata, documents
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index {collection_name}: {e}")
            return None, [], []
    
    def _save_index(self, collection_name: str, index: faiss.Index, metadata: List[Dict], documents: List[str]):
        """Save FAISS index and associated metadata"""
        try:
            index_path = self._get_index_path(collection_name)
            metadata_path = self._get_metadata_path(collection_name)
            documents_path = self._get_documents_path(collection_name)
            
            # Save FAISS index
            faiss.write_index(index, str(index_path))
            
            # Save metadata
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            # Save documents
            with open(documents_path, 'wb') as f:
                pickle.dump(documents, f)
            
            # Update cache
            self._indexes[collection_name] = index
            self._metadata_stores[collection_name] = metadata
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index {collection_name}: {e}")
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """Insert or update documents in FAISS index"""
        try:
            if not embeddings:
                logger.error("Embeddings are required for FAISS adapter")
                return False
            
            # Load existing index
            index, metadata, doc_list = self._load_index(collection_name)
            
            if index is None:
                # Create new index if it doesn't exist
                await self.create_collection(collection_name)
                index, metadata, doc_list = self._load_index(collection_name)
            
            # Convert embeddings to numpy array
            vectors = np.array(embeddings, dtype=np.float32)
            
            # Normalize vectors for cosine similarity (if using IndexFlatIP)
            if self.index_type == 'IndexFlatIP':
                faiss.normalize_L2(vectors)
            
            # Add vectors to index
            index.add(vectors)
            
            # Add metadata and documents
            for i, doc in enumerate(documents):
                doc_metadata = {
                    'id': doc.get('id', f"doc_{len(metadata)}_{datetime.now().timestamp()}"),
                    'source': doc.get('source', ''),
                    'source_type': doc.get('source_type', 'unknown'),
                    'created_at': doc.get('created_at', datetime.now().isoformat()),
                    'metadata': doc.get('metadata', {})
                }
                metadata.append(doc_metadata)
                doc_list.append(doc.get('content', ''))
            
            # Save updated index
            self._save_index(collection_name, index, metadata, doc_list)
            
            logger.info(f"Upserted {len(documents)} documents to FAISS index {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert documents to FAISS index {collection_name}: {e}")
            return False
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Search FAISS index"""
        try:
            if not query_embedding:
                logger.error("Query embedding is required for FAISS search")
                return []
            
            # Load index
            index, metadata, documents = self._load_index(collection_name)
            
            if index is None:
                logger.warning(f"FAISS index {collection_name} not found")
                return []
            
            # Convert query to numpy array
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # Normalize for cosine similarity
            if self.index_type == 'IndexFlatIP':
                faiss.normalize_L2(query_vector)
            
            # Search
            scores, indices = index.search(query_vector, min(limit, index.ntotal))
            
            # Process results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # Invalid index
                    continue
                
                # Apply filters if provided
                if filters and idx < len(metadata):
                    doc_metadata = metadata[idx]
                    skip = False
                    
                    for field, value in filters.items():
                        if field in doc_metadata:
                            if isinstance(value, list):
                                if doc_metadata[field] not in value:
                                    skip = True
                                    break
                            else:
                                if doc_metadata[field] != value:
                                    skip = True
                                    break
                    
                    if skip:
                        continue
                
                # Create result
                doc_meta = metadata[idx] if idx < len(metadata) else {}
                content = documents[idx] if idx < len(documents) else ''
                
                result = VectorSearchResult(
                    content=content,
                    metadata=doc_meta.get('metadata', {}),
                    score=float(score),
                    source=doc_meta.get('source'),
                    id=doc_meta.get('id', str(idx))
                )
                results.append(result)
            
            logger.info(f"FAISS returned {len(results)} results for query in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed in FAISS index {collection_name}: {e}")
            return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """Delete specific documents from FAISS index"""
        try:
            logger.warning("FAISS does not support individual document deletion. "
                         "Consider rebuilding the index without the unwanted documents.")
            
            # For now, we'll mark documents as deleted in metadata
            # A full implementation would require rebuilding the index
            
            index, metadata, documents = self._load_index(collection_name)
            
            if index is None:
                return False
            
            # Mark documents as deleted
            deleted_count = 0
            for i, doc_meta in enumerate(metadata):
                if doc_meta.get('id') in document_ids:
                    doc_meta['deleted'] = True
                    deleted_count += 1
            
            # Save updated metadata
            self._save_index(collection_name, index, metadata, documents)
            
            logger.info(f"Marked {deleted_count} documents as deleted in FAISS index {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from FAISS index {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a FAISS index"""
        try:
            index, metadata, documents = self._load_index(collection_name)
            
            if index is None:
                return {"error": f"Index {collection_name} not found"}
            
            active_docs = sum(1 for meta in metadata if not meta.get('deleted', False))
            
            return {
                "document_count": active_docs,
                "total_vectors": index.ntotal,
                "vector_dimension": index.d,
                "index_type": self.index_type,
                "is_trained": index.is_trained,
                "health": "green"
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for FAISS index {collection_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if FAISS is healthy"""
        try:
            collections = await self.list_collections()
            return True, f"FAISS healthy: {len(collections)} indexes available"
        except Exception as e:
            return False, f"Health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if FAISS_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.FAISS, FAISSAdapter)
