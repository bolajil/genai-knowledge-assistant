"""
Intelligent Chunking System for Enterprise Document Processing

This module provides advanced chunking strategies that maintain document coherence
and context while optimizing for retrieval accuracy.
"""

import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class IntelligentChunker:
    """Advanced document chunker that preserves context and coherence"""
    
    def __init__(self):
        self.section_patterns = [
            r'^(ARTICLE [IVX]+\..*?)$',           # Articles (Roman numerals)
            r'^(SECTION \d+\..*?)$',              # Sections
            r'^([A-Z]\.\s+[A-Z\s]+)$',           # Lettered sections
            r'^(\d+\.\s+[A-Z\s]+)$',             # Numbered sections
            r'^([A-Z][A-Z\s]{10,})$',            # All caps headers
            r'^(\d+\.\d+\s+.*?)$',               # Subsections (1.1, 1.2, etc.)
        ]
        
        self.sentence_endings = ['.', '!', '?', ';']
        self.paragraph_markers = ['\n\n', '\r\n\r\n']
    
    def chunk_document(self, text: str, strategy: str = 'contextual', 
                      chunk_size: int = 1500, overlap: int = 300) -> List[Dict[str, Any]]:
        """
        Chunk document using specified strategy
        
        Args:
            text: Document text to chunk
            strategy: Chunking strategy ('contextual', 'semantic', 'hierarchical')
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if strategy == 'contextual':
            return self._contextual_chunking(text, chunk_size, overlap)
        elif strategy == 'semantic':
            return self._semantic_chunking(text, chunk_size, overlap)
        elif strategy == 'hierarchical':
            return self._hierarchical_chunking(text, chunk_size, overlap)
        else:
            return self._contextual_chunking(text, chunk_size, overlap)
    
    def _contextual_chunking(self, text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """
        Context-aware chunking that preserves document structure and meaning
        """
        chunks = []
        
        # First, identify document structure
        sections = self._identify_document_sections(text)
        
        for section_title, section_content, section_start in sections:
            if len(section_content) <= chunk_size:
                # Small section - keep as single chunk
                chunks.append({
                    'content': section_content.strip(),
                    'metadata': {
                        'section': section_title,
                        'chunk_type': 'complete_section',
                        'char_count': len(section_content),
                        'word_count': len(section_content.split())
                    }
                })
            else:
                # Large section - split intelligently
                section_chunks = self._split_large_section(
                    section_content, section_title, chunk_size, overlap
                )
                chunks.extend(section_chunks)
        
        return chunks
    
    def _identify_document_sections(self, text: str) -> List[Tuple[str, str, int]]:
        """
        Identify document sections based on headers and structure
        
        Returns:
            List of (section_title, section_content, start_position) tuples
        """
        sections = []
        lines = text.split('\n')
        current_section = "Introduction"
        current_content = []
        start_pos = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line is a section header
            is_header = False
            for pattern in self.section_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    # Found a new section
                    if current_content:
                        # Save previous section
                        content = '\n'.join(current_content)
                        sections.append((current_section, content, start_pos))
                    
                    # Start new section
                    current_section = line_stripped
                    current_content = []
                    start_pos = i
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Add final section
        if current_content:
            content = '\n'.join(current_content)
            sections.append((current_section, content, start_pos))
        
        return sections
    
    def _split_large_section(self, content: str, section_title: str, 
                           chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """
        Split large sections while preserving context and coherence
        """
        chunks = []
        paragraphs = self._split_into_paragraphs(content)
        
        current_chunk = ""
        current_paragraphs = []
        chunk_num = 1
        
        for para in paragraphs:
            # Check if adding this paragraph would exceed chunk size
            potential_chunk = current_chunk + "\n\n" + para if current_chunk else para
            
            if len(potential_chunk) > chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append({
                    'content': current_chunk.strip(),
                    'metadata': {
                        'section': section_title,
                        'chunk_type': 'section_part',
                        'chunk_number': chunk_num,
                        'char_count': len(current_chunk),
                        'word_count': len(current_chunk.split()),
                        'paragraph_count': len(current_paragraphs)
                    }
                })
                
                # Start new chunk with overlap
                overlap_content = self._create_overlap(current_paragraphs, overlap)
                current_chunk = overlap_content + "\n\n" + para if overlap_content else para
                current_paragraphs = [para]
                chunk_num += 1
            else:
                # Add paragraph to current chunk
                current_chunk = potential_chunk
                current_paragraphs.append(para)
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': {
                    'section': section_title,
                    'chunk_type': 'section_part',
                    'chunk_number': chunk_num,
                    'char_count': len(current_chunk),
                    'word_count': len(current_chunk.split()),
                    'paragraph_count': len(current_paragraphs)
                }
            })
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs, handling various paragraph markers"""
        # Split by double newlines first
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Further split very long paragraphs at sentence boundaries
        refined_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if len(para) > 800:  # Long paragraph - split at sentences
                sentences = self._split_into_sentences(para)
                current_para = ""
                
                for sentence in sentences:
                    if len(current_para + sentence) > 800 and current_para:
                        refined_paragraphs.append(current_para.strip())
                        current_para = sentence
                    else:
                        current_para += " " + sentence if current_para else sentence
                
                if current_para.strip():
                    refined_paragraphs.append(current_para.strip())
            else:
                if para:
                    refined_paragraphs.append(para)
        
        return refined_paragraphs
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using multiple delimiters"""
        # Simple sentence splitting - can be enhanced with NLP libraries
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            if char in self.sentence_endings:
                # Check if this is likely end of sentence (not abbreviation)
                if len(current_sentence.strip()) > 10:
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
        
        # Add remaining text
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def _create_overlap(self, paragraphs: List[str], overlap_chars: int) -> str:
        """Create overlap content from the end of previous chunk"""
        if not paragraphs:
            return ""
        
        # Take last few paragraphs that fit within overlap limit
        overlap_content = ""
        for para in reversed(paragraphs):
            potential_overlap = para + "\n\n" + overlap_content if overlap_content else para
            if len(potential_overlap) <= overlap_chars:
                overlap_content = potential_overlap
            else:
                break
        
        return overlap_content
    
    def _semantic_chunking(self, text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """Semantic chunking based on content meaning and structure"""
        # This is a simplified version - can be enhanced with NLP libraries
        return self._contextual_chunking(text, chunk_size, overlap)
    
    def _hierarchical_chunking(self, text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """Hierarchical chunking that preserves document hierarchy"""
        # This is a simplified version - can be enhanced with document structure analysis
        return self._contextual_chunking(text, chunk_size, overlap)

def get_intelligent_chunker() -> IntelligentChunker:
    """Get instance of intelligent chunker"""
    return IntelligentChunker()

def optimize_chunking_for_index(index_path: str) -> Dict[str, Any]:
    """
    Analyze existing index and recommend optimal chunking parameters
    
    Args:
        index_path: Path to the document index
        
    Returns:
        Dictionary with recommended chunking parameters
    """
    recommendations = {
        'chunk_size': 1500,
        'overlap': 300,
        'strategy': 'contextual',
        'reasoning': []
    }
    
    try:
        # Check if extracted text exists
        extracted_text_path = Path(index_path) / "extracted_text.txt"
        if extracted_text_path.exists():
            with open(extracted_text_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Analyze document characteristics
            total_length = len(content)
            avg_paragraph_length = len(content) / max(1, content.count('\n\n'))
            
            # Adjust recommendations based on document characteristics
            if total_length > 100000:  # Very large document
                recommendations['chunk_size'] = 2000
                recommendations['overlap'] = 400
                recommendations['reasoning'].append("Large document - increased chunk size for better context")
            
            if avg_paragraph_length > 1000:  # Long paragraphs
                recommendations['strategy'] = 'hierarchical'
                recommendations['reasoning'].append("Long paragraphs detected - using hierarchical chunking")
            
            # Check for structured content (articles, sections)
            if re.search(r'ARTICLE [IVX]+|SECTION \d+', content):
                recommendations['strategy'] = 'contextual'
                recommendations['reasoning'].append("Structured document detected - using contextual chunking")
        
        # Check existing metadata
        meta_path = Path(index_path) / "index.meta"
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta_content = f.read()
            
            # Extract current parameters
            current_chunk_size = re.search(r'Chunk size: (\d+)', meta_content)
            current_overlap = re.search(r'Chunk overlap: (\d+)', meta_content)
            
            if current_chunk_size and current_overlap:
                current_size = int(current_chunk_size.group(1))
                current_over = int(current_overlap.group(1))
                
                if current_size < 1000:
                    recommendations['reasoning'].append("Current chunk size too small - may cause fragmentation")
                if current_over < 200:
                    recommendations['reasoning'].append("Current overlap too small - may lose context")
    
    except Exception as e:
        logger.error(f"Error analyzing index for chunking optimization: {e}")
        recommendations['reasoning'].append(f"Analysis error: {e}")
    
    return recommendations
