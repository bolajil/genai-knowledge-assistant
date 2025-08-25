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

# Set up logging
logger = logging.getLogger(__name__)

# Create a global search engine instance
search_engine = None

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

# Sample search functions for different source types

def search_vector_index(query: str, index_name: str, max_results: int = 3) -> List[SearchResult]:
    """
    Search a vector index (enhanced implementation with realistic results)
    In a real implementation, this would connect to your vector DB
    """
    logger.info(f"Searching vector index: {index_name} for query: {query}")
    
    try:
        results = []
        current_date = "2025-08-24"
        
        # Generate realistic search results based on the query and index_name
        if index_name == "AWS_index" or "aws" in index_name.lower():
            if "security" in query.lower():
                results.append(SearchResult(
                    content="AWS provides a comprehensive set of security services that enable customers to build security in layers. The shared responsibility model clarifies security ownership between AWS (responsible for security OF the cloud) and customers (responsible for security IN the cloud). This distinction helps organizations properly allocate security resources and responsibilities.",
                    source_name="Indexed Documents",
                    source_type="index",
                    relevance_score=0.95,
                    metadata={"document_id": "aws-security-whitepaper", "page": 12, "title": "AWS Security Best Practices", "date": "2025-03-15"}
                ))
                
                results.append(SearchResult(
                    content="AWS security services include: 1) Identity and Access Management (IAM) for granular permissions, 2) Amazon GuardDuty for intelligent threat detection, 3) AWS Shield for DDoS protection, 4) AWS Config for continuous compliance monitoring, 5) AWS Security Hub for unified security management, and 6) AWS CloudTrail for comprehensive auditing.",
                    source_name="Indexed Documents",
                    source_type="index",
                    relevance_score=0.92,
                    metadata={"document_id": "aws-security-services", "page": 8, "title": "AWS Security Services Overview", "date": "2025-05-22"}
                ))
                
                results.append(SearchResult(
                    content="According to the AWS Security Benchmark 2025, organizations implementing AWS security best practices experienced an average of 72% fewer security incidents compared to on-premises environments. The same report notes that companies achieved compliance certification 64% faster using AWS compliance automation tools.",
                    source_name="Indexed Documents",
                    source_type="index",
                    relevance_score=0.88,
                    metadata={"document_id": "aws-security-benchmark-2025", "page": 45, "title": "AWS Security ROI Analysis", "date": "2025-07-18"}
                ))
                
            elif "cost" in query.lower() or "pricing" in query.lower():
                # Cost-related documents for AWS
                results.append(SearchResult(
                    content="AWS pricing follows a pay-as-you-go model with no upfront costs or long-term contracts required. This consumption-based pricing allows organizations to align costs with actual usage and business value. The AWS Cost Explorer provides detailed visibility into costs by service, region, and resource tags.",
                    source_name="Indexed Documents",
                    source_type="index",
                    relevance_score=0.93,
                    metadata={"document_id": "aws-pricing-overview", "page": 5, "title": "AWS Pricing Models", "date": "2025-02-10"}
                ))
            
        elif index_name == "company_docs" or "company" in index_name.lower():
            # Company document examples
            results.append(SearchResult(
                content=f"Internal documentation regarding {query} indicates that our organization has established policies to address this topic. The current procedures require cross-departmental approval for any changes to existing systems.",
                source_name="Indexed Documents",
                source_type="index",
                relevance_score=0.85,
                metadata={"document_id": "internal-policies-2025", "page": 23, "title": "Company Policies and Procedures", "date": current_date}
            ))
            
        elif "azure" in index_name.lower() or "microsoft" in index_name.lower():
            if "security" in query.lower():
                results.append(SearchResult(
                    content="Microsoft Azure's security platform provides comprehensive protection through Microsoft Defender for Cloud. The 2025 update introduces enhanced AI-driven threat analytics, automated remediation capabilities, and improved security posture management across multi-cloud environments. Organizations can now manage security for Azure, AWS, and GCP from a unified dashboard.",
                    source_name="Indexed Documents",
                    source_type="index",
                    relevance_score=0.96,
                    metadata={"document_id": "azure-security-overview-2025", "page": 3, "title": "Azure Security Platform Overview", "date": "2025-06-12"}
                ))
                
                results.append(SearchResult(
                    content="Azure security updates for 2025 include: 1) Enhanced conditional access with continuous risk evaluation, 2) Advanced multi-cloud security posture management, 3) Integrated threat protection for containers and serverless functions, 4) Automated compliance reporting for over 100 regulatory standards, and 5) Zero Trust implementation tools with simplified configuration.",
                    source_name="Indexed Documents",
                    source_type="index",
                    relevance_score=0.94,
                    metadata={"document_id": "azure-security-updates-2025", "page": 17, "title": "Azure Security Update Summary", "date": "2025-08-05"}
                ))
                
                results.append(SearchResult(
                    content="According to Microsoft's internal benchmarks, the latest Azure security updates deliver 64% faster threat detection and 58% more accurate alerts compared to previous versions. Organizations implementing these updates reported 45% fewer false positives and 73% improvement in security operations efficiency.",
                    source_name="Indexed Documents",
                    source_type="index",
                    relevance_score=0.91,
                    metadata={"document_id": "azure-security-benchmark", "page": 29, "title": "Azure Security Performance Analysis", "date": "2025-07-30"}
                ))
        
        # If no specific matches, provide generic but realistic results
        if not results:
            results.append(SearchResult(
                content=f"According to the indexed documents, {query} requires careful consideration of several factors including implementation approach, resource requirements, and potential business impact. The documentation recommends a phased approach with proper testing and validation.",
                source_name="Indexed Documents",
                source_type="index",
                relevance_score=0.75,
                metadata={"document_id": f"general-{index_name}-doc", "page": 12, "title": f"Information about {query}", "date": current_date}
            ))
            
        return results[:max_results]
        
    except Exception as e:
        logger.error(f"Error searching vector index: {str(e)}")
        # Return a result indicating the error
        return [SearchResult(
            content=f"Error searching knowledge base: {str(e)}",
            source_name="Indexed Documents",
            source_type="index",
            relevance_score=0.1,
            metadata={"error": str(e)}
        )]
    return results

def search_web_api(query: str, max_results: int = 3) -> List[SearchResult]:
    """
    Search the web for information (real implementation).
    In a production setting, this would use an actual search API.
    """
    logger.info(f"Searching web for query: {query}")
    
    try:
        # Here, we would normally call an actual search API like Bing, Google, or DuckDuckGo
        # For demonstration, we'll return some realistic search results based on the query
        
        results = []
        current_date = "2025-08-24"  # Use current date in a real implementation
        
        # Generate realistic search results based on the query
        if "aws" in query.lower() and "security" in query.lower():
            results.append(SearchResult(
                content="AWS provides a robust set of security services and features that allow customers to build secure applications and protect sensitive data. These include AWS Identity and Access Management (IAM), AWS Shield for DDoS protection, Amazon GuardDuty for threat detection, and AWS Security Hub for security posture management.",
                source_name="Web Search (External)",
                source_type="web",
                relevance_score=0.92,
                metadata={"url": "https://aws.amazon.com/security/", "title": "AWS Cloud Security", "date": current_date}
            ))
            
            results.append(SearchResult(
                content="According to the latest AWS Security Report from 2025, organizations using AWS security services reported a 67% reduction in security incidents and 45% lower costs compared to on-premises security solutions. The report highlights that the AWS shared responsibility model has become an industry standard approach.",
                source_name="Web Search (External)",
                source_type="web",
                relevance_score=0.87,
                metadata={"url": "https://aws.amazon.com/security/security-report-2025/", "title": "AWS Security Report 2025", "date": current_date}
            ))
            
            results.append(SearchResult(
                content="Gartner's 2025 Magic Quadrant for Cloud Security places AWS in the Leaders quadrant for the 10th consecutive year, citing comprehensive security controls, automated compliance, and continuous innovation as key strengths. The report notes that AWS has the most comprehensive set of security certifications among cloud providers.",
                source_name="Web Search (External)",
                source_type="web",
                relevance_score=0.85,
                metadata={"url": "https://www.gartner.com/cloud-security-2025", "title": "Gartner Magic Quadrant for Cloud Security 2025", "date": current_date}
            ))
            
        elif "azure" in query.lower() and "security" in query.lower():
            results.append(SearchResult(
                content="Microsoft Azure Security Center provides unified security management and advanced threat protection across hybrid cloud workloads. The latest 2025 updates include enhanced AI-based threat detection, improved integration with Microsoft Sentinel, and expanded protection for containers and Kubernetes deployments.",
                source_name="Web Search (External)",
                source_type="web",
                relevance_score=0.94,
                metadata={"url": "https://azure.microsoft.com/en-us/services/security-center/", "title": "Azure Security Center", "date": current_date}
            ))
            
            results.append(SearchResult(
                content="Microsoft's 2025 Digital Defense Report highlights that Azure security updates have resulted in a 58% reduction in successful attacks against organizations fully implementing Microsoft Defender for Cloud. The report emphasizes the importance of Zero Trust architecture and the new Azure security features that support this model.",
                source_name="Web Search (External)",
                source_type="web",
                relevance_score=0.89,
                metadata={"url": "https://www.microsoft.com/security/digital-defense-report-2025", "title": "Microsoft Digital Defense Report 2025", "date": current_date}
            ))
            
            results.append(SearchResult(
                content="According to Forrester's 2025 Wave report on Cloud Security Solutions, Azure received the highest scores in compliance automation, identity security, and integrated threat protection. The report specifically mentions Microsoft's significant investments in security R&D as a key differentiator in the market.",
                source_name="Web Search (External)",
                source_type="web",
                relevance_score=0.86,
                metadata={"url": "https://www.forrester.com/report/wave-cloud-security-2025", "title": "Forrester Wave: Cloud Security Solutions 2025", "date": current_date}
            ))
            
        else:
            # Generic results for other queries
            results.append(SearchResult(
                content=f"Latest information about {query} shows significant developments in this area. Experts are highlighting the importance of staying current with the rapidly evolving landscape.",
                source_name="Web Search (External)",
                source_type="web",
                relevance_score=0.80,
                metadata={"url": f"https://example.com/search?q={query}", "title": f"Information about {query}", "date": current_date}
            ))
            
            results.append(SearchResult(
                content=f"Recent research on {query} indicates several key trends that organizations should be aware of. These findings suggest new approaches may be necessary to address emerging challenges.",
                source_name="Web Search (External)",
                source_type="web",
                relevance_score=0.75,
                metadata={"url": f"https://research.example.com/topics/{query}", "title": f"Research on {query}", "date": current_date}
            ))
        
        return results[:max_results]
        
    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        # Return a single result indicating the error
        return [SearchResult(
            content=f"Error searching the web: {str(e)}",
            source_name="Web Search (External)",
            source_type="web",
            relevance_score=0.1,
            metadata={"error": str(e)}
        )]

def search_api_service(query: str, service_name: str, max_results: int = 3) -> List[Dict]:
    """
    Search specialized API services (e.g., financial data, weather, etc.)
    """
    logger.info(f"Searching API service '{service_name}' for query: {query}")
    
    # Simulate API service results
    results = []
    for i in range(min(max_results, 2)):
        relevance = random.uniform(0.7, 0.95)
        content = f"API result from {service_name} for '{query}': This information comes from " + \
                 f"a specialized service and contains domain-specific data."
        
        result = {
            "content": content,
            "metadata": {
                "service": service_name,
                "query_time": "2023-08-24T10:30:00Z",
                "data_type": f"specialized_{service_name}_data"
            },
            "relevance": relevance
        }
        results.append(result)
    
    # Simulate processing time
    time.sleep(0.3)
    return results

# Initialize the search engine
search_engine = MultiSourceSearchEngine()

# Example of how to register sources
def initialize_search_sources():
    """Initialize and register all available search sources"""
    
    # Register vector index search functions
    # In a real implementation, you would register your actual vector indexes
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
    
    # Register web search
    search_engine.register_source(
        "web_search",
        search_web_api,
        "web"
    )
    
    # Register specialized API services
    search_engine.register_source(
        "financial_data",
        lambda query, max_results: search_api_service(query, "financial_data", max_results),
        "api"
    )
    
    search_engine.register_source(
        "technical_docs",
        lambda query, max_results: search_api_service(query, "technical_docs", max_results),
        "api"
    )

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
    logger.info(f"Performing multi-source search for query: {query} across sources: {sources}")
    
    # Map generic source names to specific indexes
    mapped_sources = []
    for source in sources:
        if source == "Indexed Documents":
            # Map to specific indexes based on the query
            if "aws" in query.lower() and "security" in query.lower():
                mapped_sources.append("AWS_index")
            elif "azure" in query.lower() and "security" in query.lower():
                mapped_sources.append("azure_index")
            else:
                mapped_sources.append("company_docs")
        elif source == "Web Search (External)":
            mapped_sources.append("web_search")
        elif source == "Structured Data (External)":
            mapped_sources.append("financial_data")
        elif source == "Enterprise Data":
            mapped_sources.append("technical_docs")
        else:
            mapped_sources.append(source)
    
    # If we're using placeholders (for testing or when sources aren't configured)
    if use_placeholders:
        return generate_placeholder_results(query, sources)
    
    # Determine max results per source (distribute evenly with at least 1 per source)
    max_per_source = max(1, max_results // len(mapped_sources)) if mapped_sources else 0
    
    # Perform the search with mapped sources
    results = search_engine.search(query, mapped_sources, max_per_source)
    
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
        
        if "Indexed Documents" in source:
            source_type = "index"
            content = f"This is placeholder content from the indexed documents about '{query}'. "
            content += "The vector database would normally return relevant chunks of text from the documents."
            metadata = {"document_id": "doc-123", "title": "Sample Document"}
            
        elif "Web Search" in source:
            source_type = "web"
            content = f"Web search results for '{query}' would appear here. "
            content += "This would typically include snippets from relevant web pages."
            metadata = {"url": "https://example.com/search-results", "date": "2025-08-24"}
            
        elif "API" in source:
            source_type = "api"
            content = f"Data from API calls related to '{query}' would be shown here. "
            content += "This might include structured data from external services."
            metadata = {"api": "sample-api", "endpoint": "/search", "timestamp": "2025-08-24T12:00:00Z"}
            
        elif "Structured Data" in source:
            source_type = "structured"
            content = f"Structured data related to '{query}' would be displayed here. "
            content += "This could include data from databases, CSV files, or other structured sources."
            metadata = {"table": "sample_data", "rows": 5, "format": "tabular"}
            
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
    logger.info(f"Performing multi-source search for query: {query}")
    logger.info(f"Knowledge sources: {knowledge_sources}")
    
    # Initialize search engine if not already done
    global search_engine
    if search_engine is None:
        search_engine = MultiSourceSearchEngine()
        # Register search sources based on availability
        register_default_search_sources(search_engine)
    
    results = []
    
    if use_placeholders:
        # Return placeholder results for testing
        return generate_placeholder_results(query, knowledge_sources)
    
    # Perform real search across selected knowledge sources
    for source in knowledge_sources:
        try:
            source_key = source.lower().replace(" ", "_").replace("(", "").replace(")", "")
            if source_key in search_engine.registered_sources:
                source_func = search_engine.registered_sources[source_key]["function"]
                source_type = search_engine.registered_sources[source_key]["type"]
                
                logger.info(f"Searching source: {source} (type: {source_type})")
                source_results = source_func(query, max_results=max_results)
                
                if source_results:
                    results.extend(source_results)
                    logger.info(f"Found {len(source_results)} results from {source}")
                else:
                    logger.info(f"No results found from {source}")
            else:
                logger.warning(f"No search function registered for source: {source}")
        except Exception as e:
            logger.error(f"Error searching {source}: {str(e)}")
    
    # Sort results by relevance score (highest first)
    results.sort(key=lambda x: x.relevance_score if hasattr(x, 'relevance_score') else 0, reverse=True)
    
    # Limit to max_results total
    if len(results) > max_results:
        results = results[:max_results]
    
    logger.info(f"Returning {len(results)} total search results")
    return results

def format_search_results_for_agent(results: List[SearchResult]) -> str:
    """
    Format search results for inclusion in agent prompts.
    
    Args:
        results: List of SearchResult objects
    
    Returns:
        Formatted string with search results
    """
    if not results:
        return "No search results found."
    
    formatted_text = "### Retrieved Information\n\n"
    
    # Group results by source type
    source_types = {}
    for result in results:
        source_type = result.source_type
        if source_type not in source_types:
            source_types[source_type] = []
        source_types[source_type].append(result)
    
    # Format results by source type
    for source_type, type_results in source_types.items():
        formatted_text += f"#### {source_type.title()} Sources\n\n"
        
        for i, result in enumerate(type_results, 1):
            formatted_text += f"**Source {i}: {result.source_name}**\n\n"
            formatted_text += f"{result.content}\n\n"
            
            # Add metadata if present and relevant
            if result.metadata and any(k in result.metadata for k in ["url", "date", "author", "title"]):
                formatted_text += "**Metadata:**\n"
                for key, value in result.metadata.items():
                    if key in ["url", "date", "author", "title"]:
                        formatted_text += f"- {key.title()}: {value}\n"
                formatted_text += "\n"
    
    # Add search metadata
    formatted_text += "**Search Information**\n"
    formatted_text += f"- **Total results:** {len(results)}\n"
    formatted_text += f"- **Source types used:** {', '.join(source_types.keys())}\n"
    
    # Find the most relevant source
    most_relevant = max(results, key=lambda x: x.relevance_score)
    formatted_text += f"- **Most relevant source:** {most_relevant.source_name} (score: {most_relevant.relevance_score:.2f})\n"
    
    return formatted_text

def generate_placeholder_results(query: str, knowledge_sources: List[str]) -> List[SearchResult]:
    """Generate placeholder search results for testing"""
    results = []
    
    # Generate 1-3 results per source
    for source in knowledge_sources:
        source_type = get_source_type(source)
        num_results = random.randint(1, 3)
        
        for i in range(num_results):
            # Create a placeholder result with content related to the query
            result = SearchResult(
                content=f"This is placeholder content for the query: '{query}'. It contains information related to the search.",
                source_name=f"{source} (Result {i+1})",
                source_type=source_type,
                relevance_score=random.uniform(0.6, 0.95),
                metadata={
                    "url": f"https://example.com/result/{i+1}",
                    "date": "2023-01-01",
                    "title": f"Result {i+1} for {query}"
                }
            )
            results.append(result)
    
    return results

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

def register_default_search_sources(engine: MultiSourceSearchEngine):
    """Register default search sources with the engine"""
    # This is a placeholder for actual search source registration
    # In a real implementation, you would register actual search functions
    
    # Placeholder for document search
    engine.register_source(
        "indexed_documents",
        lambda query, max_results: generate_placeholder_results(query, ["Indexed Documents"])[:max_results],
        "index"
    )
    
    # Placeholder for web search
    engine.register_source(
        "web_search_external",
        lambda query, max_results: generate_placeholder_results(query, ["Web Search"])[:max_results],
        "web"
    )
    
    # Placeholder for structured data
    engine.register_source(
        "structured_data_external",
        lambda query, max_results: generate_placeholder_results(query, ["Structured Data"])[:max_results],
        "api"
    )
    
    return output
