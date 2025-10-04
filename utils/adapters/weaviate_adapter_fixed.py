"""
Enhanced Weaviate adapter with better search capabilities and debugging
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer

from ..multi_vector_storage_interface import VectorStoreAdapter, VectorSearchResult
from ..weaviate_manager import WeaviateManager

logger = logging.getLogger(__name__)

class WeaviateAdapter(VectorStoreAdapter):
    """Enhanced Weaviate adapter with better search and debugging"""
    
    def __init__(self, weaviate_manager: WeaviateManager):
        self._weaviate_manager = weaviate_manager
        self._embedding_model = None
        self._embedding_cache = {}
    
    def _get_embedding_model(self, model_name: str = "all-MiniLM-L6-v2"):
        """Get or initialize embedding model"""
        if self._embedding_model is None or self._embedding_model.model_name != model_name:
            try:
                self._embedding_model = SentenceTransformer(model_name)
                logger.info(f"Initialized embedding model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize embedding model {model_name}: {e}")
                return None
        return self._embedding_model
    
    def _generate_embedding(self, text: str, model_name: str = "all-MiniLM-L6-v2") -> Optional[List[float]]:
        """Generate embedding for text"""
        cache_key = f"{model_name}:{text[:100]}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        model = self._get_embedding_model(model_name)
        if model:
            try:
                embedding = model.encode(text).tolist()
                self._embedding_cache[cache_key] = embedding
                return embedding
            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")
        return None
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Enhanced search with multiple strategies and better error handling"""
        try:
            # First check if collection exists and has data
            client = self._weaviate_manager.client
            actual_name = self._weaviate_manager._resolve_collection_name(collection_name)
            
            # Check if collection exists
            all_collections = client.collections.list_all()
            if actual_name not in all_collections:
                logger.warning(f"Collection {actual_name} does not exist in Weaviate")
                return []
            
            collection = client.collections.get(actual_name)
            
            # Check if collection has any objects
            try:
                count_response = collection.aggregate.over_all(total_count=True)
                doc_count = count_response.total_count if hasattr(count_response, 'total_count') else 0
                logger.info(f"Collection {actual_name} has {doc_count} documents")
                
                if doc_count == 0:
                    logger.warning(f"Collection {actual_name} is empty - no documents to search")
                    return []
            except Exception as e:
                logger.error(f"Failed to get document count for {actual_name}: {e}")
            
            results = []
            
            # Strategy 1: Try hybrid search if available
            if query and hasattr(collection.query, 'hybrid'):
                try:
                    # Generate embedding if not provided
                    if not query_embedding:
                        query_embedding = self._generate_embedding(query)
                    
                    if query_embedding:
                        # Hybrid search combines BM25 and vector search
                        response = collection.query.hybrid(
                            query=query,
                            vector=query_embedding,
                            limit=limit,
                            alpha=0.5,  # Balance between BM25 and vector (0.5 = equal weight)
                            return_metadata=['score', 'explain_score']
                        )
                        
                        for obj in response.objects:
                            result = self._convert_to_search_result(obj)
                            results.append(result)
                        
                        if results:
                            logger.info(f"Hybrid search returned {len(results)} results for '{query}' in {actual_name}")
                            return results
                except Exception as e:
                    logger.warning(f"Hybrid search failed: {e}, trying alternative methods")
            
            # Strategy 2: Try vector search with embedding
            if query_embedding or query:
                try:
                    # Generate embedding if needed
                    if not query_embedding and query:
                        query_embedding = self._generate_embedding(query)
                    
                    if query_embedding:
                        response = collection.query.near_vector(
                            near_vector=query_embedding,
                            limit=limit,
                            return_metadata=['score', 'distance']
                        )
                        
                        for obj in response.objects:
                            result = self._convert_to_search_result(obj)
                            results.append(result)
                        
                        if results:
                            logger.info(f"Vector search returned {len(results)} results in {actual_name}")
                            return results
                except Exception as e:
                    logger.warning(f"Vector search failed: {e}")
            
            # Strategy 3: Try BM25 text search
            if query:
                try:
                    response = collection.query.bm25(
                        query=query,
                        limit=limit,
                        return_metadata=['score']
                    )
                    
                    for obj in response.objects:
                        result = self._convert_to_search_result(obj)
                        results.append(result)
                    
                    if results:
                        logger.info(f"BM25 search returned {len(results)} results for '{query}' in {actual_name}")
                        return results
                except Exception as e:
                    logger.warning(f"BM25 search failed: {e}")
            
            # Strategy 4: Fallback to fetching all objects (last resort)
            if not results and not query and not query_embedding:
                try:
                    response = collection.query.fetch_objects(limit=limit)
                    for obj in response.objects:
                        result = self._convert_to_search_result(obj)
                        results.append(result)
                    logger.info(f"Fetch all returned {len(results)} results in {actual_name}")
                except Exception as e:
                    logger.error(f"Fetch all failed: {e}")
            
            if not results:
                logger.warning(f"No results found in {actual_name} despite trying multiple search strategies")
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed in Weaviate collection {collection_name}: {e}")
            return []
    
    def _convert_to_search_result(self, obj) -> VectorSearchResult:
        """Convert Weaviate object to VectorSearchResult"""
        try:
            # Extract properties
            properties = obj.properties if hasattr(obj, 'properties') else {}
            
            # Extract content - try multiple possible field names
            content = properties.get('content') or properties.get('text') or properties.get('page_content') or ''
            
            # Extract metadata
            metadata = properties.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    import json
                    metadata = json.loads(metadata)
                except:
                    metadata = {'raw_metadata': metadata}
            
            # Extract source
            source = properties.get('source') or metadata.get('source') or 'Unknown'
            
            # Extract score (Weaviate uses distance/score in metadata)
            score = 0.0
            if hasattr(obj, 'metadata'):
                if hasattr(obj.metadata, 'score'):
                    score = float(obj.metadata.score)
                elif hasattr(obj.metadata, 'distance'):
                    # Convert distance to similarity score (smaller distance = higher score)
                    score = 1.0 / (1.0 + float(obj.metadata.distance))
                elif hasattr(obj.metadata, 'certainty'):
                    score = float(obj.metadata.certainty)
            
            # Extract ID
            doc_id = str(obj.uuid) if hasattr(obj, 'uuid') else None
            
            return VectorSearchResult(
                content=content,
                metadata=metadata,
                score=score,
                source=source,
                id=doc_id
            )
        except Exception as e:
            logger.error(f"Failed to convert Weaviate object to search result: {e}")
            return VectorSearchResult(
                content="Error processing result",
                metadata={},
                score=0.0,
                source="Unknown",
                id=None
            )
    
    async def upsert_documents(self, 
                              collection_name: str,
                              documents: List[Dict[str, Any]],
                              embeddings: Optional[List[List[float]]] = None) -> bool:
        """Upsert documents to Weaviate collection"""
        try:
            # Use existing implementation but add embedding generation if needed
            if hasattr(self._weaviate_manager, 'add_documents'):
                # Generate embeddings if not provided
                if not embeddings and documents:
                    model = self._get_embedding_model()
                    if model:
                        texts = [doc.get('content', '') for doc in documents]
                        embeddings = [model.encode(text).tolist() for text in texts]
                
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
                
                objects = []
                for i, doc in enumerate(documents):
                    obj = {
                        "content": doc.get("content", ""),
                        "source": doc.get("source", "Unknown"),
                        "metadata": doc.get("metadata", {})
                    }
                    if embeddings and i < len(embeddings):
                        obj["vector"] = embeddings[i]
                    objects.append(obj)
                
                # Batch insert
                with collection.batch.dynamic() as batch:
                    for obj in objects:
                        batch.add_object(properties=obj)
                
                logger.info(f"Upserted {len(documents)} documents to Weaviate collection {collection_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to upsert documents to Weaviate collection {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all Weaviate collections"""
        try:
            return self._weaviate_manager.list_collections()
        except Exception as e:
            logger.error(f"Failed to list Weaviate collections: {e}")
            return []
    
    async def create_collection(self, 
                              collection_name: str,
                              dimension: Optional[int] = None,
                              **kwargs) -> bool:
        """Create a new Weaviate collection"""
        try:
            return self._weaviate_manager.create_collection(
                collection_name=collection_name,
                dimension=dimension or 384  # Default to MiniLM dimension
            )
        except Exception as e:
            logger.error(f"Failed to create Weaviate collection {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a Weaviate collection"""
        try:
            return self._weaviate_manager.delete_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to delete Weaviate collection {collection_name}: {e}")
            return False
    
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
            
            # Check if collection exists
            all_collections = client.collections.list_all()
            if actual_name not in all_collections:
                return {
                    "error": f"Collection {actual_name} does not exist",
                    "document_count": 0
                }
            
            collection = client.collections.get(actual_name)
            
            # Get collection info
            config = collection.config.get()
            
            # Count objects
            response = collection.aggregate.over_all(total_count=True)
            doc_count = response.total_count if hasattr(response, 'total_count') else 0
            
            # Get sample for dimension
            dimension = None
            if doc_count > 0:
                try:
                    sample = collection.query.fetch_objects(limit=1, include_vector=True)
                    if sample.objects and hasattr(sample.objects[0], 'vector'):
                        dimension = len(sample.objects[0].vector)
                except:
                    pass
            
            return {
                "document_count": doc_count,
                "collection_name": actual_name,
                "vector_dimension": dimension or 384,
                "vectorizer": str(config.vectorizer_config) if config.vectorizer_config else "none",
                "properties": len(config.properties) if config.properties else 0,
                "health": "green" if doc_count > 0 else "yellow"
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for Weaviate collection {collection_name}: {e}")
            return {"error": str(e), "document_count": 0}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check Weaviate health"""
        try:
            if self._weaviate_manager.client.is_ready():
                collections = self._weaviate_manager.list_collections()
                return True, f"Connected - {len(collections)} collections available"
            else:
                return False, "Weaviate client not ready"
        except Exception as e:
            return False, f"Health check failed: {str(e)}"
