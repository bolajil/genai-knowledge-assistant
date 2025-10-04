"""
Document-Only Retrieval System
Returns ONLY content from actual documents, no AI-generated responses
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DocumentOnlyRetrieval:
    """Strict document-based retrieval with no AI generation fallbacks"""
    
    def __init__(self):
        self.data_path = Path("data/indexes")
    
    def search_document_content(self, query: str, index_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for content strictly from document chunks
        Returns empty list if no document content found - NO AI GENERATION
        """
        try:
            index_path = self.data_path / index_name
            
            if not index_path.exists():
                logger.warning(f"Index {index_name} not found")
                return []
            
            # Try semantic chunks first
            semantic_results = self._search_semantic_chunks(query, index_path, max_results)
            if semantic_results:
                return semantic_results
            
            # Fallback to direct text search
            text_results = self._search_extracted_text(query, index_path, max_results)
            return text_results
            
        except Exception as e:
            logger.error(f"Error in document-only search: {e}")
            return []
    
    def _search_semantic_chunks(self, query: str, index_path: Path, max_results: int) -> List[Dict[str, Any]]:
        """Search through semantic chunks for exact document content"""
        results = []
        query_lower = query.lower()
        
        try:
            # Get all semantic chunk files
            chunk_files = sorted(index_path.glob("semantic_chunk_*.json"))
            
            if not chunk_files:
                logger.info("No semantic chunks found")
                return []
            
            logger.info(f"Searching {len(chunk_files)} semantic chunks")
            
            # Search through chunks for relevant content
            for chunk_file in chunk_files:
                try:
                    with open(chunk_file, 'r', encoding='utf-8') as f:
                        chunk_data = json.load(f)
                    
                    content = chunk_data.get('content', '').lower()
                    title = chunk_data.get('title', '').lower()
                    
                    # Calculate relevance based on query terms
                    relevance_score = self._calculate_relevance(query_lower, content, title)
                    
                    if relevance_score > 0:
                        results.append({
                            'content': chunk_data.get('content', ''),
                            'title': chunk_data.get('title', 'Untitled'),
                            'source': chunk_data.get('document_name', index_path.name),
                            'chunk_type': chunk_data.get('chunk_type', 'semantic'),
                            'hierarchy': chunk_data.get('hierarchy', []),
                            'context_path': chunk_data.get('context_path', ''),
                            'relevance_score': relevance_score,
                            'chunk_size': chunk_data.get('chunk_size', 0),
                            'metadata': chunk_data.get('metadata', {}),
                            'document_only': True  # Flag to indicate this is pure document content
                        })
                        
                except Exception as e:
                    logger.error(f"Error reading chunk {chunk_file}: {e}")
                    continue
            
            # Sort by relevance and return top results
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching semantic chunks: {e}")
            return []
    
    def _search_extracted_text(self, query: str, index_path: Path, max_results: int) -> List[Dict[str, Any]]:
        """Search extracted text file for document content"""
        try:
            text_file = index_path / "extracted_text.txt"
            
            if not text_file.exists():
                logger.info("No extracted text file found")
                return []
            
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find relevant sections
            query_terms = query.lower().split()
            lines = content.split('\n')
            relevant_sections = []
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(term in line_lower for term in query_terms):
                    # Get context around the match
                    start = max(0, i - 5)
                    end = min(len(lines), i + 15)
                    section_content = '\n'.join(lines[start:end])
                    
                    relevance_score = sum(1 for term in query_terms if term in line_lower)
                    
                    relevant_sections.append({
                        'content': section_content,
                        'title': f"Section starting at line {i+1}",
                        'source': index_path.name,
                        'line_number': i + 1,
                        'relevance_score': relevance_score,
                        'document_only': True
                    })
            
            # Remove duplicates and sort by relevance
            unique_sections = []
            seen_content = set()
            
            for section in relevant_sections:
                content_hash = hash(section['content'][:100])  # Use first 100 chars as hash
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_sections.append(section)
            
            unique_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
            return unique_sections[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching extracted text: {e}")
            return []
    
    def _calculate_relevance(self, query: str, content: str, title: str) -> float:
        """Calculate relevance score based on query term matches"""
        query_terms = query.split()
        score = 0.0
        
        for term in query_terms:
            # Title matches are weighted higher
            if term in title:
                score += 2.0
            # Content matches
            if term in content:
                score += 1.0
        
        # Bonus for exact phrase matches
        if query in content:
            score += 3.0
        
        return score

def retrieve_document_only(query: str, index_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Main function for document-only retrieval
    Returns ONLY actual document content, never generates AI responses
    """
    from utils.markdown_formatter import format_to_markdown
    
    retriever = DocumentOnlyRetrieval()
    results = retriever.search_document_content(query, index_name, max_results)
    
    if not results:
        logger.info(f"No document content found for query: '{query}' in index: '{index_name}'")
        return [{
            'content': f"No content found in document '{index_name}' for query: '{query}'",
            'title': 'No Results Found',
            'source': index_name,
            'relevance_score': 0.0,
            'document_only': True,
            'no_content_found': True,
            'markdown_formatted': True
        }]
    
    # Add markdown formatting to results
    for result in results:
        if result.get('content'):
            # Format individual content as markdown
            formatted_content = format_to_markdown([result], query)
            result['markdown_content'] = formatted_content
            result['markdown_formatted'] = True
    
    logger.info(f"Found {len(results)} document-only results with markdown formatting")
    return results
