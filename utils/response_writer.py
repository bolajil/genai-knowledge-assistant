"""
VaultMind Response Writer
Rewrites query responses in beautiful, readable markdown format
"""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ResponseWriter:
    """
    Rewrites query responses in beautiful markdown format
    Improves readability, structure, and presentation
    """
    
    def __init__(self, llm_provider: Optional[str] = None):
        """
        Initialize response writer
        
        Args:
            llm_provider: Optional LLM provider for enhanced rewriting
        """
        self.llm_provider = llm_provider
        self.use_llm = llm_provider is not None
    
    def rewrite_response(
        self,
        raw_response: str,
        query: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Rewrite response in beautiful markdown format
        
        Args:
            raw_response: Original response text
            query: User's query
            sources: List of source documents
            metadata: Additional metadata (confidence, timing, etc.)
        
        Returns:
            Beautifully formatted markdown response
        """
        try:
            if self.use_llm:
                return self._rewrite_with_llm(raw_response, query, sources, metadata)
            else:
                return self._rewrite_with_rules(raw_response, query, sources, metadata)
        except Exception as e:
            logger.error(f"Error rewriting response: {str(e)}")
            return self._fallback_format(raw_response, query, sources)
    
    def _rewrite_with_llm(
        self,
        raw_response: str,
        query: str,
        sources: Optional[List[Dict[str, Any]]],
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Rewrite response using LLM for enhanced quality"""
        try:
            from utils.llm_config import get_llm_client
            
            llm = get_llm_client(self.llm_provider)
            
            prompt = f"""You are a professional document writer. Rewrite the following response in beautiful, readable markdown format.

**Original Query:** {query}

**Raw Response:**
{raw_response}

**Instructions:**
1. Create a clear, hierarchical structure with proper headings
2. Use bullet points and numbered lists where appropriate
3. Add emphasis (bold/italic) for important points
4. Include a brief executive summary at the top
5. Organize information into logical sections
6. Add visual separators and spacing for readability
7. Ensure proper markdown syntax
8. Keep all factual information accurate
9. Make it professional and easy to scan
10. Add emojis sparingly for visual appeal

**Output Format:**
- Start with ## Executive Summary
- Follow with main sections using ### headings
- Use **bold** for key terms
- Use > blockquotes for important notes
- End with sources if provided

Rewrite the response now:"""

            rewritten = llm.invoke(prompt).content
            
            # Add sources section
            if sources:
                rewritten += "\n\n" + self._format_sources(sources)
            
            # Add metadata footer
            if metadata:
                rewritten += "\n\n" + self._format_metadata(metadata)
            
            return rewritten
            
        except Exception as e:
            logger.error(f"LLM rewriting failed: {str(e)}")
            return self._rewrite_with_rules(raw_response, query, sources, metadata)
    
    def _rewrite_with_rules(
        self,
        raw_response: str,
        query: str,
        sources: Optional[List[Dict[str, Any]]],
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Rewrite response using rule-based formatting"""
        
        # Parse the response into sections
        sections = self._parse_sections(raw_response)
        
        # Build formatted response
        formatted = []
        
        # Add header with query
        formatted.append(f"# 🔍 Query Results\n")
        formatted.append(f"> **Your Question:** {query}\n")
        formatted.append(f"---\n")
        
        # Add executive summary if available
        if 'summary' in sections or 'executive_summary' in sections:
            summary = sections.get('summary') or sections.get('executive_summary')
            formatted.append(f"## 📊 Executive Summary\n")
            formatted.append(self._format_paragraph(summary))
            formatted.append(f"\n---\n")
        
        # Add main content sections
        for section_name, content in sections.items():
            if section_name in ['summary', 'executive_summary', 'sources', 'references']:
                continue
            
            # Format section heading
            heading = self._format_heading(section_name)
            formatted.append(f"\n## {heading}\n")
            
            # Format section content
            formatted.append(self._format_content(content))
        
        # Add key points if identifiable
        key_points = self._extract_key_points(raw_response)
        if key_points:
            formatted.append(f"\n## 🔑 Key Takeaways\n")
            for point in key_points:
                formatted.append(f"- **{point}**\n")
        
        # Add sources
        if sources:
            formatted.append(f"\n---\n")
            formatted.append(self._format_sources(sources))
        
        # Add metadata footer
        if metadata:
            formatted.append(f"\n---\n")
            formatted.append(self._format_metadata(metadata))
        
        return "".join(formatted)
    
    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse text into logical sections"""
        sections = {}
        
        # Common section patterns
        section_patterns = [
            r'(?:^|\n)(?:Executive Summary|Summary):\s*(.+?)(?=\n(?:[A-Z][^:]+:|$))',
            r'(?:^|\n)(?:Detailed Analysis|Analysis):\s*(.+?)(?=\n(?:[A-Z][^:]+:|$))',
            r'(?:^|\n)(?:Key Points|Main Points):\s*(.+?)(?=\n(?:[A-Z][^:]+:|$))',
            r'(?:^|\n)(?:Findings|Results):\s*(.+?)(?=\n(?:[A-Z][^:]+:|$))',
            r'(?:^|\n)(?:Recommendations|Suggestions):\s*(.+?)(?=\n(?:[A-Z][^:]+:|$))',
            r'(?:^|\n)(?:Conclusion):\s*(.+?)(?=\n(?:[A-Z][^:]+:|$))',
        ]
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                section_name = match.group(0).split(':')[0].strip().lower().replace(' ', '_')
                section_content = match.group(1).strip()
                sections[section_name] = section_content
        
        # If no sections found, treat entire text as main content
        if not sections:
            sections['main_content'] = text
        
        return sections
    
    def _format_heading(self, section_name: str) -> str:
        """Format section heading with emoji"""
        emoji_map = {
            'summary': '📊',
            'executive_summary': '📊',
            'analysis': '🔬',
            'detailed_analysis': '🔬',
            'findings': '🔍',
            'results': '📈',
            'key_points': '🔑',
            'main_points': '🔑',
            'recommendations': '💡',
            'suggestions': '💡',
            'conclusion': '🎯',
            'main_content': '📄',
            'background': '📚',
            'context': '🌐',
            'implications': '⚡',
            'next_steps': '🚀'
        }
        
        emoji = emoji_map.get(section_name, '📌')
        title = section_name.replace('_', ' ').title()
        
        return f"{emoji} {title}"
    
    def _format_content(self, content: str) -> str:
        """Format content with proper markdown"""
        # Split into paragraphs
        paragraphs = content.split('\n\n')
        formatted = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if it's a list
            if self._is_list(para):
                formatted.append(self._format_list(para))
            # Check if it's a quote
            elif para.startswith('"') or para.startswith("'"):
                formatted.append(f"> {para}\n")
            # Regular paragraph
            else:
                formatted.append(self._format_paragraph(para))
        
        return "\n".join(formatted)
    
    def _format_paragraph(self, text: str) -> str:
        """Format a paragraph with emphasis"""
        # Bold important terms
        text = self._add_emphasis(text)
        
        # Add proper spacing
        return f"{text}\n"
    
    def _add_emphasis(self, text: str) -> str:
        """Add bold/italic emphasis to important terms"""
        # Bold numbers with context
        text = re.sub(r'(\d+%)', r'**\1**', text)
        text = re.sub(r'(\$[\d,]+)', r'**\1**', text)
        
        # Bold important keywords
        important_keywords = [
            'important', 'critical', 'essential', 'key', 'significant',
            'must', 'required', 'mandatory', 'note', 'warning', 'caution'
        ]
        
        for keyword in important_keywords:
            text = re.sub(
                rf'\b({keyword})\b',
                r'**\1**',
                text,
                flags=re.IGNORECASE
            )
        
        return text
    
    def _is_list(self, text: str) -> bool:
        """Check if text is a list"""
        lines = text.split('\n')
        list_indicators = ['-', '•', '*', '1.', '2.', '3.']
        
        list_lines = sum(
            1 for line in lines
            if any(line.strip().startswith(ind) for ind in list_indicators)
        )
        
        return list_lines >= 2
    
    def _format_list(self, text: str) -> str:
        """Format list items"""
        lines = text.split('\n')
        formatted = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Convert to markdown list
            if not line.startswith(('-', '*', '•')):
                # Add bullet if missing
                line = f"- {line}"
            elif line.startswith('•'):
                line = line.replace('•', '-', 1)
            
            formatted.append(line)
        
        return '\n'.join(formatted) + '\n'
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from text"""
        key_points = []
        
        # Look for numbered points
        numbered_pattern = r'\d+\.\s+([^.]+\.)'
        matches = re.findall(numbered_pattern, text)
        if matches:
            key_points.extend(matches[:5])  # Top 5 points
        
        # Look for bullet points
        if not key_points:
            bullet_pattern = r'[-•*]\s+([^.\n]+[.\n])'
            matches = re.findall(bullet_pattern, text)
            if matches:
                key_points.extend(matches[:5])
        
        # Clean up points
        key_points = [point.strip() for point in key_points]
        key_points = [point for point in key_points if len(point) > 20]
        
        return key_points
    
    def _format_sources(self, sources: List[Dict[str, Any]]) -> str:
        """Format source citations"""
        formatted = ["## 📚 Sources\n"]
        
        for i, source in enumerate(sources, 1):
            doc_name = source.get('document', 'Unknown')
            page = source.get('page', 'N/A')
            section = source.get('section', '')
            relevance = source.get('relevance', 0.0)
            
            # Format source entry
            entry = f"{i}. **{doc_name}**"
            
            if page != 'N/A':
                entry += f" - Page {page}"
            
            if section:
                entry += f" - {section}"
            
            if relevance > 0:
                entry += f" `(Relevance: {relevance:.2%})`"
            
            formatted.append(entry)
        
        return '\n'.join(formatted) + '\n'
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata footer"""
        formatted = ["## ℹ️ Query Information\n"]
        
        if 'confidence' in metadata:
            confidence = metadata['confidence']
            formatted.append(f"- **Confidence Score:** {confidence:.2%}")
        
        if 'response_time' in metadata:
            time_ms = metadata['response_time']
            formatted.append(f"- **Response Time:** {time_ms:.2f}ms")
        
        if 'sources_count' in metadata:
            count = metadata['sources_count']
            formatted.append(f"- **Sources Consulted:** {count}")
        
        if 'index_used' in metadata:
            index = metadata['index_used']
            formatted.append(f"- **Index:** {index}")
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted.append(f"- **Generated:** {timestamp}")
        
        return '\n'.join(formatted) + '\n'
    
    def _fallback_format(
        self,
        raw_response: str,
        query: str,
        sources: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Simple fallback formatting"""
        formatted = [
            f"# 🔍 Query Results\n",
            f"> **Your Question:** {query}\n",
            f"---\n\n",
            f"## 📄 Response\n\n",
            raw_response,
            "\n"
        ]
        
        if sources:
            formatted.append("\n---\n")
            formatted.append(self._format_sources(sources))
        
        return "".join(formatted)


class MarkdownEnhancer:
    """
    Additional markdown enhancement utilities
    """
    
    @staticmethod
    def add_table_of_contents(markdown: str) -> str:
        """Add table of contents to markdown"""
        # Extract headings
        headings = re.findall(r'^(#{2,3})\s+(.+)$', markdown, re.MULTILINE)
        
        if len(headings) < 3:
            return markdown  # Not enough headings for TOC
        
        toc = ["## 📑 Table of Contents\n"]
        
        for level, title in headings:
            # Skip TOC itself
            if 'Table of Contents' in title:
                continue
            
            # Create anchor link
            anchor = title.lower().replace(' ', '-')
            anchor = re.sub(r'[^\w-]', '', anchor)
            
            indent = "  " * (len(level) - 2)
            toc.append(f"{indent}- [{title}](#{anchor})")
        
        toc.append("\n---\n")
        
        # Insert TOC after first heading
        first_heading = re.search(r'^#[^#].*$', markdown, re.MULTILINE)
        if first_heading:
            insert_pos = first_heading.end()
            return markdown[:insert_pos] + "\n\n" + "\n".join(toc) + markdown[insert_pos:]
        
        return markdown
    
    @staticmethod
    def add_collapsible_sections(markdown: str) -> str:
        """Add collapsible sections for long content"""
        # Find long sections (> 500 chars)
        sections = re.split(r'^(#{2,3}\s+.+)$', markdown, flags=re.MULTILINE)
        
        enhanced = []
        for i, section in enumerate(sections):
            if i % 2 == 0:  # Content
                if len(section) > 500:
                    # Make it collapsible
                    enhanced.append("<details>\n<summary>Click to expand</summary>\n\n")
                    enhanced.append(section)
                    enhanced.append("\n</details>\n")
                else:
                    enhanced.append(section)
            else:  # Heading
                enhanced.append(section)
        
        return "".join(enhanced)
    
    @staticmethod
    def add_syntax_highlighting(markdown: str) -> str:
        """Ensure code blocks have syntax highlighting"""
        # Find code blocks without language
        pattern = r'```\n((?:(?!```).)+)\n```'
        
        def add_language(match):
            code = match.group(1)
            # Try to detect language
            if 'import' in code or 'def ' in code:
                return f'```python\n{code}\n```'
            elif '{' in code and '}' in code:
                return f'```json\n{code}\n```'
            elif '<' in code and '>' in code:
                return f'```html\n{code}\n```'
            else:
                return f'```text\n{code}\n```'
        
        return re.sub(pattern, add_language, markdown, flags=re.DOTALL)
    
    @staticmethod
    def beautify_tables(markdown: str) -> str:
        """Improve table formatting"""
        # Find tables and ensure proper alignment
        table_pattern = r'(\|.+\|)\n(\|[-:\s|]+\|)\n((?:\|.+\|\n?)+)'
        
        def format_table(match):
            header = match.group(1)
            separator = match.group(2)
            rows = match.group(3)
            
            # Ensure separator has alignment
            if ':' not in separator:
                separator = separator.replace('-', ':-:')
            
            return f"{header}\n{separator}\n{rows}"
        
        return re.sub(table_pattern, format_table, markdown)


# Global instance
response_writer = ResponseWriter()


def rewrite_query_response(
    raw_response: str,
    query: str,
    sources: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    use_llm: bool = False,
    enhance: bool = True
) -> str:
    """
    Convenience function to rewrite query response
    
    Args:
        raw_response: Original response text
        query: User's query
        sources: List of source documents
        metadata: Additional metadata
        use_llm: Whether to use LLM for rewriting
        enhance: Whether to apply additional enhancements
    
    Returns:
        Beautifully formatted markdown response
    """
    # Initialize writer with LLM if requested
    if use_llm:
        writer = ResponseWriter(llm_provider='openai')
    else:
        writer = response_writer
    
    # Rewrite response
    formatted = writer.rewrite_response(raw_response, query, sources, metadata)
    
    # Apply enhancements
    if enhance:
        enhancer = MarkdownEnhancer()
        formatted = enhancer.add_table_of_contents(formatted)
        formatted = enhancer.add_syntax_highlighting(formatted)
        formatted = enhancer.beautify_tables(formatted)
    
    return formatted
