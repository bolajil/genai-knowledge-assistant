"""
Search-based content creation module that uses actual search results
"""

import re
from typing import List, Dict, Any, Optional

def extract_content_from_search_results(search_results_text: str, tone: str) -> Dict[str, Any]:
    """
    Extract content from search results for content creation
    
    Args:
        search_results_text: Formatted search results text
        tone: The tone for content creation
        
    Returns:
        Dictionary with extracted content elements
    """
    # Initialize extraction results
    extracted = {
        "key_points": [],
        "context": "",
        "details": [],
        "sources": [],
        "conclusions": []
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
            
            # Extract sentences for key points (first 2-3 sentences from each result)
            sentences = re.split(r'(?<=[.!?])\s+', content)
            key_sentences = sentences[:min(3, len(sentences))]
            for sentence in key_sentences:
                if sentence and len(sentence) > 20 and sentence not in extracted["key_points"]:
                    extracted["key_points"].append(sentence)
            
            # Look for detailed content
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            for paragraph in paragraphs:
                if paragraph and len(paragraph) > 50 and paragraph not in extracted["details"]:
                    extracted["details"].append(paragraph)
            
            # Look for conclusions in the content
            conclusion_patterns = [
                r'conclude', r'summary', r'in conclusion', r'to summarize', 
                r'finally', r'overall', r'as a result', r'consequently'
            ]
            
            for pattern in conclusion_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Get a reasonable window around the match
                    start = max(0, match.start() - 30)
                    end = min(len(content), match.end() + 150)
                    
                    # Find sentence boundaries
                    sentence_start = max(0, start - content[max(0, start-100):start].rfind('.'))
                    sentence_end = end + content[end:min(len(content), end+100)].find('.')
                    if sentence_end < end:  # No period found
                        sentence_end = end
                    
                    conclusion = content[sentence_start:sentence_end+1].strip()
                    if conclusion and conclusion not in extracted["conclusions"] and len(conclusion) > 10:
                        extracted["conclusions"].append(conclusion)
    
    # Limit to reasonable amounts
    extracted["key_points"] = extracted["key_points"][:6]
    extracted["details"] = extracted["details"][:4]
    extracted["conclusions"] = extracted["conclusions"][:3]
    
    return extracted

def generate_content_from_search(task: str, tone: str, search_results_text: str = "") -> str:
    """
    Generate content based on actual search results
    
    Args:
        task: The user's task description
        tone: The tone for content creation
        search_results_text: Formatted search results text
        
    Returns:
        Created content based on search results
    """
    # If we don't have search results text, return a fallback
    if not search_results_text:
        return f"""
## Content Creation

I've created the following content based on your request:

### {task[:50]}

{'#### Executive Summary' if tone == 'Professional' or tone == 'Technical' else '#### Introduction'}

This document provides information about {task[:30]}. Please note that no specific search results were found, so this is generic content.

{'### Key Points' if tone == 'Professional' else '### Main Ideas'}

1. First point about {task[:20]}
2. Second point related to the topic
3. Third aspect worth noting
4. Additional consideration for completeness

### Detailed Content

This content would normally be based on search results related to your topic.
Consider refining your search or selecting different knowledge sources.

### Conclusion

Based on general principles, it is recommended to gather more information about {task[:20]}.
Further research would help develop more specific and relevant content.
"""
    
    # Extract content from search results
    extracted = extract_content_from_search_results(search_results_text, tone)
    
    # Format key points
    key_points = ""
    for i, point in enumerate(extracted["key_points"][:4], 1):
        key_points += f"{i}. {point}\n"
    if not key_points:
        key_points = f"1. No specific key points were identified about {task[:20]}\n"
    
    # Format detailed content
    detailed_content = ""
    for detail in extracted["details"]:
        detailed_content += f"{detail}\n\n"
    if not detailed_content:
        detailed_content = f"The search did not return detailed content about {task[:30]}."
    
    # Format conclusion
    conclusion = ""
    for concl in extracted["conclusions"]:
        conclusion += f"{concl}\n\n"
    if not conclusion:
        conclusion = f"Based on the available information, it is recommended to further explore {task[:30]} for more comprehensive insights."
    
    # Create the sources section
    sources_text = ", ".join(extracted["sources"]) if extracted["sources"] else "No specific sources identified"
    
    # Create section headers based on tone
    intro_header = "Executive Summary" if tone in ['Professional', 'Technical'] else "Introduction"
    points_header = "Key Points" if tone in ['Professional', 'Technical'] else "Main Ideas"
    details_header = "Detailed Analysis" if tone in ['Professional', 'Technical'] else "Content Details"
    conclusion_header = "Conclusion and Recommendations" if tone in ['Professional', 'Technical'] else "Wrap-up"
    
    return f"""
## Content Creation

I've created the following content based on your request and the information retrieved from knowledge sources:

### {task[:50]}

#### {intro_header}

This document provides information about {task[:30]} based on search results from {sources_text}.

### {points_header}

{key_points}

### {details_header}

{detailed_content}

### {conclusion_header}

{conclusion}
"""
