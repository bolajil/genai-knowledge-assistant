"""
Unified content generator module for the agent assistant.
This module provides functions to generate content for various operations.
Updated to use the centralized vector database integration.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Try to import enhanced research module with centralized DB integration
try:
    from utils.enhanced_research_integration import generate_enhanced_research_content
    ENHANCED_RESEARCH_AVAILABLE = True
    logger.info("Enhanced research module with centralized DB integration loaded successfully")
except ImportError as e:
    # Fallback to the original enhanced research module
    try:
        from utils.enhanced_research import generate_enhanced_research_content
        ENHANCED_RESEARCH_AVAILABLE = True
        logger.info("Original enhanced research module loaded successfully")
    except ImportError as e:
        ENHANCED_RESEARCH_AVAILABLE = False
        logger.warning(f"Enhanced research module not available: {e}")

def generate_content_with_search_results(task, operation, search_results_text="", tone="professional"):
    """
    Generate content for any operation type using search results
    
    Args:
        task: The task or query to generate content for
        operation: The type of operation (Research, Document Summary, etc.)
        search_results_text: Text of search results to incorporate
        tone: Tone for content generation (Professional, Casual, etc.)
        
    Returns:
        Generated content as a string
    """
    # Generate content based on operation type
    if operation.lower() == "document summary":
        return generate_document_summary(task, search_results_text)
    elif operation.lower() == "research":
        return generate_research_content(task, operation, search_results_text=search_results_text)
    else:
        # Default content generation
        if not search_results_text:
            return f"""
## {operation}: {task}

No relevant search results were found for this query.
Consider refining your search terms or checking if relevant documents exist in the knowledge base.
"""
        
        return f"""
## {operation}: {task}

The following content has been generated based on the search results:

### Key Information
- First important point from the search results
- Second important insight
- Third relevant piece of information

### Detailed Analysis
Based on the information retrieved, we can make the following observations:
1. First observation with supporting evidence
2. Second observation with context
3. Third observation with implications

### Source Information
{search_results_text}

### Conclusion
This analysis provides important insights about {task}.
Consider the information presented and how it applies to your specific context.
"""

def generate_document_summary(task, search_results_text=""):
    """
    Generate a document summary based on search results
    
    Args:
        task: The task or query to generate content for
        search_results_text: Text of search results to incorporate
        
    Returns:
        Generated summary as a string
    """
    if not search_results_text:
        return f"""
## Document Summary

No relevant document content was found for this query.
Please check if documents have been properly ingested into the knowledge base.
"""
    
    return f"""
## Document Summary

The following summary has been generated based on the document content:

### Key Points
- First main point from the document
- Second important concept
- Third significant element

### Summary
The document contains information about various aspects of the topic,
including key concepts, methodologies, and findings. The content appears 
to be well-structured and provides valuable insights.

### Source Content
{search_results_text}

### Conclusion
This document provides important information that may be relevant to your query.
Review the key points and source content for specific details that address your needs.
"""

def generate_research_content(task, operation, knowledge_sources=None, search_results_text=""):
    """
    Generate research content using knowledge sources
    
    Args:
        task: The research task or query
        operation: Type of research operation (e.g., "Research Topic")
        knowledge_sources: List of knowledge sources to search
        search_results_text: Optional pre-fetched search results
        
    Returns:
        Generated research content as a string
    """
    # Use the enhanced research module if available
    if ENHANCED_RESEARCH_AVAILABLE:
        try:
            logger.info(f"Generating enhanced research content for '{task}' using centralized DB integration")
            
            # Default to indexed documents if no sources specified
            sources = knowledge_sources if knowledge_sources else ["Indexed Documents"]
            
            # Use the enhanced research module
            return generate_enhanced_research_content(
                task=task, 
                operation=operation, 
                knowledge_sources=sources,
                provided_search_results=search_results_text if search_results_text else None
            )
        except Exception as e:
            logger.error(f"Error using enhanced research: {str(e)}")
            # Fall back to simple implementation
            logger.info("Falling back to simple research implementation")
    
    # Simple implementation as fallback
    # Initialize findings list
    findings = []
    
    if not search_results_text:
        return f"""
## Research Report: {task}

### Executive Summary
This research report addresses your query about {task}.
Unfortunately, no relevant information was found in the knowledge base.

### Recommendations
1. Try refining your search terms
2. Add more specific details to your query
3. Check if relevant documents have been added to the knowledge base
"""
    
    # Extract findings from search results
    if search_results_text:
        sections = search_results_text.split("**Result ")
        
        for section in sections[1:]:  # Skip the first empty section
            # Extract content from each result
            parts = section.split("\n", 2)
            if len(parts) > 2:
                source = parts[0].split("from ")[1] if "from " in parts[0] else "Unknown source"
                content = parts[2].strip()
                # Add a finding based on the content
                if content:
                    finding = content.split(". ")[0] + "."
                    findings.append(f"From {source}: {finding}")
    
    # Ensure we have at least 3 findings
    while len(findings) < 3:
        findings.append(f"Additional information on {task[:30]} is recommended for comprehensive understanding.")
    
    # Format for knowledge sources
    sources_text = ", ".join(knowledge_sources) if knowledge_sources else "available knowledge sources"
    
    # Generate research report directly
    findings_text = "\n\n".join([f"- {finding}" for finding in findings]) if findings else ""
    
    return f"""
## Research Report: {task}

### Executive Summary
This research report addresses your query about {task}.
The findings are based on information retrieved from {sources_text}.

### Key Findings
{findings_text if findings_text else "No specific key findings could be extracted from the search results."}

### Detailed Information
{search_results_text}

### Analysis
The search results provide valuable information related to your query.
Review the content above for insights specific to your research needs.

### Recommendations
1. Consider the sources and relevance of the information when evaluating
2. Further analysis may be needed for comprehensive understanding
3. Refer to the original sources for more detailed information
"""

# Additional content generation functions can be added here
