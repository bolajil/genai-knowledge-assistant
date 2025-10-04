"""
Markdown Formatter for Document Content
Formats document retrieval results into well-structured markdown
"""

import re
from typing import List, Dict, Any

class MarkdownFormatter:
    """Formats document content into readable markdown"""
    
    def __init__(self):
        self.section_patterns = [
            r'^(ARTICLE\s+[IVX]+\.?\s*.*)',
            r'^(Section\s+\d+\.?\s*.*)',
            r'^([A-Z]\.\s+.*)',
            r'^(\d+\.\s+.*)',
            r'^([a-z]\.\s+.*)'
        ]
    
    def format_document_results(self, results: List[Dict[str, Any]]) -> str:
        """Format document results into markdown"""
        if not results:
            return "## No Results Found\n\nNo content was found in the document for your query."
        
        markdown_content = []
        
        # Add header
        markdown_content.append("# Document Query Results\n")
        
        for i, result in enumerate(results, 1):
            content = result.get('content', '')
            title = result.get('title', 'Untitled')
            source = result.get('source', 'Unknown')
            section = result.get('section', 'N/A')
            relevance = result.get('relevance_score', 0.0)
            
            # Result header
            markdown_content.append(f"## Result {i}: {title}")
            markdown_content.append(f"**Source:** {source} | **Section:** {section} | **Relevance:** {relevance:.2f}\n")
            
            # Format the content
            formatted_content = self._format_content(content)
            markdown_content.append(formatted_content)
            markdown_content.append("\n---\n")
        
        return "\n".join(markdown_content)
    
    def _format_content(self, content: str) -> str:
        """Format individual content into structured markdown"""
        if not content:
            return "*No content available*"
        
        lines = content.split('\n')
        formatted_lines = []
        in_list = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_list:
                    formatted_lines.append("")
                    in_list = False
                continue
            
            # Check for section headers
            formatted_line = self._format_headers(line)
            if formatted_line != line:
                if in_list:
                    formatted_lines.append("")
                    in_list = False
                formatted_lines.append(formatted_line)
                continue
            
            # Check for list items
            list_item = self._format_list_item(line)
            if list_item:
                if not in_list:
                    formatted_lines.append("")
                formatted_lines.append(list_item)
                in_list = True
                continue
            
            # Regular paragraph
            if in_list:
                formatted_lines.append("")
                in_list = False
            formatted_lines.append(line)
        
        return "\n".join(formatted_lines)
    
    def _format_headers(self, line: str) -> str:
        """Format headers with appropriate markdown levels"""
        for pattern in self.section_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                if line.startswith('ARTICLE'):
                    return f"### {line}"
                elif line.startswith('Section'):
                    return f"#### {line}"
                elif re.match(r'^[A-Z]\.\s', line):
                    return f"##### {line}"
                else:
                    return f"**{line}**"
        return line
    
    def _format_list_item(self, line: str) -> str:
        """Format list items"""
        # Lettered lists (a., b., c.)
        if re.match(r'^[a-z]\.\s+', line):
            content = re.sub(r'^[a-z]\.\s+', '', line)
            return f"- **{line[0].upper()}.** {content}"
        
        # Numbered lists (1., 2., 3.)
        if re.match(r'^\d+\.\s+', line):
            return f"- {line}"
        
        # Already formatted lists
        if line.startswith('- ') or line.startswith('* '):
            return line
        
        return None
    
    def format_powers_section(self, content: str) -> str:
        """Special formatting for Board Powers sections"""
        if not content:
            return "*No powers content found*"
        
        markdown_content = []
        markdown_content.append("## Board of Directors Powers\n")
        
        lines = content.split('\n')
        current_section = None
        powers_list = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Main powers header
            if 'powers' in line.lower() and ('board' in line.lower() or 'section' in line.lower()):
                if powers_list:
                    markdown_content.extend(powers_list)
                    powers_list = []
                markdown_content.append(f"### {line}\n")
                continue
            
            # Power items (a., b., c., etc.)
            if re.match(r'^[a-z]\.\s+', line):
                power_text = re.sub(r'^[a-z]\.\s+', '', line)
                powers_list.append(f"- **{line[0].upper()}.** {power_text}")
                continue
            
            # Regular content
            if 'responsible for' in line.lower() or 'has all of the powers' in line.lower():
                markdown_content.append(f"*{line}*\n")
            else:
                markdown_content.append(line)
        
        # Add remaining powers
        if powers_list:
            markdown_content.append("\n### Specific Powers:")
            markdown_content.extend(powers_list)
        
        return "\n".join(markdown_content)

def format_to_markdown(results: List[Dict[str, Any]], query: str = "") -> str:
    """Main function to format document results to markdown"""
    formatter = MarkdownFormatter()
    
    # Special handling for powers queries
    if 'powers' in query.lower() and 'board' in query.lower():
        if results and len(results) == 1:
            content = results[0].get('content', '')
            if 'powers' in content.lower():
                return formatter.format_powers_section(content)
    
    return formatter.format_document_results(results)
