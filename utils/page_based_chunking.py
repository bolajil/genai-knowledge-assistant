"""
Page-Based Document Chunking Strategy
Splits documents by pages and preserves headers/sections for better LLM processing
"""

import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PageBasedChunker:
    """
    Chunks documents by pages while preserving headers and section context
    """
    
    def __init__(self, preserve_headers: bool = True, include_page_numbers: bool = True):
        self.preserve_headers = preserve_headers
        self.include_page_numbers = include_page_numbers
    
    def chunk_document_by_pages(self, content: str, document_name: str = "") -> List[Dict[str, Any]]:
        """
        Split document into page-based chunks with preserved context
        
        Args:
            content: Full document text
            document_name: Name/identifier for the document
            
        Returns:
            List of chunk dictionaries with page-based structure
        """
        try:
            chunks = []
            
            # Split by page markers (--- Page X ---)
            page_pattern = r'--- Page (\d+) ---'
            pages = re.split(page_pattern, content)
            
            if len(pages) <= 1:
                # No page markers found, fall back to section-based chunking
                return self._chunk_by_sections(content, document_name)
            
            # Process pages (skip first empty element if present)
            page_start_idx = 1 if pages[0].strip() == '' else 0
            
            for i in range(page_start_idx, len(pages), 2):
                if i + 1 < len(pages):
                    page_number = pages[i]
                    page_content = pages[i + 1].strip()
                    
                    if page_content:
                        chunk = self._create_page_chunk(
                            page_content, 
                            int(page_number), 
                            document_name
                        )
                        chunks.append(chunk)
            
            logger.info(f"Created {len(chunks)} page-based chunks for {document_name}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error in page-based chunking: {e}")
            return self._fallback_chunking(content, document_name)
    
    def _create_page_chunk(self, page_content: str, page_number: int, document_name: str) -> Dict[str, Any]:
        """Create a structured chunk for a single page"""
        
        # Extract sections and headers from the page
        sections = self._extract_page_sections(page_content)
        
        # Clean content (remove copyright, excessive whitespace)
        cleaned_content = self._clean_page_content(page_content)
        
        # Create page header if enabled
        page_header = f"Page {page_number}" if self.include_page_numbers else ""
        
        # Build structured content
        if self.preserve_headers and sections:
            structured_content = f"{page_header}\n\n"
            for section in sections:
                structured_content += f"## {section['title']}\n{section['content']}\n\n"
        else:
            structured_content = f"{page_header}\n\n{cleaned_content}"
        
        return {
            'content': structured_content.strip(),
            'page': page_number,
            'sections': [s['title'] for s in sections] if sections else [],
            'source': f"{document_name} - Page {page_number}",
            'metadata': {
                'page_number': page_number,
                'document': document_name,
                'section_count': len(sections),
                'chunk_type': 'page_based'
            },
            'length': len(structured_content),
            'raw_content': cleaned_content
        }
    
    def _extract_page_sections(self, page_content: str) -> List[Dict[str, str]]:
        """Extract sections and their titles from a page"""
        sections = []
        
        # Common section patterns
        section_patterns = [
            r'Section (\d+)\.\s*([^\n]+)',  # Section 1. Title
            r'([A-Z][A-Z\s]+)\n',          # ALL CAPS HEADERS
            r'([A-Z][a-z\s]+):\s*\n',      # Title Case with colon
            r'ARTICLE ([IVX]+)\.\s*([^\n]+)'  # ARTICLE IV. Title
        ]
        
        lines = page_content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line matches any section pattern
            is_section_header = False
            for pattern in section_patterns:
                match = re.match(pattern, line)
                if match:
                    # Save previous section if exists
                    if current_section:
                        sections.append({
                            'title': current_section,
                            'content': '\n'.join(current_content).strip()
                        })
                    
                    # Start new section
                    if len(match.groups()) > 1:
                        current_section = f"{match.group(1)} {match.group(2)}"
                    else:
                        current_section = match.group(1)
                    current_content = []
                    is_section_header = True
                    break
            
            if not is_section_header:
                current_content.append(line)
        
        # Add final section
        if current_section and current_content:
            sections.append({
                'title': current_section,
                'content': '\n'.join(current_content).strip()
            })
        
        return sections
    
    def _clean_page_content(self, content: str) -> str:
        """Clean page content by removing unwanted elements"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip copyright, page numbers, and other metadata
            if (line and 
                not line.startswith('Copyright') and 
                not line.startswith('2022136118') and
                not re.match(r'^\d+$', line) and  # Skip standalone numbers
                len(line) > 3):  # Skip very short lines
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _chunk_by_sections(self, content: str, document_name: str) -> List[Dict[str, Any]]:
        """Fallback: chunk by sections when no page markers found"""
        chunks = []
        
        # Split by major sections
        section_pattern = r'(Section \d+\.|ARTICLE [IVX]+\.|[A-Z][A-Z\s]{10,})'
        sections = re.split(section_pattern, content)
        
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                section_title = sections[i].strip()
                section_content = sections[i + 1].strip()
                
                if section_content and len(section_content) > 100:
                    chunk = {
                        'content': f"## {section_title}\n\n{section_content}",
                        'page': 1,  # Default page
                        'sections': [section_title],
                        'source': f"{document_name} - {section_title}",
                        'metadata': {
                            'section_title': section_title,
                            'document': document_name,
                            'chunk_type': 'section_based'
                        },
                        'length': len(section_content),
                        'raw_content': section_content
                    }
                    chunks.append(chunk)
        
        return chunks
    
    def _fallback_chunking(self, content: str, document_name: str) -> List[Dict[str, Any]]:
        """Final fallback: basic text chunking"""
        chunk_size = 1500
        chunks = []
        
        for i in range(0, len(content), chunk_size):
            chunk_content = content[i:i + chunk_size]
            if chunk_content.strip():
                chunk = {
                    'content': chunk_content,
                    'page': (i // chunk_size) + 1,
                    'sections': [],
                    'source': f"{document_name} - Chunk {len(chunks) + 1}",
                    'metadata': {
                        'document': document_name,
                        'chunk_type': 'fallback',
                        'start_pos': i
                    },
                    'length': len(chunk_content),
                    'raw_content': chunk_content
                }
                chunks.append(chunk)
        
        return chunks

def process_document_with_page_chunking(file_path: str) -> List[Dict[str, Any]]:
    """
    Process a document using page-based chunking strategy
    
    Args:
        file_path: Path to the document file
        
    Returns:
        List of page-based chunks
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Document not found: {file_path}")
            return []
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunker = PageBasedChunker(preserve_headers=True, include_page_numbers=True)
        chunks = chunker.chunk_document_by_pages(content, path.stem)
        
        logger.info(f"Processed {path.name} into {len(chunks)} page-based chunks")
        return chunks
        
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")
        return []

def regenerate_index_with_page_chunks(index_name: str) -> bool:
    """
    Regenerate an index using page-based chunking
    
    Args:
        index_name: Name of the index to regenerate
        
    Returns:
        Success status
    """
    try:
        from utils.index_manager import IndexManager
        
        # Get document path for the index
        index_path = Path(f"data/indexes/{index_name}")
        extracted_text_path = index_path / "extracted_text.txt"
        
        if not extracted_text_path.exists():
            logger.error(f"No extracted text found for index: {index_name}")
            return False
        
        # Process with page-based chunking
        chunks = process_document_with_page_chunking(str(extracted_text_path))
        
        if not chunks:
            logger.error("No chunks generated from page-based processing")
            return False
        
        # Initialize index manager and rebuild
        manager = IndexManager()
        
        # Convert chunks to format expected by IndexManager
        documents = []
        for chunk in chunks:
            documents.append({
                'content': chunk['content'],
                'metadata': chunk['metadata'],
                'source': chunk['source']
            })
        
        # Rebuild index with page-based chunks
        success = manager.create_index_from_documents(index_name, documents)
        
        if success:
            logger.info(f"Successfully regenerated {index_name} with page-based chunks")
        else:
            logger.error(f"Failed to regenerate {index_name}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error regenerating index {index_name}: {e}")
        return False
