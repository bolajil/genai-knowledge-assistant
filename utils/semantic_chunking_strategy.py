"""
Semantic Chunking Strategy for Document Ingestion
Implements proper semantic chunking with header-based splitting and embeddings
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import os

logger = logging.getLogger(__name__)

class SemanticChunkingStrategy:
    """
    Advanced chunking strategy that splits documents by semantic boundaries
    """
    
    def __init__(self, 
                 chunk_size: int = 512, 
                 chunk_overlap: int = 100,
                 split_by_headers: bool = True,
                 use_embeddings: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.split_by_headers = split_by_headers
        self.use_embeddings = use_embeddings
        
        # Header patterns for semantic splitting
        self.header_patterns = [
            r'^ARTICLE [IVX]+\.\s*[A-Z][^.]*$',  # ARTICLE IV. OFFICERS
            r'^Section \d+\.\s*[A-Z][^.]*$',      # Section 1. Powers
            r'^[A-Z]\.\s*[A-Z][A-Z\s]+$',        # A. COMPOSITION AND SELECTION
            r'^[A-Z][A-Z\s]{10,}$',              # ALL CAPS HEADERS
            r'^\d+\.\s*[A-Z][^.]*$',             # 1. Governing Body
            r'^[a-z]\.\s*[A-Z][^.]*$',           # a. preparing and adopting
        ]
    
    def chunk_document(self, content: str, document_name: str = "") -> List[Dict[str, Any]]:
        """
        Chunk document using semantic boundaries
        
        Args:
            content: Full document text
            document_name: Name/identifier for the document
            
        Returns:
            List of semantic chunks with metadata
        """
        try:
            # Clean content first
            cleaned_content = self._clean_content(content)
            
            if self.split_by_headers:
                chunks = self._split_by_headers(cleaned_content, document_name)
            else:
                chunks = self._split_by_size(cleaned_content, document_name)
            
            # Add embeddings if enabled
            if self.use_embeddings:
                chunks = self._add_embeddings(chunks)
            
            logger.info(f"Created {len(chunks)} semantic chunks for {document_name}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error in semantic chunking: {e}")
            return self._fallback_chunking(content, document_name)
    
    def _clean_content(self, content: str) -> str:
        """Clean content by removing unwanted elements"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip unwanted lines
            if (line and 
                not line.startswith('Copyright') and 
                not line.startswith('---') and
                not line.startswith('2022136118') and
                not re.match(r'^Page \d+', line) and
                not line.startswith('TABLE OF CONTENTS') and
                len(line) > 2):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _split_by_headers(self, content: str, document_name: str) -> List[Dict[str, Any]]:
        """Split content by semantic headers"""
        chunks = []
        lines = content.split('\n')
        
        current_section = None
        current_content = []
        section_hierarchy = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a header
            header_match = self._is_header(line)
            
            if header_match:
                # Save previous section if it exists
                if current_section and current_content:
                    chunk_text = '\n'.join(current_content)
                    if len(chunk_text) > 50:  # Only include substantial content
                        chunk = self._create_semantic_chunk(
                            chunk_text, 
                            current_section, 
                            section_hierarchy.copy(),
                            document_name,
                            len(chunks)
                        )
                        chunks.append(chunk)
                
                # Start new section
                current_section = line
                current_content = []
                
                # Update hierarchy
                header_level = self._get_header_level(line)
                section_hierarchy = self._update_hierarchy(section_hierarchy, line, header_level)
                
            else:
                current_content.append(line)
        
        # Add final section
        if current_section and current_content:
            chunk_text = '\n'.join(current_content)
            if len(chunk_text) > 50:
                chunk = self._create_semantic_chunk(
                    chunk_text, 
                    current_section, 
                    section_hierarchy.copy(),
                    document_name,
                    len(chunks)
                )
                chunks.append(chunk)
        
        # Post-process chunks to ensure proper size
        return self._optimize_chunk_sizes(chunks)
    
    def _is_header(self, line: str) -> bool:
        """Check if line matches header patterns"""
        for pattern in self.header_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _get_header_level(self, line: str) -> int:
        """Determine header hierarchy level"""
        if re.match(r'^ARTICLE [IVX]+', line):
            return 1
        elif re.match(r'^[A-Z]\.\s*[A-Z]', line):
            return 2
        elif re.match(r'^Section \d+', line):
            return 3
        elif re.match(r'^\d+\.', line):
            return 4
        elif re.match(r'^[a-z]\.', line):
            return 5
        else:
            return 6
    
    def _update_hierarchy(self, hierarchy: List[str], header: str, level: int) -> List[str]:
        """Update section hierarchy"""
        # Trim hierarchy to current level
        hierarchy = hierarchy[:level-1]
        hierarchy.append(header)
        return hierarchy
    
    def _create_semantic_chunk(self, content: str, title: str, hierarchy: List[str], 
                              document_name: str, chunk_index: int) -> Dict[str, Any]:
        """Create a semantic chunk with metadata"""
        
        # Build hierarchical context
        context_path = ' > '.join(hierarchy) if hierarchy else title
        
        # Create chunk with semantic context
        chunk_content = f"{title}\n\n{content}"
        
        return {
            'content': chunk_content,
            'title': title,
            'hierarchy': hierarchy,
            'context_path': context_path,
            'chunk_index': chunk_index,
            'chunk_size': len(chunk_content),
            'document_name': document_name,
            'chunk_type': 'semantic_header',
            'metadata': {
                'title': title,
                'hierarchy_level': len(hierarchy),
                'context_path': context_path,
                'document': document_name,
                'semantic_type': 'header_based'
            }
        }
    
    def _split_by_size(self, content: str, document_name: str) -> List[Dict[str, Any]]:
        """Fallback: split by size with overlap"""
        chunks = []
        
        for i in range(0, len(content), self.chunk_size - self.chunk_overlap):
            chunk_text = content[i:i + self.chunk_size]
            
            # Try to break at sentence boundaries
            if i + self.chunk_size < len(content):
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size * 0.7:  # Don't break too early
                    chunk_text = chunk_text[:break_point + 1]
            
            if chunk_text.strip():
                chunk = {
                    'content': chunk_text.strip(),
                    'title': f'Chunk {len(chunks) + 1}',
                    'hierarchy': [],
                    'context_path': f'Document Chunk {len(chunks) + 1}',
                    'chunk_index': len(chunks),
                    'chunk_size': len(chunk_text),
                    'document_name': document_name,
                    'chunk_type': 'size_based',
                    'metadata': {
                        'title': f'Chunk {len(chunks) + 1}',
                        'hierarchy_level': 0,
                        'context_path': f'Document Chunk {len(chunks) + 1}',
                        'document': document_name,
                        'semantic_type': 'size_based'
                    }
                }
                chunks.append(chunk)
        
        return chunks
    
    def _optimize_chunk_sizes(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize chunk sizes to stay within limits"""
        optimized_chunks = []
        
        for chunk in chunks:
            content = chunk['content']
            
            if len(content) <= self.chunk_size:
                optimized_chunks.append(chunk)
            else:
                # Split large chunks
                sub_chunks = self._split_large_chunk(chunk)
                optimized_chunks.extend(sub_chunks)
        
        return optimized_chunks
    
    def _split_large_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split a chunk that's too large"""
        content = chunk['content']
        title = chunk['title']
        
        sub_chunks = []
        for i in range(0, len(content), self.chunk_size - self.chunk_overlap):
            sub_content = content[i:i + self.chunk_size]
            
            # Try to break at sentence boundaries
            if i + self.chunk_size < len(content):
                last_period = sub_content.rfind('.')
                if last_period > self.chunk_size * 0.7:
                    sub_content = sub_content[:last_period + 1]
            
            if sub_content.strip():
                sub_chunk = chunk.copy()
                sub_chunk['content'] = sub_content.strip()
                sub_chunk['title'] = f"{title} (Part {len(sub_chunks) + 1})"
                sub_chunk['chunk_size'] = len(sub_content)
                sub_chunk['metadata'] = chunk['metadata'].copy()
                sub_chunk['metadata']['title'] = sub_chunk['title']
                sub_chunk['metadata']['is_sub_chunk'] = True
                sub_chunk['metadata']['parent_title'] = title
                
                sub_chunks.append(sub_chunk)
        
        return sub_chunks
    
    def _add_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add embeddings to chunks for semantic search"""
        try:
            # Try to use OpenAI embeddings with a safe client (avoid 'project' kwarg issues)
            from openai import OpenAI
            try:
                os.environ.pop("OPENAI_PROJECT", None)
            except Exception:
                pass
            api_key = os.getenv("OPENAI_API_KEY")
            organization = os.getenv("OPENAI_ORG") or os.getenv("OPENAI_ORGANIZATION")
            try:
                if api_key and organization:
                    client = OpenAI(api_key=api_key, organization=organization)
                elif api_key:
                    client = OpenAI(api_key=api_key)
                else:
                    client = OpenAI()
            except TypeError:
                client = OpenAI(api_key=api_key) if api_key else OpenAI()
            
            for chunk in chunks:
                try:
                    response = client.embeddings.create(
                        model="text-embedding-3-small",
                        input=chunk['content']
                    )
                    chunk['embedding'] = response.data[0].embedding
                    chunk['has_embedding'] = True
                except Exception as e:
                    logger.warning(f"Failed to create embedding for chunk: {e}")
                    chunk['has_embedding'] = False
                    
        except ImportError:
            logger.warning("OpenAI not available, skipping embeddings")
            for chunk in chunks:
                chunk['has_embedding'] = False
        except Exception as e:
            logger.error(f"Error adding embeddings: {e}")
            for chunk in chunks:
                chunk['has_embedding'] = False
        
        return chunks
    
    def _fallback_chunking(self, content: str, document_name: str) -> List[Dict[str, Any]]:
        """Simple fallback chunking if semantic chunking fails"""
        chunks = []
        
        for i in range(0, len(content), self.chunk_size):
            chunk_text = content[i:i + self.chunk_size]
            if chunk_text.strip():
                chunk = {
                    'content': chunk_text.strip(),
                    'title': f'Fallback Chunk {len(chunks) + 1}',
                    'hierarchy': [],
                    'context_path': f'Fallback Chunk {len(chunks) + 1}',
                    'chunk_index': len(chunks),
                    'chunk_size': len(chunk_text),
                    'document_name': document_name,
                    'chunk_type': 'fallback',
                    'has_embedding': False,
                    'metadata': {
                        'title': f'Fallback Chunk {len(chunks) + 1}',
                        'document': document_name,
                        'semantic_type': 'fallback'
                    }
                }
                chunks.append(chunk)
        
        return chunks

def create_semantic_chunks(content: str, document_name: str, 
                          chunk_size: int = 512, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Convenience function to create semantic chunks
    
    Args:
        content: Document content
        document_name: Document identifier
        chunk_size: Target chunk size (512-1024 recommended)
        chunk_overlap: Overlap between chunks (100-200 recommended)
        
    Returns:
        List of semantic chunks
    """
    chunker = SemanticChunkingStrategy(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        split_by_headers=True,
        use_embeddings=True
    )
    
    return chunker.chunk_document(content, document_name)
