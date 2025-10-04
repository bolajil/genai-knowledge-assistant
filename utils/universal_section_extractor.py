"""
Universal Section Extractor

Advanced section extraction system that works across all document types
to provide granular, detailed content retrieval instead of just headers.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class UniversalSectionExtractor:
    """
    Universal section extractor for detailed content retrieval across document types
    """
    
    def __init__(self):
        """Initialize the section extractor with document type patterns"""
        self.document_patterns = {
            'legal': {
                'section_patterns': [
                    r'ARTICLE\s+[IVX]+\..*?(?=ARTICLE\s+[IVX]+\.|\Z)',
                    r'Section\s+\d+\..*?(?=Section\s+\d+\.|\Z)',
                    r'[A-Z]\.\s+[A-Z][A-Z\s]+\..*?(?=[A-Z]\.\s+[A-Z]|\Z)',
                    r'\([a-z]\).*?(?=\([a-z]\)|\Z)'
                ],
                'content_indicators': ['procedures', 'requirements', 'shall', 'must', 'may'],
                'header_patterns': [r'TABLE OF CONTENTS', r'Page \d+ of \d+', r'Copyright']
            },
            'technical': {
                'section_patterns': [
                    r'Chapter\s+\d+.*?(?=Chapter\s+\d+|\Z)',
                    r'\d+\.\d+.*?(?=\d+\.\d+|\Z)',
                    r'###\s+.*?(?=###|\Z)',
                    r'##\s+.*?(?=##|\Z)'
                ],
                'content_indicators': ['implementation', 'configuration', 'setup', 'install'],
                'header_patterns': [r'Table of Contents', r'Index', r'References']
            },
            'policy': {
                'section_patterns': [
                    r'Policy\s+\d+.*?(?=Policy\s+\d+|\Z)',
                    r'Procedure\s+\d+.*?(?=Procedure\s+\d+|\Z)',
                    r'\d+\.\s+.*?(?=\d+\.|\Z)'
                ],
                'content_indicators': ['policy', 'procedure', 'guideline', 'standard'],
                'header_patterns': [r'Document Control', r'Version History']
            }
        }
    
    def detect_document_type(self, content: str) -> str:
        """
        Detect document type based on content patterns
        
        Args:
            content: Document content
            
        Returns:
            Document type ('legal', 'technical', 'policy', or 'general')
        """
        content_lower = content.lower()
        
        # Legal document indicators
        legal_indicators = ['bylaws', 'article', 'section', 'whereas', 'association', 'board of directors']
        legal_score = sum(1 for indicator in legal_indicators if indicator in content_lower)
        
        # Technical document indicators  
        technical_indicators = ['configuration', 'installation', 'api', 'system', 'implementation']
        technical_score = sum(1 for indicator in technical_indicators if indicator in content_lower)
        
        # Policy document indicators
        policy_indicators = ['policy', 'procedure', 'guideline', 'compliance', 'standard']
        policy_score = sum(1 for indicator in policy_indicators if indicator in content_lower)
        
        # Determine type based on highest score
        scores = {'legal': legal_score, 'technical': technical_score, 'policy': policy_score}
        doc_type = max(scores, key=scores.get)
        
        return doc_type if scores[doc_type] > 0 else 'general'
    
    def extract_complete_sections(self, content: str, query: str) -> List[Dict[str, Any]]:
        """
        Extract complete sections with full content based on query intent
        
        Args:
            content: Document content
            query: User query
            
        Returns:
            List of complete sections with detailed content
        """
        doc_type = self.detect_document_type(content)
        patterns = self.document_patterns.get(doc_type, self.document_patterns['legal'])
        
        # Analyze query intent
        query_intent = self.analyze_query_intent(query)
        
        # Extract sections based on patterns
        sections = []
        for pattern in patterns['section_patterns']:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                section_content = match.group(0).strip()
                
                # Skip if it's just a header or TOC entry
                if self.is_header_only(section_content, patterns['header_patterns']):
                    continue
                
                # Check relevance to query
                relevance_score = self.calculate_section_relevance(section_content, query, query_intent)
                
                if relevance_score > 0.3:  # Threshold for relevance
                    section_info = self.parse_section_details(section_content, doc_type)
                    section_info.update({
                        'relevance_score': relevance_score,
                        'query_intent': query_intent,
                        'document_type': doc_type,
                        'full_content': section_content
                    })
                    sections.append(section_info)
        
        # Sort by relevance and return top sections
        sections.sort(key=lambda x: x['relevance_score'], reverse=True)
        return sections[:5]  # Return top 5 most relevant sections
    
    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to understand what type of information is needed
        
        Args:
            query: User query
            
        Returns:
            Query intent analysis
        """
        query_lower = query.lower()
        
        intent_patterns = {
            'detailed_procedures': ['procedures', 'how to', 'steps', 'process', 'method'],
            'requirements': ['requirements', 'must', 'shall', 'needed', 'required'],
            'definitions': ['what is', 'define', 'definition', 'meaning'],
            'full_section': ['print out', 'show me', 'complete', 'entire', 'full text'],
            'specific_rules': ['rules', 'regulations', 'guidelines', 'policies'],
            'examples': ['example', 'sample', 'instance', 'case']
        }
        
        detected_intents = []
        for intent, patterns in intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                detected_intents.append(intent)
        
        return {
            'primary_intent': detected_intents[0] if detected_intents else 'general_info',
            'all_intents': detected_intents,
            'needs_full_content': 'full_section' in detected_intents or 'detailed_procedures' in detected_intents
        }
    
    def is_header_only(self, content: str, header_patterns: List[str]) -> bool:
        """
        Check if content is just a header/TOC entry without substantial content
        
        Args:
            content: Section content
            header_patterns: Patterns that indicate headers
            
        Returns:
            True if content is header-only
        """
        # Check against header patterns
        for pattern in header_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        # Check content characteristics
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Too short to be substantial content
        if len(lines) <= 3 and len(content) < 200:
            return True
        
        # Mostly dots (table of contents style)
        dot_ratio = content.count('.') / len(content) if content else 0
        if dot_ratio > 0.1:  # More than 10% dots indicates TOC
            return True
        
        # Check if it's mostly page numbers and references
        page_refs = len(re.findall(r'\d+', content))
        if page_refs > len(lines):  # More numbers than lines
            return True
        
        return False
    
    def calculate_section_relevance(self, section_content: str, query: str, query_intent: Dict[str, Any]) -> float:
        """
        Calculate how relevant a section is to the query
        
        Args:
            section_content: Content of the section
            query: User query
            query_intent: Analyzed query intent
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        content_lower = section_content.lower()
        query_lower = query.lower()
        
        # Extract key terms from query
        query_terms = re.findall(r'\b[a-zA-Z]{3,}\b', query_lower)
        
        # Base relevance from term matching
        term_matches = sum(1 for term in query_terms if term in content_lower)
        base_score = term_matches / len(query_terms) if query_terms else 0
        
        # Boost for intent-specific content
        intent_boost = 0
        if query_intent['primary_intent'] == 'detailed_procedures':
            procedure_words = ['shall', 'must', 'procedure', 'step', 'process', 'method']
            intent_boost = sum(0.1 for word in procedure_words if word in content_lower)
        
        elif query_intent['primary_intent'] == 'requirements':
            requirement_words = ['required', 'requirement', 'must', 'shall', 'mandatory']
            intent_boost = sum(0.1 for word in requirement_words if word in content_lower)
        
        # Penalty for header-like content
        header_penalty = 0
        if len(section_content) < 300:  # Very short content
            header_penalty = -0.2
        
        # Content depth bonus
        depth_bonus = min(0.3, len(section_content) / 1000)  # Bonus for longer, detailed content
        
        final_score = base_score + intent_boost + depth_bonus + header_penalty
        return max(0.0, min(1.0, final_score))
    
    def parse_section_details(self, section_content: str, doc_type: str) -> Dict[str, Any]:
        """
        Parse section to extract metadata and structure
        
        Args:
            section_content: Raw section content
            doc_type: Document type
            
        Returns:
            Parsed section information
        """
        # Extract section title
        title_patterns = [
            r'ARTICLE\s+[IVX]+\.\s*([^.\n]+)',
            r'Section\s+\d+\.\s*([^.\n]+)',
            r'^([A-Z][A-Z\s]+)\.',
            r'^([^.\n]+)'
        ]
        
        title = "Untitled Section"
        for pattern in title_patterns:
            match = re.search(pattern, section_content, re.MULTILINE)
            if match:
                title = match.group(1).strip()
                break
        
        # Extract page references
        page_matches = re.findall(r'Page\s+(\d+)', section_content)
        page_range = f"{min(page_matches)}-{max(page_matches)}" if len(page_matches) > 1 else (page_matches[0] if page_matches else 'N/A')
        
        # Extract subsections
        subsections = []
        if doc_type == 'legal':
            subsection_pattern = r'Section\s+\d+\.\s*([^.\n]+).*?(?=Section\s+\d+\.|\Z)'
            subsections = re.findall(subsection_pattern, section_content, re.DOTALL)
        
        # Clean content (remove excessive whitespace, page headers)
        cleaned_content = self.clean_section_content(section_content)
        
        return {
            'title': title,
            'content': cleaned_content,
            'page': page_range,
            'subsections': subsections,
            'word_count': len(cleaned_content.split()),
            'section_type': self.classify_section_type(cleaned_content),
            'has_procedures': self.contains_procedures(cleaned_content),
            'has_requirements': self.contains_requirements(cleaned_content)
        }
    
    def clean_section_content(self, content: str) -> str:
        """
        Clean section content by removing headers, page numbers, and formatting artifacts
        
        Args:
            content: Raw section content
            
        Returns:
            Cleaned content
        """
        # Remove page headers and footers
        content = re.sub(r'Page\s+\d+\s+of\s+\d+', '', content)
        content = re.sub(r'Copyright.*?reserved\.', '', content, flags=re.DOTALL)
        content = re.sub(r'\d{10,}', '', content)  # Remove long numbers (document IDs)
        
        # Clean up excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Multiple newlines to double
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single
        
        # Remove table of contents dots
        content = re.sub(r'\.{3,}', '', content)
        
        return content.strip()
    
    def classify_section_type(self, content: str) -> str:
        """
        Classify the type of section based on content
        
        Args:
            content: Section content
            
        Returns:
            Section type classification
        """
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['procedure', 'process', 'step', 'method']):
            return 'procedural'
        elif any(word in content_lower for word in ['definition', 'means', 'defined as']):
            return 'definitional'
        elif any(word in content_lower for word in ['power', 'authority', 'responsibility']):
            return 'authority'
        elif any(word in content_lower for word in ['meeting', 'notice', 'quorum']):
            return 'governance'
        else:
            return 'general'
    
    def contains_procedures(self, content: str) -> bool:
        """Check if content contains procedural information"""
        procedure_indicators = ['shall', 'must', 'procedure', 'step', 'process', 'following']
        return any(indicator in content.lower() for indicator in procedure_indicators)
    
    def contains_requirements(self, content: str) -> bool:
        """Check if content contains requirements"""
        requirement_indicators = ['required', 'requirement', 'must', 'shall', 'mandatory', 'necessary']
        return any(indicator in content.lower() for indicator in requirement_indicators)

# Global instance
_section_extractor = None

def get_section_extractor() -> UniversalSectionExtractor:
    """Get the global section extractor instance"""
    global _section_extractor
    if _section_extractor is None:
        _section_extractor = UniversalSectionExtractor()
    return _section_extractor

def extract_detailed_sections(content: str, query: str) -> List[Dict[str, Any]]:
    """
    Convenience function for detailed section extraction
    
    Args:
        content: Document content
        query: User query
        
    Returns:
        List of detailed sections with full content
    """
    extractor = get_section_extractor()
    return extractor.extract_complete_sections(content, query)
