"""
AWS OpenSearch Vector Store Adapter
Implements vector search using Amazon OpenSearch Service with k-NN plugin
"""

import json
import logging
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from opensearchpy.exceptions import OpenSearchException
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    # Create mock classes for type hints when opensearch is not available
    class OpenSearch:
        pass
    
    class RequestsHttpConnection:
        pass
    
    OpenSearchException = Exception

try:
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from requests_aws4auth import AWS4Auth
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    # Create mock classes for type hints when AWS packages are not available
    class boto3:
        pass
    
    class SigV4Auth:
        pass
    
    class AWSRequest:
        pass
    
    class AWS4Auth:
        pass

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

logger = logging.getLogger(__name__)

class AWSOpenSearchAdapter(BaseVectorStore):
    """AWS OpenSearch vector store implementation with k-NN support"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not OPENSEARCH_AVAILABLE:
            raise ImportError("opensearch-py package is required for AWS OpenSearch adapter")
        
        # Extract connection parameters
        params = config.connection_params
        # Prefer config; fallback to environment; finally a safe default
        env_host = os.getenv('AWS_OPENSEARCH_HOST', '').strip()
        self.host = (params.get('host') or env_host or 'localhost')
        self.port = params.get('port', 9200)
        self.use_ssl = params.get('use_ssl', True)
        self.verify_certs = params.get('verify_certs', True)
        self.region = (
            params.get('region')
            or os.getenv('AWS_REGION')
            or os.getenv('AWS_DEFAULT_REGION')
            or 'us-east-1'
        )

        # Sanitize host: accept plain hostname or full URL; reject ARNs explicitly
        try:
            from urllib.parse import urlparse
            raw = str(self.host or '').strip()
            if raw.lower().startswith('arn:'):
                # Cannot derive endpoint from ARN; force user to provide endpoint hostname
                raise ValueError("AWS_OPENSEARCH_HOST must be the domain endpoint hostname (e.g., 'search-<domain>-<hash>.<region>.es.amazonaws.com'), not an ARN.")
            if '://' in raw:
                parsed = urlparse(raw)
                if parsed.hostname:
                    self.host = parsed.hostname
                # Adopt port/scheme from URL if not explicitly set
                if params.get('port') is None and parsed.port:
                    self.port = parsed.port
                if params.get('use_ssl') is None and parsed.scheme:
                    self.use_ssl = (parsed.scheme.lower() == 'https')
            # If host looks like AWS managed/serverless, prefer HTTPS:443 unless explicitly overridden
            h = (self.host or '').lower()
            if (h.endswith('.es.amazonaws.com') or h.endswith('.aoss.amazonaws.com')):
                # Only override if user didn't explicitly set a different port
                if 'port' not in params or params.get('port') in (None, 9200):
                    self.port = 443
                if 'use_ssl' not in params or params.get('use_ssl') is None:
                    self.use_ssl = True
        except Exception as _sanitize_err:
            # Keep defaults; connection will fail with a clear error later
            logger.debug(f"OpenSearch host sanitize warning: {_sanitize_err}")
        
        # Authentication options
        self.auth_type = params.get('auth_type', 'aws_iam')  # aws_iam, basic, none
        self.username = params.get('username')
        self.password = params.get('password')
        self.aws_access_key = params.get('aws_access_key') or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = params.get('aws_secret_key') or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_session_token = params.get('aws_session_token') or os.getenv('AWS_SESSION_TOKEN')
        
        # Vector configuration
        self.vector_dimension = params.get('vector_dimension', 384)
        self.vector_method = params.get('vector_method', 'hnsw')  # hnsw, ivf
        self.similarity_metric = params.get('similarity_metric', 'cosine')  # cosine, l2, inner_product
        
        self._client = None
    
    async def connect(self) -> bool:
        """Establish connection to AWS OpenSearch"""
        try:
            # Configure authentication
            auth = None
            service_name = 'es'
            try:
                h = (self.host or '').lower()
                if h.endswith('.aoss.amazonaws.com'):
                    service_name = 'aoss'
            except Exception:
                pass
            if self.auth_type == 'aws_iam' and AWS_AVAILABLE:
                if self.aws_access_key and self.aws_secret_key:
                    auth = AWS4Auth(
                        self.aws_access_key,
                        self.aws_secret_key,
                        self.region,
                        service_name,
                        session_token=self.aws_session_token
                    )
                else:
                    # Use default AWS credentials
                    session = boto3.Session()
                    credentials = session.get_credentials()
                    auth = AWS4Auth(
                        credentials.access_key,
                        credentials.secret_key,
                        self.region,
                        service_name,
                        session_token=credentials.token
                    )
            elif self.auth_type == 'basic' and self.username and self.password:
                auth = (self.username, self.password)
            
            # Create OpenSearch client
            logger.info(f"Connecting to OpenSearch host={self.host}, port={self.port}, ssl={self.use_ssl}, verify={self.verify_certs}, region={self.region}, service={service_name}, auth_type={self.auth_type}")
            self._client = OpenSearch(
                hosts=[{'host': self.host, 'port': self.port}],
                http_auth=auth,
                use_ssl=self.use_ssl,
                verify_certs=self.verify_certs,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            info = self._client.info()
            logger.info(f"Connected to OpenSearch cluster: {info.get('cluster_name', 'unknown')}")
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to AWS OpenSearch: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close connection to OpenSearch"""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.error(f"Error disconnecting from OpenSearch: {e}")
        self._connected = False
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new index with k-NN configuration"""
        try:
            if not self._client:
                await self.connect()
            
            # Check if index already exists
            if self._client.indices.exists(index=collection_name):
                logger.info(f"Index {collection_name} already exists")
                return True
            
            # Determine replicas considering zone awareness
            replicas = kwargs.get('replicas')
            if replicas is None:
                replicas = 1
                # Try to compute awareness requirement and pick minimal valid replicas proactively
                try:
                    required_copies = self._get_zone_awareness_required_copies()
                    if isinstance(required_copies, int) and required_copies > 1:
                        # total copies = replicas + 1 must be multiple of required_copies
                        mod = (1 + replicas) % required_copies
                        if mod != 0:
                            # minimal replicas >= 0 so that (1 + replicas) % required == 0
                            target_replicas = required_copies - 1  # first multiple
                            if target_replicas != replicas:
                                replicas = target_replicas
                                logger.info(f"Zone awareness detected [{required_copies}]; setting replicas={replicas}")
                except Exception as _aw_e:
                    logger.debug(f"Zone awareness check failed: {_aw_e}")
            # Map similarity metric to OpenSearch k-NN space_type strings
            def _map_space_type(metric: str) -> str:
                m = (metric or '').lower().strip()
                if m in ('cosine', 'cosinesim', 'cosinesimil', 'cosine_sim'):  # normalize variants
                    return 'cosinesimil'
                if m in ('inner_product', 'innerproduct', 'ip'):
                    return 'innerproduct'
                # default to l2
                return 'l2'

            space_type = _map_space_type(self.similarity_metric)

            index_settings = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": kwargs.get('ef_search', 100),
                        "number_of_shards": kwargs.get('shards', 1),
                        "number_of_replicas": replicas,
                        # Ensure templates with auto_expand_replicas don't override explicit replicas
                        "auto_expand_replicas": "false"
                    }
                },
                "mappings": {
                    "properties": {
                        "content": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "vector": {
                            "type": "knn_vector",
                            "dimension": self.vector_dimension,
                            "method": {
                                "name": self.vector_method,
                                "space_type": space_type,
                                "engine": "nmslib" if self.vector_method == "hnsw" else "faiss",
                                "parameters": {
                                    "ef_construction": kwargs.get('ef_construction', 128),
                                    "m": kwargs.get('m', 24)
                                } if self.vector_method == "hnsw" else {
                                    "nlist": kwargs.get('nlist', 128),
                                    "nprobes": kwargs.get('nprobes', 10)
                                }
                            }
                        },
                        "metadata": {
                            "type": "object",
                            "enabled": True
                        },
                        "source": {
                            "type": "keyword"
                        },
                        "source_type": {
                            "type": "keyword"
                        },
                        "created_at": {
                            "type": "date"
                        }
                    }
                }
            }
            
            # Create the index
            try:
                response = self._client.indices.create(
                    index=collection_name,
                    body=index_settings
                )
                logger.info(f"Created OpenSearch index: {collection_name}")
                return response.get('acknowledged', False)
            except Exception as e:
                # Handle zone awareness replica constraint: "expected total copies needs to be a multiple of total awareness attributes [N]"
                msg = str(e)
                if 'expected total copies needs to be a multiple of total awareness attributes' in msg:
                    try:
                        m = re.search(r"\[(\d+)\]", msg)
                        if m:
                            required = int(m.group(1))
                            # Try several candidates to satisfy awareness rule across versions/templates
                            base_candidates = [max(required - 1, 0), required, max(2 * required - 1, 0), 2 * required]
                            # De-duplicate and skip current value
                            seen = set()
                            candidates = []
                            current = index_settings['settings']['index'].get('number_of_replicas', replicas)
                            for c in base_candidates:
                                if c not in seen and c != current:
                                    seen.add(c)
                                    candidates.append(c)
                            last_err = None
                            for adjusted in candidates:
                                try:
                                    logger.warning(f"Retrying index creation with replicas={adjusted} due to zone awareness requirement [{required}]")
                                    index_settings['settings']['index']['number_of_replicas'] = adjusted
                                    response = self._client.indices.create(
                                        index=collection_name,
                                        body=index_settings
                                    )
                                    logger.info(f"Created OpenSearch index after retry: {collection_name}")
                                    return response.get('acknowledged', False)
                                except Exception as e2:
                                    last_err = e2
                                    logger.debug(f"Retry with replicas={adjusted} failed: {e2}")
                                    # Continue trying other candidates regardless of error; we'll raise last error if none succeed
                                    continue
                            if last_err is not None:
                                raise last_err
                    except Exception as parse_err:
                        logger.debug(f"Replica adjustment parse failed: {parse_err}")
                # Re-raise to be caught by outer except for logging
                raise
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch index {collection_name}: {e}")
            return False

    def _get_zone_awareness_required_copies(self) -> Optional[int]:
        """Read cluster settings to compute the required total copies for zone awareness.
        Returns N if total copies (primary + replicas) must be a multiple of N; otherwise None/1.
        """
        try:
            # include_defaults increases payload a lot; try transient+persistent first
            settings = self._client.cluster.get_settings()
            # search settings in persistent, then transient, then defaults if needed
            paths = [
                settings.get('persistent', {}),
                settings.get('transient', {}),
            ]
            attrs = None
            forced_counts = []
            for root in paths:
                # cluster.routing.allocation.awareness.attributes can be comma-separated list
                attrs_val = (
                    root.get('cluster', {})
                        .get('routing', {})
                        .get('allocation', {})
                        .get('awareness', {})
                        .get('attributes')
                )
                if attrs_val:
                    attrs = [a.strip() for a in str(attrs_val).split(',') if a.strip()]
                    # For each attribute, check forced values count
                    for a in attrs:
                        key = f"force.{a}.values"
                        vals = (
                            root.get('cluster', {})
                                .get('routing', {})
                                .get('allocation', {})
                                .get('awareness', {})
                                .get('force', {})
                                .get(a, {})
                                .get('values')
                        )
                        if vals:
                            count = len(str(vals).split(','))
                            if count > 0:
                                forced_counts.append(count)
            if forced_counts:
                # product of counts across attributes
                prod = 1
                for c in forced_counts:
                    prod *= c
                return prod
            return None
        except Exception:
            return None
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete an index"""
        try:
            if not self._client:
                await self.connect()
            
            if self._client.indices.exists(index=collection_name):
                response = self._client.indices.delete(index=collection_name)
                logger.info(f"Deleted OpenSearch index: {collection_name}")
                return response.get('acknowledged', False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete OpenSearch index {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available indexes"""
        try:
            if not self._client:
                await self.connect()
            
            # Get all indices
            indices = self._client.indices.get_alias(index="*")
            return list(indices.keys())
            
        except Exception as e:
            logger.error(f"Failed to list OpenSearch indices: {e}")
            return []
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """Insert or update documents with vectors"""
        try:
            if not self._client:
                await self.connect()
            
            # Prepare bulk operations
            bulk_body = []
            
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', f"doc_{i}_{datetime.now().timestamp()}")
                
                # Prepare document
                doc_body = {
                    "content": doc.get('content', ''),
                    "metadata": doc.get('metadata', {}),
                    "source": doc.get('source', ''),
                    "source_type": doc.get('source_type', 'unknown'),
                    "created_at": doc.get('created_at', datetime.now().isoformat())
                }
                
                # Add vector if provided
                if embeddings and i < len(embeddings):
                    doc_body["vector"] = embeddings[i]
                elif 'vector' in doc:
                    doc_body["vector"] = doc['vector']
                
                # Add to bulk operations
                bulk_body.extend([
                    {"index": {"_index": collection_name, "_id": doc_id}},
                    doc_body
                ])
            
            # Execute bulk operation
            if bulk_body:
                response = self._client.bulk(body=bulk_body, refresh=True)
                
                # Check for errors
                if response.get('errors'):
                    error_count = sum(1 for item in response['items'] 
                                    if 'error' in item.get('index', {}))
                    logger.warning(f"Bulk upsert had {error_count} errors")
                
                logger.info(f"Upserted {len(documents)} documents to {collection_name}")
                return not response.get('errors', False)
            
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
        """Search for similar documents using k-NN and/or text search"""
        try:
            if not self._client:
                await self.connect()
            
            search_body = {
                "size": limit,
                "_source": ["content", "metadata", "source", "source_type", "created_at"]
            }
            
            # Build query
            query_clauses = []
            
            # Vector similarity search
            if query_embedding:
                knn_query = {
                    "knn": {
                        "vector": {
                            "vector": query_embedding,
                            "k": limit * 2  # Get more candidates for reranking
                        }
                    }
                }
                search_body.update(knn_query)
            
            # Text search
            if query:
                text_query = {
                    "multi_match": {
                        "query": query,
                        "fields": ["content^2", "metadata.*"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }
                query_clauses.append(text_query)
            
            # Apply filters
            if filters:
                filter_clauses = []
                for field, value in filters.items():
                    if isinstance(value, list):
                        filter_clauses.append({"terms": {field: value}})
                    else:
                        filter_clauses.append({"term": {field: value}})
                
                if filter_clauses:
                    query_clauses.append({"bool": {"must": filter_clauses}})
            
            # Combine queries
            if query_clauses:
                if len(query_clauses) == 1:
                    search_body["query"] = query_clauses[0]
                else:
                    search_body["query"] = {
                        "bool": {
                            "should": query_clauses,
                            "minimum_should_match": 1
                        }
                    }
            
            # Execute search
            response = self._client.search(
                index=collection_name,
                body=search_body
            )
            
            # Process results
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                
                result = VectorSearchResult(
                    content=source.get('content', ''),
                    metadata=source.get('metadata', {}),
                    score=hit['_score'],
                    source=source.get('source'),
                    id=hit['_id']
                )
                results.append(result)
            
            logger.info(f"OpenSearch returned {len(results)} results for query in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed in OpenSearch index {collection_name}: {e}")
            return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """Delete specific documents from index"""
        try:
            if not self._client:
                await self.connect()
            
            # Prepare bulk delete operations
            bulk_body = []
            for doc_id in document_ids:
                bulk_body.append({"delete": {"_index": collection_name, "_id": doc_id}})
            
            if bulk_body:
                response = self._client.bulk(body=bulk_body, refresh=True)
                logger.info(f"Deleted {len(document_ids)} documents from {collection_name}")
                return not response.get('errors', False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about an index"""
        try:
            if not self._client:
                await self.connect()
            
            # Get index stats
            stats = self._client.indices.stats(index=collection_name)
            index_stats = stats['indices'][collection_name]
            
            # Get index settings and mappings
            settings = self._client.indices.get_settings(index=collection_name)
            mappings = self._client.indices.get_mapping(index=collection_name)
            
            return {
                "document_count": index_stats['total']['docs']['count'],
                "size_bytes": index_stats['total']['store']['size_in_bytes'],
                "shards": len(index_stats['shards']),
                "settings": settings[collection_name]['settings'],
                "mappings": mappings[collection_name]['mappings'],
                "health": "green"  # Simplified health status
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if OpenSearch cluster is healthy"""
        try:
            if not self._client:
                await self.connect()
            
            # Check cluster health
            health = self._client.cluster.health()
            status = health.get('status', 'red')
            
            if status == 'green':
                return True, f"Cluster healthy: {health.get('number_of_nodes', 0)} nodes"
            elif status == 'yellow':
                return True, f"Cluster functional with warnings: {status}"
            else:
                return False, f"Cluster unhealthy: {status}"
                
        except Exception as e:
            return False, f"Health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if OPENSEARCH_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.AWS_OPENSEARCH, AWSOpenSearchAdapter)
