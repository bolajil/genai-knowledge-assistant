"""
Qdrant Vector Store Adapter
Implements vector search using Qdrant Cloud with filtering support
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, CollectionStatus, PointStruct,
        Filter, FieldCondition, MatchValue, SearchRequest
    )
    from qdrant_client.http import models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None
    # Create mock classes for type hints when qdrant is not available
    class Distance:
        COSINE = "Cosine"
        DOT = "Dot"
        EUCLID = "Euclid"
    
    class VectorParams:
        pass
    
    class CollectionStatus:
        pass
    
    class PointStruct:
        pass
    
    class Filter:
        pass
    
    class FieldCondition:
        pass
    
    class MatchValue:
        pass
    
    class SearchRequest:
        pass

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

logger = logging.getLogger(__name__)

class QdrantAdapter(BaseVectorStore):
    """Qdrant vector store implementation with filtering support"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client package is required for Qdrant adapter")
        
        # Extract connection parameters
        params = config.connection_params
        self.url = params.get('url', 'http://localhost:6333')
        self.api_key = params.get('api_key')
        self.timeout = params.get('timeout', 60)
        
        # Vector configuration
        self.vector_dimension = params.get('vector_dimension', 384)
        self.distance_metric = params.get('distance_metric', 'Cosine')  # Cosine, Euclid, Dot
        
        # Collection configuration
        self.on_disk_payload = params.get('on_disk_payload', True)
        self.hnsw_config = params.get('hnsw_config', {
            'ef_construct': 128,
            'ef': 64,
            'm': 16
        })
        
        self._client = None
    
    async def connect(self) -> bool:
        """Establish connection to Qdrant"""
        try:
            # Create Qdrant client
            self._client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=self.timeout
            )
            
            # Test connection
            collections = self._client.get_collections()
            logger.info(f"Connected to Qdrant: {len(collections.collections)} collections available")
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close connection to Qdrant"""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Qdrant: {e}")
        self._connected = False
    
    def _get_distance_metric(self) -> Distance:
        """Convert string distance metric to Qdrant Distance enum"""
        distance_map = {
            'cosine': Distance.COSINE,
            'euclidean': Distance.EUCLID,
            'dot': Distance.DOT
        }
        return distance_map.get(self.distance_metric.lower(), Distance.COSINE)
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new Qdrant collection"""
        try:
            if not self._client:
                await self.connect()
            
            # Check if collection already exists
            try:
                collection_info = self._client.get_collection(collection_name)
                if collection_info:
                    logger.info(f"Qdrant collection {collection_name} already exists")
                    return True
            except:
                pass  # Collection doesn't exist, continue with creation
            
            # Configure vector parameters
            vectors_config = VectorParams(
                size=self.vector_dimension,
                distance=self._get_distance_metric(),
                hnsw_config=models.HnswConfigDiff(
                    ef_construct=kwargs.get('ef_construct', self.hnsw_config['ef_construct']),
                    ef=kwargs.get('ef', self.hnsw_config['ef']),
                    m=kwargs.get('m', self.hnsw_config['m'])
                )
            )
            
            # Create collection
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=vectors_config,
                on_disk_payload=kwargs.get('on_disk_payload', self.on_disk_payload),
                replication_factor=kwargs.get('replication_factor', 1),
                write_consistency_factor=kwargs.get('write_consistency_factor', 1)
            )
            
            # Wait for collection to be ready
            import time
            max_wait = 60
            wait_time = 0
            while wait_time < max_wait:
                try:
                    collection_info = self._client.get_collection(collection_name)
                    if collection_info.status == CollectionStatus.GREEN:
                        break
                except:
                    pass
                
                time.sleep(2)
                wait_time += 2
            
            logger.info(f"Created Qdrant collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a Qdrant collection"""
        try:
            if not self._client:
                await self.connect()
            
            self._client.delete_collection(collection_name)
            logger.info(f"Deleted Qdrant collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Qdrant collection {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available Qdrant collections"""
        try:
            if not self._client:
                await self.connect()
            
            collections = self._client.get_collections()
            return [collection.name for collection in collections.collections]
            
        except Exception as e:
            logger.error(f"Failed to list Qdrant collections: {e}")
            return []
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """Insert or update documents with vectors"""
        try:
            if not self._client:
                await self.connect()
            
            # Prepare points for upsert
            points = []
            
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', f"doc_{i}_{datetime.now().timestamp()}")
                
                # Get vector
                vector = None
                if embeddings and i < len(embeddings):
                    vector = embeddings[i]
                elif 'vector' in doc:
                    vector = doc['vector']
                else:
                    logger.warning(f"No vector provided for document {doc_id}")
                    continue
                
                # Prepare payload (metadata)
                payload = {
                    "content": doc.get('content', ''),
                    "source": doc.get('source', ''),
                    "source_type": doc.get('source_type', 'unknown'),
                    "created_at": doc.get('created_at', datetime.now().isoformat())
                }
                
                # Add custom metadata
                if 'metadata' in doc and isinstance(doc['metadata'], dict):
                    payload.update(doc['metadata'])
                
                # Create point
                point = PointStruct(
                    id=str(doc_id),
                    vector=vector,
                    payload=payload
                )
                points.append(point)
            
            # Upsert points in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self._client.upsert(
                    collection_name=collection_name,
                    points=batch
                )
            
            logger.info(f"Upserted {len(points)} documents to Qdrant collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert documents to Qdrant collection {collection_name}: {e}")
            return False
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Search using Qdrant vector similarity with filtering"""
        try:
            if not query_embedding:
                logger.error("Query embedding is required for Qdrant search")
                return []
            
            if not self._client:
                await self.connect()
            
            # Prepare filter conditions
            filter_conditions = None
            if filters:
                conditions = []
                for field, value in filters.items():
                    if isinstance(value, list):
                        # Handle multiple values with OR logic
                        or_conditions = []
                        for v in value:
                            or_conditions.append(
                                FieldCondition(key=field, match=MatchValue(value=v))
                            )
                        if len(or_conditions) == 1:
                            conditions.append(or_conditions[0])
                        else:
                            conditions.append(models.Filter(should=or_conditions))
                    else:
                        conditions.append(
                            FieldCondition(key=field, match=MatchValue(value=value))
                        )
                
                if conditions:
                    filter_conditions = Filter(must=conditions)
            
            # Perform search
            search_result = self._client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=filter_conditions,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                score_threshold=kwargs.get('score_threshold', 0.0)
            )
            
            # Process results
            results = []
            for scored_point in search_result:
                payload = scored_point.payload or {}
                
                # Extract custom metadata
                metadata = {}
                for key, value in payload.items():
                    if key not in ['content', 'source', 'source_type', 'created_at']:
                        metadata[key] = value
                
                result = VectorSearchResult(
                    content=payload.get('content', ''),
                    metadata=metadata,
                    score=scored_point.score,
                    source=payload.get('source'),
                    id=str(scored_point.id)
                )
                results.append(result)
            
            logger.info(f"Qdrant returned {len(results)} results for query in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed in Qdrant collection {collection_name}: {e}")
            return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """Delete specific documents from Qdrant collection"""
        try:
            if not self._client:
                await self.connect()
            
            # Delete points
            self._client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=[str(doc_id) for doc_id in document_ids]
                )
            )
            
            logger.info(f"Deleted {len(document_ids)} documents from Qdrant collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from Qdrant collection {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a Qdrant collection"""
        try:
            if not self._client:
                await self.connect()
            
            # Get collection info
            collection_info = self._client.get_collection(collection_name)
            
            return {
                "document_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "status": collection_info.status.value,
                "optimizer_status": collection_info.optimizer_status.ok,
                "vector_dimension": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance.value,
                "health": "green" if collection_info.status == CollectionStatus.GREEN else "yellow"
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for Qdrant collection {collection_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if Qdrant service is healthy"""
        try:
            if not self._client:
                await self.connect()
            
            # Get cluster info to test connectivity
            collections = self._client.get_collections()
            return True, f"Qdrant healthy: {len(collections.collections)} collections available"
                
        except Exception as e:
            return False, f"Health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if QDRANT_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.QDRANT, QdrantAdapter)
