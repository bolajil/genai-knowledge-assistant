"""
Weaviate Vector Store Adapter
Wraps existing WeaviateManager to conform to the unified interface
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

try:
    from ..weaviate_manager import WeaviateManager
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False
    WeaviateManager = None

logger = logging.getLogger(__name__)

class WeaviateAdapter(BaseVectorStore):
    """Weaviate vector store adapter using existing WeaviateManager"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not WEAVIATE_AVAILABLE:
            raise ImportError("WeaviateManager is required for Weaviate adapter")
        
        # Extract connection parameters
        params = config.connection_params
        self.url = params.get('url', 'http://localhost:8080')
        self.api_key = params.get('api_key')
        self.openai_api_key = params.get('openai_api_key')
        
        # Initialize WeaviateManager
        self._weaviate_manager = WeaviateManager(
            url=self.url,
            api_key=self.api_key,
            openai_api_key=self.openai_api_key
        )
    
    async def connect(self) -> bool:
        """Establish connection to Weaviate using a robust, prefix-aware health check."""
        try:
            is_healthy, _ = await self.health_check()
            self._connected = is_healthy
            if is_healthy:
                logger.info(f"Weaviate connection successful for {self.url}")
            else:
                logger.error(f"Weaviate connection failed for {self.url}")
            return is_healthy
        except Exception as e:
            logger.error(f"Exception during Weaviate connect: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close connection to Weaviate"""
        try:
            if hasattr(self._weaviate_manager, '_client') and self._weaviate_manager._client:
                self._weaviate_manager._client.close()
        except Exception as e:
            logger.error(f"Error disconnecting from Weaviate: {e}")
        self._connected = False
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new Weaviate collection"""
        try:
            return self._weaviate_manager.create_collection(
                collection_name=collection_name,
                description=kwargs.get('description', f'VaultMind collection: {collection_name}'),
                properties=kwargs.get('properties')
            )
        except Exception as e:
            logger.error(f"Failed to create Weaviate collection {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a Weaviate collection"""
        try:
            # Use WeaviateManager's delete functionality if available
            if hasattr(self._weaviate_manager, 'delete_collection'):
                return self._weaviate_manager.delete_collection(collection_name)
            else:
                # Fallback to direct client access
                client = self._weaviate_manager.client
                actual_name = self._weaviate_manager._resolve_collection_name(collection_name)
                client.collections.delete(actual_name)
                logger.info(f"Deleted Weaviate collection: {collection_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete Weaviate collection {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available Weaviate collections"""
        try:
            if hasattr(self._weaviate_manager, 'list_collections'):
                return self._weaviate_manager.list_collections()
            else:
                # Fallback to direct client access
                client = self._weaviate_manager.client
                collections = client.collections.list_all()
                return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Failed to list Weaviate collections: {e}")
            return []
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """Insert or update documents in Weaviate"""
        try:
            if hasattr(self._weaviate_manager, 'add_documents'):
                return self._weaviate_manager.add_documents(
                    collection_name=collection_name,
                    documents=documents,
                    embeddings=embeddings
                )
            else:
                # Fallback implementation
                client = self._weaviate_manager.client
                actual_name = self._weaviate_manager._resolve_collection_name(collection_name)
                collection = client.collections.get(actual_name)
                
                # Prepare objects for batch insert
                objects = []
                for i, doc in enumerate(documents):
                    doc_obj = {
                        "content": doc.get('content', ''),
                        "source": doc.get('source', ''),
                        "source_type": doc.get('source_type', 'unknown'),
                        "created_at": doc.get('created_at', datetime.now().isoformat()),
                        "metadata": doc.get('metadata', {})
                    }
                    
                    # Add vector if provided
                    if embeddings and i < len(embeddings):
                        doc_obj["vector"] = embeddings[i]
                    elif 'vector' in doc:
                        doc_obj["vector"] = doc['vector']
                    
                    objects.append(doc_obj)
                
                # Batch insert
                with collection.batch.dynamic() as batch:
                    for obj in objects:
                        batch.add_object(properties=obj)
                
                logger.info(f"Upserted {len(documents)} documents to Weaviate collection {collection_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to upsert documents to Weaviate collection {collection_name}: {e}")
            return False
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Search Weaviate collection"""
        try:
            if hasattr(self._weaviate_manager, 'search_documents'):
                # Use existing search method if available
                results = self._weaviate_manager.search_documents(
                    collection_name=collection_name,
                    query=query,
                    query_embedding=query_embedding,
                    filters=filters,
                    limit=limit
                )
                
                # Convert to VectorSearchResult format
                search_results = []
                for result in results:
                    search_result = VectorSearchResult(
                        content=result.get('content', ''),
                        metadata=result.get('metadata', {}),
                        score=result.get('score', 0.0),
                        source=result.get('source'),
                        id=result.get('id')
                    )
                    search_results.append(search_result)
                
                return search_results
            else:
                # Fallback implementation
                client = self._weaviate_manager.client
                actual_name = self._weaviate_manager._resolve_collection_name(collection_name)
                collection = client.collections.get(actual_name)
                
                # Build query
                if query_embedding:
                    # Vector search
                    response = collection.query.near_vector(
                        near_vector=query_embedding,
                        limit=limit,
                        return_metadata=['score']
                    )
                elif query:
                    # Text search
                    response = collection.query.bm25(
                        query=query,
                        limit=limit,
                        return_metadata=['score']
                    )
                else:
                    # Get all documents
                    response = collection.query.fetch_objects(limit=limit)
                
                # Process results
                results = []
                for obj in response.objects:
                    result = VectorSearchResult(
                        content=obj.properties.get('content', ''),
                        metadata=obj.properties.get('metadata', {}),
                        score=getattr(obj.metadata, 'score', 0.0) if hasattr(obj, 'metadata') else 0.0,
                        source=obj.properties.get('source'),
                        id=str(obj.uuid)
                    )
                    results.append(result)
                
                logger.info(f"Weaviate returned {len(results)} results for query in {collection_name}")
                return results
                
        except Exception as e:
            logger.error(f"Search failed in Weaviate collection {collection_name}: {e}")
            return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """Delete specific documents from Weaviate collection"""
        try:
            client = self._weaviate_manager.client
            actual_name = self._weaviate_manager._resolve_collection_name(collection_name)
            collection = client.collections.get(actual_name)
            
            # Delete documents by UUID
            for doc_id in document_ids:
                collection.data.delete_by_id(doc_id)
            
            logger.info(f"Deleted {len(document_ids)} documents from Weaviate collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from Weaviate collection {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a Weaviate collection"""
        try:
            client = self._weaviate_manager.client
            actual_name = self._weaviate_manager._resolve_collection_name(collection_name)
            collection = client.collections.get(actual_name)
            
            # Get collection info
            config = collection.config.get()
            
            # Count objects (approximate)
            response = collection.aggregate.over_all(total_count=True)
            
            return {
                "document_count": response.total_count if hasattr(response, 'total_count') else 0,
                "collection_name": actual_name,
                "vectorizer": config.vectorizer_config,
                "properties": len(config.properties) if config.properties else 0,
                "health": "green"
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for Weaviate collection {collection_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Perform a prefix-aware health check by probing readiness and schema endpoints."""
        try:
            wm = self._weaviate_manager
            base = str(getattr(wm, 'url', '')).rstrip('/')
            if not base:
                return False, "Weaviate URL not configured"

            # Discover prefix if possible
            try:
                prefix = wm._discover_rest_prefix(force=True) or ''
            except Exception:
                prefix = ''

            # Build candidate endpoints
            endpoints = []
            tried = set()
            def add_endpoint(url):
                if url not in tried:
                    endpoints.append(url)
                    tried.add(url)

            if prefix:
                add_endpoint(f"{base}{prefix}/v1/.well-known/ready")
                add_endpoint(f"{base}{prefix}/v1/schema")
                add_endpoint(f"{base}{prefix}/v2/collections")

            for p in ['', '/api', '/weaviate', '/rest']:
                add_endpoint(f"{base}{p}/v1/.well-known/ready")
                add_endpoint(f"{base}{p}/v1/schema")
                add_endpoint(f"{base}{p}/v2/collections")

            # Probe endpoints
            for url in endpoints:
                try:
                    r = wm._http_request("GET", url, timeout=5)
                    if r.status_code in (200, 201, 204, 401, 403, 405):
                        collections = await self.list_collections()
                        return True, f"Weaviate healthy: {len(collections)} collections available at {url}"
                except Exception:
                    continue
            
            return False, "All readiness/schema probes failed"
        except Exception as e:
            return False, f"Health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if WEAVIATE_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.WEAVIATE, WeaviateAdapter)
