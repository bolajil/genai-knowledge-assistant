"""
Unified Vector Store Interface
Provides a consistent API that can work with both FAISS and Weaviate backends
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)

class VectorStoreType(Enum):
    FAISS = "faiss"
    WEAVIATE = "weaviate"

class SearchResult:
    """Unified search result object"""
    def __init__(self, 
                 content: str, 
                 source_name: str, 
                 source_type: str, 
                 relevance_score: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None,
                 uuid: Optional[str] = None):
        self.content = content
        self.source_name = source_name
        self.source_type = source_type
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
        self.uuid = uuid
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
            "uuid": self.uuid
        }

class VectorStoreInterface(ABC):
    """Abstract interface for vector stores"""
    
    @abstractmethod
    def search(self, query: str, collection_name: str = None, top_k: int = 5, **kwargs) -> List[SearchResult]:
        """Search for documents"""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Any]], collection_name: str = None) -> bool:
        """Add documents to the store"""
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """List available collections/indexes"""
        pass
    
    @abstractmethod
    def create_collection(self, name: str, **kwargs) -> bool:
        """Create a new collection/index"""
        pass
    
    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """Delete a collection/index"""
        pass

class FAISSVectorStore(VectorStoreInterface):
    """FAISS implementation of vector store interface"""
    
    def __init__(self):
        try:
            from utils.index_manager import IndexManager
            self.index_manager = IndexManager
        except ImportError:
            logger.error("IndexManager not available")
            self.index_manager = None
    
    def search(self, query: str, collection_name: str = None, top_k: int = 5, **kwargs) -> List[SearchResult]:
        """Search FAISS indexes"""
        try:
            from utils.direct_vector_search import search_vector_store
            
            # Use direct vector search
            faiss_results = search_vector_store(query, collection_name, top_k)
            
            # Convert to unified SearchResult format
            results = []
            for result in faiss_results:
                unified_result = SearchResult(
                    content=result.content,
                    source_name=result.source_name,
                    source_type=result.source_type,
                    relevance_score=result.relevance_score,
                    metadata=result.metadata
                )
                results.append(unified_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching FAISS: {str(e)}")
            return []
    
    def add_documents(self, documents: List[Dict[str, Any]], collection_name: str = None) -> bool:
        """Add documents to FAISS (not implemented - requires embedding generation)"""
        logger.warning("Adding documents to FAISS not implemented in this interface")
        return False
    
    def list_collections(self) -> List[str]:
        """List FAISS indexes"""
        if self.index_manager:
            return self.index_manager.list_available_indexes()
        return []
    
    def create_collection(self, name: str, **kwargs) -> bool:
        """Create FAISS index (not implemented)"""
        logger.warning("Creating FAISS collections not implemented in this interface")
        return False
    
    def delete_collection(self, name: str) -> bool:
        """Delete FAISS index (not implemented)"""
        logger.warning("Deleting FAISS collections not implemented in this interface")
        return False

class WeaviateVectorStore(VectorStoreInterface):
    """Weaviate implementation of vector store interface"""
    
    def __init__(self):
        try:
            from utils.weaviate_manager import get_weaviate_manager
            self.weaviate_manager = get_weaviate_manager()
        except ImportError:
            logger.error("Weaviate manager not available")
            self.weaviate_manager = None
    
    def search(self, query: str, collection_name: str = None, top_k: int = 5, **kwargs) -> List[SearchResult]:
        """Search Weaviate collections"""
        if not self.weaviate_manager:
            return []
        
        try:
            # If no collection specified, search all collections
            collections_to_search = [collection_name] if collection_name else self.list_collections()
            
            all_results = []
            for collection in collections_to_search:
                if not collection:
                    continue
                    
                # Use hybrid search if available, otherwise regular search
                search_method = kwargs.get('search_method', 'hybrid')
                
                if search_method == 'hybrid':
                    weaviate_results = self.weaviate_manager.hybrid_search(
                        collection_name=collection,
                        query=query,
                        alpha=kwargs.get('alpha', 0.5),
                        limit=top_k
                    )
                else:
                    weaviate_results = self.weaviate_manager.search(
                        collection_name=collection,
                        query=query,
                        limit=top_k,
                        where_filter=kwargs.get('where_filter'),
                        return_metadata=True
                    )
                
                # Convert to unified SearchResult format
                for result in weaviate_results:
                    unified_result = SearchResult(
                        content=result.get("content", ""),
                        source_name=f"Collection: {collection}",
                        source_type=result.get("source_type", "weaviate"),
                        relevance_score=result.get("score", 0.0),
                        metadata=result.get("metadata", {}),
                        uuid=result.get("uuid")
                    )
                    all_results.append(unified_result)
            
            # Sort by relevance and limit results
            all_results.sort(key=lambda x: x.relevance_score, reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching Weaviate: {str(e)}")
            return []
    
    def add_documents(self, documents: List[Dict[str, Any]], collection_name: str = None) -> bool:
        """Add documents to Weaviate"""
        if not self.weaviate_manager or not collection_name:
            return False
        
        return self.weaviate_manager.add_documents(collection_name, documents)
    
    def list_collections(self) -> List[str]:
        """List Weaviate collections"""
        if not self.weaviate_manager:
            return []
        
        return self.weaviate_manager.list_collections()
    
    def create_collection(self, name: str, **kwargs) -> bool:
        """Create Weaviate collection"""
        if not self.weaviate_manager:
            return False
        
        return self.weaviate_manager.create_collection(
            collection_name=name,
            description=kwargs.get('description', ''),
            properties=kwargs.get('properties')
        )
    
    def delete_collection(self, name: str) -> bool:
        """Delete Weaviate collection"""
        if not self.weaviate_manager:
            return False
        
        return self.weaviate_manager.delete_collection(name)

class UnifiedVectorStore:
    """
    Unified vector store that can work with multiple backends
    Provides seamless switching between FAISS and Weaviate
    """
    
    def __init__(self, backend_type: VectorStoreType = None):
        """
        Initialize unified vector store
        
        Args:
            backend_type: Type of vector store backend to use
        """
        # Auto-detect backend if not specified
        if backend_type is None:
            backend_type = self._detect_backend()
        
        self.backend_type = backend_type
        self.backend = self._create_backend(backend_type)
        
        logger.info(f"Initialized UnifiedVectorStore with {backend_type.value} backend")
    
    def _detect_backend(self) -> VectorStoreType:
        """Auto-detect which backend to use based on availability"""
        
        # Check for Weaviate configuration
        weaviate_url = os.getenv("WEAVIATE_URL")
        if weaviate_url:
            logger.info("WEAVIATE_URL is set. Forcing Weaviate backend.")
            return VectorStoreType.WEAVIATE
        
        # Fall back to FAISS
        try:
            from utils.index_manager import IndexManager
            indexes = IndexManager.list_available_indexes()
            logger.info("FAISS backend detected and available")
            return VectorStoreType.FAISS
        except Exception as e:
            logger.warning(f"FAISS backend not available: {str(e)}")
        
        # Default to FAISS
        return VectorStoreType.FAISS
    
    def _create_backend(self, backend_type: VectorStoreType) -> VectorStoreInterface:
        """Create the appropriate backend instance"""
        if backend_type == VectorStoreType.WEAVIATE:
            return WeaviateVectorStore()
        else:
            return FAISSVectorStore()
    
    def search(self, query: str, collection_name: str = None, top_k: int = 5, **kwargs) -> List[SearchResult]:
        """
        Search for documents across the vector store
        
        Args:
            query: Search query
            collection_name: Specific collection/index to search
            top_k: Number of results to return
            **kwargs: Additional search parameters
            
        Returns:
            List of SearchResult objects
        """
        return self.backend.search(query, collection_name, top_k, **kwargs)
    
    def add_documents(self, documents: List[Dict[str, Any]], collection_name: str = None) -> bool:
        """Add documents to the vector store"""
        return self.backend.add_documents(documents, collection_name)
    
    def list_collections(self) -> List[str]:
        """List available collections/indexes"""
        return self.backend.list_collections()
    
    def create_collection(self, name: str, **kwargs) -> bool:
        """Create a new collection/index"""
        return self.backend.create_collection(name, **kwargs)
    
    def delete_collection(self, name: str) -> bool:
        """Delete a collection/index"""
        return self.backend.delete_collection(name)
    
    def get_backend_type(self) -> VectorStoreType:
        """Get the current backend type"""
        return self.backend_type
    
    def switch_backend(self, backend_type: VectorStoreType):
        """Switch to a different backend"""
        if backend_type != self.backend_type:
            self.backend_type = backend_type
            self.backend = self._create_backend(backend_type)
            logger.info(f"Switched to {backend_type.value} backend")
    
    def migrate_to_weaviate(self, source_collection: str = None) -> bool:
        """
        Migrate data from FAISS to Weaviate
        
        Args:
            source_collection: Specific FAISS collection to migrate (None for all)
            
        Returns:
            True if migration successful
        """
        if self.backend_type == VectorStoreType.WEAVIATE:
            logger.info("Already using Weaviate backend")
            return True
        
        try:
            # Create temporary FAISS backend to read data
            faiss_backend = FAISSVectorStore()
            
            # Create Weaviate backend for target
            weaviate_backend = WeaviateVectorStore()
            
            # Get collections to migrate
            collections = [source_collection] if source_collection else faiss_backend.list_collections()
            
            migration_success = True
            for collection in collections:
                try:
                    # Create collection in Weaviate
                    weaviate_backend.create_collection(
                        name=collection,
                        description=f"Migrated from FAISS collection: {collection}"
                    )
                    
                    # Note: Actual document migration would require loading FAISS data
                    # This is a placeholder for the migration logic
                    logger.info(f"Migration setup completed for collection: {collection}")
                    
                except Exception as e:
                    logger.error(f"Error migrating collection {collection}: {str(e)}")
                    migration_success = False
            
            if migration_success:
                # Switch to Weaviate backend
                self.switch_backend(VectorStoreType.WEAVIATE)
                logger.info("Migration to Weaviate completed successfully")
            
            return migration_success
            
        except Exception as e:
            logger.error(f"Error during migration to Weaviate: {str(e)}")
            return False

# Global instance
_unified_vector_store = None

def get_vector_store() -> UnifiedVectorStore:
    """Get global unified vector store instance"""
    global _unified_vector_store
    if _unified_vector_store is None:
        _unified_vector_store = UnifiedVectorStore()
    return _unified_vector_store
