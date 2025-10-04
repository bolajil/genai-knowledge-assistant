"""
Mock Vector Store Adapter
Wraps existing MockVectorDBProvider to conform to the unified interface
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

try:
    from ..mock_vector_db_provider import get_mock_vector_db_provider
    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False
    get_mock_vector_db_provider = None

logger = logging.getLogger(__name__)

class MockAdapter(BaseVectorStore):
    """Mock vector store adapter using existing MockVectorDBProvider"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not MOCK_AVAILABLE:
            raise ImportError("MockVectorDBProvider is required for Mock adapter")
        
        self._mock_provider = get_mock_vector_db_provider()
    
    async def connect(self) -> bool:
        """Initialize mock provider (always succeeds)"""
        try:
            logger.info("Mock vector store adapter initialized")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize mock adapter: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close mock provider (no-op)"""
        self._connected = False
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a mock collection (always succeeds)"""
        try:
            logger.info(f"Created mock collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create mock collection {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a mock collection (always succeeds)"""
        try:
            logger.info(f"Deleted mock collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete mock collection {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available mock collections"""
        try:
            return self._mock_provider.get_available_indexes()
        except Exception as e:
            logger.error(f"Failed to list mock collections: {e}")
            return []
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """Mock document upsert (always succeeds)"""
        try:
            logger.info(f"Mock upserted {len(documents)} documents to {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to mock upsert documents to {collection_name}: {e}")
            return False
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Search using mock provider"""
        try:
            # Use existing mock search functionality
            mock_results = self._mock_provider.search(query or "mock query", limit)
            
            # Convert to VectorSearchResult format
            results = []
            for mock_result in mock_results:
                result = VectorSearchResult(
                    content=mock_result.content,
                    metadata=mock_result.metadata,
                    score=mock_result.relevance,
                    source=mock_result.source,
                    id=f"mock_{len(results)}"
                )
                results.append(result)
            
            logger.info(f"Mock provider returned {len(results)} results for query in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Mock search failed in {collection_name}: {e}")
            return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """Mock document deletion (always succeeds)"""
        try:
            logger.info(f"Mock deleted {len(document_ids)} documents from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to mock delete documents from {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get mock statistics about a collection"""
        try:
            return {
                "document_count": 100,  # Mock count
                "collection_name": collection_name,
                "type": "mock",
                "health": "green"
            }
        except Exception as e:
            logger.error(f"Failed to get mock stats for {collection_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check mock provider health (always healthy)"""
        try:
            status, message = self._mock_provider.get_vector_db_status()
            return status == "Ready", message
        except Exception as e:
            return False, f"Mock health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if MOCK_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.MOCK, MockAdapter)
