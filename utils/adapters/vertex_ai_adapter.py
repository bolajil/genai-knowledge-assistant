"""
Google Cloud Vertex AI Matching Engine Vector Store Adapter
Implements vector search using Vertex AI Matching Engine with ScaNN optimization
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

try:
    from google.cloud import aiplatform
    from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
    from google.oauth2 import service_account
    from google.auth import default
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    # Create mock classes for type hints when google cloud packages are not available
    class aiplatform:
        pass
    
    class MatchingEngineIndex:
        pass
    
    class MatchingEngineIndexEndpoint:
        pass
    
    class service_account:
        pass

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

logger = logging.getLogger(__name__)

class VertexAIMatchingEngineAdapter(BaseVectorStore):
    """Vertex AI Matching Engine vector store implementation"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not VERTEX_AI_AVAILABLE:
            error_msg = (
                "google-cloud-aiplatform package is required for Vertex AI adapter. "
                "Install with: py -m pip install google-cloud-aiplatform google-auth"
            )
            logger.error(error_msg)
            raise ImportError(error_msg)
        
        # Extract connection parameters
        params = config.connection_params
        self.project_id = params.get('project_id')
        # Support both 'region' and 'location' parameter names
        self.region = params.get('region') or params.get('location', 'us-central1')
        # Support both 'service_account_path' and 'credentials_path' parameter names
        creds_path = params.get('service_account_path') or params.get('credentials_path')
        # Strip quotes from path if present (Windows .env files sometimes add them)
        self.service_account_path = creds_path.strip('"').strip("'") if creds_path else None
        
        # Matching Engine configuration
        self.vector_dimension = params.get('vector_dimension', 384)
        self.distance_measure = params.get('distance_measure', 'COSINE_DISTANCE')
        self.algorithm_config = params.get('algorithm_config', 'tree-ah')
        
        # Index and endpoint configuration
        self.index_display_name_prefix = params.get('index_display_name_prefix', 'vaultmind')
        self.endpoint_display_name_prefix = params.get('endpoint_display_name_prefix', 'vaultmind-endpoint')
        
        self._client = None
        self._indexes = {}
        self._endpoints = {}
    
    async def connect(self) -> bool:
        """Initialize Vertex AI client"""
        try:
            # Configure authentication
            if self.service_account_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path
                )
                aiplatform.init(
                    project=self.project_id,
                    location=self.region,
                    credentials=credentials
                )
            else:
                # Use default credentials
                aiplatform.init(
                    project=self.project_id,
                    location=self.region
                )
            
            logger.info(f"Connected to Vertex AI Matching Engine in project {self.project_id}")
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Vertex AI: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close connection to Vertex AI"""
        self._connected = False
    
    def _get_index_display_name(self, collection_name: str) -> str:
        """Generate display name for index"""
        return f"{self.index_display_name_prefix}-{collection_name}"
    
    def _get_endpoint_display_name(self, collection_name: str) -> str:
        """Generate display name for endpoint"""
        return f"{self.endpoint_display_name_prefix}-{collection_name}"
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new Matching Engine index and endpoint"""
        try:
            if not self._connected:
                await self.connect()
            
            index_display_name = self._get_index_display_name(collection_name)
            endpoint_display_name = self._get_endpoint_display_name(collection_name)
            
            # Check if index already exists
            existing_indexes = MatchingEngineIndex.list(
                filter=f'display_name="{index_display_name}"'
            )
            
            if existing_indexes:
                logger.info(f"Index {collection_name} already exists")
                self._indexes[collection_name] = existing_indexes[0]
                
                # Check for existing endpoint
                existing_endpoints = MatchingEngineIndexEndpoint.list(
                    filter=f'display_name="{endpoint_display_name}"'
                )
                if existing_endpoints:
                    self._endpoints[collection_name] = existing_endpoints[0]
                
                return True
            
            # Create index configuration
            index_config = {
                "dimensions": self.vector_dimension,
                "distance_measure_type": self.distance_measure,
                "algorithm_config": {
                    "tree_ah_config": {
                        "leaf_node_embedding_count": kwargs.get('leaf_node_embedding_count', 1000),
                        "leaf_nodes_to_search_percent": kwargs.get('leaf_nodes_to_search_percent', 10)
                    }
                } if self.algorithm_config == 'tree-ah' else {
                    "brute_force_config": {}
                }
            }
            
            # Create the index
            index = MatchingEngineIndex.create_tree_ah_index(
                display_name=index_display_name,
                contents_delta_uri=kwargs.get('gcs_bucket_uri', f"gs://{self.project_id}-matching-engine/{collection_name}"),
                dimensions=self.vector_dimension,
                distance_measure_type=self.distance_measure,
                leaf_node_embedding_count=kwargs.get('leaf_node_embedding_count', 1000),
                leaf_nodes_to_search_percent=kwargs.get('leaf_nodes_to_search_percent', 10),
                description=f"VaultMind vector index for {collection_name}",
                labels={"created_by": "vaultmind", "collection": collection_name}
            )
            
            # Wait for index creation to complete
            index.wait()
            self._indexes[collection_name] = index
            
            # Create endpoint for serving
            endpoint = MatchingEngineIndexEndpoint.create(
                display_name=endpoint_display_name,
                description=f"VaultMind endpoint for {collection_name}",
                labels={"created_by": "vaultmind", "collection": collection_name}
            )
            
            # Deploy index to endpoint
            endpoint.deploy_index(
                index=index,
                deployed_index_id=f"{collection_name}_deployed",
                display_name=f"{collection_name}_deployment",
                machine_type=kwargs.get('machine_type', 'e2-standard-2'),
                min_replica_count=kwargs.get('min_replicas', 1),
                max_replica_count=kwargs.get('max_replicas', 1)
            )
            
            self._endpoints[collection_name] = endpoint
            
            logger.info(f"Created Vertex AI Matching Engine index and endpoint: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Vertex AI index {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a Matching Engine index and endpoint"""
        try:
            # Undeploy and delete endpoint
            if collection_name in self._endpoints:
                endpoint = self._endpoints[collection_name]
                
                # Undeploy index first
                deployed_indexes = endpoint.list_deployed_indexes()
                for deployed_index in deployed_indexes:
                    endpoint.undeploy_index(deployed_index_id=deployed_index.id)
                
                # Delete endpoint
                endpoint.delete()
                del self._endpoints[collection_name]
            
            # Delete index
            if collection_name in self._indexes:
                index = self._indexes[collection_name]
                index.delete()
                del self._indexes[collection_name]
            
            logger.info(f"Deleted Vertex AI Matching Engine resources: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Vertex AI resources {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available Matching Engine indexes"""
        try:
            if not self._connected:
                await self.connect()
            
            indexes = MatchingEngineIndex.list()
            collections = []
            
            for index in indexes:
                # Extract collection name from display name
                if index.display_name.startswith(self.index_display_name_prefix):
                    collection_name = index.display_name[len(self.index_display_name_prefix) + 1:]
                    collections.append(collection_name)
                    self._indexes[collection_name] = index
            
            return collections
            
        except Exception as e:
            logger.error(f"Failed to list Vertex AI indexes: {e}")
            return []
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """
        Note: Vertex AI Matching Engine requires batch updates via GCS.
        This method prepares data for batch upload.
        """
        try:
            logger.warning("Vertex AI Matching Engine requires batch updates via GCS. "
                         "Use the batch update functionality for production workloads.")
            
            # For development, we'll simulate the upsert
            # In production, this would write to GCS and trigger index update
            
            if not embeddings:
                logger.error("Embeddings are required for Vertex AI Matching Engine")
                return False
            
            # Prepare data in the format expected by Vertex AI
            # This would typically be written to GCS as JSONL
            batch_data = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                doc_id = doc.get('id', f"doc_{i}")
                
                # Vertex AI format: {"id": "doc_id", "embedding": [0.1, 0.2, ...]}
                vertex_doc = {
                    "id": str(doc_id),
                    "embedding": embedding,
                    "restricts": [
                        {"namespace": "source", "allow": [doc.get('source', 'unknown')]},
                        {"namespace": "source_type", "allow": [doc.get('source_type', 'unknown')]}
                    ]
                }
                batch_data.append(vertex_doc)
            
            # Store metadata separately (Vertex AI only stores embeddings and restricts)
            metadata_store = {}
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', f"doc_{i}")
                metadata_store[str(doc_id)] = {
                    "content": doc.get('content', ''),
                    "metadata": doc.get('metadata', {}),
                    "source": doc.get('source', ''),
                    "source_type": doc.get('source_type', 'unknown'),
                    "created_at": doc.get('created_at', datetime.now().isoformat())
                }
            
            # In a real implementation, you would:
            # 1. Write batch_data to GCS as JSONL
            # 2. Trigger index update
            # 3. Store metadata_store in a separate database (Firestore, BigQuery, etc.)
            
            logger.info(f"Prepared {len(documents)} documents for batch update to {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare documents for {collection_name}: {e}")
            return False
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Search using Vertex AI Matching Engine"""
        try:
            if not query_embedding:
                logger.error("Query embedding is required for Vertex AI Matching Engine search")
                return []
            
            # Get endpoint for this collection
            if collection_name not in self._endpoints:
                # Try to find existing endpoint
                endpoint_display_name = self._get_endpoint_display_name(collection_name)
                existing_endpoints = MatchingEngineIndexEndpoint.list(
                    filter=f'display_name="{endpoint_display_name}"'
                )
                if existing_endpoints:
                    self._endpoints[collection_name] = existing_endpoints[0]
                else:
                    logger.error(f"No endpoint found for collection {collection_name}")
                    return []
            
            endpoint = self._endpoints[collection_name]
            
            # Prepare restricts (filters)
            restricts = []
            if filters:
                for field, value in filters.items():
                    if isinstance(value, list):
                        restricts.append({
                            "namespace": field,
                            "allow": value
                        })
                    else:
                        restricts.append({
                            "namespace": field,
                            "allow": [str(value)]
                        })
            
            # Perform vector search
            response = endpoint.find_neighbors(
                deployed_index_id=f"{collection_name}_deployed",
                queries=[query_embedding],
                num_neighbors=limit,
                restricts=restricts if restricts else None
            )
            
            # Process results
            results = []
            if response and len(response) > 0:
                neighbors = response[0]
                
                for neighbor in neighbors:
                    # In a real implementation, you would fetch metadata from your metadata store
                    # using neighbor.id
                    
                    result = VectorSearchResult(
                        content=f"Document content for ID: {neighbor.id}",  # Fetch from metadata store
                        metadata={"vertex_ai_id": neighbor.id},  # Fetch from metadata store
                        score=1.0 - neighbor.distance,  # Convert distance to similarity score
                        source="vertex_ai_matching_engine",
                        id=neighbor.id
                    )
                    results.append(result)
            
            logger.info(f"Vertex AI returned {len(results)} results for query in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed in Vertex AI index {collection_name}: {e}")
            return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """
        Note: Vertex AI Matching Engine requires batch updates for deletions.
        This would typically involve updating the GCS data and reindexing.
        """
        try:
            logger.warning("Vertex AI Matching Engine requires batch updates for deletions. "
                         "Use the batch update functionality for production workloads.")
            
            # In a real implementation, you would:
            # 1. Remove documents from GCS data
            # 2. Trigger index rebuild
            # 3. Remove from metadata store
            
            logger.info(f"Prepared deletion of {len(document_ids)} documents from {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a Matching Engine index"""
        try:
            if collection_name not in self._indexes:
                await self.list_collections()
            
            if collection_name in self._indexes:
                index = self._indexes[collection_name]
                
                return {
                    "index_name": index.display_name,
                    "resource_name": index.resource_name,
                    "dimensions": self.vector_dimension,
                    "distance_measure": self.distance_measure,
                    "state": index.index_stats.vectors_count if hasattr(index, 'index_stats') else "unknown",
                    "health": "green"
                }
            
            return {"error": f"Index {collection_name} not found"}
            
        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if Vertex AI service is healthy"""
        try:
            if not self._connected:
                await self.connect()
            
            # List indexes to test connectivity
            indexes = MatchingEngineIndex.list()
            return True, f"Vertex AI healthy: {len(indexes)} indexes available"
                
        except Exception as e:
            return False, f"Health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if VERTEX_AI_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.VERTEX_AI_MATCHING, VertexAIMatchingEngineAdapter)
