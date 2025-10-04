"""
Multi-Vector Storage Interface
Unified interface for all vector storage backends in VaultMind GenAI Knowledge Assistant
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class VectorStoreType(Enum):
    """Supported vector store types"""
    WEAVIATE = "weaviate"
    FAISS = "faiss"
    AWS_OPENSEARCH = "aws_opensearch"
    AZURE_AI_SEARCH = "azure_ai_search"
    VERTEX_AI_MATCHING = "vertex_ai_matching"
    PINECONE = "pinecone"
    QDRANT = "qdrant"
    PGVECTOR = "pgvector"
    MONGODB = "mongodb"
    MOCK = "mock"

@dataclass
class VectorSearchResult:
    """Standardized search result across all vector stores"""
    content: str
    metadata: Dict[str, Any]
    score: float
    source: Optional[str] = None
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
            "source": self.source,
            "id": self.id
        }

@dataclass
class VectorStoreConfig:
    """Configuration for vector store connections"""
    store_type: VectorStoreType
    connection_params: Dict[str, Any]
    enabled: bool = True
    priority: int = 1  # Lower number = higher priority
    fallback_enabled: bool = True
    
class BaseVectorStore(ABC):
    """Abstract base class for all vector store implementations"""
    
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self.store_type = config.store_type
        self._client = None
        self._connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the vector store"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the vector store"""
        pass
    
    @abstractmethod
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new collection/index"""
        pass
    
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection/index"""
        pass
    
    @abstractmethod
    async def list_collections(self) -> List[str]:
        """List all available collections/indexes"""
        pass
    
    @abstractmethod
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """Insert or update documents in the collection"""
        pass
    
    @abstractmethod
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """Delete specific documents from collection"""
        pass
    
    @abstractmethod
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Tuple[bool, str]:
        """Check if the vector store is healthy"""
        pass
    
    # Synchronous wrappers for backward compatibility
    def connect_sync(self) -> bool:
        """Synchronous version of connect"""
        import asyncio
        try:
            return asyncio.run(self.connect())
        except Exception as e:
            logger.error(f"Failed to connect to {self.store_type.value}: {e}")
            return False
    
    def search_sync(self, 
                   collection_name: str,
                   query: Optional[str] = None,
                   query_embedding: Optional[List[float]] = None,
                   filters: Optional[Dict[str, Any]] = None,
                   limit: int = 10,
                   **kwargs) -> List[VectorSearchResult]:
        """Synchronous version of search"""
        import asyncio
        try:
            return asyncio.run(self.search(
                collection_name, query, query_embedding, filters, limit, **kwargs
            ))
        except Exception as e:
            logger.error(f"Search failed in {self.store_type.value}: {e}")
            return []
    
    def list_collections_sync(self) -> List[str]:
        """Synchronous version of list_collections"""
        import asyncio
        try:
            return asyncio.run(self.list_collections())
        except Exception as e:
            logger.error(f"Failed to list collections in {self.store_type.value}: {e}")
            return []

class VectorStoreStatus:
    """Status information for vector stores"""
    
    def __init__(self, store_type: VectorStoreType, connected: bool, 
                 collections: List[str], error: Optional[str] = None):
        self.store_type = store_type
        self.connected = connected
        self.collections = collections
        self.error = error
        self.collection_count = len(collections)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "store_type": self.store_type.value,
            "connected": self.connected,
            "collections": self.collections,
            "collection_count": self.collection_count,
            "error": self.error
        }

class VectorStoreFactory:
    """Factory for creating vector store instances"""
    
    _registry: Dict[VectorStoreType, type] = {}
    
    @classmethod
    def register(cls, store_type: VectorStoreType, store_class: type):
        """Register a vector store implementation"""
        cls._registry[store_type] = store_class
        logger.info(f"Registered vector store: {store_type.value}")
    
    @classmethod
    def create(cls, config: VectorStoreConfig) -> BaseVectorStore:
        """Create a vector store instance"""
        if config.store_type not in cls._registry:
            raise ValueError(f"Unknown vector store type: {config.store_type.value}")
        
        store_class = cls._registry[config.store_type]
        return store_class(config)
    
    @classmethod
    def get_available_types(cls) -> List[VectorStoreType]:
        """Get list of available vector store types"""
        return list(cls._registry.keys())

# Utility functions for embedding operations
def normalize_embedding(embedding: List[float]) -> List[float]:
    """Normalize an embedding vector"""
    import math
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude == 0:
        return embedding
    return [x / magnitude for x in embedding]

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    import math
    
    # Normalize vectors
    vec1_norm = normalize_embedding(vec1)
    vec2_norm = normalize_embedding(vec2)
    
    # Calculate dot product
    dot_product = sum(a * b for a, b in zip(vec1_norm, vec2_norm))
    return max(-1.0, min(1.0, dot_product))  # Clamp to [-1, 1]

def batch_embeddings(texts: List[str], 
                    model_name: str = "all-MiniLM-L6-v2") -> List[List[float]]:
    """Generate embeddings for a batch of texts"""
    try:
        from sentence_transformers import SentenceTransformer
        # Prefer local models directory if present to avoid network fetch
        model_dir = Path("models")
        candidates: List[Path] = []
        if model_dir.exists():
            # Exact name directory (case-insensitive)
            for p in model_dir.iterdir():
                if p.is_dir() and p.name.lower() == model_name.lower():
                    candidates.append(p)
            # Common alias for MiniLM local folder naming
            aliases = []
            if model_name.lower() == "all-minilm-l6-v2":
                aliases = ["all-minLM-L6-v2", "all-MiniLM-L6-v2"]
            for alias in aliases:
                ap = model_dir / alias
                if ap.exists():
                    candidates.append(ap)
            # Direct path fallback
            direct = model_dir / model_name
            if direct.exists():
                candidates.append(direct)
        model = None
        for c in candidates:
            try:
                model = SentenceTransformer(str(c))
                break
            except Exception:
                continue
        if model is None:
            model = SentenceTransformer(model_name)
        embeddings = model.encode(texts)
        return [emb.tolist() for emb in embeddings]
    except ImportError:
        logger.error("sentence-transformers not available for embedding generation")
        return []
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return []
