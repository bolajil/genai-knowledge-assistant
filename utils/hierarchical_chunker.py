"""
Hierarchical Chunking for VaultMind RAG Pipeline

Implements parent-child chunking strategy for enterprise documents:
- Parent chunks: 1024 tokens (preserve full context)
- Child chunks: 256 tokens (precision retrieval)
- Auto-merging: When ≥2 children from same parent retrieved, pull full parent

This replaces flat RecursiveCharacterTextSplitter(500/50) chunking.
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import hashlib

logger = logging.getLogger(__name__)

# Tokenizer for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
    _encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4/3.5 encoding
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available. Using approximate token counting.")
    _encoder = None


@dataclass
class Chunk:
    """Represents a document chunk with hierarchical metadata"""
    chunk_id: str
    content: str
    token_count: int
    chunk_type: str  # 'parent' or 'child'
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'token_count': self.token_count,
            'chunk_type': self.chunk_type,
            'parent_id': self.parent_id,
            'child_ids': self.child_ids,
            'metadata': self.metadata
        }


class HierarchicalChunker:
    """
    Creates hierarchical parent-child chunks for enterprise documents.
    
    Strategy:
    1. Split document into parent chunks (1024 tokens)
    2. Split each parent into child chunks (256 tokens)
    3. Store both with parent_id linkage
    4. At retrieval, use children for precision
    5. Auto-merge to parent when ≥2 children from same parent
    """
    
    def __init__(
        self,
        parent_chunk_size: int = 1024,
        child_chunk_size: int = 256,
        parent_overlap: int = 128,
        child_overlap: int = 32,
        min_chunk_size: int = 50
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.parent_overlap = parent_overlap
        self.child_overlap = child_overlap
        self.min_chunk_size = min_chunk_size
        
        logger.info(f"HierarchicalChunker initialized: parent={parent_chunk_size}, child={child_chunk_size}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if TIKTOKEN_AVAILABLE and _encoder:
            return len(_encoder.encode(text))
        else:
            # Approximate: ~4 chars per token for English
            return len(text) // 4
    
    def _generate_chunk_id(self, content: str, prefix: str = "chunk") -> str:
        """Generate unique chunk ID based on content hash"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{prefix}_{content_hash}_{uuid.uuid4().hex[:6]}"
    
    def _split_by_tokens(
        self,
        text: str,
        max_tokens: int,
        overlap_tokens: int
    ) -> List[str]:
        """Split text into chunks by token count with overlap"""
        if TIKTOKEN_AVAILABLE and _encoder:
            tokens = _encoder.encode(text)
            chunks = []
            start = 0
            
            while start < len(tokens):
                end = min(start + max_tokens, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = _encoder.decode(chunk_tokens)
                
                if len(chunk_tokens) >= self.min_chunk_size or start == 0:
                    chunks.append(chunk_text)
                
                # Move start with overlap
                start = end - overlap_tokens if end < len(tokens) else end
                
                # Prevent infinite loop
                if start <= 0 and end < len(tokens):
                    start = end
            
            return chunks
        else:
            # Fallback: character-based splitting
            chars_per_token = 4
            max_chars = max_tokens * chars_per_token
            overlap_chars = overlap_tokens * chars_per_token
            
            chunks = []
            start = 0
            
            while start < len(text):
                end = min(start + max_chars, len(text))
                
                # Try to break at sentence or word boundary
                if end < len(text):
                    # Look for sentence end
                    for sep in ['. ', '.\n', '! ', '? ', '\n\n']:
                        last_sep = text[start:end].rfind(sep)
                        if last_sep > max_chars // 2:
                            end = start + last_sep + len(sep)
                            break
                
                chunk_text = text[start:end].strip()
                if len(chunk_text) >= self.min_chunk_size * chars_per_token or start == 0:
                    chunks.append(chunk_text)
                
                start = end - overlap_chars if end < len(text) else end
                if start <= 0 and end < len(text):
                    start = end
            
            return chunks
    
    def chunk_document(
        self,
        text: str,
        document_id: str = None,
        dept_id: str = None,
        source: str = None,
        additional_metadata: Dict[str, Any] = None
    ) -> Tuple[List[Chunk], List[Chunk]]:
        """
        Chunk document into hierarchical parent-child structure.
        
        Args:
            text: Full document text
            document_id: Unique document identifier
            dept_id: Department ID for namespace isolation
            source: Document source (filename, URL, etc.)
            additional_metadata: Extra metadata to attach
        
        Returns:
            Tuple of (parent_chunks, child_chunks)
        """
        if not text or not text.strip():
            return [], []
        
        document_id = document_id or self._generate_chunk_id(text, "doc")
        base_metadata = {
            'document_id': document_id,
            'dept_id': dept_id,
            'source': source,
            **(additional_metadata or {})
        }
        
        parent_chunks = []
        child_chunks = []
        
        # Step 1: Create parent chunks
        parent_texts = self._split_by_tokens(
            text, 
            self.parent_chunk_size, 
            self.parent_overlap
        )
        
        for idx, parent_text in enumerate(parent_texts):
            parent_id = self._generate_chunk_id(parent_text, "parent")
            
            parent_chunk = Chunk(
                chunk_id=parent_id,
                content=parent_text,
                token_count=self.count_tokens(parent_text),
                chunk_type='parent',
                parent_id=None,
                child_ids=[],
                metadata={
                    **base_metadata,
                    'parent_index': idx,
                    'total_parents': len(parent_texts)
                }
            )
            
            # Step 2: Create child chunks from this parent
            child_texts = self._split_by_tokens(
                parent_text,
                self.child_chunk_size,
                self.child_overlap
            )
            
            for child_idx, child_text in enumerate(child_texts):
                child_id = self._generate_chunk_id(child_text, "child")
                
                child_chunk = Chunk(
                    chunk_id=child_id,
                    content=child_text,
                    token_count=self.count_tokens(child_text),
                    chunk_type='child',
                    parent_id=parent_id,
                    child_ids=[],
                    metadata={
                        **base_metadata,
                        'parent_index': idx,
                        'child_index': child_idx,
                        'total_children_in_parent': len(child_texts)
                    }
                )
                
                parent_chunk.child_ids.append(child_id)
                child_chunks.append(child_chunk)
            
            parent_chunks.append(parent_chunk)
        
        logger.info(f"Document chunked: {len(parent_chunks)} parents, {len(child_chunks)} children")
        return parent_chunks, child_chunks
    
    def prepare_for_indexing(
        self,
        parent_chunks: List[Chunk],
        child_chunks: List[Chunk],
        index_children_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Prepare chunks for vector store indexing.
        
        Args:
            parent_chunks: List of parent chunks
            child_chunks: List of child chunks
            index_children_only: If True, only index children (parents stored separately)
        
        Returns:
            List of dicts ready for embedding and upserting
        """
        docs_for_indexing = []
        
        if index_children_only:
            # Index children for precision retrieval
            for chunk in child_chunks:
                docs_for_indexing.append({
                    'id': chunk.chunk_id,
                    'content': chunk.content,
                    'metadata': {
                        **chunk.metadata,
                        'chunk_type': 'child',
                        'parent_id': chunk.parent_id,
                        'token_count': chunk.token_count
                    }
                })
        else:
            # Index both parents and children
            for chunk in parent_chunks:
                docs_for_indexing.append({
                    'id': chunk.chunk_id,
                    'content': chunk.content,
                    'metadata': {
                        **chunk.metadata,
                        'chunk_type': 'parent',
                        'child_ids': chunk.child_ids,
                        'token_count': chunk.token_count
                    }
                })
            
            for chunk in child_chunks:
                docs_for_indexing.append({
                    'id': chunk.chunk_id,
                    'content': chunk.content,
                    'metadata': {
                        **chunk.metadata,
                        'chunk_type': 'child',
                        'parent_id': chunk.parent_id,
                        'token_count': chunk.token_count
                    }
                })
        
        return docs_for_indexing
    
    def get_stats(self, parent_chunks: List[Chunk], child_chunks: List[Chunk]) -> Dict[str, Any]:
        """Get chunking statistics"""
        parent_tokens = sum(c.token_count for c in parent_chunks)
        child_tokens = sum(c.token_count for c in child_chunks)
        
        return {
            'parent_count': len(parent_chunks),
            'child_count': len(child_chunks),
            'total_parent_tokens': parent_tokens,
            'total_child_tokens': child_tokens,
            'avg_parent_tokens': parent_tokens / max(1, len(parent_chunks)),
            'avg_child_tokens': child_tokens / max(1, len(child_chunks)),
            'avg_children_per_parent': len(child_chunks) / max(1, len(parent_chunks))
        }


class AutoMergingRetriever:
    """
    Retrieves child chunks and auto-merges to parent when appropriate.
    
    Strategy:
    - Query returns child chunks
    - If ≥2 children from same parent, retrieve full parent
    - Return merged context with proper citations
    """
    
    def __init__(
        self,
        merge_threshold: int = 2,
        parent_store: Dict[str, Chunk] = None
    ):
        self.merge_threshold = merge_threshold
        self.parent_store = parent_store or {}
    
    def register_parents(self, parent_chunks: List[Chunk]):
        """Register parent chunks for later retrieval"""
        for parent in parent_chunks:
            self.parent_store[parent.chunk_id] = parent
    
    def auto_merge(
        self,
        child_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Auto-merge child results to parents when threshold met.
        
        Args:
            child_results: List of retrieved child chunks with metadata
        
        Returns:
            List of merged results (parents where applicable, children otherwise)
        """
        # Group children by parent_id
        parent_children: Dict[str, List[Dict]] = {}
        orphan_children = []
        
        for result in child_results:
            parent_id = result.get('metadata', {}).get('parent_id')
            if parent_id:
                if parent_id not in parent_children:
                    parent_children[parent_id] = []
                parent_children[parent_id].append(result)
            else:
                orphan_children.append(result)
        
        merged_results = []
        used_parents = set()
        
        # Check each parent group
        for parent_id, children in parent_children.items():
            if len(children) >= self.merge_threshold and parent_id in self.parent_store:
                # Merge to parent
                parent = self.parent_store[parent_id]
                
                # Calculate merged score (average of child scores)
                avg_score = sum(c.get('score', 0) for c in children) / len(children)
                
                merged_results.append({
                    'id': parent.chunk_id,
                    'content': parent.content,
                    'score': avg_score,
                    'metadata': {
                        **parent.metadata,
                        'merged_from_children': len(children),
                        'child_ids': [c.get('id') for c in children],
                        'chunk_type': 'merged_parent'
                    }
                })
                used_parents.add(parent_id)
                logger.info(f"Auto-merged {len(children)} children to parent {parent_id}")
            else:
                # Keep children as-is
                merged_results.extend(children)
        
        # Add orphan children
        merged_results.extend(orphan_children)
        
        # Sort by score
        merged_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return merged_results


# Global instances
_chunker = None
_retriever = None

def get_hierarchical_chunker() -> HierarchicalChunker:
    """Get or create global hierarchical chunker"""
    global _chunker
    if _chunker is None:
        _chunker = HierarchicalChunker()
    return _chunker

def get_auto_merging_retriever() -> AutoMergingRetriever:
    """Get or create global auto-merging retriever"""
    global _retriever
    if _retriever is None:
        _retriever = AutoMergingRetriever()
    return _retriever


def chunk_document_hierarchical(
    text: str,
    document_id: str = None,
    dept_id: str = None,
    source: str = None,
    metadata: Dict[str, Any] = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    Convenience function to chunk a document hierarchically.
    
    Returns:
        Tuple of (parent_dicts, child_dicts) ready for indexing
    """
    chunker = get_hierarchical_chunker()
    parents, children = chunker.chunk_document(
        text, document_id, dept_id, source, metadata
    )
    
    # Register parents for auto-merging
    retriever = get_auto_merging_retriever()
    retriever.register_parents(parents)
    
    # Convert to dicts
    parent_dicts = [p.to_dict() for p in parents]
    child_dicts = [c.to_dict() for c in children]
    
    return parent_dicts, child_dicts
