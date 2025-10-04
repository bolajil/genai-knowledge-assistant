"""
Enhanced Search Bylaw Integration

This module integrates the specialized ByLaw document retrieval 
with the enhanced search system to ensure proper document content access.
"""

import logging
from typing import List, Dict, Any, Optional
import time

# Configure logging
logger = logging.getLogger(__name__)

# Import enhanced search components
try:
    from utils.enhanced_search import get_enhanced_search, SearchResult, EnhancedSearch
    ENHANCED_SEARCH_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced search not available")
    ENHANCED_SEARCH_AVAILABLE = False

# Import bylaw document retrieval
try:
    from utils.bylaw_retrieval import search_bylaw_documents
    BYLAW_RETRIEVAL_AVAILABLE = True
except ImportError:
    logger.warning("ByLaw document retrieval not available")
    BYLAW_RETRIEVAL_AVAILABLE = False

# Patch the EnhancedSearch class if available
if ENHANCED_SEARCH_AVAILABLE and BYLAW_RETRIEVAL_AVAILABLE:
    try:
        # Get the original search method
        original_search = EnhancedSearch.search
        
        # Define the enhanced search method with ByLaw specialization
        def enhanced_search_with_bylaw(self, query: str, max_results: int = 5, 
                                     search_type: str = "hybrid", 
                                     index_name: Optional[str] = None, 
                                     **kwargs) -> List[SearchResult]:
            """
            Enhanced search method with special handling for ByLaw indexes
            
            Args:
                query: The search query
                max_results: Maximum number of results to return
                search_type: Type of search to perform
                index_name: Specific index to search
                **kwargs: Additional search parameters
                
            Returns:
                List of SearchResult objects
            """
            # Check if this is a ByLaw index search
            if index_name and "bylaw" in index_name.lower():
                logger.info(f"Using specialized ByLaw retrieval for index: {index_name}")
                try:
                    # Use the specialized ByLaw document retrieval
                    bylaw_results = search_bylaw_documents(query, max_results)
                    
                    # Convert to SearchResult objects
                    results = []
                    for result in bylaw_results:
                        content = result.get("content", "")
                        if not content or content.strip() == "":
                            content = "This document appears to be empty or could not be retrieved properly."
                        
                        # Create a search result
                        search_result = SearchResult(
                            content=content,
                            source=f"ByLaw Document ({index_name})",
                            relevance=result.get("score", 0.5),
                            doc_id=str(result.get("doc_idx", "")),
                            metadata=result.get("metadata", {})
                        )
                        results.append(search_result)
                    
                    # If no results found, add a fallback result
                    if not results:
                        logger.warning(f"No ByLaw results found for query: {query}")
                        results.append(SearchResult(
                            content="No relevant content found in the ByLaw documents. Please try a different query.",
                            source="ByLaw Search System",
                            relevance=0.1,
                            doc_id="",
                            metadata={}
                        ))
                    
                    return results
                    
                except Exception as e:
                    logger.error(f"Error in specialized ByLaw retrieval: {e}")
                    # Fall back to original search
                    return original_search(self, query, max_results, search_type, index_name, **kwargs)
            else:
                # Use the original search method for other indexes
                return original_search(self, query, max_results, search_type, index_name, **kwargs)
        
        # Patch the EnhancedSearch class
        EnhancedSearch.search = enhanced_search_with_bylaw
        logger.info("EnhancedSearch patched with specialized ByLaw retrieval")
        
        # Refresh the singleton instance
        get_enhanced_search.cache_clear()
        get_enhanced_search()
        logger.info("Enhanced search instance refreshed with ByLaw specialization")
        
    except Exception as e:
        logger.error(f"Error patching EnhancedSearch with ByLaw specialization: {e}")
else:
    logger.warning("Cannot patch EnhancedSearch with ByLaw specialization - components not available")
