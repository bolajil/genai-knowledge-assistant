"""
Simple query helpers for FastAPI endpoints
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def query_index(
    query: str,
    index_name: str = "default",
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Query the vector store index
    
    Args:
        query: Query string
        index_name: Name of the index/collection
        top_k: Number of results to return
        
    Returns:
        List of matching documents with metadata
    """
    try:
        # Use the direct vector database provider (works without async issues)
        from utils.vector_db_init import get_any_vector_db_provider
        
        vector_db = get_any_vector_db_provider()
        
        # Use the vector DB's query method with flexible parameter names
        if hasattr(vector_db, 'query_index'):
            results = vector_db.query_index(
                query=query,
                index_name=index_name,
                top_k=top_k
            )
        elif hasattr(vector_db, 'search'):
            # Try different parameter combinations for different providers
            try:
                results = vector_db.search(
                    query=query,
                    index_name=index_name,
                    top_k=top_k
                )
            except TypeError:
                # Try alternative parameter names
                try:
                    results = vector_db.search(
                        query_text=query,
                        index=index_name,
                        k=top_k
                    )
                except TypeError:
                    # Final fallback - just query
                    results = vector_db.search(query, top_k)
        else:
            results = []
        
        # Ensure results are in the expected format
        formatted_results = []
        for result in results:
            if isinstance(result, dict):
                formatted_results.append(result)
            else:
                formatted_results.append({
                    'content': str(result),
                    'metadata': {},
                    'score': 0.0
                })
        
        return formatted_results
        
    except ImportError:
        logger.warning("Multi-vector manager not available, using fallback")
        
        # Try unified search engine
        try:
            from utils.unified_search_engine import UnifiedSearchEngine
            search_engine = UnifiedSearchEngine()
            
            results = search_engine.search(
                query=query,
                index_name=index_name,
                top_k=top_k
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Unified search failed: {e}")
            
            # Final fallback: return empty results
            return []
        
    except Exception as e:
        logger.error(f"Error querying index: {e}")
        return []
