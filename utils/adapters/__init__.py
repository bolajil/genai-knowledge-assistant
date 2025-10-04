"""
Vector Store Adapters Package
Imports all available vector store adapters for the multi-vector storage system.

If an adapter's third-party dependency is missing, we register a graceful stub
so the VectorStoreFactory still recognizes the store type and the UI can display
it with a clear error. This avoids "Unknown vector store type" errors and makes
configuration guidance visible to the user.
"""

from typing import Dict
from ..multi_vector_storage_interface import (
    BaseVectorStore,
    VectorStoreConfig,
    VectorSearchResult,
    VectorStoreType,
    VectorStoreFactory,
)
import logging

logger = logging.getLogger(__name__)

# Try to import real adapters (they self-register if dependencies are available)
try:
    from .weaviate_adapter import WeaviateAdapter  # noqa: F401
except Exception:
    pass

try:
    from .faiss_adapter import FAISSAdapter  # noqa: F401
except Exception:
    pass

try:
    from .mock_adapter import MockAdapter  # noqa: F401
except Exception:
    pass

try:
    from .aws_opensearch_adapter import AWSOpenSearchAdapter  # noqa: F401
except Exception:
    pass

try:
    from .azure_ai_search_adapter import AzureAISearchAdapter  # noqa: F401
except Exception:
    pass

try:
    from .vertex_ai_adapter import VertexAIMatchingEngineAdapter  # noqa: F401
except Exception:
    pass

try:
    from .pinecone_adapter import PineconeAdapter  # noqa: F401
    logger.info("Pinecone adapter loaded successfully")
except Exception as e:
    # Surface adapter import issues clearly in logs (common cause in Streamlit runtime)
    logger.error(f"Pinecone adapter import failed: {e}")
    try:
        import pinecone as _pc  # type: ignore
        logger.info(
            "'pinecone' package importable; version=%s", getattr(_pc, "__version__", "unknown")
        )
    except Exception as pe:
        logger.error("'pinecone' package NOT importable in current runtime: %s", pe)
    import traceback as _tb
    logger.debug("Pinecone adapter import traceback:\n%s", _tb.format_exc())

try:
    from .qdrant_adapter import QdrantAdapter  # noqa: F401
except Exception:
    pass

try:
    from .pgvector_adapter import PGVectorAdapter  # noqa: F401
except Exception:
    pass

try:
    from .mongodb_adapter import MongoDBAdapter  # noqa: F401
except Exception:
    pass


# Register stub adapters for any store types that aren't registered yet
_STUB_REASONS: Dict[VectorStoreType, str] = {
    VectorStoreType.AWS_OPENSEARCH: "Missing dependency: opensearch-py (and optionally boto3, requests-aws4auth)",
    VectorStoreType.AZURE_AI_SEARCH: "Missing dependency: azure-search-documents (and azure-identity)",
    VectorStoreType.VERTEX_AI_MATCHING: "Missing dependency: google-cloud-aiplatform (and google-auth)",
    VectorStoreType.PINECONE: "Missing dependency: pinecone-client",
    VectorStoreType.QDRANT: "Missing dependency: qdrant-client",
    VectorStoreType.PGVECTOR: "Missing dependency: psycopg2-binary / asyncpg",
    VectorStoreType.MONGODB: "Missing dependency: pymongo",
}


class _MissingDependencyAdapter(BaseVectorStore):
    """Graceful stub when a real adapter cannot be registered.

    Shows up in the UI as a disconnected store with a clear error message.
    """

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        # Select reason per store type
        self._reason = _STUB_REASONS.get(
            config.store_type, "Adapter unavailable: missing dependency or registration"
        )

    async def connect(self) -> bool:
        self._connected = False
        return False

    async def disconnect(self) -> None:
        self._connected = False

    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        return False

    async def delete_collection(self, collection_name: str) -> bool:
        return False

    async def list_collections(self):  # -> List[str]
        return []

    async def upsert_documents(self, collection_name: str, documents, embeddings=None) -> bool:
        return False

    async def search(self, collection_name: str, query=None, query_embedding=None, filters=None, limit: int = 10, **kwargs):
        return []

    async def delete_documents(self, collection_name: str, document_ids) -> bool:
        return False

    async def get_collection_stats(self, collection_name: str):
        return {"error": self._reason}

    async def health_check(self):
        return False, self._reason


def _ensure_stub(store_type: VectorStoreType):
    try:
        if store_type not in VectorStoreFactory.get_available_types():
            VectorStoreFactory.register(store_type, _MissingDependencyAdapter)
            logger.info(f"Registered stub adapter for {store_type.value}")
    except Exception as e:
        logger.debug(f"Failed to register stub for {store_type.value}: {e}")


for _stype in _STUB_REASONS.keys():
    _ensure_stub(_stype)

# Report which adapters are currently registered to aid debugging in Streamlit logs
try:
    registered = [t.value for t in VectorStoreFactory.get_available_types()]
    logger.info("Registered vector adapters: %s", registered)
except Exception as _e:
    logger.debug("Could not list registered adapters: %s", _e)

