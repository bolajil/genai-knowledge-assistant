"""
Enhanced Page-Based Chunking Integration
Integrates page-based chunking with existing retrieval systems
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from .page_based_chunking import PageBasedChunker, process_document_with_page_chunking

logger = logging.getLogger(__name__)

class EnhancedPageChunkingRetrieval:
    """
    Enhanced retrieval system using page-based chunking for better LLM processing
    """
    
    def __init__(self):
        self.chunker = PageBasedChunker(preserve_headers=True, include_page_numbers=True)
    
    def retrieve_with_page_chunks(self, query: str, index_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve information using page-based chunking strategy
        
        Args:
            query: Search query
            index_name: Name of the index to search
            max_results: Maximum number of results to return
            
        Returns:
            List of relevant page chunks with enhanced context
        """
        try:
            # Get document content
            index_path = Path(f"data/indexes/{index_name}")
            extracted_text_path = index_path / "extracted_text.txt"
            
            if not extracted_text_path.exists():
                logger.error(f"No extracted text found for index: {index_name}")
                return []
            
            with open(extracted_text_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Generate page-based chunks
            chunks = self.chunker.chunk_document_by_pages(content, index_name)
            
            if not chunks:
                logger.warning("No chunks generated from page-based processing")
                return []
            
            # Score and rank chunks based on query relevance
            scored_chunks = self._score_chunks_for_query(query, chunks)
            
            # Return top results with enhanced formatting
            results = []
            for chunk in scored_chunks[:max_results]:
                enhanced_chunk = self._enhance_chunk_for_display(chunk, query)
                results.append(enhanced_chunk)
            
            logger.info(f"Retrieved {len(results)} page-based chunks for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error in page-based retrieval: {e}")
            return []
    
    def _score_chunks_for_query(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score chunks based on query relevance"""
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        for chunk in chunks:
            score = 0
            content_lower = chunk['content'].lower()
            
            # Exact phrase matching (highest score)
            if query_lower in content_lower:
                score += 100
            
            # Individual term matching
            for term in query_terms:
                if term in content_lower:
                    score += 20
            
            # Section title matching (high relevance)
            for section in chunk.get('sections', []):
                section_lower = section.lower()
                if any(term in section_lower for term in query_terms):
                    score += 50
            
            # Page context bonus for specific queries
            if 'removal' in query_lower and any('removal' in s.lower() for s in chunk.get('sections', [])):
                score += 75
            if 'vacancy' in query_lower and any('vacancy' in s.lower() for s in chunk.get('sections', [])):
                score += 75
            if 'director' in query_lower and any('director' in s.lower() for s in chunk.get('sections', [])):
                score += 50
            
            chunk['relevance_score'] = score / 100.0  # Normalize to 0-1 range
        
        # Sort by relevance score (descending)
        return sorted(chunks, key=lambda x: x['relevance_score'], reverse=True)
    
    def _enhance_chunk_for_display(self, chunk: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Enhance chunk with display-friendly formatting"""
        
        # Create enhanced response with clear structure
        page_num = chunk.get('page', 1)
        sections = chunk.get('sections', [])
        
        # Build section context
        section_context = ""
        if sections:
            section_context = f"\n**Sections on this page:** {', '.join(sections)}\n"
        
        enhanced_response = f"""# Page {page_num} Content

{section_context}
## Relevant Information:

{chunk['content']}

---
*Source: {chunk['source']} | Relevance: {chunk['relevance_score']:.2f}*"""
        
        return {
            'content': chunk['content'],
            'source': chunk['source'],
            'page': page_num,
            'section': ', '.join(sections) if sections else f'Page {page_num}',
            'relevance_score': chunk['relevance_score'],
            'timestamp': 'N/A',
            'file_path': chunk['metadata']['document'],
            'metadata': chunk['metadata'],
            'llm_processed': True,
            'enhanced_response': enhanced_response,
            'quality_score': min(chunk['relevance_score'] + 0.2, 1.0),  # Boost quality for page-based chunks
            'sections': sections,
            'page_number': page_num
        }

def integrate_page_chunking_with_query_assistant():
    """
    Integration function to update query assistant with page-based chunking
    """
    try:
        # Update the query assistant to use page-based chunking for ByLaw queries
        from pathlib import Path
        
        query_assistant_path = Path("tabs/query_assistant.py")
        if not query_assistant_path.exists():
            logger.error("Query assistant file not found")
            return False
        
        # Read current content
        with open(query_assistant_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if page chunking integration already exists
        if "EnhancedPageChunkingRetrieval" in content:
            logger.info("Page chunking integration already exists")
            return True
        
        # Add import for page chunking
        import_line = "from utils.enhanced_page_chunking import EnhancedPageChunkingRetrieval"
        
        # Find the imports section and add our import
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith("from utils.enhanced_llm_integration"):
                lines.insert(i + 1, import_line)
                break
        
        # Update the content
        updated_content = '\n'.join(lines)
        
        # Write back to file
        with open(query_assistant_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logger.info("Successfully integrated page chunking with query assistant")
        return True
        
    except Exception as e:
        logger.error(f"Error integrating page chunking: {e}")
        return False

def create_page_based_bylaw_retrieval(query: str, index_name: str = "ByLawS2_index") -> List[Dict[str, Any]]:
    """
    Specialized function for ByLaw queries using page-based chunking
    
    Args:
        query: User query
        index_name: Index to search (default: ByLawS2_index)
        
    Returns:
        List of relevant page-based results
    """
    try:
        retriever = EnhancedPageChunkingRetrieval()
        results = retriever.retrieve_with_page_chunks(query, index_name, max_results=3)
        
        # Filter for most relevant results
        if results:
            # Ensure we get the most relevant page
            top_results = [r for r in results if r['relevance_score'] > 0.5]
            if not top_results:
                top_results = results[:1]  # At least return the best match
            
            logger.info(f"Page-based ByLaw retrieval returned {len(top_results)} results")
            return top_results
        
        return []
        
    except Exception as e:
        logger.error(f"Error in page-based ByLaw retrieval: {e}")
        return []
