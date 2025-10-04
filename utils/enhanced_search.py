"""
Enhanced Search Utility

This utility provides advanced search capabilities that combine vector search,
metadata filtering, and hybrid search approaches for more accurate results.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import vector database with graceful fallbacks
try:
    from utils.vector_db_init import get_any_vector_db_provider, VECTOR_DB_AVAILABLE
    vector_db_provider = get_any_vector_db_provider()
except ImportError:
    logger.warning("Vector database provider not available.")
    VECTOR_DB_AVAILABLE = False
    vector_db_provider = None

# Try to import the enhanced query processor
try:
    from utils.enhanced_query_processor import get_query_processor
    query_processor = get_query_processor()
    ENHANCED_QUERY_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced query processor not available.")
    ENHANCED_QUERY_AVAILABLE = False
    query_processor = None

# Try to import the enhanced metadata search
try:
    from utils.enhanced_metadata_search import get_metadata_search_engine
    metadata_search_engine = get_metadata_search_engine()
    METADATA_SEARCH_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced metadata search engine not available.")
    METADATA_SEARCH_AVAILABLE = False
    metadata_search_engine = None

class SearchResult:
    """Unified search result format"""
    
    def __init__(self, content: str, source: str, relevance: float = 0.0, 
                 doc_id: Optional[str] = None, metadata: Optional[Dict] = None):
        self.content = content
        self.source = source
        self.relevance = relevance
        self.doc_id = doc_id
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "content": self.content,
            "source": self.source,
            "relevance": self.relevance,
            "doc_id": self.doc_id,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'SearchResult':
        """Create from dictionary"""
        return cls(
            content=data.get("content", ""),
            source=data.get("source", "Unknown"),
            relevance=data.get("relevance", 0.0),
            doc_id=data.get("doc_id"),
            metadata=data.get("metadata", {})
        )

class EnhancedSearch:
    """
    Enhanced search utility that combines vector search, metadata filtering, 
    and hybrid search approaches
    """
    
    def __init__(self):
        """Initialize the enhanced search utility"""
        self.search_stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "avg_response_time": 0,
            "total_response_time": 0
        }
        
    def search(self, query: str, max_results: int = 5, filters: Optional[Dict] = None, 
               search_type: str = "hybrid", index_name: Optional[str] = None, **kwargs) -> List[SearchResult]:
        """
        Perform a search using the best available method
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            filters: Dictionary of metadata filters
            search_type: Type of search to perform ("vector", "metadata", "hybrid")
            index_name: Specific index to search (if None, search all indexes)
            
        Returns:
            List of SearchResult objects
        """
        # Track search stats
        self.search_stats["total_searches"] += 1
        start_time = time.time()
        
        results = []
        success = False
        
        try:
            # Use the appropriate search method based on type and availability
            if search_type == "metadata" and METADATA_SEARCH_AVAILABLE:
                results = self._metadata_search(query, max_results, filters)
            elif search_type == "vector" and VECTOR_DB_AVAILABLE:
                results = self._vector_search(query, max_results, filters, index_name)
            elif search_type == "hybrid":
                results = self._hybrid_search(query, max_results, filters, index_name, **kwargs)
            else:
                # Fall back to best available method
                if ENHANCED_QUERY_AVAILABLE:
                    results = self._enhanced_query_search(query, max_results, filters, index_name, **kwargs)
                elif VECTOR_DB_AVAILABLE:
                    results = self._vector_search(query, max_results, filters, index_name)
                elif METADATA_SEARCH_AVAILABLE:
                    results = self._metadata_search(query, max_results, filters)
                else:
                    # No search methods available
                    logger.warning("No search methods available")
                    results = []
            
            # Sort results by relevance
            results = sorted(results, key=lambda x: x.relevance, reverse=True)
            
            # Limit to max_results
            results = results[:max_results]
            
            # If no results found, add a fallback result
            if not results:
                logger.warning(f"No results found for query: {query}")
                results.append(SearchResult(
                    content="No relevant content found in the documents. Please try a different query or check if the document has been properly indexed.",
                    source="Search System",
                    relevance=0.1,
                    doc_id=None,
                    metadata={"query": query, "status": "no_results"}
                ))
            
            # Update search stats
            success = True
            self.search_stats["successful_searches"] += 1
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            self.search_stats["failed_searches"] += 1
            
        # Update timing stats
        end_time = time.time()
        duration = end_time - start_time
        self.search_stats["total_response_time"] += duration
        
        if self.search_stats["total_searches"] > 0:
            self.search_stats["avg_response_time"] = (
                self.search_stats["total_response_time"] / self.search_stats["total_searches"]
            )
        
        return results
    
    def _metadata_search(self, query: str, max_results: int = 5, 
                        filters: Optional[Dict] = None) -> List[SearchResult]:
        """
        Perform a metadata-based search
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            filters: Dictionary of metadata filters
            
        Returns:
            List of SearchResult objects
        """
        if not METADATA_SEARCH_AVAILABLE or not metadata_search_engine:
            logger.warning("Metadata search not available")
            return []
        
        try:
            # Execute metadata query
            doc_ids = metadata_search_engine.execute_metadata_query(query)
            
            # Apply additional filters if provided
            if filters:
                # Convert filters to metadata query
                filter_query = " ".join([f"{k}:{v}" for k, v in filters.items()])
                filtered_ids = metadata_search_engine.execute_metadata_query(filter_query)
                
                # Get intersection
                doc_ids = list(set(doc_ids).intersection(set(filtered_ids)))
            
            # Get metadata for matching documents
            docs_metadata = metadata_search_engine.get_metadata_for_documents(doc_ids)
            
            # Convert to SearchResult objects
            results = []
            for doc_id, metadata in docs_metadata.items():
                # Try to get content from vector DB if available
                content = f"Document ID: {doc_id}"
                
                if VECTOR_DB_AVAILABLE and vector_db_provider:
                    try:
                        # Try to get the document content
                        doc_content = vector_db_provider.get_document_by_id(doc_id)
                        if doc_content:
                            content = doc_content
                    except Exception:
                        pass
                
                # Create a search result
                results.append(SearchResult(
                    content=content,
                    source=metadata.get("source", "Unknown"),
                    relevance=1.0,  # Metadata matches have high relevance
                    doc_id=doc_id,
                    metadata=metadata
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Metadata search error: {e}")
            return []
    
    def _vector_search(self, query: str, max_results: int = 5, 
                      filters: Optional[Dict] = None, 
                      index_name: Optional[str] = None) -> List[SearchResult]:
        """
        Perform a vector-based search
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            filters: Dictionary of metadata filters
            index_name: Specific index to search (if None, search all indexes)
            
        Returns:
            List of SearchResult objects
        """
        if not VECTOR_DB_AVAILABLE or not vector_db_provider:
            logger.warning("Vector search not available")
            return []
        
        try:
            # Search the vector database
            if index_name:
                # Search in a specific index
                logger.info(f"Searching in specific index: {index_name}")
                try:
                    results = vector_db_provider.search_index(query, index_name, max_results)
                except Exception as e:
                    logger.error(f"Error searching specific index {index_name}: {e}")
                    # Try to fall back to general search
                    results = vector_db_provider.search(query, max_results=max_results)
            else:
                # Search across all indexes
                results = vector_db_provider.search(query, max_results=max_results)
            
            # Convert to SearchResult objects
            search_results = []
            for result in results:
                if isinstance(result, dict):
                    content = result.get("content", "")
                    if not content or content.strip() == "":
                        content = "This document appears to be empty or could not be retrieved properly."
                    
                    metadata = result.get("metadata", {})
                    source = metadata.get("source", "Vector Database")
                    relevance = metadata.get("score", 0.5)
                    doc_id = metadata.get("doc_id")
                else:
                    # Handle other result formats
                    content = str(result)
                    if not content or content.strip() == "":
                        content = "This document appears to be empty or could not be retrieved properly."
                    
                    metadata = {}
                    source = "Vector Database"
                    relevance = 0.5
                    doc_id = None
                
                # Create a search result
                search_results.append(SearchResult(
                    content=content,
                    source=source,
                    relevance=relevance,
                    doc_id=doc_id,
                    metadata=metadata
                ))
            
            # Apply filters if provided
            if filters:
                filtered_results = []
                for result in search_results:
                    match = True
                    for key, value in filters.items():
                        if key not in result.metadata or result.metadata[key] != value:
                            match = False
                            break
                    
                    if match:
                        filtered_results.append(result)
                
                search_results = filtered_results
            
            return search_results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    def _enhanced_query_search(self, query: str, max_results: int = 5, 
                              filters: Optional[Dict] = None,
                              index_name: Optional[str] = None,
                              **kwargs) -> List[SearchResult]:
        """
        Perform a search using the enhanced query processor
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            filters: Dictionary of metadata filters
            
        Returns:
            List of SearchResult objects
        """
        if not ENHANCED_QUERY_AVAILABLE or not query_processor:
            logger.warning("Enhanced query search not available")
            return []
        
        try:
            # Process the query using the enhanced processor
            use_metadata_search = kwargs.get("use_metadata_search", True)
            
            results = query_processor.search(
                query=query,
                top_k=max_results,
                filters=filters,
                use_metadata_search=use_metadata_search
            )
            
            # Convert to SearchResult objects
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    content=result.content,
                    source=result.source,
                    relevance=result.relevance,
                    doc_id=result.doc_id,
                    metadata=result.metadata
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Enhanced query search error: {e}")
            return []
    
    def _hybrid_search(self, query: str, max_results: int = 5, 
                      filters: Optional[Dict] = None,
                      index_name: Optional[str] = None,
                      **kwargs) -> List[SearchResult]:
        """
        Perform a hybrid search combining vector and metadata approaches
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            filters: Dictionary of metadata filters
            index_name: Specific index to search (if None, search all indexes)
            
        Returns:
            List of SearchResult objects
        """
        # Check for metadata search patterns in the query
        metadata_patterns = False
        metadata_results = []
        
        if METADATA_SEARCH_AVAILABLE and metadata_search_engine:
            try:
                # Look for metadata patterns in the query
                if any(pattern in query for pattern in ["type:", "date:", "size:", "author:", "category:", "source:"]):
                    metadata_patterns = True
                    metadata_results = self._metadata_search(query, max_results, filters)
            except Exception as e:
                logger.error(f"Metadata part of hybrid search error: {e}")
        
        # Perform vector search
        vector_results = []
        if VECTOR_DB_AVAILABLE and vector_db_provider:
            try:
                # If we have metadata patterns, clean the query for vector search
                clean_query = query
                if metadata_patterns:
                    # Remove metadata patterns from the query
                    for pattern in ["type:", "date:", "size:", "author:", "category:", "source:"]:
                        if pattern in clean_query:
                            parts = clean_query.split(pattern)
                            if len(parts) > 1:
                                # Remove the pattern and value
                                value_part = parts[1].split(" ")[0]
                                clean_query = clean_query.replace(f"{pattern}{value_part}", "").strip()
                
                vector_results = self._vector_search(clean_query, max_results, filters, index_name)
            except Exception as e:
                logger.error(f"Vector part of hybrid search error: {e}")
        
        # If enhanced query processor is available, use it
        enhanced_results = []
        if ENHANCED_QUERY_AVAILABLE and query_processor:
            try:
                enhanced_results = self._enhanced_query_search(query, max_results, filters, **kwargs)
            except Exception as e:
                logger.error(f"Enhanced part of hybrid search error: {e}")
        
        # Combine results with deduplication
        all_results = {}
        
        # Add results from each source, prioritizing better matches
        for result in metadata_results + vector_results + enhanced_results:
            if result.doc_id:
                # Use doc_id for deduplication if available
                if result.doc_id not in all_results or result.relevance > all_results[result.doc_id].relevance:
                    all_results[result.doc_id] = result
            else:
                # Otherwise use content hash
                content_hash = hash(result.content)
                if content_hash not in all_results or result.relevance > all_results[content_hash].relevance:
                    all_results[content_hash] = result
        
        # Convert back to list
        combined_results = list(all_results.values())
        
        # Sort by relevance
        combined_results.sort(key=lambda x: x.relevance, reverse=True)
        
        # Limit to max_results
        return combined_results[:max_results]

# Factory function to get an enhanced search instance
def get_enhanced_search() -> EnhancedSearch:
    """
    Get an enhanced search instance
    
    Returns:
        EnhancedSearch instance
    """
    return EnhancedSearch()
