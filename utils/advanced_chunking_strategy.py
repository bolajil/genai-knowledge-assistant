"""
Advanced Chunking Strategy Implementation

Implements sophisticated document chunking with configurable parameters:
- Respects section breaks and document structure
- Extracts and preserves tables
- Maintains heading hierarchy
- Optimized chunk size and overlap
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AdvancedChunkingStrategy:
    """Advanced document chunker with structure-aware processing"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with chunking configuration"""
        self.config = config or {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "respect_section_breaks": True,
            "extract_tables": True,
            "preserve_heading_structure": True
        }
        
        # Patterns for document structure detection
        self.heading_patterns = [
            r'^(#{1,6}\s+.*?)$',                    # Markdown headings
            r'^([A-Z][A-Z\s]{5,})$',               # All caps headings
            r'^(ARTICLE [IVX]+\..*?)$',            # Articles
            r'^(SECTION \d+\..*?)$',               # Sections
            r'^(\d+\.\s+[A-Z].*?)$',               # Numbered headings
            r'^([A-Z]\.\s+[A-Z].*?)$',             # Lettered headings
        ]
        
        self.table_patterns = [
            r'\|.*?\|.*?\|',                       # Markdown tables
            r'^\s*\+[-=]+\+',                     # ASCII tables
            r'^\s*[A-Za-z\s]+\s+[A-Za-z\s]+\s+[A-Za-z\s]+',  # Column-like data
        ]
        
        self.section_break_patterns = [
            r'\n\s*\n\s*\n',                      # Multiple line breaks
            r'---+',                              # Horizontal rules
            r'===+',                              # Double line breaks
            r'^\s*\*\s*\*\s*\*\s*$',             # Asterisk breaks
        ]
    
    def chunk_document(self, text: str, source_name: str = "document") -> List[Dict[str, Any]]:
        """
        Chunk document using advanced strategy
        
        Args:
            text: Document text to chunk
            source_name: Name/identifier for the source document
            
        Returns:
            List of chunk dictionaries with enhanced metadata
        """
        chunks = []
        
        # Step 1: Extract and preserve document structure
        document_structure = self._analyze_document_structure(text)
        
        # Step 2: Extract tables if enabled
        tables = []
        if self.config.get("extract_tables", True):
            text, tables = self._extract_tables(text)
        
        # Step 3: Process by sections if enabled
        if self.config.get("respect_section_breaks", True):
            sections = self._split_by_sections(text, document_structure)
        else:
            sections = [("Main Content", text, 0)]
        
        # Step 4: Chunk each section while preserving structure
        chunk_id = 1
        for section_title, section_content, section_start in sections:
            section_chunks = self._chunk_section(
                section_content, 
                section_title, 
                source_name,
                chunk_id
            )
            chunks.extend(section_chunks)
            chunk_id += len(section_chunks)
        
        # Step 5: Add table chunks if any were extracted
        for table_id, table_content in enumerate(tables, 1):
            chunks.append({
                'content': table_content,
                'source': source_name,
                'chunk_type': 'table',
                'chunk_id': f"table_{table_id}",
                'section': 'Tables',
                'metadata': {
                    'is_table': True,
                    'table_number': table_id,
                    'char_count': len(table_content),
                    'word_count': len(table_content.split())
                }
            })
        
        logger.info(f"Advanced chunking created {len(chunks)} chunks from {source_name}")
        return chunks
    
    def _analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """Analyze document structure to identify headings and sections"""
        structure = {
            'headings': [],
            'sections': [],
            'tables': [],
            'total_lines': len(text.split('\n'))
        }
        
        lines = text.split('\n')
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check for headings
            for pattern in self.heading_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    structure['headings'].append({
                        'text': line_stripped,
                        'line_number': line_num,
                        'level': self._determine_heading_level(line_stripped)
                    })
                    break
        
        return structure
    
    def _determine_heading_level(self, heading_text: str) -> int:
        """Determine the hierarchical level of a heading"""
        # Markdown headings
        if heading_text.startswith('#'):
            return heading_text.count('#')
        
        # Article level (highest)
        if re.match(r'^ARTICLE [IVX]+', heading_text, re.IGNORECASE):
            return 1
        
        # Section level
        if re.match(r'^SECTION \d+', heading_text, re.IGNORECASE):
            return 2
        
        # Numbered items
        if re.match(r'^\d+\.', heading_text):
            return 3
        
        # Lettered items
        if re.match(r'^[A-Z]\.', heading_text):
            return 4
        
        # All caps (assume section level)
        if heading_text.isupper() and len(heading_text) > 5:
            return 2
        
        return 3  # Default level
    
    def _extract_tables(self, text: str) -> Tuple[str, List[str]]:
        """Extract tables from text and return cleaned text + table list"""
        tables = []
        cleaned_text = text
        
        # Find markdown tables
        table_pattern = r'(\|.*?\|.*?\n)+'
        matches = re.finditer(table_pattern, text, re.MULTILINE)
        
        for match in reversed(list(matches)):  # Reverse to maintain indices
            table_content = match.group(0).strip()
            if len(table_content.split('\n')) >= 2:  # At least header + one row
                tables.insert(0, table_content)
                # Replace table with placeholder
                cleaned_text = cleaned_text[:match.start()] + f"\n[TABLE_{len(tables)}]\n" + cleaned_text[match.end():]
        
        # Find ASCII tables (simple detection)
        ascii_table_pattern = r'(\+[-=]+\+.*?\n)+'
        matches = re.finditer(ascii_table_pattern, cleaned_text, re.MULTILINE)
        
        for match in reversed(list(matches)):
            table_content = match.group(0).strip()
            if len(table_content.split('\n')) >= 3:  # Header, separator, data
                tables.insert(0, table_content)
                cleaned_text = cleaned_text[:match.start()] + f"\n[TABLE_{len(tables)}]\n" + cleaned_text[match.end():]
        
        return cleaned_text, tables
    
    def _split_by_sections(self, text: str, structure: Dict[str, Any]) -> List[Tuple[str, str, int]]:
        """Split text by sections based on document structure"""
        sections = []
        
        if not structure['headings']:
            # No headings found, treat as single section
            return [("Main Content", text, 0)]
        
        lines = text.split('\n')
        current_section = "Introduction"
        current_content = []
        current_start = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line is a heading
            is_heading = False
            for heading in structure['headings']:
                if heading['line_number'] == i:
                    # Save previous section
                    if current_content:
                        section_text = '\n'.join(current_content)
                        if section_text.strip():
                            sections.append((current_section, section_text, current_start))
                    
                    # Start new section
                    current_section = heading['text']
                    current_content = []
                    current_start = i
                    is_heading = True
                    break
            
            if not is_heading:
                current_content.append(line)
        
        # Add final section
        if current_content:
            section_text = '\n'.join(current_content)
            if section_text.strip():
                sections.append((current_section, section_text, current_start))
        
        return sections
    
    def _chunk_section(self, content: str, section_title: str, source_name: str, start_chunk_id: int) -> List[Dict[str, Any]]:
        """Chunk a section while preserving structure"""
        chunks = []
        chunk_size = self.config.get("chunk_size", 1000)
        overlap = self.config.get("chunk_overlap", 200)
        
        # Split content into paragraphs
        paragraphs = self._split_into_paragraphs(content)
        
        current_chunk = ""
        current_paragraphs = []
        chunk_num = 0
        
        for para in paragraphs:
            # Check if adding this paragraph exceeds chunk size
            potential_chunk = current_chunk + "\n\n" + para if current_chunk else para
            
            if len(potential_chunk) > chunk_size and current_chunk:
                # Save current chunk
                chunk_num += 1
                chunks.append(self._create_chunk(
                    current_chunk.strip(),
                    source_name,
                    section_title,
                    start_chunk_id + chunk_num - 1,
                    chunk_num,
                    len(current_paragraphs)
                ))
                
                # Start new chunk with substantial overlap for better context
                overlap_content = self._create_overlap_content(current_paragraphs, overlap)
                current_chunk = overlap_content + "\n\n" + para if overlap_content else para
                current_paragraphs = [para]
            else:
                # Add paragraph to current chunk
                current_chunk = potential_chunk
                current_paragraphs.append(para)
        
        # Add final chunk
        if current_chunk.strip():
            chunk_num += 1
            chunks.append(self._create_chunk(
                current_chunk.strip(),
                source_name,
                section_title,
                start_chunk_id + chunk_num - 1,
                chunk_num,
                len(current_paragraphs)
            ))
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs with smart boundary detection"""
        # Split by double newlines first
        paragraphs = re.split(r'\n\s*\n', text)
        
        refined_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If paragraph is too long, split by sentences
            if len(para) > 600:
                sentences = self._split_into_sentences(para)
                current_para = ""
                
                for sentence in sentences:
                    if len(current_para + sentence) > 600 and current_para:
                        refined_paragraphs.append(current_para.strip())
                        current_para = sentence
                    else:
                        current_para += " " + sentence if current_para else sentence
                
                if current_para.strip():
                    refined_paragraphs.append(current_para.strip())
            else:
                refined_paragraphs.append(para)
        
        return refined_paragraphs
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_overlap_content(self, paragraphs: List[str], overlap_chars: int) -> str:
        """Create overlap content from end of previous chunk"""
        if not paragraphs:
            return ""
        
        overlap_content = ""
        for para in reversed(paragraphs):
            potential_overlap = para + "\n\n" + overlap_content if overlap_content else para
            if len(potential_overlap) <= overlap_chars:
                overlap_content = potential_overlap
            else:
                break
        
        return overlap_content
    
    def _create_chunk(self, content: str, source: str, section: str, 
                     chunk_id: int, section_chunk_num: int, paragraph_count: int) -> Dict[str, Any]:
        """Create a chunk dictionary with comprehensive metadata"""
        return {
            'content': content,
            'source': source,
            'section': section,
            'chunk_id': chunk_id,
            'chunk_type': 'content',
            'metadata': {
                'section_chunk_number': section_chunk_num,
                'paragraph_count': paragraph_count,
                'char_count': len(content),
                'word_count': len(content.split()),
                'has_headings': bool(re.search(r'^[A-Z\s]{10,}$', content, re.MULTILINE)),
                'has_numbered_items': bool(re.search(r'^\d+\.', content, re.MULTILINE)),
                'chunking_strategy': 'advanced_structure_aware'
            }
        }

def get_advanced_chunking_strategy(config: Dict[str, Any] = None) -> AdvancedChunkingStrategy:
    """Get instance of advanced chunking strategy"""
    default_config = {
        "chunk_size": 1500,
        "chunk_overlap": 500,
        "respect_section_breaks": True,
        "extract_tables": True,
        "preserve_heading_structure": True
    }
    
    if config:
        default_config.update(config)
    
    return AdvancedChunkingStrategy(default_config)

def apply_advanced_chunking_to_index(index_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Apply advanced chunking strategy to an existing index
    
    Args:
        index_path: Path to the document index
        config: Chunking configuration parameters
        
    Returns:
        Results of the re-chunking operation
    """
    chunker = get_advanced_chunking_strategy(config)
    results = {
        'status': 'unknown',
        'original_chunks': 0,
        'new_chunks': 0,
        'tables_extracted': 0,
        'sections_identified': 0,
        'processing_time': 0
    }
    
    try:
        import time
        start_time = time.time()
        
        index_path = Path(index_path)
        extracted_text_path = index_path / "extracted_text.txt"
        
        if not extracted_text_path.exists():
            results['status'] = 'no_extracted_text'
            return results
        
        # Read original content
        with open(extracted_text_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply advanced chunking
        chunks = chunker.chunk_document(content, source_name=index_path.name)
        
        # Count results
        results['new_chunks'] = len(chunks)
        results['tables_extracted'] = len([c for c in chunks if c.get('chunk_type') == 'table'])
        results['sections_identified'] = len(set(c.get('section', 'Unknown') for c in chunks))
        results['processing_time'] = time.time() - start_time
        results['status'] = 'success'
        
        # Save chunking results
        chunking_results_path = index_path / "advanced_chunks.json"
        import json
        with open(chunking_results_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        # Update index metadata
        meta_path = index_path / "index.meta"
        if meta_path.exists():
            with open(meta_path, 'a', encoding='utf-8') as f:
                f.write(f"\nAdvanced chunking applied: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                f.write(f"\nChunk size: {config.get('chunk_size', 1000) if config else 1000}")
                f.write(f"\nChunk overlap: {config.get('chunk_overlap', 200) if config else 200}")
                f.write(f"\nStructure-aware: True")
                f.write(f"\nTables extracted: {results['tables_extracted']}")
        
        logger.info(f"Advanced chunking completed for {index_path}: {results}")
        
    except Exception as e:
        results['status'] = 'error'
        results['error'] = str(e)
        logger.error(f"Advanced chunking failed for {index_path}: {e}")
    
    return results
