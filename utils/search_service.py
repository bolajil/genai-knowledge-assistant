"""
SearchService - Unified search service for the application
Provides consistent search functionality across all tabs
"""
import os
import logging
from typing import List, Dict, Any, Optional, Union

from .index_manager import IndexManager
from .simple_search import SearchResult

logger = logging.getLogger(__name__)

class SearchService:
    """
    Centralized search service for consistent search functionality across tabs
    """
    
    @classmethod
    def get_available_indexes(cls) -> List[str]:
        """
        Get a list of all available indexes
        
        Returns:
            List of available index names
        """
        return IndexManager.list_available_indexes()
    
    @classmethod
    def search(cls, 
               query: str, 
               index_names: List[str], 
               max_results: int = 5, 
               use_metadata_filter: bool = False,
               metadata_filters: Dict[str, Any] = None) -> List[SearchResult]:
        """
        Search across multiple indexes with consistent result format
        
        Args:
            query: The search query
            index_names: List of index names to search
            max_results: Maximum number of results per index
            use_metadata_filter: Whether to filter results by metadata
            metadata_filters: Dictionary of metadata filters to apply
            
        Returns:
            List of SearchResult objects
        """
        all_results = []
        metadata_filters = metadata_filters or {}
        
        # Import necessary modules for searching
        try:
            from app.utils.faiss_loader import search_faiss_index
            
            # Search each specified index
            for index_name in index_names:
                try:
                    # Search the index
                    raw_results = search_faiss_index(
                        index_name=index_name,
                        query=query,
                        top_k=max_results
                    )
                    
                    # Convert results to SearchResult objects
                    for result in raw_results:
                        # Apply metadata filters if needed
                        if use_metadata_filter and metadata_filters:
                            if not cls._matches_metadata_filters(result.get("metadata", {}), metadata_filters):
                                continue
                                
                        all_results.append(SearchResult(
                            content=result.get("content", ""),
                            source_name=index_name,
                            source_type="index",
                            relevance_score=result.get("score", 0.0),
                            metadata={
                                "document": result.get("document", "unknown"),
                                "page": result.get("page", 0),
                                "index": index_name,
                                **result.get("metadata", {})
                            }
                        ))
                except Exception as e:
                    logger.error(f"Error searching index '{index_name}': {str(e)}")
                    # Add error result
                    all_results.append(SearchResult(
                        content=f"Error searching index '{index_name}': {str(e)}",
                        source_name=index_name,
                        source_type="error",
                        relevance_score=0.0,
                        metadata={"error": str(e)}
                    ))
        except ImportError:
            logger.warning("FAISS loader not available, using simple search instead")
            # Fall back to simple search implementation
            from .simple_search import perform_multi_source_search
            return perform_multi_source_search(
                query=query,
                knowledge_sources=index_names,
                max_results=max_results
            )
        
        # Sort by relevance score (highest first)
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Limit to the top N most relevant results across all indexes
        return all_results[:max_results * len(index_names)]
    
    @classmethod
    def search_web(cls, query: str, max_results: int = 3, search_engines: List[str] = None) -> List[SearchResult]:
        """
        Search the web for relevant information
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            search_engines: List of search engines to use
            
        Returns:
            List of SearchResult objects
        """
        try:
            # Try to use real web search if available
            # Add implementation for real web search here
            pass
        except Exception as e:
            logger.warning(f"Real web search unavailable: {str(e)}")
        
        # Fallback to simple search implementation
        from .simple_search import perform_multi_source_search
        return perform_multi_source_search(
            query=query,
            knowledge_sources=["Web Search (External)"],
            max_results=max_results,
            search_engines=search_engines
        )
    
    @classmethod
    def format_results_for_display(cls, results: List[SearchResult], format_type: str = "markdown") -> str:
        """
        Format search results for display in different formats
        
        Args:
            results: List of SearchResult objects
            format_type: Format type (markdown, html, text)
            
        Returns:
            Formatted string with search results
        """
        if not results:
            return "No search results found for your query."
        
        if format_type == "markdown":
            return cls._format_markdown(results)
        elif format_type == "html":
            return cls._format_html(results)
        else:
            return cls._format_text(results)
    
    @classmethod
    def _format_markdown(cls, results: List[SearchResult]) -> str:
        """Format results as markdown"""
        formatted_text = "### Search Results\n\n"
        
        for i, result in enumerate(results, 1):
            formatted_text += f"**Result {i} - {result.source_name}** (Score: {result.relevance_score:.2f})\n\n"
            formatted_text += f"{result.content}\n\n"
            
            # Add metadata if available
            if result.metadata and len(result.metadata) > 0:
                formatted_text += "**Source Information:**\n"
                for key, value in result.metadata.items():
                    if key not in ["query", "error"] and not key.startswith("_"):
                        formatted_text += f"- {key}: {value}\n"
                formatted_text += "\n"
            
            formatted_text += "---\n\n"
        
        return formatted_text
    
    @classmethod
    def _format_html(cls, results: List[SearchResult]) -> str:
        """Format results as HTML"""
        formatted_text = "<h3>Search Results</h3>"
        
        for i, result in enumerate(results, 1):
            formatted_text += f"<div class='search-result'>"
            formatted_text += f"<h4>Result {i} - {result.source_name}</h4>"
            formatted_text += f"<p>{result.content}</p>"
            
            # Add metadata if available
            if result.metadata and len(result.metadata) > 0:
                formatted_text += "<div class='metadata'>"
                formatted_text += "<h5>Source Information:</h5>"
                formatted_text += "<ul>"
                for key, value in result.metadata.items():
                    if key not in ["query", "error"] and not key.startswith("_"):
                        formatted_text += f"<li><strong>{key}:</strong> {value}</li>"
                formatted_text += "</ul>"
                formatted_text += "</div>"
            
            formatted_text += f"<div class='score'>Relevance Score: {result.relevance_score:.2f}</div>"
            formatted_text += "</div>"
            formatted_text += "<hr>"
        
        return formatted_text
    
    @classmethod
    def _format_text(cls, results: List[SearchResult]) -> str:
        """Format results as plain text"""
        formatted_text = "SEARCH RESULTS:\n\n"
        
        for i, result in enumerate(results, 1):
            formatted_text += f"RESULT {i} - {result.source_name} (Score: {result.relevance_score:.2f})\n"
            formatted_text += f"{result.content}\n\n"
            
            # Add metadata if available
            if result.metadata and len(result.metadata) > 0:
                formatted_text += "Source Information:\n"
                for key, value in result.metadata.items():
                    if key not in ["query", "error"] and not key.startswith("_"):
                        formatted_text += f"- {key}: {value}\n"
                formatted_text += "\n"
            
            formatted_text += "-" * 40 + "\n\n"
        
        return formatted_text
    
    @staticmethod
    def _matches_metadata_filters(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if metadata matches the specified filters
        
        Args:
            metadata: Document metadata
            filters: Metadata filters to apply
            
        Returns:
            True if metadata matches all filters, False otherwise
        """
        for key, value in filters.items():
            if key not in metadata:
                return False
                
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            elif metadata[key] != value:
                return False
                
        return True
