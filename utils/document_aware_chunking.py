"""
Document-Aware Chunking System
=============================
Multi-layered approach for intelligent document chunking based on document type and structure.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    LEGAL = "legal"
    TECHNICAL = "technical"
    ACADEMIC = "academic"
    UNSTRUCTURED = "unstructured"

@dataclass
class DocumentChunk:
    """Represents a document chunk with rich metadata."""
    content: str
    chunk_id: str
    document_type: DocumentType
    section_hierarchy: List[str]  # ["Article III", "Section 2", "Subsection a"]
    parent_context: str
    keywords: List[str]
    start_position: int
    end_position: int
    word_count: int
    metadata: Dict[str, Any]

class DocumentTypeDetector:
    """Detect document type based on content patterns."""
    
    def __init__(self):
        self.legal_patterns = [
            r'ARTICLE\s+[IVX]+\.',
            r'Section\s+\d+\.',
            r'Subsection\s+[a-z]\)',
            r'BYLAWS?\s+OF',
            r'WHEREAS,',
            r'NOW,?\s+THEREFORE',
            r'shall\s+be\s+deemed',
            r'pursuant\s+to',
        ]
        
        self.technical_patterns = [
            r'Step\s+\d+:',
            r'Procedure\s+\d+',
            r'Configuration',
            r'Installation',
            r'Requirements:',
            r'Prerequisites:',
            r'Note:\s+',
            r'Warning:\s+',
        ]
        
        self.academic_patterns = [
            r'Abstract\s*:?',
            r'Introduction\s*:?',
            r'Methodology\s*:?',
            r'Results\s*:?',
            r'Conclusion\s*:?',
            r'References\s*:?',
            r'et\s+al\.',
            r'\[\d+\]',  # Citations
        ]
    
    def detect_type(self, content: str) -> DocumentType:
        """Detect document type based on content patterns."""
        content_lower = content.lower()
        
        # Count pattern matches
        legal_score = sum(1 for pattern in self.legal_patterns 
                         if re.search(pattern, content, re.IGNORECASE))
        technical_score = sum(1 for pattern in self.technical_patterns 
                            if re.search(pattern, content, re.IGNORECASE))
        academic_score = sum(1 for pattern in self.academic_patterns 
                           if re.search(pattern, content, re.IGNORECASE))
        
        # Determine type based on highest score
        scores = {
            DocumentType.LEGAL: legal_score,
            DocumentType.TECHNICAL: technical_score,
            DocumentType.ACADEMIC: academic_score
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            return DocumentType.UNSTRUCTURED
        
        return max(scores, key=scores.get)

class StructureBasedChunker:
    """Extract chunks based on document structure."""
    
    def __init__(self):
        self.hierarchy_patterns = {
            DocumentType.LEGAL: [
                (r'ARTICLE\s+([IVX]+)\.\s*([A-Z\s:;]+)', 'article'),
                (r'Section\s+(\d+)\.\s*([A-Za-z\s:;]+)', 'section'),
                (r'Subsection\s+([a-z])\)\s*([A-Za-z\s:;]+)', 'subsection'),
                (r'([A-Z]\.\s+[A-Z\s]+)', 'clause'),
            ],
            DocumentType.TECHNICAL: [
                (r'Chapter\s+(\d+):\s*([A-Za-z\s]+)', 'chapter'),
                (r'(\d+\.\s+[A-Za-z\s]+)', 'section'),
                (r'(\d+\.\d+\s+[A-Za-z\s]+)', 'subsection'),
                (r'Step\s+(\d+):\s*([A-Za-z\s]+)', 'step'),
            ],
            DocumentType.ACADEMIC: [
                (r'(Abstract)\s*:?\s*', 'abstract'),
                (r'(\d+\.\s+[A-Za-z\s]+)', 'section'),
                (r'(\d+\.\d+\s+[A-Za-z\s]+)', 'subsection'),
                (r'(References?)\s*:?\s*', 'references'),
            ]
        }
    
    def extract_structure(self, content: str, doc_type: DocumentType) -> List[Dict]:
        """Extract document structure based on type."""
        if doc_type not in self.hierarchy_patterns:
            return []
        
        structure_elements = []
        patterns = self.hierarchy_patterns[doc_type]
        
        for pattern, element_type in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
            for match in matches:
                structure_elements.append({
                    'start': match.start(),
                    'end': match.end(),
                    'title': match.group(0).strip(),
                    'type': element_type,
                    'level': self._get_hierarchy_level(element_type),
                    'full_match': match.group(0)
                })
        
        # Sort by position
        structure_elements.sort(key=lambda x: x['start'])
        return structure_elements
    
    def _get_hierarchy_level(self, element_type: str) -> int:
        """Get hierarchy level for element type."""
        level_map = {
            'article': 1, 'chapter': 1, 'abstract': 1,
            'section': 2,
            'subsection': 3, 'step': 3,
            'clause': 4, 'references': 1
        }
        return level_map.get(element_type, 5)
    
    def chunk_by_structure(self, content: str, doc_type: DocumentType) -> List[DocumentChunk]:
        """Create chunks based on document structure."""
        structure = self.extract_structure(content, doc_type)
        if not structure:
            return []
        
        chunks = []
        
        for i, element in enumerate(structure):
            # Determine chunk boundaries
            chunk_start = element['end']
            if i + 1 < len(structure):
                chunk_end = structure[i + 1]['start']
            else:
                chunk_end = len(content)
            
            # Extract content
            chunk_content = content[chunk_start:chunk_end].strip()
            
            # Skip if too short or empty
            if len(chunk_content) < 50:
                continue
            
            # Build hierarchy context
            hierarchy = self._build_hierarchy(structure, i)
            parent_context = self._build_parent_context(hierarchy)
            
            # Create chunk
            chunk = DocumentChunk(
                content=f"**{element['title']}**\n\n{chunk_content}",
                chunk_id=self._generate_chunk_id(element['title'], chunk_content),
                document_type=doc_type,
                section_hierarchy=hierarchy,
                parent_context=parent_context,
                keywords=self._extract_keywords(chunk_content),
                start_position=chunk_start,
                end_position=chunk_end,
                word_count=len(chunk_content.split()),
                metadata={
                    'element_type': element['type'],
                    'hierarchy_level': element['level'],
                    'title': element['title']
                }
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _build_hierarchy(self, structure: List[Dict], current_index: int) -> List[str]:
        """Build hierarchy path for current element."""
        current_element = structure[current_index]
        current_level = current_element['level']
        
        hierarchy = [current_element['title']]
        
        # Look backwards for parent elements
        for i in range(current_index - 1, -1, -1):
            element = structure[i]
            if element['level'] < current_level:
                hierarchy.insert(0, element['title'])
                current_level = element['level']
        
        return hierarchy
    
    def _build_parent_context(self, hierarchy: List[str]) -> str:
        """Build parent context string."""
        if len(hierarchy) <= 1:
            return ""
        return " > ".join(hierarchy[:-1])
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        # Simple keyword extraction - can be enhanced with NLP
        words = re.findall(r'\b[A-Za-z]{4,}\b', content.lower())
        # Remove common words
        common_words = {'shall', 'will', 'must', 'may', 'should', 'would', 'could', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in set(words) if word not in common_words]
        return keywords[:10]  # Top 10 keywords
    
    def _generate_chunk_id(self, title: str, content: str) -> str:
        """Generate unique chunk ID."""
        combined = f"{title}:{content[:100]}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]

class SemanticChunker:
    """Semantic-based chunking using embeddings."""
    
    def __init__(self):
        self.sentence_splitter = re.compile(r'(?<=[.!?])\s+')
    
    def chunk_semantically(self, content: str, doc_type: DocumentType, max_chunk_size: int = 1500) -> List[DocumentChunk]:
        """Create semantically coherent chunks."""
        # Split into sentences
        sentences = self.sentence_splitter.split(content)
        
        # Group sentences into chunks
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence)
            
            # If adding this sentence would exceed max size, finalize current chunk
            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunk_content = ' '.join(current_chunk)
                chunk = DocumentChunk(
                    content=chunk_content,
                    chunk_id=self._generate_chunk_id(chunk_content),
                    document_type=doc_type,
                    section_hierarchy=["Semantic Chunk"],
                    parent_context="",
                    keywords=self._extract_keywords(chunk_content),
                    start_position=0,  # Would need position tracking
                    end_position=0,
                    word_count=len(chunk_content.split()),
                    metadata={'chunking_method': 'semantic'}
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            chunk = DocumentChunk(
                content=chunk_content,
                chunk_id=self._generate_chunk_id(chunk_content),
                document_type=doc_type,
                section_hierarchy=["Semantic Chunk"],
                parent_context="",
                keywords=self._extract_keywords(chunk_content),
                start_position=0,
                end_position=0,
                word_count=len(chunk_content.split()),
                metadata={'chunking_method': 'semantic'}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        words = re.findall(r'\b[A-Za-z]{4,}\b', content.lower())
        common_words = {'shall', 'will', 'must', 'may', 'should', 'would', 'could', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in set(words) if word not in common_words]
        return keywords[:10]
    
    def _generate_chunk_id(self, content: str) -> str:
        """Generate unique chunk ID."""
        return hashlib.md5(content[:100].encode()).hexdigest()[:12]

class DocumentAwareChunker:
    """Main chunking system that combines multiple strategies."""
    
    def __init__(self):
        self.type_detector = DocumentTypeDetector()
        self.structure_chunker = StructureBasedChunker()
        self.semantic_chunker = SemanticChunker()
    
    def chunk_document(self, content: str, source_path: str = "") -> List[DocumentChunk]:
        """
        Chunk document using hybrid approach:
        1. Detect document type
        2. Try structure-based chunking
        3. Fall back to semantic chunking if needed
        """
        logger.info(f"Starting document-aware chunking for: {source_path}")
        
        # Phase 1: Document Type Detection
        doc_type = self.type_detector.detect_type(content)
        logger.info(f"Detected document type: {doc_type.value}")
        
        chunks = []
        
        # Phase 2: Structure-Based Chunking
        if doc_type != DocumentType.UNSTRUCTURED:
            try:
                structure_chunks = self.structure_chunker.chunk_by_structure(content, doc_type)
                if structure_chunks:
                    logger.info(f"Structure-based chunking successful: {len(structure_chunks)} chunks")
                    chunks.extend(structure_chunks)
                else:
                    logger.info("Structure-based chunking yielded no results, falling back to semantic")
            except Exception as e:
                logger.warning(f"Structure-based chunking failed: {e}")
        
        # Phase 3: Semantic Chunking (fallback or supplement)
        if not chunks or doc_type == DocumentType.UNSTRUCTURED:
            try:
                semantic_chunks = self.semantic_chunker.chunk_semantically(content, doc_type)
                logger.info(f"Semantic chunking produced: {len(semantic_chunks)} chunks")
                chunks.extend(semantic_chunks)
            except Exception as e:
                logger.error(f"Semantic chunking failed: {e}")
        
        # Phase 4: Metadata Enrichment
        for chunk in chunks:
            chunk.metadata.update({
                'source_path': source_path,
                'document_type': doc_type.value,
                'chunking_timestamp': str(Path(__file__).stat().st_mtime),
                'total_chunks': len(chunks)
            })
        
        logger.info(f"Document chunking complete: {len(chunks)} total chunks")
        return chunks
    
    def get_chunk_context(self, chunk: DocumentChunk, all_chunks: List[DocumentChunk]) -> str:
        """Reconstruct context for a chunk during retrieval."""
        context_parts = []
        
        # Add parent context
        if chunk.parent_context:
            context_parts.append(f"Context: {chunk.parent_context}")
        
        # Add section hierarchy
        if len(chunk.section_hierarchy) > 1:
            hierarchy_str = " > ".join(chunk.section_hierarchy)
            context_parts.append(f"Location: {hierarchy_str}")
        
        # Add document type context
        context_parts.append(f"Document Type: {chunk.document_type.value.title()}")
        
        return " | ".join(context_parts)

def chunk_document_intelligently(content: str, source_path: str = "") -> List[Dict[str, Any]]:
    """
    Main function for intelligent document chunking.
    Returns chunks in format compatible with existing system.
    """
    chunker = DocumentAwareChunker()
    chunks = chunker.chunk_document(content, source_path)
    
    # Convert to compatible format
    formatted_chunks = []
    for chunk in chunks:
        formatted_chunks.append({
            'content': chunk.content,
            'source': source_path or 'Unknown',
            'page': 'Multiple',
            'section': chunk.section_hierarchy[-1] if chunk.section_hierarchy else 'Unknown',
            'confidence_score': 0.9,  # High confidence for structure-based chunks
            'word_count': chunk.word_count,
            'metadata': {
                'chunk_id': chunk.chunk_id,
                'document_type': chunk.document_type.value,
                'section_hierarchy': chunk.section_hierarchy,
                'parent_context': chunk.parent_context,
                'keywords': chunk.keywords,
                'extraction_method': 'document_aware',
                **chunk.metadata
            }
        })
    
    return formatted_chunks

if __name__ == "__main__":
    # Test the chunking system
    test_content = """
    ARTICLE III. BOARD OF DIRECTORS: NUMBER, POWERS, MEETINGS
    
    Section 1. Organizational MEETINGS
    The first meeting of the Board of Directors shall be held immediately following each annual meeting of the Association.
    
    Section 2. BOARD MEETINGS; Action Outside of Meeting
    Regular meetings of the Board of Directors may be held at such time and place as shall be determined, from time to time, by a majority of the directors, but at least four (4) times per year. Special meetings of the Board of Directors may be called by the president or by any two (2) directors. The Board may take action outside of a meeting if all Directors consent in writing to the action.
    """
    
    chunks = chunk_document_intelligently(test_content, "test_bylaws.pdf")
    
    print(f"Generated {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(f"Section: {chunk['section']}")
        print(f"Content: {chunk['content'][:200]}...")
        print(f"Hierarchy: {chunk['metadata']['section_hierarchy']}")
