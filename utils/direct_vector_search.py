"""
Direct vector store search integration for the Agent Assistant.
This module provides direct access to the FAISS vector store for search.
"""

import os
import logging
import sys
from typing import List, Dict, Any, Optional
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import FAISS loader
try:
    from app.utils.faiss_loader import safe_load_faiss
    FAISS_AVAILABLE = True
except ImportError:
    logger.warning("FAISS loader not available. Falling back to mock search.")
    FAISS_AVAILABLE = False

class SearchResult:
    """Object representing a search result from any source"""
    def __init__(self, 
                 content: str, 
                 source_name: str, 
                 source_type: str, 
                 relevance_score: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None):
        self.content = content
        self.source_name = source_name
        self.source_type = source_type  # "index", "web", "file", "api", etc.
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
    
    def __str__(self):
        return f"SearchResult(source={self.source_name}, type={self.source_type}, score={self.relevance_score:.2f})"
    
    def to_dict(self):
        return {
            "content": self.content,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata
        }

def get_available_indexes():
    """Get a list of available FAISS indexes"""
    indexes = []
    try:
        # Path to the faiss_index directory
        faiss_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'faiss_index')
        
        # Get all subdirectories that contain index files
        for root, dirs, files in os.walk(faiss_dir):
            if 'index.faiss' in files and 'index.pkl' in files:
                # Extract the index name from the path
                index_name = os.path.basename(root).replace('_index', '')
                indexes.append(index_name)
        
        logger.info(f"Found {len(indexes)} available indexes: {indexes}")
    except Exception as e:
        logger.error(f"Error getting available indexes: {str(e)}")
    
    return indexes

def search_vector_store(query: str, index_name: str = None, top_k: int = 5) -> List[SearchResult]:
    """
    Search the vector store for relevant documents
    
    Args:
        query: The search query
        index_name: Specific index to search (if None, searches across all available indexes)
        top_k: Number of results to return
        
    Returns:
        List of SearchResult objects
    """
    results = []
    
    if not FAISS_AVAILABLE:
        logger.warning("FAISS not available, returning mock results")
        return _get_mock_results(query, top_k)
    
    try:
        # Path to the faiss_index directory
        faiss_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'faiss_index')
        
        if index_name:
            # Search specific index
            index_path = os.path.join(faiss_dir, f"{index_name}_index")
            if not os.path.exists(index_path):
                # Try without _index suffix
                index_path = os.path.join(faiss_dir, index_name)
            
            if os.path.exists(index_path):
                results.extend(_search_single_index(query, index_path, index_name, top_k))
            else:
                logger.warning(f"Index '{index_name}' not found at {index_path}")
        else:
            # Search all available indexes
            available_indexes = get_available_indexes()
            for idx_name in available_indexes:
                index_path = os.path.join(faiss_dir, f"{idx_name}_index")
                if not os.path.exists(index_path):
                    # Try without _index suffix
                    index_path = os.path.join(faiss_dir, idx_name)
                
                if os.path.exists(index_path):
                    results.extend(_search_single_index(query, index_path, idx_name, top_k // len(available_indexes) + 1))
    
    except Exception as e:
        logger.error(f"Error searching vector store: {str(e)}")
        return _get_mock_results(query, top_k)
    
    # Sort by relevance score and limit to top_k
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    return results[:top_k]

def _search_single_index(query: str, index_path: str, index_name: str, top_k: int) -> List[SearchResult]:
    """Search a single FAISS index with timeout handling"""
    import signal
    from contextlib import contextmanager

    class TimeoutException(Exception):
        pass

    @contextmanager
    def time_limit(seconds):
        def signal_handler(signum, frame):
            raise TimeoutException("Timed out!")
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)

    results = []
    try:
        with time_limit(10):  # 10 second timeout
            logger.info(f"Loading FAISS index from {index_path}")
            faiss_index = safe_load_faiss(index_path)
            
            docs_with_scores = faiss_index.similarity_search_with_score(query, k=top_k)
            
            for doc, score in docs_with_scores:
                relevance_score = 1.0 / (1.0 + score)
                results.append(SearchResult(
                    content=doc.page_content,
                    source_name=f"Index: {index_name}",
                    source_type="index",
                    relevance_score=relevance_score,
                    metadata=doc.metadata
                ))
                
    except TimeoutException:
        logger.error(f"Timeout searching index {index_name}")
        return []
    except Exception as e:
        logger.error(f"Error searching index {index_name}: {str(e)}", exc_info=True)
        return []
    
    return results

def _get_mock_results(query: str, top_k: int) -> List[SearchResult]:
    """Generate mock search results when FAISS is not available"""
    results = []
    
    for i in range(min(top_k, 3)):
        result = SearchResult(
            content=f"This is a mock search result for query: '{query}'. In a real implementation, this would contain actual content from your vector store.",
            source_name="Mock Vector Store",
            source_type="index",
            relevance_score=0.9 - (i * 0.1),
            metadata={"mock": True, "query": query}
        )
        results.append(result)
    
    return results

def perform_multi_source_search(query: str, knowledge_sources: List[str], max_results: int = 5, use_placeholders: bool = False) -> List[SearchResult]:
    """
    Perform search across multiple sources based on user query and selected knowledge sources.
    
    Args:
        query: The user's query string
        knowledge_sources: List of knowledge source names to search
        max_results: Maximum number of results to return
        use_placeholders: Whether to return placeholder results (for testing)
    
    Returns:
        List of SearchResult objects
    """
    results = []
    
    # Generate placeholder results for testing if requested
    if use_placeholders:
        for source in knowledge_sources:
            source_type = _get_source_type(source)
            for i in range(min(2, max_results)):
                result = SearchResult(
                    content=f"This is placeholder content for the query: '{query}'.\n\nIt simulates information that would be retrieved from the {source} knowledge source.\n\nIn a real implementation, this would contain actual search results.",
                    source_name=source,
                    source_type=source_type,
                    relevance_score=0.9 - (i * 0.1),
                    metadata={
                        "url": f"https://example.com/result/{i+1}",
                        "date": "2023-01-01",
                        "title": f"Result for {query}"
                    }
                )
                results.append(result)
        return results
    
    # Perform actual searches based on knowledge sources
    for source in knowledge_sources:
        if "Indexed Documents" in source or "Internal" in source:
            # Search vector store
            vector_results = search_vector_store(query, top_k=max_results)
            results.extend(vector_results)
        
        elif "Web Search" in source:
            # Mock web search (replace with actual web search API when available)
            for i in range(min(2, max_results)):
                result = SearchResult(
                    content=f"Web search result for '{query}'. This would typically come from a search API like Bing or Google.",
                    source_name="Web Search",
                    source_type="web",
                    relevance_score=0.85 - (i * 0.1),
                    metadata={"web": True}
                )
                results.append(result)
        
        elif "API Data" in source or "Structured Data" in source:
            # Mock API/structured data (replace with actual data source when available)
            result = SearchResult(
                content=f"Structured data for '{query}'. This would typically come from an API or database.",
                source_name=source,
                source_type="api",
                relevance_score=0.8,
                metadata={"api": True}
            )
            results.append(result)
    
    # Sort by relevance and limit results
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    return results[:max_results]

def format_search_results_for_agent(results: List[SearchResult]) -> str:
    """
    Format search results for inclusion in agent responses.
    
    Args:
        results: List of SearchResult objects
    
    Returns:
        Formatted string with search results
    """
    if not results:
        return "No search results found for your query."
    
    formatted_text = "### Search Results Summary\n\n"
    
    # Add each result with its source
    for i, result in enumerate(results, 1):
        formatted_text += f"**Result {i} from {result.source_name}:**\n\n"
        formatted_text += f"{result.content}\n\n"
        
        # Add metadata if available
        if result.metadata and len(result.metadata) > 0:
            # Filter out internal metadata fields
            display_metadata = {k: v for k, v in result.metadata.items() 
                              if k not in ['mock', 'query'] and not k.startswith('_')}
            
            if display_metadata:
                formatted_text += "**Metadata:**\n"
                for key, value in display_metadata.items():
                    formatted_text += f"- {key}: {value}\n"
                formatted_text += "\n"
        
        formatted_text += f"*Source: {result.source_name} | Relevance: {result.relevance_score:.2f}*\n\n"
        formatted_text += "---\n\n"
    
    # Add a summary
    formatted_text += f"*Found {len(results)} results across {len(set(r.source_name for r in results))} sources.*\n\n"
    
    return formatted_text

def _get_source_type(source_name: str) -> str:
    """Map a source name to a source type"""
    source_name = source_name.lower()
    
    if "document" in source_name or "index" in source_name or "internal" in source_name:
        return "index"
    elif "web" in source_name:
        return "web"
    elif "api" in source_name or "data" in source_name:
        return "api"
    elif "enterprise" in source_name:
        return "enterprise"
    else:
        return "other"
