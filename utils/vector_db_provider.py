"""
Vector Database Provider
=======================

A centralized provider for vector database access across the application.
This module provides a unified interface for interacting with different vector
database backends (FAISS, Weaviate, etc.) with consistent error handling,
connection pooling, and monitoring.
"""

import os
import logging
import time
import faiss
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import pickle
from datetime import datetime
from functools import lru_cache
from sentence_transformers import SentenceTransformer
import traceback

# Import the centralized configuration
from config.vector_db_config import get_vector_db_config, VectorDBType

# Configure logging
logger = logging.getLogger(__name__)

class VectorDBProvider:
    """
    Centralized provider for vector database access
    
    This class provides a unified interface for vector database operations
    with consistent error handling, connection management, and monitoring.
    """
    
    def __init__(self):
        """Initialize the vector database provider"""
        self.config = get_vector_db_config()
        self.embedding_model = None
        self._initialize_embedding_model()
        
        # Track database connections and status
        self._connections = {}
        self._last_error = None
        self._available_indexes = None
        self._last_refresh = None
        
        # Initialize metrics for monitoring
        self._metrics = {
            "queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "query_time_total": 0,
            "last_query_time": 0,
        }
    
    def _initialize_embedding_model(self):
        """Initialize the sentence transformer embedding model"""
        try:
            embedding_config = self.config.get_embedding_config()
            self.embedding_model = SentenceTransformer(embedding_config["model_name"])
            logger.info(f"Initialized embedding model: {embedding_config['model_name']}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self._last_error = str(e)
    
    def get_available_indexes(self, force_refresh=False) -> List[str]:
        """
        Get all available vector indexes across all configured database types
        
        Args:
            force_refresh: If True, force a refresh of the available indexes
            
        Returns:
            List of available index names
        """
        # Return cached result if available and not forcing refresh
        if not force_refresh and self._available_indexes is not None and self._last_refresh is not None:
            # Only use cache if it's less than 5 minutes old
            if (datetime.now() - self._last_refresh).total_seconds() < 300:
                return self._available_indexes
        
        indexes = []
        
        # Check FAISS indexes
        indexes.extend(self._discover_faiss_indexes())
        
        # Check Weaviate collections if enabled
        if self.config.is_feature_enabled("enable_weaviate"):
            indexes.extend(self._discover_weaviate_indexes())
        
        # Check other database types as needed
        
        # Cache the results
        self._available_indexes = sorted(list(set(indexes)))  # Remove duplicates
        self._last_refresh = datetime.now()
        
        return self._available_indexes
    
    def _discover_faiss_indexes(self) -> List[str]:
        """Discover all available FAISS indexes"""
        indexes = []
        faiss_paths = self.config.get_db_paths(VectorDBType.FAISS)
        
        for path in faiss_paths:
            if not path.exists() or not path.is_dir():
                continue

            for item in path.iterdir():
                if item.is_dir():
                    # Check if it's a valid FAISS index (contains index.faiss and at least one .pkl)
                    has_faiss = (item / "index.faiss").exists()
                    has_metadata = any(item.glob("*.pkl"))
                    if has_faiss and has_metadata:
                        indexes.append(item.name)
        
        logger.info(f"Discovered {len(indexes)} FAISS indexes")
        return indexes
    
    def _discover_weaviate_indexes(self) -> List[str]:
        """Discover all available Weaviate collections (indexes)"""
        try:
            # Prefer centralized manager which includes prefix discovery and fallbacks
            from utils.weaviate_manager import get_weaviate_manager  # type: ignore

            mgr = get_weaviate_manager()
            names = mgr.list_collections()
            logger.info(f"Discovered {len(names)} Weaviate collections via WeaviateManager")
            return names
        except ImportError:
            logger.warning("Weaviate integration not available")
            return []
        except Exception as e:
            logger.error(f"Error discovering Weaviate collections: {e}")
            self._last_error = str(e)
            return []
    
    def find_index_path(self, index_name: str) -> Optional[Path]:
        """
        Find the path for a specific FAISS index
        
        Args:
            index_name: Name of the index to find
            
        Returns:
            Path to the index directory or None if not found
        """
        faiss_paths = self.config.get_db_paths(VectorDBType.FAISS)
        
        for base_path in faiss_paths:
            index_path = base_path / index_name
            if index_path.exists() and index_path.is_dir():
                has_faiss = (index_path / "index.faiss").exists()
                has_metadata = any(index_path.glob("*.pkl"))
                if has_faiss and has_metadata:
                    return index_path
    
        return None
    
    @lru_cache(maxsize=16)
    def _load_faiss_index(self, index_path: Path) -> Tuple[Any, Dict[str, Any]]:
        """
        Load a FAISS index and its metadata from disk with robust fallbacks.
        
        Args:
            index_path: Directory containing index.faiss and metadata pickle.
        
        Returns:
            Tuple of (faiss_index, metadata_dict)
        """
        try:
            # Expected files
            faiss_file = index_path / "index.faiss"
            # Prefer common names but accept any .pkl present
            preferred = ["index.pkl", "documents.pkl", "metadata.pkl"]
            metadata_candidates = [index_path / name for name in preferred]
            # If none of the preferred names exist, fallback to the first .pkl file
            metadata_file = next((c for c in metadata_candidates if c.exists()), None)
            if not metadata_file:
                any_pkl = list(index_path.glob("*.pkl"))
                metadata_file = any_pkl[0] if any_pkl else None
            
            if not faiss_file.exists():
                raise FileNotFoundError(f"FAISS index file not found at {faiss_file}")
            if not metadata_file:
                raise FileNotFoundError(f"No metadata file found in {index_path}")
            
            logger.info(f"Loading FAISS index from {faiss_file}")
            faiss_index = faiss.read_index(str(faiss_file))
            
            logger.info(f"Loading metadata from {metadata_file}")
            with open(metadata_file, "rb") as f:
                metadata = pickle.load(f)
            
            # Handle tuple-based LangChain FAISS pickles: (docstore, index_to_docstore_id)
            try:
                if isinstance(metadata, tuple) and len(metadata) == 2:
                    docstore, idx_map = metadata
                    if isinstance(idx_map, dict) and idx_map:
                        def _get_doc_dict(ds: Any) -> Optional[Dict[str, Any]]:
                            for attr in ("_dict", "dict", "docs", "_docs", "store", "_store"):
                                d = getattr(ds, attr, None)
                                if isinstance(d, dict):
                                    return d
                            return None
                        doc_dict = _get_doc_dict(docstore)
                        ordered = sorted(
                            [
                                (int(k) if isinstance(k, (int, str)) and str(k).isdigit() else k, v)
                                for k, v in idx_map.items()
                            ],
                            key=lambda x: int(x[0]) if isinstance(x[0], (int, str)) and str(x[0]).isdigit() else 0,
                        )
                        docs: List[str] = []
                        metas: List[Dict[str, Any]] = []
                        ids: List[str] = []
                        for _, uid in ordered:
                            ids.append(uid)
                            doc_obj = None
                            try:
                                if isinstance(doc_dict, dict) and uid in doc_dict:
                                    doc_obj = doc_dict.get(uid)
                                elif hasattr(docstore, "search"):
                                    try:
                                        doc_obj = docstore.search(uid)
                                    except Exception:
                                        doc_obj = None
                            except Exception:
                                doc_obj = None
                            if doc_obj is not None:
                                content = getattr(doc_obj, "page_content", "")
                                meta_obj = getattr(doc_obj, "metadata", {}) or {}
                                if not isinstance(meta_obj, dict):
                                    try:
                                        meta_obj = dict(meta_obj)
                                    except Exception:
                                        meta_obj = {}
                            else:
                                content = ""
                                meta_obj = {}
                            docs.append(content if isinstance(content, str) else str(content))
                            metas.append(meta_obj)
                        metadata = {"documents": docs, "metadatas": metas, "ids": ids}
            except Exception as tuple_recon_err:
                logger.debug(f"Failed tuple-based FAISS metadata reconstruction: {tuple_recon_err}")
            
            # If this is a LangChain FAISS pickle, reconstruct documents from the docstore
            try:
                if isinstance(metadata, dict) and ("docstore" in metadata) and ("index_to_docstore_id" in metadata):
                    docstore = metadata.get("docstore")
                    idx_map = metadata.get("index_to_docstore_id") or {}
                    if isinstance(idx_map, dict) and len(idx_map) > 0:
                        def _get_doc_dict(ds: Any) -> Optional[Dict[str, Any]]:
                            for attr in ("_dict", "dict", "docs", "_docs", "store", "_store"):
                                d = getattr(ds, attr, None)
                                if isinstance(d, dict):
                                    return d
                            return None
                        doc_dict = _get_doc_dict(docstore)
                        # Build ordered lists aligned to index positions
                        ordered = sorted(
                            [(int(k), v) for k, v in idx_map.items()], key=lambda x: x[0]
                        )
                        docs: List[str] = []
                        metas: List[Dict[str, Any]] = []
                        ids: List[str] = []
                        for _, uid in ordered:
                            ids.append(uid)
                            doc_obj = None
                            try:
                                if isinstance(doc_dict, dict) and uid in doc_dict:
                                    doc_obj = doc_dict.get(uid)
                                elif hasattr(docstore, "search"):
                                    try:
                                        doc_obj = docstore.search(uid)
                                    except Exception:
                                        doc_obj = None
                            except Exception:
                                doc_obj = None
                            # Extract page_content and metadata from LangChain Document
                            if doc_obj is not None:
                                content = getattr(doc_obj, "page_content", "")
                                meta_obj = getattr(doc_obj, "metadata", {}) or {}
                                if not isinstance(meta_obj, dict):
                                    try:
                                        meta_obj = dict(meta_obj)
                                    except Exception:
                                        meta_obj = {}
                            else:
                                content = ""
                                meta_obj = {}
                            docs.append(content if isinstance(content, str) else str(content))
                            metas.append(meta_obj)
                        metadata = {"documents": docs, "metadatas": metas, "ids": ids}
            except Exception as recon_err:
                logger.debug(f"Failed to reconstruct documents from LangChain FAISS pickle: {recon_err}")
            
            # Handle mis-saved metadata where 'documents' contains a single tuple (docstore, index_to_docstore_id)
            try:
                if isinstance(metadata, dict) and isinstance(metadata.get("documents"), list) and metadata["documents"]:
                    first_doc = metadata["documents"][0]
                    if isinstance(first_doc, tuple) and len(first_doc) == 2:
                        docstore, idx_map = first_doc
                        if isinstance(idx_map, dict):
                            def _get_doc_dict(ds: Any) -> Optional[Dict[str, Any]]:
                                for attr in ("_dict", "dict", "docs", "_docs", "store", "_store"):
                                    d = getattr(ds, attr, None)
                                    if isinstance(d, dict):
                                        return d
                                return None
                            doc_dict = _get_doc_dict(docstore)
                            ordered = sorted(
                                [
                                    (int(k) if isinstance(k, (int, str)) and str(k).isdigit() else k, v)
                                    for k, v in idx_map.items()
                                ],
                                key=lambda x: int(x[0]) if isinstance(x[0], (int, str)) and str(x[0]).isdigit() else 0,
                            )
                            docs: List[str] = []
                            metas: List[Dict[str, Any]] = []
                            ids: List[str] = []
                            for _, uid in ordered:
                                ids.append(uid)
                                doc_obj = None
                                try:
                                    if isinstance(doc_dict, dict) and uid in doc_dict:
                                        doc_obj = doc_dict.get(uid)
                                    elif hasattr(docstore, "search"):
                                        try:
                                            doc_obj = docstore.search(uid)
                                        except Exception:
                                            doc_obj = None
                                except Exception:
                                    doc_obj = None
                                if doc_obj is not None:
                                    content = getattr(doc_obj, "page_content", "")
                                    meta_obj = getattr(doc_obj, "metadata", {}) or {}
                                    if not isinstance(meta_obj, dict):
                                        try:
                                            meta_obj = dict(meta_obj)
                                        except Exception:
                                            meta_obj = {}
                                else:
                                    content = ""
                                    meta_obj = {}
                                docs.append(content if isinstance(content, str) else str(content))
                                metas.append(meta_obj)
                            metadata = {"documents": docs, "metadatas": metas, "ids": ids}
            except Exception as recon2_err:
                logger.debug(f"Failed to reconstruct from tuple-in-documents format: {recon2_err}")
            
            # Normalize metadata structure
            if isinstance(metadata, dict):
                # Map alternate keys
                if "texts" in metadata and "documents" not in metadata:
                    metadata["documents"] = metadata.get("texts", [])
                if "metadatas" not in metadata and "metadata" in metadata and isinstance(metadata["metadata"], list):
                    metadata["metadatas"] = metadata["metadata"]
                if "documents" not in metadata:
                    metadata["documents"] = []
                if "metadatas" not in metadata:
                    metadata["metadatas"] = [{} for _ in range(len(metadata.get("documents", [])))]
            else:
                # Convert non-dict metadata to a standard dict
                if isinstance(metadata, list):
                    metadata = {"documents": metadata, "metadatas": [{} for _ in metadata]}
                else:
                    metadata = {"documents": [str(metadata)], "metadatas": [{}]}
            
            # Validate sizes
            index_size = getattr(faiss_index, "ntotal", 0)
            doc_size = len(metadata.get("documents", []))
            if index_size and doc_size and doc_size != index_size:
                logger.warning(f"Index vectors ({index_size}) != documents ({doc_size}) in {index_path}")
            
            logger.info(f"Successfully loaded FAISS index with {index_size} vectors")
            return faiss_index, metadata
        except Exception as e:
            logger.error(f"Error loading FAISS index at {index_path}: {e}")
            logger.debug("Traceback:\n" + traceback.format_exc())
            # Graceful fallback to empty structures
            empty_index = faiss.IndexFlatL2(1)
            empty_metadata: Dict[str, Any] = {"documents": [], "metadatas": []}
            return empty_index, empty_metadata
    
    def get_vector_db_status(self) -> Tuple[str, str]:
        """
        Get the current status of the vector database provider
        
        Returns:
            Tuple of (status, message)
            Status can be: "Ready", "Error", "Warning", "Initializing"
        """
        try:
            # Check if we have any available indexes
            if not self._available_indexes:
                self.get_available_indexes(force_refresh=True)
            
            if not self._available_indexes:
                # Check if FAISS files exist in the expected locations
                faiss_paths = self.config.get_db_paths(VectorDBType.FAISS)
                found_files = []
                
                for path in faiss_paths:
                    if path.exists():
                        faiss_files = list(path.glob("*.faiss"))
                        pkl_files = list(path.glob("*.pkl"))
                        found_files.extend(faiss_files)
                        found_files.extend(pkl_files)
                
                if found_files:
                    # We have files but they're not being recognized as indexes
                    return "Warning", f"Found {len(found_files)} vector files but no valid indexes detected"
                else:
                    return "Error", "No vector databases found"
            
            # Check if embedding model is loaded
            if not self.embedding_model:
                return "Warning", "Embedding model not loaded"
            
            # Check database connections
            connection_issues = []
            working_indexes = 0
            
            for db_type, paths in self.config.db_paths.items():
                if db_type == VectorDBType.FAISS:
                    for path in paths:
                        if path.exists():
                            # Check if we can load a FAISS index
                            try:
                                faiss_files = list(path.glob("*.faiss"))
                                if faiss_files:
                                    # Try to load one index to verify it works
                                    test_index = faiss.read_index(str(faiss_files[0]))
                                    if test_index.ntotal == 0:
                                        connection_issues.append(f"Empty FAISS index: {faiss_files[0]}")
                                    else:
                                        working_indexes += 1
                                else:
                                    connection_issues.append(f"No FAISS files found in {path}")
                            except Exception as e:
                                connection_issues.append(f"FAISS error in {path}: {str(e)}")
            
            if working_indexes == 0:
                return "Error", "No working vector indexes found"
            
            if connection_issues:
                return "Warning", f"Vector DB partially ready ({working_indexes} working). Issues: {'; '.join(connection_issues[:2])}"
            
            return "Ready", f"Vector database ready with {working_indexes} working indexes"
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error checking vector DB status: {e}")
            return "Error", f"Status check failed: {str(e)}"
            raise
    
    def search_index(self, query: str, index_name: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Search a vector index using the specified query
        
        Args:
            query: The query string to search for
            index_name: Name of the index to search
            top_k: Number of results to return (default: from config)
            
        Returns:
            List of search results, each containing content, source, and score
        """
        # Use configured top_k if not specified
        if top_k is None:
            top_k = self.config.search_top_k
        
        # Track metrics
        start_time = time.time()
        self._metrics["queries"] += 1
        
        try:
            # Check if this is a Weaviate collection
            if self.config.is_feature_enabled("enable_weaviate") and index_name in self._discover_weaviate_indexes():
                results = self._search_weaviate(query, index_name, top_k)
            else:
                # Default to FAISS
                results = self._search_faiss(query, index_name, top_k)
            
            # Update metrics for successful query
            self._metrics["successful_queries"] += 1
            query_time = time.time() - start_time
            self._metrics["query_time_total"] += query_time
            self._metrics["last_query_time"] = query_time
            
            return results
            
        except Exception as e:
            # Update metrics for failed query
            self._metrics["failed_queries"] += 1
            query_time = time.time() - start_time
            self._metrics["last_query_time"] = query_time
            
            logger.error(f"Error searching index {index_name}: {e}")
            self._last_error = str(e)
            
            # Return empty results on error
            return []
    
    def _search_faiss(self, query: str, index_name: str, top_k: int) -> List[Dict[str, Any]]:
        """Search a FAISS index"""
        # Find the index path
        index_path = self.find_index_path(index_name)
        if not index_path:
            raise ValueError(f"Index '{index_name}' not found")
        
        # Load the index and metadata
        faiss_index, metadata = self._load_faiss_index(index_path)
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0]
        # Ensure proper dtype and shape
        query_embedding = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        
        # Adjust dimensionality to match index if needed
        index_dim = faiss_index.d if hasattr(faiss_index, "d") else query_embedding.shape[1]
        q_dim = query_embedding.shape[1]
        if q_dim != index_dim:
            if q_dim > index_dim:
                logger.warning(f"Truncating query embedding from dim {q_dim} to index dim {index_dim}")
                query_embedding = query_embedding[:, :index_dim]
            else:
                logger.warning(f"Padding query embedding from dim {q_dim} to index dim {index_dim}")
                pad = np.zeros((1, index_dim - q_dim), dtype=np.float32)
                query_embedding = np.hstack([query_embedding, pad])
        
        # Search the index
        distances, indices = faiss_index.search(query_embedding, top_k)
        
        # Format results
        results = []
        for i, doc_idx in enumerate(indices[0]):
            if doc_idx != -1:  # -1 indicates no more results
                # Get the document from metadata
                doc_id: Optional[str] = None
                if isinstance(metadata.get("ids"), list) and len(metadata["ids"]) > doc_idx:
                    doc_id = metadata["ids"][doc_idx]
                elif isinstance(metadata.get("index_to_docstore_id"), dict):
                    # Fallback if raw mapping is present
                    doc_id = metadata["index_to_docstore_id"].get(doc_idx) or metadata["index_to_docstore_id"].get(str(doc_idx))
                if doc_id is None:
                    doc_id = str(doc_idx)
                
                # Try to get content from different metadata formats
                content: str = ""
                if "documents" in metadata and len(metadata["documents"]) > doc_idx:
                    doc_item = metadata["documents"][doc_idx]
                    try:
                        # Handle tuple of (docstore, idx_map) leaked into documents
                        if isinstance(doc_item, tuple) and len(doc_item) == 2:
                            ds, idx_map = doc_item
                            uid = None
                            if isinstance(idx_map, dict):
                                uid = idx_map.get(doc_idx) or idx_map.get(str(doc_idx))
                            doc_obj = None
                            if uid is not None:
                                # Try common docstore dict attributes
                                for attr in ("_dict", "dict", "docs", "_docs", "store", "_store"):
                                    d = getattr(ds, attr, None)
                                    if isinstance(d, dict) and uid in d:
                                        doc_obj = d.get(uid)
                                        break
                                if doc_obj is None and hasattr(ds, "search"):
                                    try:
                                        doc_obj = ds.search(uid)
                                    except Exception:
                                        doc_obj = None
                            if doc_obj is not None:
                                content = getattr(doc_obj, "page_content", "") or ""
                            else:
                                content = ""
                        elif hasattr(doc_item, "page_content"):
                            content = getattr(doc_item, "page_content", "") or ""
                        elif isinstance(doc_item, dict) and "page_content" in doc_item:
                            content = str(doc_item.get("page_content") or "")
                        else:
                            content = doc_item if isinstance(doc_item, str) else str(doc_item)
                    except Exception:
                        content = doc_item if isinstance(doc_item, str) else str(doc_item)
                elif "texts" in metadata and len(metadata["texts"]) > doc_idx:
                    content = metadata["texts"][doc_idx]
                doc_metadata: Dict[str, Any] = {}
                if "metadatas" in metadata and len(metadata["metadatas"]) > doc_idx:
                    doc_metadata = metadata["metadatas"][doc_idx]
                # If not present, try to extract from Document object
                try:
                    if (not doc_metadata) and "documents" in metadata and len(metadata["documents"]) > doc_idx:
                        doc_item2 = metadata["documents"][doc_idx]
                        meta2 = getattr(doc_item2, "metadata", None)
                        if isinstance(meta2, dict):
                            doc_metadata = meta2
                except Exception:
                    pass
                
                # Extract source and page information
                source = (
                    doc_metadata.get("source")
                    or doc_metadata.get("source_file")
                    or doc_metadata.get("file_path")
                    or doc_metadata.get("path")
                    or "Unknown"
                )
                page = (
                    doc_metadata.get("page")
                    or doc_metadata.get("page_number")
                    or doc_metadata.get("page_index")
                    or None
                )
                
                # Create the result dictionary
                result = {
                    "content": content,
                    "source": source,
                    # Convert L2 distance to a bounded similarity score in (0, 1]
                    "score": float(1.0 / (1.0 + float(max(0.0, distances[0][i])))),
                    "id": doc_id
                }
                
                # Add page number if available
                if page is not None:
                    result["page"] = page
                    
                # Add any other metadata
                if doc_metadata:
                    result["metadata"] = doc_metadata
                
                results.append(result)
        
        return results
    
    def _search_weaviate(self, query: str, collection_name: str, top_k: int) -> List[Dict[str, Any]]:
        """Search a Weaviate collection"""
        try:
            # Use the WeaviateManager's robust search with named-vector fallbacks
            from utils.weaviate_manager import get_weaviate_manager  # type: ignore

            mgr = get_weaviate_manager()
            # Try hybrid first for better lexical+semantic recall; it internally falls back to near_text
            raw_results = mgr.hybrid_search(collection_name=collection_name, query=query, limit=top_k)

            results: List[Dict[str, Any]] = []
            for r in raw_results:
                content = r.get("content", "")
                source = r.get("source", "Weaviate")
                score = float(r.get("score") or 0.0)
                rid = r.get("uuid") or r.get("id") or ""
                out: Dict[str, Any] = {
                    "content": content,
                    "source": source,
                    "score": score,
                    "id": rid,
                }
                meta = r.get("metadata")
                if isinstance(meta, dict) and meta:
                    out["metadata"] = meta
                results.append(out)

            return results
            
        except ImportError:
            raise ImportError("Weaviate integration not available")
        except Exception as e:
            logger.error(f"Error searching Weaviate collection {collection_name}: {e}")
            raise
    
    # --- Ingestion ---
    def add_documents(self, documents: List[Any], collection_name: str) -> bool:
        """Attempt to ingest documents into Weaviate.

        Returns True on success. Returns False if Weaviate is disabled or ingestion fails
        (allowing caller to fallback to FAISS or another backend).
        """
        try:
            # Only support Weaviate ingestion here. FAISS write is handled by caller.
            if not self.config.is_feature_enabled("enable_weaviate"):
                logger.info("Weaviate feature disabled (ENABLE_WEAVIATE=false); skipping Weaviate ingestion")
                return False
            from utils.weaviate_manager import get_weaviate_manager  # type: ignore
        except Exception as e:
            logger.warning(f"Weaviate manager not available for ingestion: {e}")
            return False

        try:
            mgr = get_weaviate_manager()
            # Normalize collection name to Weaviate class rules is handled by manager
            try:
                existing = set(mgr.list_collections() or [])
            except Exception as e_list:
                logger.warning(f"Unable to list Weaviate collections before ingest: {e_list}")
                existing = set()

            # Create collection if missing
            if (collection_name not in existing) and (getattr(mgr, "create_collection", None)):
                try:
                    created = mgr.create_collection(collection_name, description=f"Ingested by VectorDBProvider at {datetime.now().isoformat()}")
                    if not created:
                        logger.warning(f"Create collection reported False for '{collection_name}' (may already exist)")
                except Exception as ce:
                    logger.warning(f"Create collection failed for '{collection_name}': {ce}")

            # Convert input documents to dicts expected by manager
            def _to_doc_dict(d: Any) -> Dict[str, Any]:
                try:
                    # LangChain Document
                    content = getattr(d, "page_content", None)
                    metadata = getattr(d, "metadata", None)
                    if isinstance(content, str):
                        src = None
                        if isinstance(metadata, dict):
                            src = metadata.get("source") or metadata.get("file_path") or metadata.get("path")
                        return {
                            "content": content,
                            "source": src or collection_name,
                            "source_type": str(metadata.get("source_type") if isinstance(metadata, dict) else "document"),
                            "metadata": metadata if isinstance(metadata, dict) else {},
                        }
                except Exception:
                    pass
                try:
                    # Pre-built dict
                    if isinstance(d, dict):
                        out = {
                            "content": d.get("content") or d.get("text") or d.get("page_content") or str(d),
                            "source": d.get("source") or d.get("file_path") or collection_name,
                            "source_type": d.get("source_type") or "document",
                            "metadata": d.get("metadata") or {},
                        }
                        # propagate page if present
                        if d.get("page") is not None:
                            try:
                                out["metadata"]["page"] = d.get("page")
                            except Exception:
                                pass
                        return out
                except Exception:
                    pass
                # Fallback best-effort
                return {
                    "content": str(d),
                    "source": collection_name,
                    "source_type": "document",
                    "metadata": {},
                }

            docs: List[Dict[str, Any]] = [_to_doc_dict(d) for d in documents]
            # Filter empties
            docs = [d for d in docs if isinstance(d.get("content"), str) and d["content"].strip()]
            if not docs:
                logger.warning("No non-empty documents to ingest")
                return False

            # Ingest in batches via detailed stats path when available
            batch_size = 100
            processed_total = 0
            warnings_total: List[str] = []
            for i in range(0, len(docs), batch_size):
                batch = docs[i:i+batch_size]
                try:
                    if getattr(mgr, "add_documents_with_stats", None):
                        stats = mgr.add_documents_with_stats(collection_name, batch)
                        if not stats.get("success"):
                            logger.warning(f"Batch ingest reported failure: {stats.get('error')}")
                        processed_total += int(stats.get("processed_count") or 0)
                        warnings_total.extend(stats.get("warnings") or [])
                    else:
                        ok = mgr.add_documents(collection_name, batch)
                        processed_total += len(batch) if ok else 0
                except Exception as be:
                    logger.error(f"Weaviate batch ingest error: {be}")
                    return False

            if processed_total <= 0:
                logger.warning("No documents processed by Weaviate ingest")
                return False
            if warnings_total:
                logger.warning(f"Weaviate ingest warnings: {'; '.join(warnings_total[:3])}")
            logger.info(f"Ingested {processed_total} documents into Weaviate collection '{collection_name}'")
            # Clear caches so new collection is visible immediately
            try:
                self.clear_cache()
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error(f"Weaviate ingestion failed: {e}")
            self._last_error = str(e)
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the vector database provider"""
        metrics = self._metrics.copy()
        
        # Calculate derived metrics
        if metrics["queries"] > 0:
            metrics["success_rate"] = metrics["successful_queries"] / metrics["queries"] * 100
            metrics["avg_query_time"] = metrics["query_time_total"] / metrics["queries"]
        else:
            metrics["success_rate"] = 0
            metrics["avg_query_time"] = 0
            
        return metrics
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message"""
        return self._last_error
    
    def clear_cache(self):
        """Clear internal caches"""
        self._load_faiss_index.cache_clear()
        self._available_indexes = None
        self._last_refresh = None

# Create a singleton instance
_db_provider_instance = None

def get_vector_db_provider() -> VectorDBProvider:
    """Get the singleton VectorDBProvider instance"""
    global _db_provider_instance
    if _db_provider_instance is None:
        _db_provider_instance = VectorDBProvider()
    return _db_provider_instance
