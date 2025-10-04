"""
Multi-Vector Storage Manager
Config-driven routing system for vector store selection with fallback mechanisms
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Make PyYAML optional to avoid hard import failures during UI import
try:
    import yaml  # type: ignore
except Exception:  # noqa: BLE001 - we want to catch any import issues
    yaml = None  # Fallback handled in _load_config

# Make python-dotenv optional
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # noqa: BLE001
    load_dotenv = None

from .multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType, 
    VectorStoreFactory, VectorStoreStatus
)

# Import adapters to register them
from . import adapters

logger = logging.getLogger(__name__)

@dataclass
class MultiVectorConfig:
    """Configuration for multi-vector storage system"""
    primary_stores: List[VectorStoreConfig]
    fallback_stores: List[VectorStoreConfig]
    parallel_ingestion: bool = False
    query_fallback: bool = True
    health_check_interval: int = 300  # seconds
    max_concurrent_operations: int = 5
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MultiVectorConfig':
        """Create config from dictionary"""
        primary_stores = [
            VectorStoreConfig(**store_config) 
            for store_config in config_dict.get('primary_stores', [])
        ]
        fallback_stores = [
            VectorStoreConfig(**store_config) 
            for store_config in config_dict.get('fallback_stores', [])
        ]
        
        return cls(
            primary_stores=primary_stores,
            fallback_stores=fallback_stores,
            parallel_ingestion=config_dict.get('parallel_ingestion', False),
            query_fallback=config_dict.get('query_fallback', True),
            health_check_interval=config_dict.get('health_check_interval', 300),
            max_concurrent_operations=config_dict.get('max_concurrent_operations', 5)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'primary_stores': [asdict(store) for store in self.primary_stores],
            'fallback_stores': [asdict(store) for store in self.fallback_stores],
            'parallel_ingestion': self.parallel_ingestion,
            'query_fallback': self.query_fallback,
            'health_check_interval': self.health_check_interval,
            'max_concurrent_operations': self.max_concurrent_operations
        }

class MultiVectorStorageManager:
    """
    Multi-vector storage manager with config-driven routing and fallback mechanisms
    """
    
    def __init__(self, config_path: Optional[str] = None, config: Optional[MultiVectorConfig] = None):
        self.config_path = config_path or "config/multi_vector_config.yaml"
        self.config = config
        
        self._primary_stores: Dict[str, BaseVectorStore] = {}
        self._fallback_stores: Dict[str, BaseVectorStore] = {}
        self._store_status: Dict[str, VectorStoreStatus] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        # Ensure environment variables from local config files are loaded early
        self._preload_env()
        
        # Load configuration
        if not self.config:
            self.config = self._load_config()
        
        # Initialize stores
        self._initialize_stores()
    
    def _load_config(self) -> MultiVectorConfig:
        """Load configuration from file or create default"""
        config_file = Path(self.config_path)
        # If default .yaml does not exist, try .yml automatically
        if not config_file.exists() and config_file.suffix.lower() == ".yaml":
            alt = config_file.with_suffix(".yml")
            if alt.exists():
                config_file = alt
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    if config_file.suffix.lower() in ['.yaml', '.yml']:
                        # If PyYAML is not available, gracefully fall back to defaults
                        if yaml is None:
                            logger.warning("PyYAML not available; using default multi-vector configuration")
                            return self._create_default_config()
                        config_dict = yaml.safe_load(f)
                    else:
                        config_dict = json.load(f)
                
                # Support both new (primary_stores/fallback_stores) and legacy (primary_store/vector_stores) schemas
                # Only treat as NEW schema if lists contain dict items with 'store_type' or 'connection_params'.
                if self._is_new_schema(config_dict):
                    return MultiVectorConfig.from_dict(config_dict)
                else:
                    converted = self._convert_legacy_config(config_dict)
                    return converted
            except Exception as e:
                logger.error(f"Failed to load config from {config_file}: {e}")
        
        # Create default configuration
        return self._create_default_config()

    def _preload_env(self) -> None:
        """Load environment variables from known locations so adapters can read them.
        Order: config/storage.env, config/weaviate.env, .env. Later files can override earlier values.
        """
        try:
            if not load_dotenv:
                return
            # The new order loads storage.env LAST, giving it the highest precedence.
            for p in [Path(".env"), Path("config/weaviate.env"), Path("config/storage.env")]:
                try:
                    if p.exists():
                        load_dotenv(dotenv_path=str(p), override=True)
                        logger.info(f"Loaded environment from {p}")
                except Exception as e:
                    logger.warning(f"Could not load environment from {p}: {e}")
        except Exception:
            # Do not block manager initialization on env loading errors
            pass

    def _is_new_schema(self, cfg: Dict[str, Any]) -> bool:
        """Heuristically detect if the loaded YAML uses the NEW schema.

        New schema expects 'primary_stores'/'fallback_stores' lists where each item
        is a dict containing keys like 'store_type' and optional 'connection_params'.
        Legacy schema often has 'primary_store' and 'fallback_stores' with 'type' strings/dicts
        and a separate 'vector_stores' mapping of provider params.
        """
        try:
            for key in ('primary_stores', 'fallback_stores'):
                if key in cfg:
                    items = cfg.get(key)
                    if isinstance(items, list) and items:
                        first = items[0]
                        if isinstance(first, dict) and (
                            'store_type' in first or 'connection_params' in first
                        ):
                            return True
                        # If dicts only have 'type' (legacy pattern) or items are strings, treat as legacy
            return False
        except Exception:
            return False

    def _expand_env(self, value: Any) -> Any:
        """Expand ${ENV_VAR} placeholders in strings; recurse for dicts/lists."""
        if isinstance(value, str):
            import re
            def repl(match):
                env_name = match.group(1)
                return os.getenv(env_name, "")
            return re.sub(r"\$\{([^}]+)\}", repl, value)
        elif isinstance(value, dict):
            return {k: self._expand_env(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._expand_env(v) for v in value]
        return value

    def _map_store_type(self, t: str) -> VectorStoreType:
        mapping = {
            'weaviate': VectorStoreType.WEAVIATE,
            'faiss': VectorStoreType.FAISS,
            'aws_opensearch': VectorStoreType.AWS_OPENSEARCH,
            'azure_ai_search': VectorStoreType.AZURE_AI_SEARCH,
            'vertex_ai': VectorStoreType.VERTEX_AI_MATCHING,
            'vertex_ai_matching': VectorStoreType.VERTEX_AI_MATCHING,
            'pinecone': VectorStoreType.PINECONE,
            'qdrant': VectorStoreType.QDRANT,
            'pgvector': VectorStoreType.PGVECTOR,
            'mock': VectorStoreType.MOCK,
        }
        lower = (t or '').lower()
        if lower not in mapping:
            raise ValueError(f"Unknown vector store type in config: {t}")
        return mapping[lower]

    def _map_store_params(self, store_type: VectorStoreType, params: Dict[str, Any]) -> Dict[str, Any]:
        """Map legacy YAML parameter keys to adapter-specific connection_params."""
        p = dict(params or {})
        # Expand env placeholders
        p = self._expand_env(p)
        if store_type == VectorStoreType.FAISS:
            # YAML uses index_path; adapter expects index_directory
            if 'index_directory' not in p and 'index_path' in p:
                p['index_directory'] = p.pop('index_path')
            # dimension -> vector_dimension
            if 'dimension' in p and 'vector_dimension' not in p:
                p['vector_dimension'] = p.pop('dimension')
        elif store_type == VectorStoreType.AWS_OPENSEARCH:
            # aws_region -> region
            if 'aws_region' in p and 'region' not in p:
                p['region'] = p.pop('aws_region')
            # aws_access_key_id -> aws_access_key
            if 'aws_access_key_id' in p and 'aws_access_key' not in p:
                p['aws_access_key'] = p.pop('aws_access_key_id')
            # aws_secret_access_key -> aws_secret_key
            if 'aws_secret_access_key' in p and 'aws_secret_key' not in p:
                p['aws_secret_key'] = p.pop('aws_secret_access_key')
        elif store_type == VectorStoreType.AZURE_AI_SEARCH:
            # Already aligned: endpoint, api_key
            pass
        elif store_type == VectorStoreType.WEAVIATE:
            # Ensure keys are url, api_key; allow openai_api_key passthrough
            pass
        elif store_type == VectorStoreType.VERTEX_AI_MATCHING:
            # Ensure required keys project_id, location, index_endpoint, credentials_path
            pass
        elif store_type == VectorStoreType.PINECONE:
            # Debug: Log what parameters are being passed to Pinecone
            logger.info(f"Pinecone config params: {p}")
            logger.info(f"API key present in params: {bool(p.get('api_key'))}")
            if p.get('api_key'):
                logger.info(f"API key starts with: {p.get('api_key')[:8]}...")
        # No remapping needed for qdrant, pgvector defaults
        return p

    def _convert_legacy_config(self, cfg: Dict[str, Any]) -> MultiVectorConfig:
        """Convert legacy YAML schema (primary_store, vector_stores, fallback_stores)
        into MultiVectorConfig with VectorStoreConfig entries.
        """
        try:
            primary = []
            fallbacks = []
            vector_stores_block = cfg.get('vector_stores', {}) or {}

            def make_vs_config(type_str: str, priority: int) -> Optional[VectorStoreConfig]:
                try:
                    vstype = self._map_store_type(type_str)
                    raw_params = vector_stores_block.get(type_str, {})
                    params = self._map_store_params(vstype, raw_params)
                    return VectorStoreConfig(store_type=vstype, connection_params=params, priority=priority)
                except Exception as e:
                    logger.error(f"Failed to map store '{type_str}': {e}")
                    return None

            # Primary
            if 'primary_store' in cfg and isinstance(cfg['primary_store'], dict):
                ptype = cfg['primary_store'].get('type')
                if ptype:
                    vs = make_vs_config(ptype, 1)
                    if vs:
                        primary.append(vs)

            # Fallbacks
            if 'fallback_stores' in cfg and isinstance(cfg['fallback_stores'], list):
                for i, item in enumerate(cfg['fallback_stores'], start=2):
                    if isinstance(item, dict):
                        ftype = item.get('type')
                    else:
                        ftype = str(item)
                    if ftype:
                        vs = make_vs_config(ftype, i)
                        if vs:
                            fallbacks.append(vs)

            # Ensure at least a mock fallback
            if not fallbacks:
                fallbacks.append(VectorStoreConfig(
                    store_type=VectorStoreType.MOCK,
                    connection_params={},
                    priority=99
                ))

            # Config flags
            parallel_enabled = bool(cfg.get('parallel_ingestion', {}).get('enabled', False))
            query_fallback = bool(cfg.get('query', {}).get('enable_fallback', True))
            health_interval = int(cfg.get('monitoring', {}).get('health_check_interval', 300))
            max_concurrent = int(cfg.get('performance', {}).get('max_concurrent_operations', 5))

            return MultiVectorConfig(
                primary_stores=primary,
                fallback_stores=fallbacks,
                parallel_ingestion=parallel_enabled,
                query_fallback=query_fallback,
                health_check_interval=health_interval,
                max_concurrent_operations=max_concurrent
            )
        except Exception as e:
            logger.error(f"Failed to convert legacy multi-vector config: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> MultiVectorConfig:
        """Create default multi-vector configuration"""
        # Try to detect existing vector stores
        primary_stores = []
        fallback_stores = []
        
        # Check for existing Weaviate configuration
        weaviate_url = os.getenv('WEAVIATE_URL')
        weaviate_api_key = os.getenv('WEAVIATE_API_KEY')
        if weaviate_url:
            primary_stores.append(VectorStoreConfig(
                store_type=VectorStoreType.WEAVIATE,
                connection_params={
                    'url': weaviate_url,
                    'api_key': weaviate_api_key,
                    'openai_api_key': os.getenv('OPENAI_API_KEY')
                },
                priority=1
            ))
        
        # Check for FAISS indexes
        faiss_dir = Path("data/faiss_index")
        if faiss_dir.exists() and any(faiss_dir.iterdir()):
            primary_stores.append(VectorStoreConfig(
                store_type=VectorStoreType.FAISS,
                connection_params={
                    'index_directory': str(faiss_dir),
                    'vector_dimension': 384
                },
                priority=2
            ))
        
        # Include common cloud vector stores as fallback so they appear in the UI
        fallback_stores.extend([
            VectorStoreConfig(
                store_type=VectorStoreType.AWS_OPENSEARCH,
                connection_params={},
                priority=90
            ),
            VectorStoreConfig(
                store_type=VectorStoreType.AZURE_AI_SEARCH,
                connection_params={},
                priority=91
            ),
            VectorStoreConfig(
                store_type=VectorStoreType.VERTEX_AI_MATCHING,
                connection_params={},
                priority=92
            ),
            VectorStoreConfig(
                store_type=VectorStoreType.PINECONE,
                connection_params={},
                priority=93
            ),
            VectorStoreConfig(
                store_type=VectorStoreType.QDRANT,
                connection_params={},
                priority=94
            ),
            VectorStoreConfig(
                store_type=VectorStoreType.PGVECTOR,
                connection_params={},
                priority=95
            ),
            # Always include mock as final fallback
            VectorStoreConfig(
                store_type=VectorStoreType.MOCK,
                connection_params={},
                priority=99
            ),
        ])
        
        return MultiVectorConfig(
            primary_stores=primary_stores,
            fallback_stores=fallback_stores,
            parallel_ingestion=False,
            query_fallback=True
        )
    
    def _initialize_stores(self):
        """Initialize all configured vector stores"""
        # Initialize primary stores
        for store_config in self.config.primary_stores:
            if not store_config.enabled:
                continue
                
            try:
                store = VectorStoreFactory.create(store_config)
                store_key = f"{store_config.store_type.value}_{store_config.priority}"
                self._primary_stores[store_key] = store
                
                # Test connection
                connected = store.connect_sync()
                collections = store.list_collections_sync() if connected else []
                error_msg = None
                if not connected:
                    # The error is now implicitly captured by the failed connect attempt.
                    # We no longer need a separate health_check call here.
                    error_msg = "Connection failed during initialization."
                
                self._store_status[store_key] = VectorStoreStatus(
                    store_type=store_config.store_type,
                    connected=connected,
                    collections=collections,
                    error=None if connected else error_msg
                )
                
                logger.info(f"Initialized {store_config.store_type.value} store: {connected}")
                
            except Exception as e:
                logger.error(f"Failed to initialize {store_config.store_type.value}: {e}")
                store_key = f"{store_config.store_type.value}_{store_config.priority}"
                self._store_status[store_key] = VectorStoreStatus(
                    store_type=store_config.store_type,
                    connected=False,
                    collections=[],
                    error=str(e)
                )
        
        # Initialize fallback stores
        for store_config in self.config.fallback_stores:
            if not store_config.enabled:
                continue
                
            try:
                store = VectorStoreFactory.create(store_config)
                store_key = f"fallback_{store_config.store_type.value}_{store_config.priority}"
                self._fallback_stores[store_key] = store
                
                # Test connection
                connected = store.connect_sync()
                collections = store.list_collections_sync() if connected else []
                error_msg = None
                if not connected:
                    # The error is now implicitly captured by the failed connect attempt.
                    # We no longer need a separate health_check call here.
                    error_msg = "Connection failed during initialization."

                self._store_status[store_key] = VectorStoreStatus(
                    store_type=store_config.store_type,
                    connected=connected,
                    collections=collections,
                    error=None if connected else error_msg
                )
                
                logger.info(f"Initialized fallback {store_config.store_type.value} store: {connected}")
                
            except Exception as e:
                logger.error(f"Failed to initialize fallback {store_config.store_type.value}: {e}")
                # Record status even on failure so UI can display the configured store
                store_key = f"fallback_{store_config.store_type.value}_{store_config.priority}"
                self._store_status[store_key] = VectorStoreStatus(
                    store_type=store_config.store_type,
                    connected=False,
                    collections=[],
                    error=str(e)
                )
    
    def get_available_stores(self) -> List[Dict[str, Any]]:
        """Get list of available vector stores with their status"""
        stores = []
        
        for store_key, status in self._store_status.items():
            store_info = {
                'key': store_key,
                'type': status.store_type.value,
                'connected': status.connected,
                'collections': status.collections,
                'collection_count': status.collection_count,
                'error': status.error,
                'is_fallback': store_key.startswith('fallback_')
            }
            stores.append(store_info)
        
        # Sort by priority (primary first, then fallback)
        stores.sort(key=lambda x: (x['is_fallback'], x['key']))
        return stores
    
    def get_primary_store(self) -> Optional[BaseVectorStore]:
        """Get the highest priority available primary store"""
        # Sort by priority (lower number = higher priority)
        sorted_stores = sorted(
            self._primary_stores.items(),
            key=lambda x: int(x[0].split('_')[-1])
        )
        
        for store_key, store in sorted_stores:
            if self._store_status.get(store_key, VectorStoreStatus(VectorStoreType.MOCK, False, [])).connected:
                return store
        
        return None
    
    def get_fallback_store(self) -> Optional[BaseVectorStore]:
        """Get the highest priority available fallback store"""
        # Sort by priority (lower number = higher priority)
        sorted_stores = sorted(
            self._fallback_stores.items(),
            key=lambda x: int(x[0].split('_')[-1])
        )
        
        for store_key, store in sorted_stores:
            if self._store_status.get(store_key, VectorStoreStatus(VectorStoreType.MOCK, False, [])).connected:
                return store
        
        return None
    
    def get_store_by_type(self, store_type: VectorStoreType) -> Optional[BaseVectorStore]:
        """Get a specific store by type"""
        # Check primary stores first
        for store_key, store in self._primary_stores.items():
            if store.store_type == store_type:
                status = self._store_status.get(store_key)
                # Special handling for Pinecone - always return if it's primary
                if store_type == VectorStoreType.PINECONE and not store_key.endswith('_fallback'):
                    logger.info(f"Returning primary Pinecone store: {store_key}")
                    return store
                elif status and status.connected:
                    return store
        
        # Check fallback stores
        for store_key, store in self._fallback_stores.items():
            if store.store_type == store_type:
                status = self._store_status.get(store_key)
                if status and status.connected:
                    return store
        
        return None
    
    async def create_collection(self, collection_name: str, store_type: Optional[VectorStoreType] = None, **kwargs) -> bool:
        """Create a collection in the specified store or primary store"""
        if store_type:
            store = self.get_store_by_type(store_type)
        else:
            store = self.get_primary_store()
        
        if not store:
            logger.error("No available vector store for collection creation")
            return False
        
        try:
            success = await store.create_collection(collection_name, **kwargs)
            if success:
                logger.info(f"Created collection '{collection_name}' in {store.store_type.value}")
            return success
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            return False
    
    async def list_collections(self, store_type: Optional[VectorStoreType] = None) -> List[str]:
        """List collections from specified store or all available stores"""
        if store_type:
            store = self.get_store_by_type(store_type)
            if store:
                return await store.list_collections()
            return []
        
        # Aggregate collections from all connected stores
        all_collections = set()
        
        for store in self._primary_stores.values():
            try:
                collections = await store.list_collections()
                all_collections.update(collections)
            except Exception as e:
                logger.error(f"Failed to list collections from {store.store_type.value}: {e}")
        
        return list(all_collections)
    
    async def delete_collection(self, collection_name: str, store_type: Optional[VectorStoreType] = None) -> bool:
        """Delete a collection from specified store or primary store"""
        if store_type:
            store = self.get_store_by_type(store_type)
        else:
            store = self.get_primary_store()
        
        if not store:
            logger.error("No available vector store for collection deletion")
            return False
        
        try:
            success = await store.delete_collection(collection_name)
            if success:
                logger.info(f"Deleted collection '{collection_name}' from {store.store_type.value}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
            return False
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None,
                             store_type: Optional[VectorStoreType] = None) -> bool:
        """Upsert documents to specified store or primary store"""
        if self.config.parallel_ingestion:
            return await self._parallel_upsert(collection_name, documents, embeddings, store_type)
        else:
            return await self._single_upsert(collection_name, documents, embeddings, store_type)
    
    async def _single_upsert(self, 
                           collection_name: str,
                           documents: List[Dict[str, Any]],
                           embeddings: Optional[List[List[float]]] = None,
                           store_type: Optional[VectorStoreType] = None) -> bool:
        """Upsert to a single store"""
        if store_type:
            store = self.get_store_by_type(store_type)
        else:
            store = self.get_primary_store()
        
        if not store:
            logger.error("No available vector store for document upsert")
            return False
        
        try:
            success = await store.upsert_documents(collection_name, documents, embeddings)
            if success:
                logger.info(f"Upserted {len(documents)} documents to '{collection_name}' in {store.store_type.value}")
            return success
        except Exception as e:
            logger.error(f"Failed to upsert documents to '{collection_name}': {e}")
            return False
    
    async def _parallel_upsert(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None,
                             store_type: Optional[VectorStoreType] = None) -> bool:
        """Upsert to multiple stores in parallel"""
        stores_to_use = []
        
        if store_type:
            store = self.get_store_by_type(store_type)
            if store:
                stores_to_use.append(store)
        else:
            # Use all connected primary stores
            for store in self._primary_stores.values():
                store_key = f"{store.store_type.value}_{getattr(store.config, 'priority', 1)}"
                if self._store_status.get(store_key, VectorStoreStatus(VectorStoreType.MOCK, False, [])).connected:
                    stores_to_use.append(store)
        
        if not stores_to_use:
            logger.error("No available vector stores for parallel upsert")
            return False
        
        # Execute upserts in parallel
        tasks = []
        for store in stores_to_use:
            task = store.upsert_documents(collection_name, documents, embeddings)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Parallel upsert failed for {stores_to_use[i].store_type.value}: {result}")
            elif result:
                success_count += 1
                logger.info(f"Parallel upsert succeeded for {stores_to_use[i].store_type.value}")
        
        return success_count > 0
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    store_type: Optional[VectorStoreType] = None,
                    **kwargs) -> List[VectorSearchResult]:
        """Search in specified store or with fallback"""
        if store_type:
            store = self.get_store_by_type(store_type)
            if store:
                return await store.search(collection_name, query, query_embedding, filters, limit, **kwargs)
            return []
        
        # Try primary store first
        primary_store = self.get_primary_store()
        if primary_store:
            try:
                results = await primary_store.search(collection_name, query, query_embedding, filters, limit, **kwargs)
                if results or not self.config.query_fallback:
                    return results
            except Exception as e:
                logger.error(f"Primary search failed in {primary_store.store_type.value}: {e}")
        
        # Fallback to fallback store if enabled and primary failed
        if self.config.query_fallback:
            fallback_store = self.get_fallback_store()
            if fallback_store:
                try:
                    results = await fallback_store.search(collection_name, query, query_embedding, filters, limit, **kwargs)
                    logger.info(f"Used fallback store {fallback_store.store_type.value} for search")
                    return results
                except Exception as e:
                    logger.error(f"Fallback search failed in {fallback_store.store_type.value}: {e}")
        
        return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str],
                             store_type: Optional[VectorStoreType] = None) -> bool:
        """Delete documents from specified store or primary store"""
        if store_type:
            store = self.get_store_by_type(store_type)
        else:
            store = self.get_primary_store()
        
        if not store:
            logger.error("No available vector store for document deletion")
            return False
        
        try:
            success = await store.delete_documents(collection_name, document_ids)
            if success:
                logger.info(f"Deleted {len(document_ids)} documents from '{collection_name}' in {store.store_type.value}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete documents from '{collection_name}': {e}")
            return False
    
    def collection_exists_sync(self, collection_name: str, store_type: VectorStoreType) -> bool:
        """Synchronously check if a collection exists using a direct REST API call to bypass SDK issues."""
        if store_type != VectorStoreType.WEAVIATE:
            # Fallback to original logic for other stores
            store = self.get_store_by_type(store_type)
            if store and hasattr(store, 'list_collections_sync'):
                return collection_name in store.list_collections_sync()
            return False

        # Direct REST API check for Weaviate
        try:
            import requests
            store = self.get_store_by_type(VectorStoreType.WEAVIATE)
            # The 'store' is the adapter itself.
            if not store or not hasattr(store, 'url') or not hasattr(store, 'api_key'):
                logger.error("Weaviate adapter is missing url or api_key for direct check.")
                return False

            url = f"{store.url}/v1/schema/{collection_name}"
            headers = {"Authorization": f"Bearer {store.api_key}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Direct REST check: Collection '{collection_name}' found.")
                return True
            elif response.status_code == 404:
                logger.warning(f"Direct REST check: Collection '{collection_name}' not found.")
                return False
            else:
                logger.error(f"Direct REST check failed with status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception during direct REST check for collection existence: {e}")
            return False

    async def get_collection_stats(self, collection_name: str, store_type: Optional[VectorStoreType] = None) -> Dict[str, Any]:
        """Get collection statistics from specified store or primary store"""
        if store_type:
            store = self.get_store_by_type(store_type)
        else:
            store = self.get_primary_store()
        
        if not store:
            return {"error": "No available vector store"}
        
        try:
            return await store.get_collection_stats(collection_name)
        except Exception as e:
            logger.error(f"Failed to get collection stats for '{collection_name}': {e}")
            return {"error": str(e)}
    
    async def health_check_all(self) -> Dict[str, Tuple[bool, str]]:
        """Perform health check on all stores"""
        health_results = {}
        
        # Check primary stores
        for store_key, store in self._primary_stores.items():
            try:
                health_results[store_key] = await store.health_check()
            except Exception as e:
                health_results[store_key] = (False, f"Health check failed: {e}")
        
        # Check fallback stores
        for store_key, store in self._fallback_stores.items():
            try:
                health_results[store_key] = await store.health_check()
            except Exception as e:
                health_results[store_key] = (False, f"Health check failed: {e}")
        
        return health_results
    
    def save_config(self, config_path: Optional[str] = None):
        """Save current configuration to file"""
        path = config_path or self.config_path
        config_file = Path(path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_file, 'w') as f:
                if config_file.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config.to_dict(), f, default_flow_style=False)
                else:
                    json.dump(self.config.to_dict(), f, indent=2)
            
            logger.info(f"Saved multi-vector config to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save config to {config_file}: {e}")
    
    def close(self):
        """Close all connections and cleanup resources"""
        # Close all stores
        for store in list(self._primary_stores.values()) + list(self._fallback_stores.values()):
            try:
                asyncio.run(store.disconnect())
            except Exception as e:
                logger.error(f"Error closing {store.store_type.value}: {e}")
        
        # shutdown executor
        self._executor.shutdown(wait=True)
        
        logger.info("Multi-vector storage manager closed")
    
    # Synchronous wrappers for common operations
    def create_collection_sync(self, collection_name: str, store_type: Optional[VectorStoreType] = None, **kwargs) -> bool:
        """Synchronous wrapper for create_collection"""
        return asyncio.run(self.create_collection(collection_name, store_type, **kwargs))
    
    def list_collections_sync(self, store_type: Optional[VectorStoreType] = None) -> List[str]:
        """Synchronous wrapper for list_collections"""
        return asyncio.run(self.list_collections(store_type))
    
    def get_collection_stats_sync(self, collection_name: str, store_type: Optional[VectorStoreType] = None) -> Dict[str, Any]:
        """Synchronous wrapper for get_collection_stats"""
        return asyncio.run(self.get_collection_stats(collection_name, store_type))
    
    def health_check_all_sync(self) -> Dict[str, Tuple[bool, str]]:
        """Synchronous wrapper for health_check_all"""
        return asyncio.run(self.health_check_all())
    
    def delete_collection_sync(self, collection_name: str, store_type: Optional[VectorStoreType] = None) -> bool:
        """Synchronous wrapper for delete_collection"""
        return asyncio.run(self.delete_collection(collection_name, store_type))

# Global instance for easy access
_global_manager: Optional[MultiVectorStorageManager] = None

def get_multi_vector_manager(config_path: Optional[str] = None) -> MultiVectorStorageManager:
    """Get or create global multi-vector storage manager"""
    global _global_manager
    
    if _global_manager is None:
        _global_manager = MultiVectorStorageManager(config_path)
    
    return _global_manager

def close_global_manager():
    """Close global multi-vector storage manager"""
    global _global_manager
    
    if _global_manager:
        _global_manager.close()
        _global_manager = None
