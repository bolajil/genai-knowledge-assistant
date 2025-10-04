"""
Search-based research content generator that uses actual search results
"""

import re
from typing import List, Dict, Any, Optional

def extract_data_from_search_results(search_results_text: str, operation: str) -> Dict[str, Any]:
    """
    Extract relevant data from search results based on the research operation
    
    Args:
        search_results_text: Formatted search results text
        operation: The type of research operation
        
    Returns:
        Dictionary with extracted key findings, context, and recommendations
    """
    # Initialize extraction results
    extracted = {
        "key_findings": [],
        "context": "",
        "data_points": [],
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
            
            # Add to context
            if content:
                extracted["context"] += content + "\n\n"
            
            # Extract sentences for key findings (first 2-3 sentences from each result)
            sentences = re.split(r'(?<=[.!?])\s+', content)
            key_sentences = sentences[:min(3, len(sentences))]
            for sentence in key_sentences:
                if sentence and len(sentence) > 20 and sentence not in extracted["key_findings"]:
                    extracted["key_findings"].append(sentence)
            
            # Look for data points in the content based on the operation type
            if operation == "Data Analysis":
                # Look for percentages, numbers, statistics
                data_patterns = [r'\d+%', r'\d+\s+percent', r'increased by', r'decreased by', 
                                 r'\d+\.\d+', r'\$\d+', r'million', r'billion']
            elif operation == "Market Research":
                # Look for market-related terms
                data_patterns = [r'market share', r'growth rate', r'trend', r'segment', 
                                 r'competitor', r'customer', r'demand', r'forecast']
            elif operation == "Competitive Analysis":
                # Look for comparison terms
                data_patterns = [r'compared to', r'versus', r'advantage', r'better than',
                                 r'competitor', r'leading', r'market position', r'differentiator']
            else:
                # General research terms
                data_patterns = [r'finding', r'result', r'shows that', r'indicates', 
                                 r'according to', r'research', r'study', r'analysis']
            
            for pattern in data_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Get a reasonable window around the match
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 100)
                    
                    # Find sentence boundaries
                    sentence_start = max(0, start - content[max(0, start-100):start].rfind('.'))
                    sentence_end = end + content[end:min(len(content), end+100)].find('.')
                    if sentence_end < end:  # No period found
                        sentence_end = end
                    
                    data_point = content[sentence_start:sentence_end+1].strip()
                    if data_point and data_point not in extracted["data_points"] and len(data_point) > 10:
                        extracted["data_points"].append(data_point)
            
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
                    
                    # Find sentence boundaries
                    sentence_start = max(0, start - content[max(0, start-100):start].rfind('.'))
                    sentence_end = end + content[end:min(len(content), end+100)].find('.')
                    if sentence_end < end:  # No period found
                        sentence_end = end
                    
                    recommendation = content[sentence_start:sentence_end+1].strip()
                    if recommendation and recommendation not in extracted["recommendations"] and len(recommendation) > 10:
                        extracted["recommendations"].append(recommendation)
    
    # Limit to reasonable amounts
    extracted["key_findings"] = extracted["key_findings"][:5]
    extracted["data_points"] = extracted["data_points"][:6]
    extracted["recommendations"] = extracted["recommendations"][:4]
    
    return extracted

def generate_research_from_search(task: str, operation: str, knowledge_sources: List[str], search_results_text: str = "") -> str:
    """
    Generate research content based on actual search results
    
    Args:
        task: The user's task description
        operation: The type of research operation
        knowledge_sources: List of knowledge sources used
        search_results_text: Formatted search results text
        
    Returns:
        A research report based on the operation and search results
    """
    # If we don't have search results text, return a fallback
    if not search_results_text:
        return f"""
## Research Report: {task[:50]}

### Executive Summary
This research report attempts to examine {task[:50]}, but no information was available in the selected knowledge sources.
Consider refining your search or selecting different knowledge sources.

### Key Research Findings
1. No specific information was found on this topic
2. Consider refining your search terms
3. Try selecting different knowledge sources

### Research Methodology
The research attempted to use information from: {", ".join(knowledge_sources)}.
However, no relevant results were found.

### Recommendations
1. Try searching with different keywords
2. Select additional knowledge sources
3. Consider adding specific documents to the knowledge base if this is an important topic
"""
    
    # Extract data from search results
    extracted = extract_data_from_search_results(search_results_text, operation)
    
    # Format title based on operation and task
    if operation == "Data Analysis":
        title = f"Data Analysis Report: {task[:50]}"
    elif operation == "Market Research":
        title = f"Market Research: {task[:50]}"
    elif operation == "Competitive Analysis":
        title = f"Competitive Analysis: {task[:50]}"
    elif operation == "Problem Analysis":
        title = f"Problem Analysis: {task[:50]}"
    else:
        title = f"Research Report: {task[:50]}"
    
    # Format findings based on extracted data
    key_findings = ""
    for i, finding in enumerate(extracted["key_findings"], 1):
        key_findings += f"{i}. {finding}\n"
    if not key_findings:
        key_findings = "1. No specific key findings were identified in the search results."
    
    # Format data points based on operation
    data_section_title = ""
    if operation == "Data Analysis":
        data_section_title = "### Data Analysis Results"
    elif operation == "Market Research":
        data_section_title = "### Market Insights"
    elif operation == "Competitive Analysis":
        data_section_title = "### Competitive Landscape"
    elif operation == "Problem Analysis":
        data_section_title = "### Problem Factors"
    else:
        data_section_title = "### Detailed Findings"
    
    data_points = ""
    for i, point in enumerate(extracted["data_points"], 1):
        data_points += f"{i}) {point}\n\n"
    if not data_points:
        data_points = "No specific data points were identified in the search results."
    
    # Format recommendations
    recommendations = ""
    for i, rec in enumerate(extracted["recommendations"], 1):
        recommendations += f"{i}. {rec}\n"
    if not recommendations:
        recommendations = "1. Gather more specific information about this topic\n2. Consult additional sources for more detailed recommendations"
    
    # Create the sources section
    sources_text = ", ".join(extracted["sources"]) if extracted["sources"] else "No specific sources identified"
    
    # Build the response based on the operation
    if operation == "Data Analysis":
        return f"""
## {title}

### Executive Summary
This data analysis examines {task[:50]}, identifying key trends, patterns, and insights from the available data.
The analysis provides actionable findings that can inform decision-making and strategy development.

### Key Findings
{key_findings}

### Methodology
This analysis utilized data from the following sources: {sources_text}.
The analysis techniques included examining patterns, identifying trends, and extracting relevant data points from the search results.

{data_section_title}
{data_points}

### Implications
The data analysis has several implications:
- Business impacts include insights for strategic planning and resource allocation
- Performance indicators suggest areas for optimization and improvement
- Decision support for both short-term actions and long-term planning

### Recommendations
{recommendations}
"""
    elif operation == "Market Research":
        return f"""
## {title}

### Executive Summary
This market research examines {task[:50]}, analyzing market trends, customer preferences, competitive landscape, and growth opportunities.
The findings provide strategic insights to guide business decisions and market positioning.

### Key Market Findings
{key_findings}

### Research Methodology
This research gathered information from {sources_text}.
The approach included analyzing market data, identifying trends, and extracting relevant insights from the search results.

{data_section_title}
{data_points}

### Market Trends
The research identifies these significant trends:
- Primary trend affecting the overall market direction
- Secondary trend influencing customer behavior
- Emerging trend that may impact future market dynamics

### Recommendations
{recommendations}
"""
    elif operation == "Competitive Analysis":
        return f"""
## {title}

### Executive Summary
This competitive analysis examines {task[:50]}, comparing key players, market positions, strengths, weaknesses, and strategic approaches.
The analysis provides insights for competitive positioning and strategic advantage.

### Key Competitive Insights
{key_findings}

### Analysis Methodology
This analysis examined information from {sources_text}.
The approach included comparing competitors, identifying differentiators, and analyzing strategic positions from the search results.

{data_section_title}
{data_points}

### Recommendations
{recommendations}
"""
    elif operation == "Problem Analysis":
        return f"""
## {title}

### Executive Summary
This problem analysis examines {task[:50]}, identifying root causes, contributing factors, impacts, and potential solutions.
The analysis provides a structured approach to understanding and addressing the problem.

### Key Problem Insights
{key_findings}

### Analysis Methodology
This analysis examined information from {sources_text}.
The approach included identifying problem factors, causal relationships, and potential solutions from the search results.

{data_section_title}
{data_points}

### Recommendations
{recommendations}
"""
    else:
        # General research report
        return f"""
## {title}

### Executive Summary
This research report examines {task[:50]}, analyzing key aspects, current knowledge, and implications.
The findings provide valuable insights based on information from multiple sources.

### Key Research Findings
{key_findings}

### Research Methodology
This research gathered information from {sources_text}.
The approach included analyzing available information and extracting relevant insights from the search results.

### Detailed Findings
{data_points}

### Implications
The research has several implications:
- Practical implications for application of the findings
- Theoretical implications for understanding the subject
- Future implications for ongoing developments in this area

### Recommendations
{recommendations}
"""
