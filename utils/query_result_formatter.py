"""
Enhanced Query Result Formatter
================================
Provides enterprise-grade formatting for query results with complete sentences,
proper citations, and enhanced metadata display.
"""

import re
from typing import List, Dict, Any, Optional
from .text_cleaning import clean_document_text, is_noise_text
from datetime import datetime


class QueryResultFormatter:
    """Format query results with enterprise standards"""
    
    # Configuration constants
    KEY_POINT_MAX_LENGTH = 300
    SNIPPET_MAX_LENGTH = 500
    EXCERPT_MAX_LENGTH = 400
    
    @staticmethod
    def extract_complete_sentences(text: str, max_length: int = 500) -> str:
        """
        Extract complete sentences up to max_length.
        Ensures no truncation mid-sentence.
        
        Args:
            text: Input text to extract from
            max_length: Maximum character length
            
        Returns:
            Complete sentences within length limit
        """
        if not text:
            return ""
        # Clean first
        text = clean_document_text(text)
        if not text:
            return ""
        if len(text) <= max_length:
            return text.strip()
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        result = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if is_noise_text(sentence):
                continue
                
            # Check if adding this sentence exceeds limit
            if current_length + len(sentence) + 1 <= max_length:
                result.append(sentence)
                current_length += len(sentence) + 1
            else:
                break
        
        # If we got at least one sentence, return it
        if result:
            return ' '.join(result)
        
        # Fallback: return truncated text at sentence boundary
        truncated = text[:max_length]
        last_period = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_period > max_length * 0.5:  # At least 50% of desired length
            return truncated[:last_period + 1].strip()
        
        return truncated.strip() + "..."
    
    @staticmethod
    def format_key_point(content: str, source: str, page: Optional[int] = None, 
                        section: Optional[str] = None, index: int = 1) -> str:
        """
        Format a single key point with complete sentence and citation.
        
        Args:
            content: The content to format
            source: Source document name
            page: Page number (optional)
            section: Section name (optional)
            index: Point number
            
        Returns:
            Formatted key point with citation
        """
        # Clean and filter noise
        content = clean_document_text(content or "")
        if not content or is_noise_text(content):
            return ""
        # Extract complete sentence(s)
        clean_content = QueryResultFormatter.extract_complete_sentences(
            content,
            QueryResultFormatter.KEY_POINT_MAX_LENGTH
        )
        if not clean_content:
            return ""
        
        # Build citation
        citation_parts = [f"Source: {source}"]
        if isinstance(page, int) or (isinstance(page, str) and page.isdigit()):
            citation_parts.append(f"Page {page}")
        if section:
            citation_parts.append(f"Section: {section}")
        
        citation = ", ".join(citation_parts)
        
        return f"{index}. **{clean_content}** _({citation})_"
    
    @staticmethod
    def format_source_citation(result: Dict[str, Any], index: int = 1) -> str:
        """
        Format a source citation with enhanced metadata.
        
        Args:
            result: Result dictionary with content and metadata
            index: Citation number
            
        Returns:
            Formatted citation with metadata
        """
        source = result.get('source', 'Unknown')
        page = result.get('page')
        section = result.get('section')
        score = result.get('relevance_score', 0.0)
        content = clean_document_text(result.get('content', '') or '')
        if not content or is_noise_text(content):
            return ""
        
        # Extract clean excerpt
        excerpt = QueryResultFormatter.extract_complete_sentences(
            content,
            QueryResultFormatter.EXCERPT_MAX_LENGTH
        )
        
        # Build header
        header_parts = [f"**{index}. {source}**"]
        if isinstance(page, int) or (isinstance(page, str) and page.isdigit()):
            header_parts.append(f"(Page {page})")
        
        header = " ".join(header_parts)
        
        # Build metadata line
        metadata_parts = []
        if section:
            metadata_parts.append(f"📑 Section: {section}")
        if score > 0:
            # Add confidence indicator
            if score >= 0.8:
                confidence = "🟢 High"
            elif score >= 0.6:
                confidence = "🟡 Medium"
            else:
                confidence = "🟠 Low"
            metadata_parts.append(f"{confidence} Relevance: {score:.1%}")
        
        metadata = " | ".join(metadata_parts) if metadata_parts else ""
        
        # Format output
        lines = [header]
        if metadata:
            lines.append(f"- {metadata}")
        lines.append(f"- **Excerpt**: {excerpt}")
        lines.append("")  # Spacing
        
        return "\n".join(lines)
    
    @staticmethod
    def format_enhanced_metadata(result: Dict[str, Any]) -> str:
        """
        Format enhanced metadata display for enterprise standards.
        
        Args:
            result: Result dictionary
            
        Returns:
            Formatted metadata string
        """
        metadata_lines = []
        
        # Document type
        doc_type = result.get('document_type', result.get('type', 'Document'))
        metadata_lines.append(f"📄 **Type**: {doc_type}")
        
        # Source
        source = result.get('source', 'Unknown')
        metadata_lines.append(f"📚 **Source**: {source}")
        
        # Page and section
        page = result.get('page')
        section = result.get('section')
        if page:
            metadata_lines.append(f"📖 **Page**: {page}")
        if section:
            metadata_lines.append(f"📑 **Section**: {section}")
        
        # Last updated (if available)
        last_updated = result.get('last_updated', result.get('date'))
        if last_updated:
            metadata_lines.append(f"📅 **Last Updated**: {last_updated}")
        
        # Version (if available)
        version = result.get('version')
        if version:
            metadata_lines.append(f"🔢 **Version**: {version}")
        
        # Relevance score
        score = result.get('relevance_score', 0.0)
        if score > 0:
            if score >= 0.8:
                confidence = "🟢 High Confidence"
            elif score >= 0.6:
                confidence = "🟡 Medium Confidence"
            else:
                confidence = "🟠 Low Confidence"
            metadata_lines.append(f"**Relevance**: {confidence} ({score:.1%})")
        
        return "\n".join(metadata_lines)
    
    @staticmethod
    def generate_related_queries(original_query: str) -> List[str]:
        """
        Generate related query suggestions based on the original query.
        
        Args:
            original_query: The original search query
            
        Returns:
            List of related query suggestions
        """
        # Extract key terms
        query_lower = original_query.lower()
        
        related = []
        
        # Pattern-based suggestions
        if 'powers' in query_lower or 'authority' in query_lower:
            related.extend([
                "What are the duties of Board members?",
                "What are the limitations on Board powers?",
                "How are Board powers delegated?"
            ])
        
        if 'board' in query_lower:
            related.extend([
                "How are Board members elected?",
                "What is the term length for Board members?",
                "What are Board meeting requirements?"
            ])
        
        if 'meeting' in query_lower:
            related.extend([
                "What is the quorum requirement for meetings?",
                "How is meeting notice provided?",
                "What are special meeting procedures?"
            ])
        
        if 'election' in query_lower or 'vote' in query_lower:
            related.extend([
                "What is the voting procedure?",
                "Who is eligible to vote?",
                "How are election results determined?"
            ])
        
        # Generic fallbacks
        if not related:
            related = [
                f"What are the requirements for {query_lower}?",
                f"What are the procedures for {query_lower}?",
                f"What are the limitations on {query_lower}?"
            ]
        
        # Return unique suggestions (max 5)
        return list(dict.fromkeys(related))[:5]
    
    @staticmethod
    def format_confidence_indicator(score: float) -> str:
        """
        Format a visual confidence indicator.
        
        Args:
            score: Confidence score (0.0 to 1.0)
            
        Returns:
            Formatted confidence indicator
        """
        if score >= 0.8:
            return "🟢 High Confidence"
        elif score >= 0.6:
            return "🟡 Medium Confidence"
        else:
            return "🟠 Low Confidence"
    
    @staticmethod
    def create_action_buttons_html(result_id: str) -> str:
        """
        Create HTML for result action buttons.
        
        Args:
            result_id: Unique identifier for the result
            
        Returns:
            HTML string for action buttons
        """
        return f"""
        <div class="result-actions" style="margin-top: 10px;">
            <button onclick="copyToClipboard_{result_id}()" style="margin-right: 5px;">📋 Copy</button>
            <button onclick="shareResult_{result_id}()" style="margin-right: 5px;">🔗 Share</button>
            <button onclick="exportResult_{result_id}()" style="margin-right: 5px;">📥 Export</button>
            <button onclick="saveResult_{result_id}()" style="margin-right: 5px;">⭐ Save</button>
        </div>
        <script>
        function copyToClipboard_{result_id}() {{
            const text = document.getElementById('result_{result_id}').innerText;
            navigator.clipboard.writeText(text).then(() => alert('Copied to clipboard!'));
        }}
        function shareResult_{result_id}() {{
            alert('Share functionality - integrate with your sharing system');
        }}
        function exportResult_{result_id}() {{
            alert('Export functionality - integrate with your export system');
        }}
        function saveResult_{result_id}() {{
            alert('Save functionality - integrate with your favorites system');
        }}
        </script>
        """


# Convenience functions for backward compatibility
def extract_complete_sentences(text: str, max_length: int = 500) -> str:
    """Extract complete sentences - convenience function"""
    return QueryResultFormatter.extract_complete_sentences(text, max_length)


def format_key_point(content: str, source: str, page: Optional[int] = None, 
                    section: Optional[str] = None, index: int = 1) -> str:
    """Format key point - convenience function"""
    return QueryResultFormatter.format_key_point(content, source, page, section, index)


def format_source_citation(result: Dict[str, Any], index: int = 1) -> str:
    """Format source citation - convenience function"""
    return QueryResultFormatter.format_source_citation(result, index)
