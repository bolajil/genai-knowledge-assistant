"""
Vector DB Provider Initializer

This module initializes the vector database provider for the VaultMIND application.
It automatically falls back to the mock provider if the real provider is not available.
"""

import logging
from typing import Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the vector database provider
def init_vector_db_provider() -> Tuple[bool, Any]:
    """
    Initialize the vector database provider with fallback to mock provider
    
    Returns:
        Tuple of (success, provider)
    """
    # Try to use real vector database provider first
    try:
        from utils.vector_db_provider import get_vector_db_provider
        
        # Get the vector database provider instance
        provider = get_vector_db_provider()
        logger.info("Vector database provider initialized successfully")
        
        # Check provider status
        status, message = provider.get_vector_db_status()
        if status == "Ready":
            logger.info(f"Vector DB Status: {status} - {message}")
            return True, provider
        else:
            logger.warning(f"Vector DB Status: {status} - {message}")
            logger.warning("Falling back to mock provider...")
    except Exception as e:
        logger.warning(f"Real vector database provider not available: {e}")
        logger.warning("Falling back to mock provider...")
    
    # Fall back to mock provider
    try:
        from utils.mock_vector_db_provider import get_mock_vector_db_provider
        
        # Get the mock vector database provider
        mock_provider = get_mock_vector_db_provider()
        logger.info("Mock vector database provider initialized successfully")
        
        # Check provider status
        status, message = mock_provider.get_vector_db_status()
        logger.info(f"Mock Vector DB Status: {status} - {message}")
        
        return True, mock_provider
    except Exception as e:
        logger.error(f"Mock vector database provider not available: {e}")
        return False, None

# Singleton provider instance
_provider_instance = None
VECTOR_DB_AVAILABLE = False

def get_any_vector_db_provider():
    """
    Get the singleton vector database provider instance
    Will use the real provider if available, otherwise the mock provider
    
    Returns:
        Vector database provider instance or None if not available
    """
    global _provider_instance, VECTOR_DB_AVAILABLE
    
    if _provider_instance is None:
        success, provider = init_vector_db_provider()
        if success:
            _provider_instance = provider
            VECTOR_DB_AVAILABLE = True
        else:
            VECTOR_DB_AVAILABLE = False
    
    return _provider_instance
