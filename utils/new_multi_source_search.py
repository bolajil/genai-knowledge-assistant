"""
Multi-source search utility for the Agent Assistant.
This module provides functions to search across multiple data sources.
"""
import os
import logging
import json
import requests
from typing import List, Dict, Any, Optional
import time
import random
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

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

class MultiSourceSearchEngine:
    """
    Search engine that can query multiple sources and aggregate results.
    """
    def __init__(self):
        self.registered_sources = {}
    
    def register_source(self, source_name: str, search_function, source_type: str):
        """Register a search function for a specific source"""
        self.registered_sources[source_name] = {
            "function": search_function,
            "type": source_type
        }
        logger.info(f"Registered search source: {source_name} (type: {source_type})")
    
    def search(self, query: str, sources: List[str] = None, max_results_per_source: int = 3) -> List[SearchResult]:
        """
        Search across multiple sources and return aggregated results
        
        Args:
            query: Search query string
            sources: List of source names to search (if None, search all registered sources)
            max_results_per_source: Maximum number of results to return per source
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        all_results = []
        sources_to_search = sources or self.registered_sources.keys()
        
        for source_name in sources_to_search:
            if source_name not in self.registered_sources:
                logger.warning(f"Source '{source_name}' not registered. Skipping.")
                continue
                
            source_config = self.registered_sources[source_name]
            search_function = source_config["function"]
            source_type = source_config["type"]
            
            try:
                logger.info(f"Searching source: {source_name}")
                source_results = search_function(query, max_results=max_results_per_source)
                
                # Convert to SearchResult objects if they aren't already
                for result in source_results:
                    if not isinstance(result, SearchResult):
                        content = result.get("content", "")
                        metadata = result.get("metadata", {})
                        relevance = result.get("relevance", 0.0)
                        
                        result_obj = SearchResult(
                            content=content,
                            source_name=source_name,
                            source_type=source_type,
                            relevance_score=relevance,
                            metadata=metadata
                        )
                        all_results.append(result_obj)
                    else:
                        all_results.append(result)
                        
            except Exception as e:
                logger.error(f"Error searching source '{source_name}': {str(e)}")
        
        # Sort results by relevance score, highest first
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_results
    
    def search_all(self, query: str, max_results_per_source: int = 3) -> List[SearchResult]:
        """Search all registered sources"""
        return self.search(query, sources=None, max_results_per_source=max_results_per_source)
    
    def search_specified(self, query: str, sources: List[str], max_results_per_source: int = 3) -> List[SearchResult]:
        """Search only specified sources"""
        return self.search(query, sources=sources, max_results_per_source=max_results_per_source)

# Sample search functions for different source types

def search_vector_index(query: str, index_name: str, max_results: int = 3) -> List[Dict]:
    """
    Search a vector index (placeholder for actual implementation)
    In a real implementation, this would connect to your vector DB
    """
    # Simulate some search results
    logger.info(f"Searching vector index: {index_name} for query: {query}")
    
    # This would be replaced with actual vector search
    results = []
    for i in range(min(max_results, 5)):
        # Generate a simulated result
        relevance = random.uniform(0.5, 0.95)
        content = f"This is a search result from index {index_name} related to '{query}'. " + \
                 f"It contains information that might be helpful for answering the query."
        
        result = {
            "content": content,
            "metadata": {
                "document_id": f"doc_{i}_{index_name}",
                "page_number": i + 1,
                "timestamp": "2023-08-15"
            },
            "relevance": relevance
        }
        results.append(result)
    
    # Simulate processing time
    time.sleep(0.5)
    return results

def web_search(query: str, max_results: int = 3) -> List[Dict]:
    """
    Perform a web search using a search engine API
    In a real implementation, this would connect to web search APIs
    """
    # Simulate web search results
    results = []
    
    # Simulate API call delay
    time.sleep(0.5)
    
    # Create some mock search results
    web_topics = [
        "Understanding the latest developments",
        "Key factors to consider in analysis",
        "Expert perspectives on the topic",
        "Historical context and evolution",
        "Recent breakthroughs and innovations",
        "Comparative studies and benchmarks",
        "Future trends and predictions"
    ]
    
    for i in range(min(max_results, 5)):
        # Generate a somewhat relevant result based on the query
        topic = random.choice(web_topics)
        content = f"According to web sources, {query} is related to {topic}. "
        content += f"Multiple experts have discussed this topic with varying perspectives. "
        content += f"Recent developments suggest important implications for this field."
        
        results.append({
            "content": content,
            "metadata": {
                "url": f"https://example.com/search?q={query.replace(' ', '+')}&result={i}",
                "title": f"{topic.title()} - Web Result",
                "snippet": content[:100] + "..."
            },
            "relevance": 0.7 - (i * 0.1)  # Decreasing relevance for demo purposes
        })
    
    return results

def technical_docs_search(query: str, max_results: int = 3) -> List[Dict]:
    """Search technical documentation sources"""
    results = []
    
    # Simulate technical docs search
    time.sleep(0.3)
    
    # Create some mock results
    technical_topics = [
        "Technical specifications and requirements",
        "Implementation details and architecture",
        "API documentation and usage examples",
        "Configuration options and best practices",
        "Performance considerations and optimizations"
    ]
    
    for i in range(min(max_results, 3)):
        topic = random.choice(technical_topics)
        content = f"Technical documentation for '{query}' describes {topic}. "
        content += f"The documentation provides detailed information on implementation approaches and considerations."
        
        results.append({
            "content": content,
            "metadata": {
                "doc_id": f"tech_{i}",
                "title": f"{topic} - Technical Documentation",
                "last_updated": "2025-07-15"
            },
            "relevance": 0.8 - (i * 0.1)
        })
    
    return results

def knowledge_base_search(query: str, max_results: int = 3) -> List[Dict]:
    """Search internal knowledge base"""
    results = []
    
    # Simulate KB search
    time.sleep(0.4)
    
    # Create some mock results
    kb_topics = [
        "Internal processes and procedures",
        "Company policies and guidelines",
        "Frequently asked questions",
        "Troubleshooting steps and solutions",
        "Best practices and recommendations"
    ]
    
    for i in range(min(max_results, 4)):
        topic = random.choice(kb_topics)
        content = f"The knowledge base entry for '{query}' covers {topic}. "
        content += f"This information is maintained by the organization and regularly updated."
        
        results.append({
            "content": content,
            "metadata": {
                "kb_id": f"kb_{i}",
                "title": f"{topic} - Knowledge Base",
                "category": "Internal Documentation"
            },
            "relevance": 0.75 - (i * 0.1)
        })
    
    return results

def api_data_search(query: str, max_results: int = 3) -> List[Dict]:
    """Search data from external APIs"""
    results = []
    
    # Simulate API search
    time.sleep(0.6)
    
    # Create some mock results
    api_topics = [
        "Real-time market data",
        "Customer information",
        "Product inventory",
        "Financial metrics",
        "Operational statistics"
    ]
    
    for i in range(min(max_results, 3)):
        topic = random.choice(api_topics)
        content = f"API data related to '{query}' provides {topic}. "
        content += f"This data is retrieved from external systems through secure API connections."
        
        results.append({
            "content": content,
            "metadata": {
                "api_source": f"api_{i}",
                "data_type": topic,
                "timestamp": datetime.now().isoformat()
            },
            "relevance": 0.65 - (i * 0.1)
        })
    
    return results

# Initialize the search engine
search_engine = MultiSourceSearchEngine()

# Register default search sources
def initialize_search_sources():
    """Initialize and register all available search sources"""
    
    # Register web search
    search_engine.register_source("Web Search", web_search, "web")
    
    # Register technical documentation search
    search_engine.register_source("Technical Docs", technical_docs_search, "docs")
    
    # Register knowledge base search
    search_engine.register_source("Knowledge Base", knowledge_base_search, "kb")
    
    # Register API-based search
    search_engine.register_source("API Data", api_data_search, "api")
    
    # Register vector index search functions (simulated)
    search_engine.register_source(
        "AWS_index", 
        lambda query, max_results: search_vector_index(query, "AWS_index", max_results),
        "index"
    )
    
    search_engine.register_source(
        "company_docs", 
        lambda query, max_results: search_vector_index(query, "company_docs", max_results),
        "index"
    )
    
    logger.info(f"Registered {len(search_engine.registered_sources)} default search sources")

# Call this to initialize the search engine with default sources
initialize_search_sources()

def perform_multi_source_search(query: str, sources: List[str], max_results: int = 10, 
                              use_placeholders: bool = False) -> List[SearchResult]:
    """
    Perform a search across multiple sources
    
    Args:
        query: The search query
        sources: List of source names to search
        max_results: Maximum number of total results to return
        use_placeholders: If True, generate placeholder results for testing
    
    Returns:
        List of SearchResult objects
    """
    # If we're using placeholders (for testing or when sources aren't configured)
    if use_placeholders:
        return generate_placeholder_results(query, sources)
    
    # Determine max results per source (distribute evenly with at least 1 per source)
    max_per_source = max(1, max_results // len(sources)) if sources else 0
    
    # Perform the search
    results = search_engine.search(query, sources, max_per_source)
    
    # If no results were found, try to provide some helpful information
    if not results and sources:
        # Add a "no results" placeholder for each source
        for source in sources:
            source_type = "unknown"
            if "Web" in source:
                source_type = "web"
            elif "API" in source:
                source_type = "api"
            elif "Document" in source:
                source_type = "index"
            elif "Data" in source:
                source_type = "structured"
            
            no_result = SearchResult(
                content=f"No information found for query: '{query}'",
                source_name=source,
                source_type=source_type,
                relevance_score=0.0,
                metadata={"query": query, "status": "no_results"}
            )
            results.append(no_result)
    
    # Limit to max_results
    return results[:max_results]

def generate_placeholder_results(query: str, sources: List[str]) -> List[SearchResult]:
    """Generate placeholder results for testing or when real sources aren't available"""
    results = []
    
    for source in sources:
        source_type = "unknown"
        content = ""
        metadata = {}
        
        if "Index" in source or "index" in source:
            source_type = "index"
            content = f"This is placeholder content from the indexed documents about '{query}'. "
            content += "The vector database would normally return relevant chunks of text from the documents."
            metadata = {"document_id": "doc-123", "title": "Sample Document"}
            
        elif "Web" in source:
            source_type = "web"
            content = f"Web search results for '{query}' would appear here. "
            content += "This would typically include snippets from relevant web pages."
            metadata = {"url": "https://example.com/search-results", "date": "2025-08-24"}
            
        elif "API" in source:
            source_type = "api"
            content = f"Data from API calls related to '{query}' would be shown here. "
            content += "This might include structured data from external services."
            metadata = {"api": "sample-api", "endpoint": "/search", "timestamp": "2025-08-24T12:00:00Z"}
            
        elif "Tech" in source or "Docs" in source:
            source_type = "docs"
            content = f"Technical documentation related to '{query}' would be displayed here. "
            content += "This would include specifications, guides, and implementation details."
            metadata = {"doc_type": "technical", "category": "documentation"}
            
        elif "Knowledge" in source:
            source_type = "kb"
            content = f"Knowledge base entries about '{query}' would appear here. "
            content += "This would include internal documentation and best practices."
            metadata = {"kb_id": "kb-456", "category": "Internal"}
            
        else:
            source_type = "unknown"
            content = f"Information about '{query}' from {source} would appear here."
        
        # Create a search result with some randomized relevance score
        relevance = random.uniform(0.5, 0.95)
        result = SearchResult(
            content=content,
            source_name=source,
            source_type=source_type,
            relevance_score=relevance,
            metadata=metadata
        )
        
        results.append(result)
    
    # Sort by relevance score (descending)
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    return results

def format_search_results_for_agent(results: List[SearchResult]) -> str:
    """
    Format search results into a string suitable for including in agent responses
    
    Args:
        results: List of SearchResult objects
    
    Returns:
        Formatted string with search results
    """
    if not results:
        return """
### Search Results

**No specific information was found in the selected knowledge sources.**

This could be due to:
- The query may be too specific or use terminology not present in the sources
- The requested information might not be available in the selected sources
- Additional sources may need to be selected for more comprehensive results

Consider:
- Rephrasing your query with different terms
- Selecting additional knowledge sources
- Providing more context in your task description
"""
    
    output = "### Information Retrieved from Sources\n\n"
    
    # Group by source type
    source_types = {}
    for result in results:
        source_type = result.source_type.title() if hasattr(result, 'source_type') else "Unknown"
        if source_type not in source_types:
            source_types[source_type] = []
        source_types[source_type].append(result)
    
    # Format each source type
    for source_type, type_results in source_types.items():
        output += f"#### {source_type} Sources\n"
        
        for i, result in enumerate(type_results):
            # Add more detailed information about the source
            output += f"**From {result.source_name}** (relevance: {result.relevance_score:.2f}):\n"
            
            # Add metadata if available
            if hasattr(result, 'metadata') and result.metadata:
                if 'title' in result.metadata:
                    output += f"*Source: {result.metadata['title']}*\n"
                if 'url' in result.metadata:
                    output += f"*URL: {result.metadata['url']}*\n"
                if 'date' in result.metadata:
                    output += f"*Date: {result.metadata['date']}*\n"
                    
            # Add the content with better formatting
            content = result.content if hasattr(result, 'content') else "No content available"
            output += "<div class='search-result-item'>\n"
            output += f"{content.strip()}\n"
            output += "</div>\n\n"
    
    # Add a summary section
    output += "#### Search Summary\n"
    output += f"- **Total results found:** {len(results)}\n"
    output += f"- **Source types used:** {', '.join(source_types.keys())}\n"
    
    # Find the most relevant source if there are results
    if results:
        most_relevant = max(results, key=lambda x: x.relevance_score if hasattr(x, 'relevance_score') else 0)
        source_name = most_relevant.source_name if hasattr(most_relevant, 'source_name') else "Unknown"
        relevance_score = most_relevant.relevance_score if hasattr(most_relevant, 'relevance_score') else 0
        output += f"- **Most relevant source:** {source_name} (score: {relevance_score:.2f})\n\n"
    
    return output
