"""
Vector Database Configuration
============================

Centralized configuration for all vector database connections (FAISS, Weaviate, etc.)
This module provides a single source of truth for vector database paths, 
configuration settings, and connection parameters.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

# Calculate absolute path to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

class VectorDBType(Enum):
    """Types of supported vector databases"""
    FAISS = "faiss"
    WEAVIATE = "weaviate"
    PINECONE = "pinecone"
    MILVUS = "milvus"
    CUSTOM = "custom"

class VectorDBConfig:
    """
    Centralized configuration for vector databases
    
    This class provides a single configuration point for all vector database
    settings, including paths, connection parameters, and feature flags.
    """
    
    def __init__(self):
        # Standard paths for different types of vector stores
        self.db_paths = {
            VectorDBType.FAISS: [
                PROJECT_ROOT / "data" / "faiss_index",
                PROJECT_ROOT / "data" / "indexes",
                PROJECT_ROOT / "vector_store",
                PROJECT_ROOT / "vectorstores",
            ],
            VectorDBType.WEAVIATE: [],
            VectorDBType.PINECONE: [],
            VectorDBType.MILVUS: [],
        }
        
        # Load environment variables for configuration
        self._load_from_env()
        
        # Default connection parameters
        self.connection_params = {
            VectorDBType.WEAVIATE: {
                "url": os.getenv("WEAVIATE_URL", "http://localhost:8080"),
                "api_key": os.getenv("WEAVIATE_API_KEY", ""),
                "timeout": int(os.getenv("WEAVIATE_TIMEOUT", "30")),
                "batch_size": int(os.getenv("WEAVIATE_BATCH_SIZE", "100")),
                "default_vectorizer": os.getenv("WEAVIATE_VECTORIZER", "text2vec-openai"),
                "enable_hybrid_search": os.getenv("WEAVIATE_HYBRID_SEARCH", "true").lower() == "true",
            },
            VectorDBType.PINECONE: {
                "api_key": os.getenv("PINECONE_API_KEY", ""),
                "environment": os.getenv("PINECONE_ENVIRONMENT", ""),
            },
            VectorDBType.MILVUS: {
                "host": os.getenv("MILVUS_HOST", "localhost"),
                "port": int(os.getenv("MILVUS_PORT", "19530")),
            }
        }
        
        # Feature flags
        self.features = {
            "enable_weaviate": os.getenv("ENABLE_WEAVIATE", "false").lower() == "true",
            "enable_pinecone": os.getenv("ENABLE_PINECONE", "false").lower() == "true",
            "enable_milvus": os.getenv("ENABLE_MILVUS", "false").lower() == "true",
            "use_unified_search": os.getenv("USE_UNIFIED_SEARCH", "true").lower() == "true",
        }
        
        # Set embedding model configuration
        self.embedding_model = os.getenv("DEFAULT_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        
        # Performance settings
        self.search_top_k = int(os.getenv("SEARCH_TOP_K", "5"))
        self.batch_size = int(os.getenv("BATCH_SIZE", "64"))
        self.use_gpu = os.getenv("USE_GPU_FOR_EMBEDDINGS", "false").lower() == "true"
        
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Check for custom FAISS paths
        custom_faiss_paths = os.getenv("FAISS_INDEX_PATHS")
        if custom_faiss_paths:
            # Parse comma-separated list of paths
            paths = [Path(p.strip()) for p in custom_faiss_paths.split(",")]
            # Validate paths exist
            valid_paths = [p for p in paths if p.exists()]
            if valid_paths:
                # Replace default paths with custom ones
                self.db_paths[VectorDBType.FAISS] = valid_paths
                logger.info(f"Using custom FAISS paths: {valid_paths}")
    
    def get_db_paths(self, db_type: VectorDBType) -> List[Path]:
        """Get all configured paths for the specified database type"""
        return self.db_paths.get(db_type, [])
    
    def get_primary_db_path(self, db_type: VectorDBType) -> Optional[Path]:
        """Get the primary (first) path for the specified database type"""
        paths = self.get_db_paths(db_type)
        return paths[0] if paths else None
    
    def get_connection_params(self, db_type: VectorDBType) -> Dict[str, Any]:
        """Get connection parameters for the specified database type"""
        return self.connection_params.get(db_type, {})
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(feature_name, False)
    
    def get_all_vector_db_paths(self) -> List[Path]:
        """Get all configured vector database paths"""
        all_paths = []
        for db_type in VectorDBType:
            all_paths.extend(self.get_db_paths(db_type))
        return all_paths
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding model configuration"""
        return {
            "model_name": self.embedding_model,
            "dimension": self.embedding_dimension,
            "use_gpu": self.use_gpu,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        return {
            "db_paths": {db_type.value: [str(p) for p in paths] 
                        for db_type, paths in self.db_paths.items()},
            "connection_params": self.connection_params,
            "features": self.features,
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dimension,
            "search_top_k": self.search_top_k,
            "batch_size": self.batch_size,
            "use_gpu": self.use_gpu,
        }

# Create a singleton instance
_config_instance = None

def get_vector_db_config() -> VectorDBConfig:
    """Get the singleton VectorDBConfig instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = VectorDBConfig()
    return _config_instance
