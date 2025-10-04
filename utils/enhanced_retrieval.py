"""
Enhanced Retrieval System for ByLaw and other text-based indexes

This module provides enhanced document retrieval that can handle different index formats
including extracted text files and proper FAISS indexes.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentChunk:
    """Represents a chunk of document content with metadata"""
    def __init__(self, content: str, source: str, page: int = None, chunk_id: int = None):
        self.page_content = content
        self.metadata = {
            'source': source,
            'page': page,
            'chunk_id': chunk_id
        }

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks with advanced structure-aware processing"""
    # Use advanced chunking strategy if available
    try:
        from utils.advanced_chunking_strategy import get_advanced_chunking_strategy
        
        chunking_config = {
            "chunk_size": chunk_size,
            "chunk_overlap": overlap,
            "respect_section_breaks": True,
            "extract_tables": True,
            "preserve_heading_structure": True
        }
        
        chunker = get_advanced_chunking_strategy(chunking_config)
        chunk_results = chunker.chunk_document(text, "document")
        
        # Extract just the content for backward compatibility
        return [chunk['content'] for chunk in chunk_results]
        
    except ImportError:
        # Fallback to improved basic chunking with section awareness
        chunks = []
        
        # Split by sections first (look for "Section" headers)
        section_pattern = r'(Section \d+\..*?)(?=Section \d+\.|$)'
        sections = re.findall(section_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if sections:
            # Process each section separately
            for section in sections:
                section_chunks = _basic_chunk_text(section.strip(), chunk_size, overlap)
                chunks.extend(section_chunks)
        else:
            # Fallback to basic chunking
            chunks = _basic_chunk_text(text, chunk_size, overlap)
        
        return chunks

def _basic_chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Basic text chunking with overlap"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at natural boundaries (paragraph > sentence > word)
        if end < len(text):
            # First try paragraph boundary
            para_end = text.rfind('\n\n', start, end)
            if para_end > start + chunk_size - 400:
                end = para_end + 2
            else:
                # Then try sentence boundary
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size - 300:
                    end = sentence_end + 1
                else:
                    # Finally try word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + chunk_size - 100:
                        end = word_end
        
        chunk = text[start:end].strip()
        if chunk and len(chunk) > 50:  # Only include substantial chunks
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def load_bylaw_content(index_path: str) -> List[DocumentChunk]:
    """Enhanced version with page-based chunking"""
    chunks = []
    
    extracted_text_path = Path(index_path) / "extracted_text.txt"
    if not extracted_text_path.exists():
        logger.error(f"No extracted_text.txt found in {index_path}")
        return chunks
    
    try:
        with open(extracted_text_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # First split by pages (--- Page markers)
        pages = content.split("--- Page")
        
        for page_num, page_content in enumerate(pages[1:], 1):  # Skip first empty
            page_header, *page_body = page_content.split('\n', 1)
            page_text = page_body[0] if page_body else ""
            
            # Then split by sections within each page
            sections = re.split(r'(Section \d+\..*?)(?=Section \d+\.|$)', 
                              page_text, 
                              flags=re.DOTALL | re.IGNORECASE)
            
            # Process sections in pairs (title + content)
            for i in range(0, len(sections)-1, 2):
                section_title = sections[i].strip()
                section_content = sections[i+1].strip() if i+1 < len(sections) else ""
                
                if section_content:
                    # Create chunk with page and section info
                    doc_chunk = DocumentChunk(
                        content=f"{section_title}\n\n{section_content}",
                        source=f"Page {page_num} - {section_title[:50]}",
                        page=page_num,
                        chunk_id=len(chunks)+1
                    )
                    chunks.append(doc_chunk)
        
        logger.info(f"Loaded {len(chunks)} page-based chunks from ByLaw document")
        return chunks
    
    except Exception as e:
        logger.error(f"Error loading ByLaw content: {e}")
        return chunks

def search_bylaw_content(query: str, index_path: str, max_results: int = 5) -> List[DocumentChunk]:
    """Search ByLaw content using enhanced semantic and contextual matching"""
    chunks = load_bylaw_content(index_path)
    
    if not chunks:
        return []
    
    # Enhanced multi-strategy search with better keyword matching
    query_words = query.lower().split()
    query_lower = query.lower()
    scored_chunks = []
    
    # Define key terms for better matching
    key_terms = {
        'removal': ['removal', 'remove', 'removed'],
        'directors': ['director', 'directors'],
        'vacancies': ['vacancy', 'vacancies', 'vacant'],
        'meetings': ['meeting', 'meetings'],
        'board': ['board'],
        'notice': ['notice', 'notification'],
        'assessment': ['assessment', 'assessments'],
        'voting': ['vote', 'voting', 'votes']
    }
    
    for chunk in chunks:
        content_lower = chunk.page_content.lower()
        score = 0
        
        # 1. Exact phrase matching (highest weight)
        if query_lower in content_lower:
            score += 100
        
        # 2. Key term matching with higher weights
        for term_group, variants in key_terms.items():
            if any(term in query_lower for term in variants):
                for variant in variants:
                    if variant in content_lower:
                        score += 30  # Higher weight for key terms
        
        # 3. Individual keyword matching with context
        for word in query_words:
            if len(word) > 2:  # Skip very short words
                word_count = content_lower.count(word)
                if word_count > 0:
                    # Boost score based on word importance and frequency
                    word_score = word_count * (3 if len(word) > 5 else 2)
                    
                    # Context bonus: check if word appears near other query words
                    word_positions = [i for i in range(len(content_lower)) if content_lower.startswith(word, i)]
                    for pos in word_positions:
                        context_window = content_lower[max(0, pos-50):pos+50]
                        context_matches = sum(1 for w in query_words if w in context_window and w != word)
                        if context_matches > 0:
                            word_score += context_matches * 5
                    
                    score += word_score
        
        # 4. Section relevance bonus
        if chunk.metadata.get('page'):
            # Boost chunks from earlier pages (often contain key definitions)
            page_num = chunk.metadata['page']
            if page_num <= 5:
                score += 5
        
        # 5. Content quality bonus
        content_length = len(chunk.page_content)
        if 500 <= content_length <= 2000:  # Prefer medium-length chunks
            score += 3
        
        if score > 0:
            scored_chunks.append((score, chunk))
    
    # Sort by score and return top results
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Ensure we return diverse results (avoid too many chunks from same page)
    diverse_results = []
    used_pages = set()
    
    for score, chunk in scored_chunks:
        page = chunk.metadata.get('page', 0)
        if len(diverse_results) < max_results:
            if page not in used_pages or len(diverse_results) < max_results // 2:
                diverse_results.append(chunk)
                used_pages.add(page)
    
    # If we don't have enough diverse results, fill with highest scoring
    if len(diverse_results) < max_results:
        for score, chunk in scored_chunks:
            if chunk not in diverse_results and len(diverse_results) < max_results:
                diverse_results.append(chunk)
    
    return diverse_results

def enhanced_document_search(query: str, index_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Enhanced document search that handles different index types"""
    from utils.simple_vector_manager import get_simple_index_path
    
    index_path = get_simple_index_path(index_name)
    if not index_path:
        logger.error(f"Index path not found for {index_name}")
        return []
    
    # Check if this is a ByLaw-style index
    if (Path(index_path) / "extracted_text.txt").exists():
        logger.info(f"Using enhanced retrieval for {index_name}")
        chunks = search_bylaw_content(query, index_path, max_results)
        
        results = []
        for chunk in chunks:
            # Ensure we return a dictionary with all expected fields
            result_dict = {
                'content': chunk.page_content,
                'source': chunk.metadata.get('source', 'Unknown'),
                'page': chunk.metadata.get('page', 'N/A'),
                'score': 0.8,  # Default score for text-based search
                'relevance_score': 0.8,
                'metadata': chunk.metadata
            }
            results.append(result_dict)
        
        return results
    
    # For other index types, return empty (will fall back to standard retrieval)
    return []
