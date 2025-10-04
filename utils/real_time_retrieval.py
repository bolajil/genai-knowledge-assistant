"""
Real-Time Document Retrieval System

This module ensures fresh, non-cached document retrieval with proper query-to-content mapping.
Eliminates cached responses and ensures actual document content is returned.
"""

import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import hashlib

# Enterprise integration
try:
    from utils.enterprise_integration_layer import get_enterprise_retrieval_system, EnterpriseConfig
    ENTERPRISE_AVAILABLE = True
except ImportError:
    ENTERPRISE_AVAILABLE = False

logger = logging.getLogger(__name__)

class RealTimeRetriever:
    """Real-time document retriever that bypasses caching and ensures fresh content"""
    
    def __init__(self, enable_enterprise: bool = True):
        self.cache_buster = str(int(time.time()))
        self.query_history = {}
        self.enable_enterprise = enable_enterprise and ENTERPRISE_AVAILABLE
        
        # Initialize enterprise system if available
        if self.enable_enterprise:
            try:
                config = EnterpriseConfig(
                    enable_hybrid_search=True,
                    enable_semantic_chunking=True,
                    enable_structured_output=False,  # Keep original output format
                    enable_metadata_filtering=True,
                    enable_caching=False  # Real-time should not cache
                )
                self.enterprise_system = get_enterprise_retrieval_system(config)
                logger.info("Enterprise features enabled for real-time retrieval")
            except Exception as e:
                logger.warning(f"Enterprise initialization failed: {e}")
                self.enable_enterprise = False
                self.enterprise_system = None
        else:
            self.enterprise_system = None
        
    def retrieve_fresh_content(self, query: str, index_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve fresh content directly from documents without caching
        
        Args:
            query: User's search query
            index_name: Name of the index to search
            max_results: Maximum number of results to return
            
        Returns:
            List of fresh document chunks with actual content
        """
        # Generate unique query ID to prevent caching
        query_id = hashlib.md5(f"{query}_{index_name}_{time.time()}".encode()).hexdigest()
        
        logger.info(f"Real-time retrieval for query: '{query}' in index: '{index_name}' [ID: {query_id}]")
        
        # Get index path
        from utils.simple_vector_manager import get_simple_index_path
        index_path = get_simple_index_path(index_name)
        
        if not index_path:
            logger.error(f"Index path not found for: {index_name}")
            return []
        
        # Try enterprise retrieval first if available
        if self.enable_enterprise and self.enterprise_system:
            try:
                logger.info("Using enterprise hybrid search for real-time retrieval")
                results = self.enterprise_system.retrieve_with_enterprise_features(
                    query, index_name, max_results, use_cache=False
                )
                
                if results:
                    # Log retrieval for debugging
                    self.query_history[query_id] = {
                        'query': query,
                        'index_name': index_name,
                        'timestamp': time.time(),
                        'results_count': len(results),
                        'first_result_preview': results[0]['content'][:100] if results else 'No results',
                        'method': 'enterprise_hybrid'
                    }
                    return results
            except Exception as e:
                logger.warning(f"Enterprise retrieval failed, falling back to disk read: {e}")
        
        # Fallback to original disk-based retrieval
        results = self._read_fresh_from_disk(query, index_path, max_results)
        
        # Log retrieval for debugging
        self.query_history[query_id] = {
            'query': query,
            'index_name': index_name,
            'timestamp': time.time(),
            'results_count': len(results),
            'first_result_preview': results[0]['content'][:100] if results else 'No results',
            'method': 'disk_read_fallback'
        }
        
        return results
    
    def _read_fresh_from_disk(self, query: str, index_path: str, max_results: int) -> List[Dict[str, Any]]:
        """Read content directly from disk files without any caching"""
        results = []
        index_path = Path(index_path)
        
        # Check for extracted text file (like ByLaw)
        extracted_text_path = index_path / "extracted_text.txt"
        if extracted_text_path.exists():
            logger.info(f"Reading fresh content from: {extracted_text_path}")
            results.extend(self._process_extracted_text(query, extracted_text_path, max_results))
        
        # Check for other document files
        for file_path in index_path.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.html', '.json']:
                if file_path.name != "extracted_text.txt" and file_path.name != "index.meta":
                    logger.info(f"Reading fresh content from: {file_path}")
                    results.extend(self._process_single_file(query, file_path, max_results - len(results)))
                    
                    if len(results) >= max_results:
                        break
        
        # Sort by relevance and return top results
        return self._rank_fresh_results(results, query)[:max_results]
    
    def _process_extracted_text(self, query: str, file_path: Path, max_results: int) -> List[Dict[str, Any]]:
        """Process extracted text file with advanced chunking strategy"""
        results = []
        
        try:
            # Force fresh read with timestamp
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Fresh read: {len(content)} characters from {file_path}")
            
            # Apply advanced chunking strategy
            from utils.advanced_chunking_strategy import get_advanced_chunking_strategy
            
            chunking_config = {
                "chunk_size": 1500,
                "chunk_overlap": 500,
                "respect_section_breaks": True,
                "extract_tables": True,
                "preserve_heading_structure": True
            }
            
            chunker = get_advanced_chunking_strategy(chunking_config)
            chunks = chunker.chunk_document(content, source_name=str(file_path.name))
            
            # Filter and score chunks based on query relevance
            for chunk in chunks:
                chunk_content = chunk['content']
                
                if self._content_matches_query(chunk_content, query):
                    relevance_score = self._calculate_fresh_relevance(chunk_content, query)
                    
                    results.append({
                        'content': chunk_content,
                        'source': f"{chunk['source']} - {chunk['section']}",
                        'page': chunk.get('metadata', {}).get('page', 'N/A'),
                        'section': chunk['section'],
                        'relevance_score': relevance_score,
                        'timestamp': time.time(),
                        'file_path': str(file_path),
                        'chunk_type': chunk.get('chunk_type', 'content'),
                        'chunk_metadata': chunk.get('metadata', {})
                    })
            
            # Sort by relevance and return top results
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results[:max_results]
        
        except Exception as e:
            logger.error(f"Error processing extracted text with advanced chunking: {e}")
            # Fallback to original method
            return self._process_extracted_text_fallback(query, file_path, max_results)
        
        return results
    
    def _process_extracted_text_fallback(self, query: str, file_path: Path, max_results: int) -> List[Dict[str, Any]]:
        """Fallback method for processing extracted text without advanced chunking"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by pages (original method)
            pages = re.split(r'--- Page (\d+) ---', content)
            
            for i in range(1, len(pages), 2):
                if i + 1 < len(pages):
                    page_num = int(pages[i])
                    page_content = pages[i + 1].strip()
                    
                    if page_content and self._content_matches_query(page_content, query):
                        # Extract relevant sections from this page
                        relevant_sections = self._extract_relevant_sections(page_content, query)
                        
                        for section_num, section_content in enumerate(relevant_sections, 1):
                            results.append({
                                'content': section_content,
                                'source': f"ByLaw Document - Page {page_num}, Section {section_num}",
                                'page': page_num,
                                'section': f"Section {section_num}",
                                'relevance_score': self._calculate_fresh_relevance(section_content, query),
                                'timestamp': time.time(),
                                'file_path': str(file_path)
                            })
                            
                            if len(results) >= max_results:
                                break
                
                if len(results) >= max_results:
                    break
        
        except Exception as e:
            logger.error(f"Error in fallback processing: {e}")
        
        return results
    
    def _process_single_file(self, query: str, file_path: Path, max_results: int) -> List[Dict[str, Any]]:
        """Process individual document file with fresh content"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Fresh read: {len(content)} characters from {file_path}")
            
            if self._content_matches_query(content, query):
                # Split content into meaningful chunks
                chunks = self._create_fresh_chunks(content, query)
                
                for chunk_num, chunk_content in enumerate(chunks, 1):
                    results.append({
                        'content': chunk_content,
                        'source': f"{file_path.name} - Chunk {chunk_num}",
                        'page': chunk_num,
                        'section': f"Chunk {chunk_num}",
                        'relevance_score': self._calculate_fresh_relevance(chunk_content, query),
                        'timestamp': time.time(),
                        'file_path': str(file_path)
                    })
                    
                    if len(results) >= max_results:
                        break
        
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
        
        return results
    
    def _content_matches_query(self, content: str, query: str) -> bool:
        """Check if content is relevant to the query"""
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Check for exact phrase match
        if query_lower in content_lower:
            return True
        
        # Check for keyword matches
        query_words = query_lower.split()
        matches = sum(1 for word in query_words if len(word) > 2 and word in content_lower)
        
        # Require at least 50% of meaningful words to match
        return matches >= len([w for w in query_words if len(w) > 2]) * 0.5
    
    def _extract_relevant_sections(self, page_content: str, query: str) -> List[str]:
        """Extract the most relevant sections from a page"""
        # Split by paragraphs
        paragraphs = [p.strip() for p in page_content.split('\n\n') if p.strip()]
        
        relevant_sections = []
        query_lower = query.lower()
        
        # Find paragraphs that contain query terms
        for para in paragraphs:
            if self._content_matches_query(para, query):
                # Include context (previous and next paragraph if available)
                para_index = paragraphs.index(para)
                
                context_start = max(0, para_index - 1)
                context_end = min(len(paragraphs), para_index + 2)
                
                context_section = '\n\n'.join(paragraphs[context_start:context_end])
                
                if context_section not in relevant_sections:
                    relevant_sections.append(context_section)
        
        # If no specific matches, return first few paragraphs
        if not relevant_sections and paragraphs:
            relevant_sections = paragraphs[:3]
        
        return relevant_sections
    
    def _create_fresh_chunks(self, content: str, query: str) -> List[str]:
        """Create fresh chunks focused on query relevance"""
        # Split content into sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Check if this sentence is relevant
            if self._content_matches_query(sentence, query):
                # Start a new chunk around this relevant sentence
                if current_chunk and len(current_chunk) > 500:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
            else:
                # Add to current chunk if not too long
                if len(current_chunk + sentence) < 1500:
                    current_chunk += " " + sentence if current_chunk else sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _calculate_fresh_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score for fresh content"""
        content_lower = content.lower()
        query_lower = query.lower()
        score = 0.0
        
        # Exact phrase match
        if query_lower in content_lower:
            score += 1.0
        
        # Individual word matches
        query_words = [w for w in query_lower.split() if len(w) > 2]
        for word in query_words:
            if word in content_lower:
                score += 0.5
                # Bonus for multiple occurrences
                score += min(content_lower.count(word) * 0.1, 0.3)
        
        # Content quality bonus
        if 200 <= len(content) <= 2000:
            score += 0.2
        
        # Normalize score
        return min(score, 1.0)
    
    def _rank_fresh_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rank results by fresh relevance calculation"""
        # Sort by relevance score (descending) and timestamp (descending for freshness)
        return sorted(results, key=lambda x: (x['relevance_score'], x['timestamp']), reverse=True)
    
    def get_query_history(self) -> Dict[str, Any]:
        """Get history of queries for debugging"""
        return self.query_history
    
    def clear_cache(self):
        """Clear any internal caching"""
        self.query_history.clear()
        self.cache_buster = str(int(time.time()))
        logger.info("Real-time retriever cache cleared")

def get_real_time_retriever() -> RealTimeRetriever:
    """Get instance of real-time retriever"""
    return RealTimeRetriever()

def verify_fresh_content(query: str, index_name: str) -> Dict[str, Any]:
    """
    Verify that content retrieval is working correctly and returning fresh data
    
    Returns:
        Dictionary with verification results and diagnostics
    """
    retriever = get_real_time_retriever()
    
    verification = {
        'query': query,
        'index_name': index_name,
        'timestamp': time.time(),
        'status': 'unknown',
        'diagnostics': []
    }
    
    try:
        # Get fresh results
        results = retriever.retrieve_fresh_content(query, index_name, max_results=3)
        
        if not results:
            verification['status'] = 'no_results'
            verification['diagnostics'].append('No results returned from fresh retrieval')
        else:
            verification['status'] = 'success'
            verification['results_count'] = len(results)
            verification['first_result_length'] = len(results[0]['content'])
            verification['contains_query_terms'] = any(
                query.lower() in result['content'].lower() for result in results
            )
            verification['diagnostics'].append(f"Retrieved {len(results)} fresh results")
            verification['diagnostics'].append(f"First result: {results[0]['content'][:100]}...")
            
            # Check for cached/generic responses
            generic_indicators = ['simulated', 'demonstration', 'example', 'sample']
            is_generic = any(
                indicator in result['content'].lower() 
                for result in results 
                for indicator in generic_indicators
            )
            
            if is_generic:
                verification['status'] = 'cached_detected'
                verification['diagnostics'].append('WARNING: Generic/cached content detected')
            
    except Exception as e:
        verification['status'] = 'error'
        verification['error'] = str(e)
        verification['diagnostics'].append(f"Error during verification: {e}")
    
    return verification
