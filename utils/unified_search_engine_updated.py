"""
Unified Search Engine for VaultMind
Provides consistent document retrieval and LLM integration across all tabs
Updated to use the centralized vector database provider
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import time

# Import the centralized vector database provider
from utils.vector_db_provider import get_vector_db_provider

logger = logging.getLogger(__name__)

class UnifiedSearchEngine:
    """
    Centralized search engine that connects indexes to actual document content
    and integrates with LLMs for intelligent responses
    """
    
    def __init__(self):
        self.db_provider = get_vector_db_provider()
        self.openai_client = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize OpenAI client"""
        try:
            # Initialize OpenAI client
            import openai
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                openai.api_key = openai_key
                self.openai_client = openai
                logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
    def search_index(self, query: str, index_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search a specific index for documents matching the query
        
        Args:
            query: The search query
            index_name: Name of the index to search
            top_k: Number of results to return
            
        Returns:
            List of search results with content, source, and relevance score
        """
        # Track performance
        start_time = time.time()
        
        try:
            # Use the vector database provider to search the index
            results = self.db_provider.search_index(query, index_name, top_k)
            
            # If no results, return an informative message
            if not results:
                logger.warning(f"No results found for query '{query}' in index '{index_name}'")
                return [{
                    "content": f"No results found for '{query}' in index '{index_name}'.",
                    "source": "Search Engine",
                    "score": 0.0
                }]
            
            # Log successful search
            duration = time.time() - start_time
            logger.info(f"Search completed in {duration:.3f}s, found {len(results)} results for '{query}' in '{index_name}'")
            
            return results
            
        except Exception as e:
            # Log the error and return an informative message
            duration = time.time() - start_time
            logger.error(f"Search failed in {duration:.3f}s: {str(e)}")
            
            return [{
                "content": f"Error searching for '{query}' in index '{index_name}': {str(e)}",
                "source": "Search Engine Error",
                "score": 0.0
            }]
    
    def get_available_indexes(self, force_refresh: bool = False) -> List[str]:
        """
        Get a list of all available indexes
        
        Args:
            force_refresh: Whether to force a refresh of the index list
            
        Returns:
            List of available index names
        """
        return self.db_provider.get_available_indexes(force_refresh)
    
    def get_vector_db_status(self) -> Tuple[str, str]:
        """
        Get the current status of the vector databases
        
        Returns:
            Tuple of (status, message) where status is "Ready" or "Error"
        """
        return self.db_provider.get_vector_db_status()
    
    def get_search_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the search engine
        
        Returns:
            Dictionary of metrics
        """
        return self.db_provider.get_metrics()

# Create a singleton instance
_search_engine_instance = None

def get_search_engine() -> UnifiedSearchEngine:
    """Get the singleton UnifiedSearchEngine instance"""
    global _search_engine_instance
    if _search_engine_instance is None:
        _search_engine_instance = UnifiedSearchEngine()
    return _search_engine_instance

# Simplified API functions for backward compatibility

def search_index_unified(query: str, index_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search a specific index for documents matching the query (simplified API)
    
    Args:
        query: The search query
        index_name: Name of the index to search
        top_k: Number of results to return
        
    Returns:
        List of search results with content, source, and relevance score
    """
    search_engine = get_search_engine()
    return search_engine.search_index(query, index_name, top_k)

def get_unified_indexes(force_refresh: bool = False) -> List[str]:
    """
    Get a list of all available indexes (simplified API)
    
    Args:
        force_refresh: Whether to force a refresh of the index list
        
    Returns:
        List of available index names
    """
    search_engine = get_search_engine()
    return search_engine.get_available_indexes(force_refresh)

def get_vector_db_status() -> Tuple[str, str]:
    """
    Get the current status of the vector databases (simplified API)
    
    Returns:
        Tuple of (status, message) where status is "Ready" or "Error"
    """
    search_engine = get_search_engine()
    return search_engine.get_vector_db_status()
