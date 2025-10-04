"""
Enterprise Document Processor

Comprehensive document processing system that handles all file formats
with enterprise-grade accuracy and detailed content extraction.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentChunk:
    """Enhanced document chunk with rich metadata"""
    def __init__(self, content: str, source: str, page: int = None, 
                 section: str = None, chunk_id: int = None, 
                 chunk_type: str = "content", confidence: float = 1.0):
        self.page_content = content
        self.metadata = {
            'source': source,
            'page': page,
            'section': section,
            'chunk_id': chunk_id,
            'chunk_type': chunk_type,
            'confidence': confidence,
            'word_count': len(content.split()),
            'char_count': len(content)
        }

class EnterpriseDocumentProcessor:
    """Enterprise-grade document processor for all file formats"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.doc', '.txt', '.md', '.html', '.htm', '.rtf']
        self.chunk_strategies = {
            'semantic': self._semantic_chunking,
            'hierarchical': self._hierarchical_chunking,
            'sliding_window': self._sliding_window_chunking,
            'paragraph': self._paragraph_chunking
        }
    
    def process_document(self, file_path: str, strategy: str = 'semantic') -> List[DocumentChunk]:
        """Process any document format with specified chunking strategy"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"Document not found: {file_path}")
            return []
        
        # Extract text based on file format
        text_content = self._extract_text(file_path)
        if not text_content:
            return []
        
        # Apply chunking strategy
        chunks = self.chunk_strategies.get(strategy, self._semantic_chunking)(text_content, str(file_path))
        
        logger.info(f"Processed {file_path.name}: {len(chunks)} chunks created")
        return chunks
    
    def _extract_text(self, file_path: Path) -> str:
        """Extract text from various file formats"""
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.pdf':
                return self._extract_pdf_text(file_path)
            elif extension in ['.docx', '.doc']:
                return self._extract_word_text(file_path)
            elif extension in ['.txt', '.md']:
                return self._extract_plain_text(file_path)
            elif extension in ['.html', '.htm']:
                return self._extract_html_text(file_path)
            elif extension == '.rtf':
                return self._extract_rtf_text(file_path)
            else:
                logger.warning(f"Unsupported format: {extension}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF with page preservation"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    text += f"\n--- Page {page_num} ---\n{page_text}\n"
            return text
        except ImportError:
            # Fallback: try to read as text if PyPDF2 not available
            logger.warning("PyPDF2 not available, attempting text extraction")
            return self._extract_plain_text(file_path)
    
    def _extract_word_text(self, file_path: Path) -> str:
        """Extract text from Word documents"""
        try:
            import docx
            doc = docx.Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except ImportError:
            logger.warning("python-docx not available")
            return ""
    
    def _extract_plain_text(self, file_path: Path) -> str:
        """Extract plain text with encoding detection"""
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        
        logger.error(f"Could not decode {file_path} with any encoding")
        return ""
    
    def _extract_html_text(self, file_path: Path) -> str:
        """Extract text from HTML files"""
        try:
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file.read(), 'html.parser')
                return soup.get_text()
        except ImportError:
            # Fallback: basic HTML tag removal
            content = self._extract_plain_text(file_path)
            return re.sub(r'<[^>]+>', '', content)
    
    def _extract_rtf_text(self, file_path: Path) -> str:
        """Extract text from RTF files"""
        try:
            from striprtf.striprtf import rtf_to_text
            with open(file_path, 'r') as file:
                return rtf_to_text(file.read())
        except ImportError:
            logger.warning("striprtf not available")
            return self._extract_plain_text(file_path)
    
    def _semantic_chunking(self, text: str, source: str) -> List[DocumentChunk]:
        """Advanced semantic chunking based on content structure"""
        chunks = []
        
        # Split by pages first if page markers exist
        if "--- Page" in text:
            pages = re.split(r'--- Page \d+ ---', text)
            for page_num, page_content in enumerate(pages, 1):
                if page_content.strip():
                    page_chunks = self._chunk_page_content(page_content.strip(), source, page_num)
                    chunks.extend(page_chunks)
        else:
            # Process as single document
            chunks = self._chunk_page_content(text, source)
        
        return chunks
    
    def _chunk_page_content(self, content: str, source: str, page: int = None) -> List[DocumentChunk]:
        """Chunk content within a page using multiple strategies"""
        chunks = []
        
        # Split by sections (headers, numbered items, etc.)
        sections = self._identify_sections(content)
        
        for section_num, (section_title, section_content) in enumerate(sections, 1):
            if len(section_content) > 1500:  # Large sections need sub-chunking
                sub_chunks = self._sliding_window_chunking(section_content, source, chunk_size=1200, overlap=200)
                for i, sub_chunk in enumerate(sub_chunks):
                    sub_chunk.metadata.update({
                        'page': page,
                        'section': section_title,
                        'chunk_id': f"{section_num}.{i+1}"
                    })
                    chunks.append(sub_chunk)
            else:
                chunk = DocumentChunk(
                    content=section_content,
                    source=source,
                    page=page,
                    section=section_title,
                    chunk_id=section_num,
                    chunk_type="section"
                )
                chunks.append(chunk)
        
        return chunks
    
    def _identify_sections(self, content: str) -> List[Tuple[str, str]]:
        """Identify document sections based on structure"""
        sections = []
        
        # Look for various section patterns
        patterns = [
            r'^(ARTICLE [IVX]+\..*?)$',  # Articles
            r'^([A-Z]\.\s+[A-Z\s]+)$',   # Lettered sections
            r'^(\d+\.\s+[A-Z\s]+)$',     # Numbered sections
            r'^([A-Z][A-Z\s]{10,})$',    # All caps headers
        ]
        
        lines = content.split('\n')
        current_section = "Introduction"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                current_content.append(line)
                continue
            
            # Check if line matches any section pattern
            is_header = False
            for pattern in patterns:
                if re.match(pattern, line):
                    # Save previous section
                    if current_content:
                        sections.append((current_section, '\n'.join(current_content)))
                    
                    # Start new section
                    current_section = line
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections.append((current_section, '\n'.join(current_content)))
        
        return sections
    
    def _hierarchical_chunking(self, text: str, source: str) -> List[DocumentChunk]:
        """Hierarchical chunking based on document structure"""
        # Implementation for hierarchical chunking
        return self._semantic_chunking(text, source)  # Fallback for now
    
    def _sliding_window_chunking(self, text: str, source: str, chunk_size: int = 1000, overlap: int = 200) -> List[DocumentChunk]:
        """Sliding window chunking with overlap"""
        chunks = []
        start = 0
        chunk_id = 1
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size - 200:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk = DocumentChunk(
                    content=chunk_text,
                    source=source,
                    chunk_id=chunk_id,
                    chunk_type="sliding_window"
                )
                chunks.append(chunk)
                chunk_id += 1
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _paragraph_chunking(self, text: str, source: str) -> List[DocumentChunk]:
        """Paragraph-based chunking"""
        paragraphs = text.split('\n\n')
        chunks = []
        
        for i, para in enumerate(paragraphs, 1):
            if para.strip():
                chunk = DocumentChunk(
                    content=para.strip(),
                    source=source,
                    chunk_id=i,
                    chunk_type="paragraph"
                )
                chunks.append(chunk)
        
        return chunks

# Singleton instance
_processor_instance = None

def get_enterprise_processor() -> EnterpriseDocumentProcessor:
    """Get singleton enterprise document processor"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = EnterpriseDocumentProcessor()
    return _processor_instance
