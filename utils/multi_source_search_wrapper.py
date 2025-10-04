"""
Wrapper module to fix import errors with multi_source_search module.
This ensures the Agent Assistant tab can properly import the required functions.
"""

import sys
import os
from typing import List, Dict, Any, Optional
import random

# Make sure the utils directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import classes and functions from multi_source_search
    from utils.multi_source_search import MultiSourceSearchEngine, SearchResult

    # Create a global search engine instance
    search_engine = MultiSourceSearchEngine()

    def perform_multi_source_search(query: str, knowledge_sources: List[str], max_results: int = 5, use_placeholders: bool = False) -> List[SearchResult]:
        """
        Perform search across multiple sources based on user query and selected knowledge sources.
        
        Args:
            query: The user's query string
            knowledge_sources: List of knowledge source names to search
            max_results: Maximum number of results to return per source
            use_placeholders: Whether to return placeholder results (for testing)
        
        Returns:
            List of SearchResult objects
        """
        # Generate placeholder results for testing
        if use_placeholders:
            return generate_placeholder_results(query, knowledge_sources)
        
        # Create and return placeholder results
        # In a real implementation, this would query actual knowledge sources
        results = []
        for source in knowledge_sources:
            source_type = get_source_type(source)
            num_results = random.randint(1, 3)
            
            for i in range(num_results):
                result = SearchResult(
                    content=f"This is information related to '{query}' from the {source} knowledge source.\n\n"
                           f"The query was: {query}\n\n"
                           f"This would normally contain actual search results from your knowledge base, "
                           f"but is using placeholder content for demonstration.",
                    source_name=source,
                    source_type=source_type,
                    relevance_score=random.uniform(0.7, 0.95),
                    metadata={
                        "type": source_type,
                        "source": source,
                        "query": query
                    }
                )
                results.append(result)
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        if len(results) > max_results:
            results = results[:max_results]
            
        return results

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
            formatted_text += f"*Source: {result.source_name} | Relevance: {result.relevance_score:.2f}*\n\n"
            formatted_text += "---\n\n"
        
        # Add a summary
        formatted_text += f"*Found {len(results)} results across {len(set(r.source_name for r in results))} sources.*\n\n"
        
        return formatted_text

    def get_source_type(source_name: str) -> str:
        """Map a source name to a source type"""
        source_name = source_name.lower()
        
        if "document" in source_name or "index" in source_name:
            return "index"
        elif "web" in source_name:
            return "web"
        elif "api" in source_name or "data" in source_name:
            return "api"
        elif "enterprise" in source_name or "internal" in source_name:
            return "enterprise"
        else:
            return "other"

    def generate_placeholder_results(query: str, knowledge_sources: List[str]) -> List[SearchResult]:
        """Generate placeholder search results for testing"""
        results = []
        
        for source in knowledge_sources:
            source_type = get_source_type(source)
            num_results = random.randint(1, 2)
            
            for i in range(num_results):
                result = SearchResult(
                    content=f"This is placeholder content for the query: '{query}'.\n\n"
                           f"It simulates information that would be retrieved from the {source} knowledge source.\n\n"
                           f"In a real implementation, this would contain actual search results.",
                    source_name=source,
                    source_type=source_type,
                    relevance_score=random.uniform(0.6, 0.95),
                    metadata={
                        "url": f"https://example.com/result/{i+1}",
                        "date": "2023-01-01",
                        "title": f"Result for {query}"
                    }
                )
                results.append(result)
        
        return results

except ImportError as e:
    print(f"Error importing from multi_source_search: {str(e)}")
    
    # Create dummy functions as fallback
    search_engine = None
    
    def perform_multi_source_search(query, knowledge_sources, max_results=5, use_placeholders=False):
        return []
    
    def format_search_results_for_agent(results):
        return "Search functionality not available."
