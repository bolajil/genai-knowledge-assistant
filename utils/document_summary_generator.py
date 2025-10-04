"""
Modified document summary generator that uses actual search results
"""

import re
from typing import List, Dict, Any, Optional

def extract_content_from_search_results(search_results_text: str) -> Dict[str, Any]:
    """
    Extract useful content from search results for document summary generation
    
    Args:
        search_results_text: Formatted search results text
        
    Returns:
        Dictionary with extracted key points, findings, and sources
    """
    # Initialize extraction results
    extracted = {
        "key_points": [],
        "context": "",
        "findings": [],
        "sources": [],
        "recommendations": []
    }
    
    if not search_results_text or "No search results found" in search_results_text:
        return extracted
    
    # Extract content from individual search results
    results_sections = re.split(r'\*\*Result \d+', search_results_text)
    
    for section in results_sections[1:]:  # Skip the header section
        # Extract source
        source_match = re.search(r'\*Source: (.*?) \|', section)
        if source_match:
            source = source_match.group(1).strip()
            if source not in extracted["sources"]:
                extracted["sources"].append(source)
        
        # Get the main content (exclude metadata)
        content_parts = section.split("*Source:", 1)
        if len(content_parts) > 0:
            content = content_parts[0].strip()
            
            # Extract sentences for key points (first 2-3 sentences from each result)
            sentences = re.split(r'(?<=[.!?])\s+', content)
            key_sentences = sentences[:min(3, len(sentences))]
            for sentence in key_sentences:
                if sentence and len(sentence) > 20 and sentence not in extracted["key_points"]:
                    extracted["key_points"].append(sentence)
            
            # Add to context
            if content:
                extracted["context"] += content + "\n\n"
            
            # Look for findings/facts in the content
            fact_patterns = [
                r'\d+%', r'increased by', r'decreased by', r'improved', r'reduced',
                r'enables', r'provides', r'supports', r'allows', r'ensures'
            ]
            
            for pattern in fact_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Get a reasonable window around the match
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 100)
                    window = content[start:end]
                    
                    # Find sentence boundaries
                    sentence_start = max(0, start - content[max(0, start-100):start].rfind('.'))
                    sentence_end = end + content[end:min(len(content), end+100)].find('.')
                    if sentence_end < end:  # No period found
                        sentence_end = end
                    
                    finding = content[sentence_start:sentence_end+1].strip()
                    if finding and finding not in extracted["findings"] and len(finding) > 10:
                        extracted["findings"].append(finding)
            
            # Look for recommendations in the content
            rec_patterns = [
                r'recommend', r'should', r'advised to', r'best practice', 
                r'important to', r'necessary to', r'suggested', r'consider'
            ]
            
            for pattern in rec_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Get a reasonable window around the match
                    start = max(0, match.start() - 30)
                    end = min(len(content), match.end() + 100)
                    window = content[start:end]
                    
                    # Find sentence boundaries
                    sentence_start = max(0, start - content[max(0, start-100):start].rfind('.'))
                    sentence_end = end + content[end:min(len(content), end+100)].find('.')
                    if sentence_end < end:  # No period found
                        sentence_end = end
                    
                    recommendation = content[sentence_start:sentence_end+1].strip()
                    if recommendation and recommendation not in extracted["recommendations"] and len(recommendation) > 10:
                        extracted["recommendations"].append(recommendation)
    
    # Limit to reasonable amounts
    extracted["key_points"] = extracted["key_points"][:5]
    extracted["findings"] = extracted["findings"][:6]
    extracted["recommendations"] = extracted["recommendations"][:4]
    
    return extracted

def generate_document_summary_from_search(task: str, search_results_text: str) -> str:
    """
    Generate a document summary using actual search results content
    
    Args:
        task: The user's task description
        search_results_text: Formatted search results text
        
    Returns:
        A document summary based on search results
    """
    if not search_results_text or "No search results found" in search_results_text:
        # Fall back to generic summary if no search results
        return f"""
## Document Summary

### Executive Summary
No specific information was found in the knowledge base about "{task}". This is a generic summary template.

### Key Points
1. No specific data was found for your query
2. Consider refining your search terms
3. Try selecting different knowledge sources

### Context and Background
The requested information about "{task}" could not be found in the selected knowledge sources.

### Methodology
This summary would normally analyze information retrieved from the knowledge sources you selected.

### Detailed Findings
Without specific information, detailed findings cannot be provided.

### Implications
Without specific data, implications cannot be determined.

### Recommendations
1. Try searching with different keywords
2. Select additional knowledge sources
3. Consider adding specific documents to the knowledge base if this is an important topic
"""
    
    # Extract content from search results
    extracted = extract_content_from_search_results(search_results_text)
    
    # Create title from task
    title = task[:50] + ("..." if len(task) > 50 else "")
    
    # Generate the summary using extracted content
    key_points = "\n".join([f"{i+1}. {point}" for i, point in enumerate(extracted["key_points"])])
    if not key_points:
        key_points = "1. No specific key points were identified in the search results"
    
    findings = ""
    for i, finding in enumerate(extracted["findings"]):
        findings += f"{i+1}) {finding}\n\n"
    if not findings:
        findings = "No specific findings were identified in the search results."
    
    recommendations = "\n".join([f"{i+1}. {rec}" for i, rec in enumerate(extracted["recommendations"])])
    if not recommendations:
        recommendations = "1. Consider gathering more information about this topic\n2. Consult additional sources for specific recommendations"
    
    # Create the sources section
    sources_text = ", ".join(extracted["sources"]) if extracted["sources"] else "No specific sources identified"
    
    return f"""
## Document Summary

### Executive Summary
This document provides a summary of information related to "{title}", based on the search results from knowledge sources.

### Key Points
{key_points}

### Context and Background
{extracted["context"][:500] + "..." if len(extracted["context"]) > 500 else extracted["context"]}

### Methodology
This summary analyzes information retrieved from the following knowledge sources: {sources_text}.

### Detailed Findings
{findings}

### Implications
The information presented has several implications for understanding {title}.

### Recommendations
{recommendations}
"""

def should_use_custom_generator(task: str) -> bool:
    """
    Determine if we should use the custom generator based on the task
    
    Args:
        task: The user's task description
        
    Returns:
        Boolean indicating whether to use custom generator
    """
    # Skip custom generator for AWS and Azure specific tasks (to be removed after testing)
    aws_terms = ["aws security", "aws cloud", "amazon web services"]
    azure_terms = ["azure security", "azure cloud", "microsoft azure"]
    
    for term in aws_terms + azure_terms:
        if term in task.lower():
            return False
    
    return True
