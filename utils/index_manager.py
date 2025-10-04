"""
IndexManager - Centralized manager for vector indexes
Provides standardized access to vector indexes across the application
"""
import os
import shutil
import logging
import faiss
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class IndexManager:
    """
    Centralized manager for vector indexes.
    Ensures consistent access to indexes across different tabs and components.
    """
    
    # Define standard paths for indexes with priority order
    STANDARD_PATHS = [
        os.path.join("data", "faiss_index"),  # Primary location
        os.path.join("data", "indexes"),       # Secondary location
        os.path.join("vector_store"),         # Legacy location
        os.path.join("vectorstores")          # Alternative legacy location
    ]
    
    # Global cache for loaded indexes
    _index_cache = {}
    
    @classmethod
    def delete_index(cls, index_name: str) -> Dict[str, Any]:
        """
        Delete an index and all its associated files
        
        Args:
            index_name: Name of the index to delete
            
        Returns:
            Dict with status and details of the deletion
        """
        result = {
            'success': False,
            'message': '',
            'deleted_paths': [],
            'errors': []
        }
        
        try:
            # Find all possible locations for this index
            possible_paths = []
            
            # Check FAISS index locations with multiple naming patterns
            for base_path in cls.STANDARD_PATHS:
                for suffix in ['', '_index', '_index_index']:
                    full_name = f"{index_name}{suffix}"
                    index_path = os.path.join(base_path, full_name)
                    if os.path.exists(index_path):
                        possible_paths.append(index_path)
                
                # Also check for exact directory matches (case variations)
                for item in os.listdir(base_path) if os.path.exists(base_path) else []:
                    item_path = os.path.join(base_path, item)
                    if os.path.isdir(item_path):
                        # Check if directory name contains the index name (case insensitive)
                        if index_name.lower() in item.lower() or item.lower().startswith(index_name.lower()):
                            possible_paths.append(item_path)
            
            # Check for standalone files
            for base_path in cls.STANDARD_PATHS:
                for ext in ['.faiss', '.pkl', '.index']:
                    file_path = os.path.join(base_path, f"{index_name}{ext}")
                    if os.path.exists(file_path):
                        possible_paths.append(file_path)
            
            # Remove duplicates while preserving order
            possible_paths = list(dict.fromkeys(possible_paths))
            
            if not possible_paths:
                # Debug: Show what we're looking for
                debug_info = []
                for base_path in cls.STANDARD_PATHS:
                    if os.path.exists(base_path):
                        items = os.listdir(base_path)
                        debug_info.append(f"{base_path}: {items}")
                
                result['message'] = f"Index '{index_name}' not found. Searched locations: {debug_info}"
                return result
            
            # Delete all found paths
            for path in possible_paths:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                        logger.info(f"Deleted directory: {path}")
                    else:
                        os.remove(path)
                        logger.info(f"Deleted file: {path}")
                    
                    result['deleted_paths'].append(path)
                    
                except Exception as e:
                    error_msg = f"Failed to delete {path}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
            
            # Clear from cache if present
            if index_name in cls._index_cache:
                del cls._index_cache[index_name]
            
            # Clear all cached index lists to force refresh
            if hasattr(cls, '_available_indexes'):
                delattr(cls, '_available_indexes')
            
            if result['deleted_paths']:
                result['success'] = True
                result['message'] = f"Successfully deleted index '{index_name}' from {len(result['deleted_paths'])} location(s)"
                
                # Force refresh of index lists in Streamlit session
                try:
                    import streamlit as st
                    st.session_state['index_deleted'] = True
                    if 'cached_index_list' in st.session_state:
                        del st.session_state['cached_index_list']
                    if 'available_indexes' in st.session_state:
                        del st.session_state['available_indexes']
                except:
                    pass  # Streamlit not available in non-web context
            else:
                result['message'] = f"Failed to delete any files for index '{index_name}'"
            
        except Exception as e:
            result['message'] = f"Error deleting index '{index_name}': {str(e)}"
            result['errors'].append(str(e))
            logger.error(result['message'])
        
        return result
    
    @classmethod
    def list_all_indexes(cls) -> Dict[str, List[str]]:
        """
        List all available indexes by type
        
        Returns:
            Dict with 'faiss' and 'directory' keys containing lists of index names
        """
        indexes = {
            'faiss': [],
            'directory': [],
            'unknown': []
        }
        
        try:
            # Check FAISS index directory
            faiss_dir = Path("data/faiss_index")
            if faiss_dir.exists():
                for item in faiss_dir.iterdir():
                    if item.is_dir() and item.name.endswith('_index'):
                        index_name = item.name.replace('_index', '')
                        indexes['faiss'].append(index_name)
            
            # Check directory index directory
            indexes_dir = Path("data/indexes")
            if indexes_dir.exists():
                for item in indexes_dir.iterdir():
                    if item.is_dir():
                        # Check if it has extracted_text.txt (directory index)
                        text_file = item / "extracted_text.txt"
                        if text_file.exists():
                            index_name = item.name.replace('_index', '')
                            indexes['directory'].append(index_name)
                        else:
                            # Might be a FAISS directory
                            index_name = item.name.replace('_index', '')
                            indexes['unknown'].append(index_name)
            
        except Exception as e:
            logger.error(f"Error listing indexes: {str(e)}")
        
        return indexes
    _document_cache = {}
    
    @classmethod
    def get_standard_index_path(cls, index_name: str = None) -> str:
        """
        Get the standard path for faiss indexes
        
        Args:
            index_name: Optional name of the index
            
        Returns:
            Standard path for the index or base directory
        """
        base_path = cls.STANDARD_PATHS[0]  # Use primary path
        
        # Ensure the directory exists
        os.makedirs(base_path, exist_ok=True)
        
        if index_name:
            # Handle the case where index_name already contains the _index suffix
            if not index_name.endswith("_index"):
                index_path = os.path.join(base_path, f"{index_name}_index")
            else:
                index_path = os.path.join(base_path, index_name)
            
            return index_path
        
        return base_path
    
    @classmethod
    def list_available_indexes(cls, force_refresh: bool = False) -> List[str]:
        """
        Get a list of all available indexes from all possible locations
        
        Args:
            force_refresh: Whether to force refresh the index list
            
        Returns:
            List of available index names
        """
        # Use cache if available and not forcing refresh
        if hasattr(cls, '_available_indexes') and not force_refresh:
            return cls._available_indexes
        
        available_indexes = []
        
        # Search all potential index locations
        for base_path in cls.STANDARD_PATHS:
            if os.path.exists(base_path):
                for item in os.listdir(base_path):
                    item_path = os.path.join(base_path, item)
                    if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "index.faiss")):
                        # Normalize index name (remove _index suffix if present)
                        normalized_name = item
                        if normalized_name.endswith("_index"):
                            normalized_name = normalized_name[:-6]
                            
                        if normalized_name not in available_indexes:
                            available_indexes.append(normalized_name)
        
        # Cache the results
        cls._available_indexes = available_indexes
        return available_indexes
    
    @classmethod
    def load_index(cls, index_name: str, force_reload: bool = False) -> Tuple[Any, List[Dict]]:
        """
        Load a FAISS index with consistent naming and location handling
        
        Args:
            index_name: Name of the index to load
            force_reload: Whether to force reload the index
            
        Returns:
            Tuple of (faiss_index, documents)
            
        Raises:
            FileNotFoundError: If the index cannot be found
        """
        # Check cache first
        cache_key = index_name.lower()
        if not force_reload and cache_key in cls._index_cache:
            return cls._index_cache[cache_key]
        
        # Normalize index name (ensure it doesn't have _index suffix)
        normalized_name = index_name
        if normalized_name.endswith("_index"):
            normalized_name = normalized_name[:-6]
        
        # Generate all possible index paths to try
        possible_paths = []
        for base_path in cls.STANDARD_PATHS:
            possible_paths.extend([
                os.path.join(base_path, normalized_name),
                os.path.join(base_path, f"{normalized_name}_index"),
                os.path.join(base_path, normalized_name.upper()),
                os.path.join(base_path, f"{normalized_name.upper()}_index"),
            ])
        
        # Try each path until we find a valid index
        for path in possible_paths:
            faiss_path = os.path.join(path, "index.faiss")
            pickle_path = os.path.join(path, "index.pkl")
            
            if os.path.exists(faiss_path) and os.path.exists(pickle_path):
                try:
                    logger.info(f"Loading index from: {path}")
                    
                    # Load the FAISS index
                    index = faiss.read_index(faiss_path)
                    
                    # Load the documents
                    with open(pickle_path, "rb") as f:
                        documents = pickle.load(f)
                    
                    # Cache the loaded index
                    cls._index_cache[cache_key] = (index, documents)
                    cls._document_cache[cache_key] = documents
                    
                    logger.info(f"Successfully loaded index '{index_name}' with {len(documents)} documents")
                    return index, documents
                except Exception as e:
                    logger.warning(f"Error loading index from {path}: {str(e)}")
        
        # If we reach here, the index wasn't found
        error_msg = f"Could not find a valid FAISS index for '{index_name}'. Checked paths: {possible_paths}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    @classmethod
    def save_index(cls, index_name: str, index: Any, documents: List[Dict]) -> str:
        """
        Save a FAISS index to the standard location
        
        Args:
            index_name: Name of the index
            index: FAISS index object
            documents: List of documents
            
        Returns:
            Path where the index was saved
        """
        # Get the standard path for this index
        index_path = cls.get_standard_index_path(index_name)
        
        # Ensure the directory exists
        os.makedirs(index_path, exist_ok=True)
        
        # Save the index and documents
        faiss_path = os.path.join(index_path, "index.faiss")
        pickle_path = os.path.join(index_path, "index.pkl")
        
        try:
            # Save the FAISS index
            faiss.write_index(index, faiss_path)
            
            # Save the documents
            with open(pickle_path, "wb") as f:
                pickle.dump(documents, f)
            
            # Update cache
            cache_key = index_name.lower()
            cls._index_cache[cache_key] = (index, documents)
            cls._document_cache[cache_key] = documents
            
            logger.info(f"Successfully saved index '{index_name}' to {index_path}")
            return index_path
        except Exception as e:
            logger.error(f"Error saving index '{index_name}': {str(e)}")
            raise
    
    @classmethod
    def migrate_legacy_indexes(cls) -> Dict[str, str]:
        """
        Migrate indexes from legacy paths to the standard path
        
        Returns:
            Dict mapping old paths to new paths for migrated indexes
        """
        migration_results = {}
        standard_base = cls.STANDARD_PATHS[0]
        
        # Check legacy paths for indexes to migrate
        for legacy_path in cls.STANDARD_PATHS[1:]:
            if os.path.exists(legacy_path):
                for item in os.listdir(legacy_path):
                    source_path = os.path.join(legacy_path, item)
                    if os.path.isdir(source_path):
                        faiss_file = os.path.join(source_path, "index.faiss")
                        pkl_file = os.path.join(source_path, "index.pkl")
                        
                        if os.path.exists(faiss_file) and os.path.exists(pkl_file):
                            dest_path = os.path.join(standard_base, item)
                            
                            try:
                                os.makedirs(dest_path, exist_ok=True)
                                
                                shutil.copy(faiss_file, os.path.join(dest_path, "index.faiss"))
                                shutil.copy(pkl_file, os.path.join(dest_path, "index.pkl"))
                                
                                logger.info(f"Migrated index from {source_path} to {dest_path}")
                                migration_results[source_path] = dest_path
                            except Exception as e:
                                logger.error(f"Error migrating index from {source_path} to {dest_path}: {str(e)}")
        
        # Refresh available indexes after migration
        cls.list_available_indexes(force_refresh=True)
        
        return migration_results
