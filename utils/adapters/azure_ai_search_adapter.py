"""
Azure AI Search Vector Store Adapter
Implements vector search using Azure Cognitive Search with semantic reranking
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

try:
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.models import VectorizedQuery
    from azure.search.documents.indexes.models import (
        SearchIndex, SearchField, SearchFieldDataType, VectorSearch,
        HnswAlgorithmConfiguration, VectorSearchProfile, SemanticConfiguration,
        SemanticSearch, SemanticField, SemanticPrioritizedFields
    )
    from azure.core.credentials import AzureKeyCredential
    from azure.identity import DefaultAzureCredential
    AZURE_SEARCH_AVAILABLE = True
except ImportError:
    AZURE_SEARCH_AVAILABLE = False
    # Create mock classes for type hints when azure packages are not available
    class SearchClient:
        pass
    
    class SearchIndexClient:
        pass
    
    class VectorizedQuery:
        pass
    
    class SearchIndex:
        pass
    
    class SearchField:
        pass
    
    class SearchFieldDataType:
        pass
    
    class VectorSearch:
        pass
    
    class HnswAlgorithmConfiguration:
        pass
    
    class VectorSearchProfile:
        pass
    
    class SemanticConfiguration:
        pass
    
    class SemanticSearch:
        pass
    
    class SemanticField:
        pass
    
    class SemanticPrioritizedFields:
        pass
    
    class AzureKeyCredential:
        pass
    
    class DefaultAzureCredential:
        pass

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

logger = logging.getLogger(__name__)

class AzureAISearchAdapter(BaseVectorStore):
    """Azure AI Search vector store implementation with semantic reranking"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not AZURE_SEARCH_AVAILABLE:
            raise ImportError("azure-search-documents package is required for Azure AI Search adapter")
        
        # Extract connection parameters
        params = config.connection_params
        self.service_name = params.get('service_name')
        self.endpoint = params.get('endpoint') or f"https://{self.service_name}.search.windows.net"
        self.api_key = params.get('api_key')
        self.use_managed_identity = params.get('use_managed_identity', False)
        
        # Vector configuration
        self.vector_dimension = params.get('vector_dimension', 384)
        self.vector_algorithm = params.get('vector_algorithm', 'hnsw')
        self.similarity_metric = params.get('similarity_metric', 'cosine')
        
        # Semantic search configuration
        self.enable_semantic_search = params.get('enable_semantic_search', True)
        self.semantic_config_name = params.get('semantic_config_name', 'default-semantic-config')
        
        self._search_client = None
        self._index_client = None
    
    async def connect(self) -> bool:
        """Establish connection to Azure AI Search"""
        try:
            # Configure authentication
            if self.use_managed_identity:
                credential = DefaultAzureCredential()
            elif self.api_key:
                credential = AzureKeyCredential(self.api_key)
            else:
                raise ValueError("Either api_key or use_managed_identity must be provided")
            
            # Create clients
            self._index_client = SearchIndexClient(
                endpoint=self.endpoint,
                credential=credential
            )
            
            # Test connection
            service_stats = self._index_client.get_service_statistics()
            logger.info(f"Connected to Azure AI Search: {service_stats}")
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Azure AI Search: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close connection to Azure AI Search"""
        # Azure SDK handles connection pooling automatically
        self._connected = False
    
    def _get_search_client(self, index_name: str) -> SearchClient:
        """Get search client for specific index"""
        if self.use_managed_identity:
            credential = DefaultAzureCredential()
        else:
            credential = AzureKeyCredential(self.api_key)
        
        return SearchClient(
            endpoint=self.endpoint,
            index_name=index_name,
            credential=credential
        )
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new search index with vector and semantic search configuration"""
        try:
            if not self._index_client:
                await self.connect()
            
            # Check if index already exists
            try:
                existing_index = self._index_client.get_index(collection_name)
                if existing_index:
                    logger.info(f"Index {collection_name} already exists")
                    return True
            except:
                pass  # Index doesn't exist, continue with creation
            
            # Define search fields
            fields = [
                SearchField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    searchable=False,
                    filterable=True
                ),
                SearchField(
                    name="content",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    analyzer_name="standard.lucene"
                ),
                SearchField(
                    name="vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.vector_dimension,
                    vector_search_profile_name="default-vector-profile"
                ),
                SearchField(
                    name="source",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=True,
                    sortable=True,
                    facetable=True
                ),
                SearchField(
                    name="source_type",
                    type=SearchFieldDataType.String,
                    searchable=False,
                    filterable=True,
                    sortable=False,
                    facetable=True
                ),
                SearchField(
                    name="created_at",
                    type=SearchFieldDataType.DateTimeOffset,
                    searchable=False,
                    filterable=True,
                    sortable=True,
                    facetable=False
                ),
                SearchField(
                    name="metadata",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False
                )
            ]
            
            # Configure vector search
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="default-hnsw-algorithm",
                        parameters={
                            "m": kwargs.get('m', 4),
                            "efConstruction": kwargs.get('ef_construction', 400),
                            "efSearch": kwargs.get('ef_search', 500),
                            "metric": self.similarity_metric
                        }
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="default-vector-profile",
                        algorithm_configuration_name="default-hnsw-algorithm"
                    )
                ]
            )
            
            # Configure semantic search if enabled
            semantic_search = None
            if self.enable_semantic_search:
                semantic_search = SemanticSearch(
                    configurations=[
                        SemanticConfiguration(
                            name=self.semantic_config_name,
                            prioritized_fields=SemanticPrioritizedFields(
                                title_field=None,
                                content_fields=[
                                    SemanticField(field_name="content")
                                ],
                                keywords_fields=[
                                    SemanticField(field_name="source"),
                                    SemanticField(field_name="metadata")
                                ]
                            )
                        )
                    ]
                )
            
            # Create the index
            index = SearchIndex(
                name=collection_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            
            result = self._index_client.create_index(index)
            logger.info(f"Created Azure AI Search index: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Azure AI Search index {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a search index"""
        try:
            if not self._index_client:
                await self.connect()
            
            self._index_client.delete_index(collection_name)
            logger.info(f"Deleted Azure AI Search index: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Azure AI Search index {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available search indexes"""
        try:
            if not self._index_client:
                await self.connect()
            
            indexes = self._index_client.list_indexes()
            return [index.name for index in indexes]
            
        except Exception as e:
            logger.error(f"Failed to list Azure AI Search indexes: {e}")
            return []
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """Insert or update documents with vectors"""
        try:
            search_client = self._get_search_client(collection_name)
            
            # Prepare documents
            docs_to_upload = []
            
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', f"doc_{i}_{datetime.now().timestamp()}")
                
                # Prepare document
                doc_body = {
                    "id": str(doc_id),
                    "content": doc.get('content', ''),
                    "source": doc.get('source', ''),
                    "source_type": doc.get('source_type', 'unknown'),
                    "created_at": doc.get('created_at', datetime.now().isoformat()),
                    "metadata": json.dumps(doc.get('metadata', {}))
                }
                
                # Add vector if provided
                if embeddings and i < len(embeddings):
                    doc_body["vector"] = embeddings[i]
                elif 'vector' in doc:
                    doc_body["vector"] = doc['vector']
                
                docs_to_upload.append(doc_body)
            
            # Upload documents
            if docs_to_upload:
                result = search_client.upload_documents(documents=docs_to_upload)
                
                # Check for errors
                success_count = sum(1 for r in result if r.succeeded)
                error_count = len(result) - success_count
                
                if error_count > 0:
                    logger.warning(f"Document upload had {error_count} errors")
                
                logger.info(f"Uploaded {success_count} documents to {collection_name}")
                return error_count == 0
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert documents to {collection_name}: {e}")
            return False
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Search using vector similarity and/or semantic search"""
        try:
            search_client = self._get_search_client(collection_name)
            
            # Prepare search parameters
            search_params = {
                "top": limit,
                "select": ["id", "content", "source", "source_type", "created_at", "metadata"]
            }
            
            # Add vector search if embedding provided
            vector_queries = []
            if query_embedding:
                vector_query = VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=limit * 2,  # Get more candidates
                    fields="vector"
                )
                vector_queries.append(vector_query)
                search_params["vector_queries"] = vector_queries
            
            # Add text search
            search_text = query if query else "*"
            
            # Add filters
            filter_expression = None
            if filters:
                filter_parts = []
                for field, value in filters.items():
                    if isinstance(value, list):
                        # Handle list of values with 'or' logic
                        or_parts = [f"{field} eq '{v}'" for v in value]
                        filter_parts.append(f"({' or '.join(or_parts)})")
                    else:
                        filter_parts.append(f"{field} eq '{value}'")
                
                if filter_parts:
                    filter_expression = " and ".join(filter_parts)
                    search_params["filter"] = filter_expression
            
            # Add semantic search if enabled and query provided
            if self.enable_semantic_search and query:
                search_params["query_type"] = "semantic"
                search_params["semantic_configuration_name"] = self.semantic_config_name
                search_params["query_caption"] = "extractive"
                search_params["query_answer"] = "extractive"
            
            # Execute search
            results = search_client.search(
                search_text=search_text,
                **search_params
            )
            
            # Process results
            search_results = []
            for result in results:
                # Parse metadata
                metadata = {}
                try:
                    if result.get('metadata'):
                        metadata = json.loads(result['metadata'])
                except:
                    pass
                
                search_result = VectorSearchResult(
                    content=result.get('content', ''),
                    metadata=metadata,
                    score=result.get('@search.score', 0.0),
                    source=result.get('source'),
                    id=result.get('id')
                )
                search_results.append(search_result)
            
            logger.info(f"Azure AI Search returned {len(search_results)} results for query in {collection_name}")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed in Azure AI Search index {collection_name}: {e}")
            return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """Delete specific documents from index"""
        try:
            search_client = self._get_search_client(collection_name)
            
            # Prepare documents for deletion
            docs_to_delete = [{"id": doc_id} for doc_id in document_ids]
            
            if docs_to_delete:
                result = search_client.delete_documents(documents=docs_to_delete)
                
                success_count = sum(1 for r in result if r.succeeded)
                logger.info(f"Deleted {success_count} documents from {collection_name}")
                return success_count == len(document_ids)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a search index"""
        try:
            if not self._index_client:
                await self.connect()
            
            # Get index information
            index = self._index_client.get_index(collection_name)
            
            # Get document count (approximate)
            search_client = self._get_search_client(collection_name)
            count_result = search_client.search(
                search_text="*",
                include_total_count=True,
                top=0
            )
            
            return {
                "document_count": count_result.get_count(),
                "field_count": len(index.fields),
                "vector_search_enabled": index.vector_search is not None,
                "semantic_search_enabled": index.semantic_search is not None,
                "index_name": index.name,
                "health": "green"
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if Azure AI Search service is healthy"""
        try:
            if not self._index_client:
                await self.connect()
            
            # Get service statistics
            stats = self._index_client.get_service_statistics()
            
            return True, f"Service healthy: {stats.get('counters', {}).get('index_counter', {}).get('usage', 0)} indexes"
                
        except Exception as e:
            return False, f"Health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if AZURE_SEARCH_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.AZURE_AI_SEARCH, AzureAISearchAdapter)
