"""
Helper function to generate generic research content based on search results.
This is used by the main research content generator function.
"""

def generate_generic_research(task, operation, knowledge_sources, search_results_text=""):
    """Generate generic research content based on search results"""
    
    # Use search results if available
    if search_results_text:
        # Extract findings from search results
        findings = []
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
            findings.append(f"Additional research on {task[:30]} is recommended for comprehensive understanding.")
        
        sources_text = ", ".join(knowledge_sources) if knowledge_sources else "available knowledge sources"
        
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
            knowledge_reference = f"\n\n### Knowledge Sources Used\n"
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
