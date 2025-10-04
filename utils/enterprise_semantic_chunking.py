"""
Enterprise Semantic Chunking System

Implements advanced semantic chunking using LangChain-style recursive text splitting
with document structure awareness and metadata preservation.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Enhanced document chunk with comprehensive metadata"""
    content: str
    source: str
    chunk_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'content': self.content,
            'source': self.source,
            'chunk_id': self.chunk_id,
            'metadata': self.metadata
        }

class RecursiveCharacterTextSplitter:
    """LangChain-style recursive text splitter with enterprise enhancements"""
    
    def __init__(
        self,
        chunk_size: int = 1500,
        chunk_overlap: int = 500,
        separators: List[str] = None,
        length_function: callable = len,
        is_separator_regex: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function
        self.is_separator_regex = is_separator_regex
        
        # Default separators in order of preference
        self.separators = separators or [
            "\n\n",  # Paragraphs
            "\n",    # Lines
            r"(?<=\. )",  # Sentences (regex)
            " ",     # Words
            ""       # Characters
        ]
    
    def split_text(self, text: str) -> List[str]:
        """Split text recursively using separators"""
        return self._split_text_recursive(text, self.separators)
    
    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using the provided separators"""
        if not separators:
            return [text] if text else []
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        # Split by current separator
        if self.is_separator_regex and separator not in [" ", ""]:
            try:
                splits = re.split(separator, text)
            except re.error:
                splits = text.split(separator)
        else:
            splits = text.split(separator)
        
        # Process splits
        chunks = []
        current_chunk = ""
        
        for split in splits:
            if not split:
                continue
            
            # Check if adding this split would exceed chunk size
            potential_chunk = current_chunk + separator + split if current_chunk else split
            
            if self.length_function(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # Current chunk is ready, save it
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Check if split itself is too large
                if self.length_function(split) > self.chunk_size:
                    # Recursively split this piece
                    sub_chunks = self._split_text_recursive(split, remaining_separators)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        # Add overlap between chunks
        return self._add_overlap(chunks)
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """Add overlap between consecutive chunks"""
        if len(chunks) <= 1 or self.chunk_overlap <= 0:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
            else:
                # Get overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-self.chunk_overlap:] if len(prev_chunk) > self.chunk_overlap else prev_chunk
                
                # Add overlap to current chunk
                overlapped_chunk = overlap_text + "\n\n" + chunk
                overlapped_chunks.append(overlapped_chunk)
        
        return overlapped_chunks

class HTMLHeaderTextSplitter:
    """Split HTML/structured text based on headers"""
    
    def __init__(self, headers_to_split_on: List[Tuple[str, str]]):
        self.headers_to_split_on = headers_to_split_on
    
    def split_text(self, text: str) -> List[DocumentChunk]:
        """Split text based on HTML headers or markdown headers"""
        chunks = []
        
        # Convert headers to regex patterns
        header_patterns = []
        for tag, name in self.headers_to_split_on:
            if tag.startswith('h'):
                # HTML header
                pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
                header_patterns.append((pattern, name, tag))
            else:
                # Markdown header
                level = len(tag) if tag.startswith('#') else 1
                pattern = rf'^{"#" * level}\s+(.*?)$'
                header_patterns.append((pattern, name, tag))
        
        # Find all headers
        headers = []
        for pattern, name, tag in header_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                headers.append({
                    'start': match.start(),
                    'end': match.end(),
                    'title': match.group(1).strip(),
                    'level': name,
                    'tag': tag
                })
        
        # Sort headers by position
        headers.sort(key=lambda x: x['start'])
        
        # Split text into sections
        for i, header in enumerate(headers):
            start_pos = header['end']
            end_pos = headers[i + 1]['start'] if i + 1 < len(headers) else len(text)
            
            section_content = text[start_pos:end_pos].strip()
            if section_content:
                chunks.append(DocumentChunk(
                    content=section_content,
                    source=f"Section: {header['title']}",
                    chunk_id=f"section_{i}",
                    metadata={
                        'header_title': header['title'],
                        'header_level': header['level'],
                        'section_number': i + 1,
                        'chunk_type': 'section'
                    }
                ))
        
        return chunks

class EnterpriseSemanticChunker:
    """Enterprise-grade semantic chunking with structure awareness"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "chunk_size": 1500,
            "chunk_overlap": 500,
            "respect_section_breaks": True,
            "extract_tables": True,
            "preserve_heading_structure": True,
            "detect_document_type": True
        }
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["chunk_size"],
            chunk_overlap=self.config["chunk_overlap"]
        )
        
        self.html_splitter = HTMLHeaderTextSplitter([
            ("h1", "Header 1"),
            ("h2", "Header 2"),
            ("h3", "Header 3"),
            ("#", "Markdown H1"),
            ("##", "Markdown H2"),
            ("###", "Markdown H3")
        ])
    
    def chunk_document(self, text: str, source: str, document_type: str = None) -> List[DocumentChunk]:
        """Main chunking method with document type detection"""
        try:
            # Auto-detect document type if not provided
            if not document_type and self.config.get("detect_document_type", True):
                document_type = self._detect_document_type(text)
            
            # Apply document-specific chunking strategy
            if document_type == "legal":
                return self._chunk_legal_document(text, source)
            elif document_type == "technical":
                return self._chunk_technical_document(text, source)
            elif document_type == "structured":
                return self._chunk_structured_document(text, source)
            else:
                return self._chunk_general_document(text, source)
                
        except Exception as e:
            logger.error(f"Chunking failed for {source}: {e}")
            return self._fallback_chunking(text, source)
    
    def _detect_document_type(self, text: str) -> str:
        """Auto-detect document type based on content patterns"""
        text_lower = text.lower()
        
        # Legal document indicators
        legal_indicators = [
            "article", "section", "bylaws", "whereas", "therefore",
            "shall", "agreement", "contract", "legal", "law"
        ]
        
        # Technical document indicators
        technical_indicators = [
            "api", "function", "class", "method", "parameter",
            "configuration", "installation", "setup", "code"
        ]
        
        # Structured document indicators
        structured_indicators = [
            "<h1>", "<h2>", "<h3>", "# ", "## ", "### ",
            "table", "| ", "+--", "===", "---"
        ]
        
        legal_score = sum(1 for indicator in legal_indicators if indicator in text_lower)
        technical_score = sum(1 for indicator in technical_indicators if indicator in text_lower)
        structured_score = sum(1 for indicator in structured_indicators if indicator in text)
        
        if legal_score >= 3:
            return "legal"
        elif technical_score >= 3:
            return "technical"
        elif structured_score >= 2:
            return "structured"
        else:
            return "general"
    
    def _chunk_legal_document(self, text: str, source: str) -> List[DocumentChunk]:
        """Specialized chunking for legal documents"""
        chunks = []
        
        # First, identify major sections (Articles, Sections)
        article_pattern = r'(ARTICLE [IVX]+\..*?)(?=ARTICLE [IVX]+\.|$)'
        section_pattern = r'(SECTION \d+\..*?)(?=SECTION \d+\.|ARTICLE [IVX]+\.|$)'
        
        # Split by articles first
        articles = re.split(r'(?=ARTICLE [IVX]+\.)', text, flags=re.IGNORECASE)
        
        for article_num, article_text in enumerate(articles):
            if not article_text.strip():
                continue
            
            # Extract article title
            article_match = re.match(r'(ARTICLE [IVX]+\..*?)(?:\n|$)', article_text, re.IGNORECASE)
            article_title = article_match.group(1) if article_match else f"Article {article_num + 1}"
            
            # Split article into sections
            sections = re.split(r'(?=SECTION \d+\.)', article_text, flags=re.IGNORECASE)
            
            for section_num, section_text in enumerate(sections):
                if len(section_text.strip()) > 100:  # Only substantial sections
                    # Further chunk if section is too large
                    if len(section_text) > self.config["chunk_size"]:
                        sub_chunks = self.text_splitter.split_text(section_text)
                        for sub_num, sub_chunk in enumerate(sub_chunks):
                            chunks.append(DocumentChunk(
                                content=sub_chunk,
                                source=source,
                                chunk_id=f"article_{article_num}_section_{section_num}_chunk_{sub_num}",
                                metadata={
                                    'document_type': 'legal',
                                    'article_title': article_title,
                                    'article_number': article_num + 1,
                                    'section_number': section_num + 1,
                                    'chunk_type': 'legal_subsection',
                                    'char_count': len(sub_chunk),
                                    'word_count': len(sub_chunk.split())
                                }
                            ))
                    else:
                        chunks.append(DocumentChunk(
                            content=section_text.strip(),
                            source=source,
                            chunk_id=f"article_{article_num}_section_{section_num}",
                            metadata={
                                'document_type': 'legal',
                                'article_title': article_title,
                                'article_number': article_num + 1,
                                'section_number': section_num + 1,
                                'chunk_type': 'legal_section',
                                'char_count': len(section_text),
                                'word_count': len(section_text.split())
                            }
                        ))
        
        return chunks
    
    def _chunk_technical_document(self, text: str, source: str) -> List[DocumentChunk]:
        """Specialized chunking for technical documents"""
        # Use HTML/Markdown header splitting for technical docs
        if any(marker in text for marker in ["#", "<h", "```"]):
            header_chunks = self.html_splitter.split_text(text)
            
            # Further split large sections
            final_chunks = []
            for chunk in header_chunks:
                if len(chunk.content) > self.config["chunk_size"]:
                    sub_chunks = self.text_splitter.split_text(chunk.content)
                    for i, sub_chunk in enumerate(sub_chunks):
                        final_chunks.append(DocumentChunk(
                            content=sub_chunk,
                            source=source,
                            chunk_id=f"{chunk.chunk_id}_sub_{i}",
                            metadata={
                                **chunk.metadata,
                                'document_type': 'technical',
                                'parent_section': chunk.metadata.get('header_title', 'Unknown'),
                                'sub_chunk_number': i + 1
                            }
                        ))
                else:
                    chunk.metadata.update({
                        'document_type': 'technical',
                        'char_count': len(chunk.content),
                        'word_count': len(chunk.content.split())
                    })
                    final_chunks.append(chunk)
            
            return final_chunks
        else:
            return self._chunk_general_document(text, source)
    
    def _chunk_structured_document(self, text: str, source: str) -> List[DocumentChunk]:
        """Chunking for structured documents with headers/tables"""
        return self.html_splitter.split_text(text)
    
    def _chunk_general_document(self, text: str, source: str) -> List[DocumentChunk]:
        """General purpose chunking"""
        text_chunks = self.text_splitter.split_text(text)
        
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunks.append(DocumentChunk(
                content=chunk_text,
                source=source,
                chunk_id=f"chunk_{i}",
                metadata={
                    'document_type': 'general',
                    'chunk_number': i + 1,
                    'char_count': len(chunk_text),
                    'word_count': len(chunk_text.split()),
                    'chunk_type': 'general_content'
                }
            ))
        
        return chunks
    
    def _fallback_chunking(self, text: str, source: str) -> List[DocumentChunk]:
        """Simple fallback chunking if main methods fail"""
        try:
            # Simple paragraph-based splitting
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            chunks = []
            current_chunk = ""
            chunk_num = 0
            
            for paragraph in paragraphs:
                if len(current_chunk + paragraph) > self.config["chunk_size"] and current_chunk:
                    chunks.append(DocumentChunk(
                        content=current_chunk.strip(),
                        source=source,
                        chunk_id=f"fallback_chunk_{chunk_num}",
                        metadata={
                            'document_type': 'unknown',
                            'chunk_type': 'fallback',
                            'char_count': len(current_chunk),
                            'word_count': len(current_chunk.split())
                        }
                    ))
                    chunk_num += 1
                    current_chunk = paragraph
                else:
                    current_chunk += "\n\n" + paragraph if current_chunk else paragraph
            
            # Add final chunk
            if current_chunk:
                chunks.append(DocumentChunk(
                    content=current_chunk.strip(),
                    source=source,
                    chunk_id=f"fallback_chunk_{chunk_num}",
                    metadata={
                        'document_type': 'unknown',
                        'chunk_type': 'fallback',
                        'char_count': len(current_chunk),
                        'word_count': len(current_chunk.split())
                    }
                ))
            
            return chunks
            
        except Exception as e:
            logger.error(f"Fallback chunking failed: {e}")
            return []

def get_enterprise_semantic_chunker(config: Dict[str, Any] = None) -> EnterpriseSemanticChunker:
    """Get instance of enterprise semantic chunker"""
    return EnterpriseSemanticChunker(config)

def chunk_document_with_metadata(text: str, source: str, document_type: str = None) -> List[DocumentChunk]:
    """Convenience function for chunking with metadata"""
    chunker = get_enterprise_semantic_chunker()
    return chunker.chunk_document(text, source, document_type)
