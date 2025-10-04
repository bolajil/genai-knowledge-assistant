"""
PDF Section Extractor
====================
Extracts actual section content from PDF documents instead of table of contents.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import PyPDF2
import pdfplumber

logger = logging.getLogger(__name__)

class PDFSectionExtractor:
    """Extract actual section content from PDF documents."""
    
    def __init__(self):
        self.section_patterns = [
            r'Section\s+(\d+)\.\s+([A-Z\s]+[;:]?\s*[A-Za-z\s]*)',  # Section 2. BOARD MEETINGS; Action
            r'ARTICLE\s+([IVX]+)\.\s+([A-Z\s]+)',  # ARTICLE III. BOARD OF DIRECTORS
            r'([A-Z]\.\s+[A-Z\s]+)',  # A. COMPOSITION AND SELECTION
            r'(\d+\.\s+[A-Za-z\s]+)',  # 1. Organizational MEETINGS
        ]
    
    def extract_pdf_text_with_structure(self, pdf_path: str) -> Dict[str, str]:
        """Extract text from PDF while preserving structure."""
        try:
            structured_content = {}
            
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- Page {page_num} ---\n{page_text}\n"
                
                # Split into sections
                sections = self._parse_sections(full_text)
                return sections
                
        except Exception as e:
            logger.error(f"Error extracting PDF structure: {e}")
            return {}
    
    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse text into sections with actual content."""
        sections = {}
        
        # Find all section headers and their positions
        section_matches = []
        for pattern in self.section_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            for match in matches:
                section_matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'title': match.group(0).strip(),
                    'full_match': match.group(0)
                })
        
        # Sort by position in document
        section_matches.sort(key=lambda x: x['start'])
        
        # Extract content between sections
        for i, section in enumerate(section_matches):
            section_title = section['title']
            section_start = section['end']
            
            # Find end of this section (start of next section or end of document)
            if i + 1 < len(section_matches):
                section_end = section_matches[i + 1]['start']
            else:
                section_end = len(text)
            
            # Extract section content
            section_content = text[section_start:section_end].strip()
            
            # Clean up content - remove excessive whitespace
            section_content = re.sub(r'\n\s*\n\s*\n', '\n\n', section_content)
            section_content = re.sub(r'[ \t]+', ' ', section_content)
            
            # Only include sections with substantial content (not just TOC entries)
            if len(section_content) > 100 and not self._is_toc_entry(section_content):
                sections[section_title] = section_content
        
        return sections
    
    def _is_toc_entry(self, content: str) -> bool:
        """Check if content is just a table of contents entry."""
        # TOC entries typically have lots of dots and page numbers
        dot_count = content.count('.')
        page_numbers = len(re.findall(r'\b\d+\b', content))
        
        # If more than 30% dots or lots of isolated numbers, likely TOC
        if len(content) > 0 and (dot_count / len(content) > 0.3 or page_numbers > 5):
            return True
        
        # Check for TOC-specific patterns
        toc_patterns = [
            r'\.{3,}',  # Multiple dots
            r'\d+\s*$',  # Ends with page number
            r'^\s*[A-Z]\.\s+[A-Z\s]+\s*\.{3,}\s*\d+',  # A. SECTION NAME ... 5
        ]
        
        for pattern in toc_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        
        return False
    
    def find_section_content(self, pdf_path: str, query: str) -> List[Dict[str, str]]:
        """Find sections that match the query and return their full content."""
        sections = self.extract_pdf_text_with_structure(pdf_path)
        
        matching_sections = []
        query_lower = query.lower()
        
        # Search for relevant sections
        for section_title, section_content in sections.items():
            title_lower = section_title.lower()
            content_lower = section_content.lower()
            
            # Check if query matches section title or content
            if (any(word in title_lower for word in query_lower.split()) or
                any(word in content_lower for word in query_lower.split())):
                
                matching_sections.append({
                    'section_title': section_title,
                    'content': section_content,
                    'word_count': len(section_content.split()),
                    'relevance_score': self._calculate_relevance(query, section_title, section_content)
                })
        
        # Sort by relevance
        matching_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return matching_sections
    
    def _calculate_relevance(self, query: str, title: str, content: str) -> float:
        """Calculate relevance score for a section."""
        query_words = set(query.lower().split())
        title_words = set(title.lower().split())
        content_words = set(content.lower().split())
        
        # Title matches are more important
        title_matches = len(query_words.intersection(title_words))
        content_matches = len(query_words.intersection(content_words))
        
        # Calculate score
        title_score = title_matches * 2.0  # Title matches worth double
        content_score = content_matches * 0.1  # Content matches worth less
        
        total_score = title_score + content_score
        
        # Normalize by query length
        if len(query_words) > 0:
            total_score = total_score / len(query_words)
        
        return total_score

def extract_board_meeting_procedures(pdf_path: str) -> Dict[str, str]:
    """Specific function to extract board meeting procedures."""
    extractor = PDFSectionExtractor()
    
    # Look for board meeting related sections
    queries = [
        "board meetings",
        "action outside meeting",
        "notice of meetings",
        "special meetings",
        "quorum",
        "conduct of meetings"
    ]
    
    all_sections = {}
    
    for query in queries:
        sections = extractor.find_section_content(pdf_path, query)
        for section in sections:
            all_sections[section['section_title']] = section['content']
    
    return all_sections

if __name__ == "__main__":
    # Test the extractor
    pdf_path = r"c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\indexes\ByLawS2_index\source_document.pdf"
    
    if Path(pdf_path).exists():
        extractor = PDFSectionExtractor()
        sections = extractor.find_section_content(pdf_path, "board meetings action outside")
        
        print(f"Found {len(sections)} relevant sections:")
        for section in sections[:3]:  # Show top 3
            print(f"\n{'='*50}")
            print(f"SECTION: {section['section_title']}")
            print(f"RELEVANCE: {section['relevance_score']:.2f}")
            print(f"WORD COUNT: {section['word_count']}")
            print(f"{'='*50}")
            print(section['content'][:500] + "..." if len(section['content']) > 500 else section['content'])
    else:
        print(f"PDF file not found: {pdf_path}")
