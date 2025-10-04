"""
Cache management utilities for VaultMind GenAI Knowledge Assistant
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def clear_streamlit_cache():
    """Clear Streamlit cache and force reload of components"""
    try:
        import streamlit as st
        
        # Clear all Streamlit caches
        st.cache_data.clear()
        st.cache_resource.clear()
        
        logger.info("Streamlit cache cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to clear Streamlit cache: {e}")
        return False

def reload_environment():
    """Reload environment variables from config files"""
    try:
        # Reload in correct order (later files override earlier ones)
        load_dotenv('.env', override=True)
        load_dotenv('config/weaviate.env', override=True) 
        load_dotenv('config/storage.env', override=True)
        
        logger.info("Environment variables reloaded")
        return True
    except Exception as e:
        logger.error(f"Failed to reload environment: {e}")
        return False

def reset_multi_vector_manager():
    """Reset the global multi-vector manager"""
    try:
        from .multi_vector_storage_manager import close_global_manager
        close_global_manager()
        logger.info("Multi-vector manager reset")
        return True
    except Exception as e:
        logger.error(f"Failed to reset multi-vector manager: {e}")
        return False

def full_cache_reset():
    """Perform a complete cache reset"""
    success = True
    
    # 1. Reload environment
    if not reload_environment():
        success = False
    
    # 2. Reset multi-vector manager
    if not reset_multi_vector_manager():
        success = False
    
    # 3. Clear Streamlit cache
    if not clear_streamlit_cache():
        success = False
    
    return success

def get_cache_status():
    """Get current cache and configuration status"""
    status = {
        'environment_loaded': bool(os.getenv('PINECONE_API_KEY')),
        'weaviate_configured': bool(os.getenv('WEAVIATE_URL')),
        'manager_available': False,
        'pinecone_available': False
    }
    
    try:
        from .multi_vector_storage_manager import get_multi_vector_manager
        from .multi_vector_storage_interface import VectorStoreType
        
        manager = get_multi_vector_manager()
        status['manager_available'] = True
        
        pinecone_store = manager.get_store_by_type(VectorStoreType.PINECONE)
        status['pinecone_available'] = bool(pinecone_store)
        
    except Exception as e:
        logger.error(f"Error checking manager status: {e}")
    
    return status
