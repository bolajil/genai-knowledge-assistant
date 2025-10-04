"""
Unified content generator module for the agent assistant.
This module provides functions to generate content for various operations.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Try to import enhanced research module
try:
    from utils.enhanced_research import generate_enhanced_research_content
    ENHANCED_RESEARCH_AVAILABLE = True
    logger.info("Enhanced research module loaded successfully")
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

Based on the search results, here's the information related to your query:

{search_results_text}

This information was compiled from the available knowledge base. For more specific details,
consider refining your query or adding additional context.
"""

def generate_document_summary(task, search_results_text=""):
    """Generate a document summary using search results"""
    if not search_results_text:
        return f"""
## Document Summary

### Executive Summary
This document summarizes information related to: {task}
No relevant search results were found for this topic.

### Key Points
1. No specific information available in the knowledge base
2. Consider refining your search or adding relevant documents
3. The system could not find matching content for your query
"""
    
    return f"""
## Document Summary

### Executive Summary
This document summarizes information related to: {task}
The summary is based on information retrieved from the knowledge base.

{search_results_text}

### Key Points
Based on the search results above, the key points are:
1. The search results contain relevant information about your query
2. Review the information for insights related to your specific needs
3. The content comes from indexed documents in the knowledge base
"""

def generate_research_content(task, operation, knowledge_sources=None, search_results_text=""):
    """Generate research content using search results"""
    # Try to use enhanced research if available
    if ENHANCED_RESEARCH_AVAILABLE:
        try:
            # Convert knowledge_sources to list if it's None
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
    
    # Generate research report directly instead of calling other functions
    sources_text = ", ".join(knowledge_sources) if knowledge_sources else "available knowledge sources"
    
    # Format the findings into a nice report
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

# Helper function for internal use only - will be implemented if needed
def _generate_research_specific(task, operation, knowledge_sources, search_results_text, findings):
    """Generate research content"""
    sources_text = ", ".join(knowledge_sources) if knowledge_sources else "available knowledge sources"
    
    if search_results_text:
        return f"""
## Research Report: {task[:50]}

### Executive Summary
This research report investigates {task}, based on information retrieved from the knowledge sources.

### Introduction
This research examines {task} using information available in the selected knowledge sources.

### Search Results
{search_results_text}

### Key Findings
1. {findings[0] if findings else "No specific findings were extracted from the search results."}
2. {findings[1] if len(findings) > 1 else "Further research is recommended for a complete understanding."}
3. {findings[2] if len(findings) > 2 else "Consider consulting additional sources for comprehensive information."}

### Analysis
The research shows that the information retrieved from the knowledge sources provides insights specifically
related to the query: "{task}". The analysis is based directly on the search results shown above.

### Business Implications
Organizations can use this information to:
- Make informed decisions based on the research findings
- Consider the implications of the information for their specific context
- Identify areas where further research might be beneficial

### Recommendations
Based on this research:
1. Review the information from the search results carefully
2. Consider how it applies to your specific situation
3. Consult the original sources for more detailed information
4. Conduct additional research if needed for a comprehensive understanding
"""
    else:
        # No search results available
        knowledge_reference = ""
        if knowledge_sources:
            knowledge_reference = "\n\n### Knowledge Sources Used\n"
            for source in knowledge_sources:
                knowledge_reference += f"- {source}: No relevant information found\n"
        
        return f"""
## Research Report: {task[:50]}

### Executive Summary
This research report was meant to investigate {task}, but no relevant information was found in the knowledge sources.

### Introduction
The research attempted to examine {task} using the selected knowledge sources, but couldn't find specific information.

### No Relevant Information Found
Unfortunately, no specific information was found in the knowledge sources that directly addresses your research question.

### Suggestions
1. Try refining your research question to be more specific
2. Check if the relevant documents have been added to the knowledge base
3. Consider using different search terms
4. Expand the knowledge sources to include more relevant materials

{knowledge_reference}

### Next Steps
Please refine your query or add relevant documents to the knowledge base for better results.
"""

def generate_summary(task, search_results_text, findings):
    """Generate document summary"""
    if search_results_text:
        return f"""
## Document Summary

### Executive Summary
This document summarizes information related to: {task}
The summary is based on information retrieved from selected knowledge sources.

{search_results_text}

### Key Points
1. {findings[0] if findings else "No specific key points were found in the search results."}
2. {findings[1] if len(findings) > 1 else "Further analysis is recommended for a complete understanding."}
3. {findings[2] if len(findings) > 2 else "Consider consulting additional sources for comprehensive information."}
4. The information above is derived directly from the search results.

### Summary of Findings
The document provides information specifically related to the query: "{task}". 
The information has been retrieved from various knowledge sources and represents 
the most relevant content available at this time.

### Implications
The information presented has the following implications:
1. It provides direct answers based on available knowledge sources
2. The response is tailored to address the specific query
3. The information comes from the search results shown above
"""
    else:
        return f"""
## Document Summary

### Executive Summary
This document aims to summarize information related to: {task}
However, no specific information was found in the knowledge sources.

### Suggestions
1. Try refining your search query to be more specific
2. Check if the relevant documents have been added to the knowledge base
3. Consider using different search terms
4. Consult external sources for information on this topic

### Next Steps
Please refine your query or add relevant documents to the knowledge base for better results.
"""

def generate_content(task, tone, search_results_text, findings):
    """Generate content creation response"""
    if search_results_text:
        return f"""
## Content Creation

I've created the following content based on your request and the information retrieved from knowledge sources:

### {task}

{search_results_text}

{'#### Executive Summary' if tone == 'Professional' or tone == 'Technical' else '#### Introduction'}

This document provides information about {task}. It incorporates data from various knowledge sources
to give you accurate and relevant content.

{'### Key Points' if tone == 'Professional' else '### Main Ideas'}

1. {findings[0] if findings else "First important point related to the topic"}
2. {findings[1] if len(findings) > 1 else "Second significant aspect that needs attention"}
3. {findings[2] if len(findings) > 2 else "Third element that contributes to understanding"}

### Detailed Content

The information presented is based directly on the search results shown above. The content has been
organized to address your specific request: "{task}".

### Conclusion

Based on the search results presented, this document provides information specifically relevant to your query.
For more comprehensive information, you may want to explore the original sources in greater detail.
"""
    else:
        return f"""
## Content Creation

I'd like to create content for your request, but I don't have specific information from knowledge sources.

### {task}

#### No Relevant Information Found

Unfortunately, I couldn't find specific information in the knowledge sources that matches your request.
You might want to:

1. Try refining your search query to be more specific
2. Check if the relevant documents have been added to the knowledge base
3. Consider using different search terms

### Suggestions

If you'd like to proceed with content creation, please provide more specific information or check
that the relevant knowledge sources have been included in your search.
"""

def generate_generic(task, operation, search_results_text, findings):
    """Generate generic response for other operation types"""
    if search_results_text:
        return f"""
## {operation} Results

### Your Query
{task}

### Search Results
{search_results_text}

### Key Information
1. {findings[0] if findings else "No specific information was found in the search results."}
2. {findings[1] if len(findings) > 1 else "Consider refining your query for more specific results."}
3. {findings[2] if len(findings) > 2 else "The information is based on the search results shown above."}

### Summary
The information above is directly related to your query about {task}.
It represents the most relevant content found in the knowledge sources.
"""
    else:
        return f"""
## {operation} Results

### Your Query
{task}

### No Relevant Information Found
Unfortunately, no specific information was found in the knowledge sources that matches your query.

### Suggestions
1. Try refining your query to be more specific
2. Check if the relevant documents have been added to the knowledge base
3. Consider using different search terms
4. Expand your search to include more knowledge sources

### Next Steps
Please refine your query or add relevant documents to the knowledge base for better results.
"""
