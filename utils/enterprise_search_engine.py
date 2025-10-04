"""
Enterprise Search Engine

Advanced search engine with semantic understanding, context awareness,
and enterprise-grade response quality.
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnterpriseSearchResult:
    """Enhanced search result with rich context"""
    def __init__(self, content: str, source: str, relevance: float,
                 page: int = None, section: str = None, context: str = None):
        self.content = content
        self.source = source
        self.relevance = relevance
        self.page = page
        self.section = section
        self.context = context
        self.metadata = {
            'source': source,
            'page': page,
            'section': section,
            'relevance': relevance,
            'word_count': len(content.split()),
            'timestamp': datetime.now().isoformat()
        }

class EnterpriseSearchEngine:
    """Enterprise-grade search engine with advanced capabilities"""
    
    def __init__(self):
        self.search_strategies = {
            'comprehensive': self._comprehensive_search,
            'semantic': self._semantic_search,
            'keyword': self._keyword_search,
            'contextual': self._contextual_search
        }
    
    def search(self, query: str, index_name: str, strategy: str = 'comprehensive', 
               max_results: int = 10) -> List[EnterpriseSearchResult]:
        """Perform enterprise-grade search with specified strategy"""
        
        # Get index path
        from utils.simple_vector_manager import get_simple_index_path
        index_path = get_simple_index_path(index_name)
        
        if not index_path:
            logger.error(f"Index not found: {index_name}")
            return []
        
        # Load and process documents
        documents = self._load_documents(index_path)
        if not documents:
            return []
        
        # Apply search strategy
        search_func = self.search_strategies.get(strategy, self._comprehensive_search)
        results = search_func(query, documents, max_results)
        
        logger.info(f"Enterprise search for '{query}' in {index_name}: {len(results)} results")
        return results
    
    def _load_documents(self, index_path: str) -> List[Dict[str, Any]]:
        """Load documents from index path"""
        documents = []
        index_path = Path(index_path)
        
        # Handle text-based indexes (like ByLaw)
        extracted_text_path = index_path / "extracted_text.txt"
        if extracted_text_path.exists():
            documents.extend(self._load_extracted_text(extracted_text_path))
        
        # Handle other document types
        for file_path in index_path.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.html']:
                if file_path.name != "extracted_text.txt":
                    documents.extend(self._load_single_document(file_path))
        
        return documents
    
    def _load_extracted_text(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load and parse extracted text with page structure"""
        documents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by pages and sections
            pages = re.split(r'--- Page (\d+) ---', content)
            
            current_page = 1
            for i in range(1, len(pages), 2):
                if i + 1 < len(pages):
                    page_num = int(pages[i])
                    page_content = pages[i + 1].strip()
                    
                    if page_content:
                        # Further split by sections within the page
                        sections = self._identify_page_sections(page_content)
                        
                        for section_title, section_content in sections:
                            if section_content.strip():
                                documents.append({
                                    'content': section_content.strip(),
                                    'source': f"ByLaw Document",
                                    'page': page_num,
                                    'section': section_title,
                                    'full_context': page_content
                                })
            
        except Exception as e:
            logger.error(f"Error loading extracted text: {e}")
        
        return documents
    
    def _load_single_document(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load a single document file"""
        documents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into logical chunks
            chunks = self._chunk_document(content)
            
            for i, chunk in enumerate(chunks):
                documents.append({
                    'content': chunk,
                    'source': file_path.name,
                    'chunk_id': i + 1,
                    'full_context': content
                })
        
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {e}")
        
        return documents
    
    def _identify_page_sections(self, content: str) -> List[tuple]:
        """Identify sections within a page"""
        sections = []
        
        # Common section patterns
        patterns = [
            (r'^(ARTICLE [IVX]+\..*?)$', 'article'),
            (r'^([A-Z]\.\s+[A-Z\s]+)$', 'section'),
            (r'^(\d+\.\s+.+?)$', 'numbered_item'),
            (r'^([A-Z][A-Z\s]{5,})$', 'header')
        ]
        
        lines = content.split('\n')
        current_section = "Content"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                current_content.append(line)
                continue
            
            # Check for section headers
            is_header = False
            for pattern, section_type in patterns:
                if re.match(pattern, line):
                    # Save previous section
                    if current_content:
                        section_text = '\n'.join(current_content).strip()
                        if section_text:
                            sections.append((current_section, section_text))
                    
                    # Start new section
                    current_section = line
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Add final section
        if current_content:
            section_text = '\n'.join(current_content).strip()
            if section_text:
                sections.append((current_section, section_text))
        
        return sections if sections else [("Content", content)]
    
    def _chunk_document(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Intelligent document chunking"""
        chunks = []
        
        # Try to split by paragraphs first
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _comprehensive_search(self, query: str, documents: List[Dict], max_results: int) -> List[EnterpriseSearchResult]:
        """Comprehensive search combining multiple strategies"""
        
        # Combine results from different strategies
        semantic_results = self._semantic_search(query, documents, max_results // 2)
        keyword_results = self._keyword_search(query, documents, max_results // 2)
        contextual_results = self._contextual_search(query, documents, max_results // 2)
        
        # Merge and deduplicate results
        all_results = {}
        
        for result in semantic_results + keyword_results + contextual_results:
            key = f"{result.source}_{result.page}_{hash(result.content[:100])}"
            if key not in all_results or all_results[key].relevance < result.relevance:
                all_results[key] = result
        
        # Sort by relevance and return top results
        sorted_results = sorted(all_results.values(), key=lambda x: x.relevance, reverse=True)
        return sorted_results[:max_results]
    
    def _semantic_search(self, query: str, documents: List[Dict], max_results: int) -> List[EnterpriseSearchResult]:
        """Semantic search with context understanding"""
        results = []
        query_terms = query.lower().split()
        
        for doc in documents:
            content = doc['content']
            content_lower = content.lower()
            
            # Calculate semantic relevance
            relevance = 0.0
            
            # Exact phrase matching (highest weight)
            if query.lower() in content_lower:
                relevance += 1.0
            
            # Term frequency scoring
            for term in query_terms:
                term_count = content_lower.count(term)
                if term_count > 0:
                    relevance += min(term_count * 0.1, 0.5)  # Cap individual term contribution
            
            # Context relevance (if related terms appear)
            context_terms = self._get_context_terms(query)
            for term in context_terms:
                if term in content_lower:
                    relevance += 0.2
            
            # Section title relevance
            if doc.get('section') and any(term in doc['section'].lower() for term in query_terms):
                relevance += 0.3
            
            if relevance > 0:
                result = EnterpriseSearchResult(
                    content=content,
                    source=doc.get('source', 'Unknown'),
                    relevance=relevance,
                    page=doc.get('page'),
                    section=doc.get('section'),
                    context=doc.get('full_context', '')[:500] + "..." if doc.get('full_context') else None
                )
                results.append(result)
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:max_results]
    
    def _keyword_search(self, query: str, documents: List[Dict], max_results: int) -> List[EnterpriseSearchResult]:
        """Traditional keyword-based search"""
        results = []
        query_terms = set(query.lower().split())
        
        for doc in documents:
            content = doc['content']
            content_words = set(content.lower().split())
            
            # Calculate keyword overlap
            overlap = len(query_terms.intersection(content_words))
            if overlap > 0:
                relevance = overlap / len(query_terms)
                
                result = EnterpriseSearchResult(
                    content=content,
                    source=doc.get('source', 'Unknown'),
                    relevance=relevance,
                    page=doc.get('page'),
                    section=doc.get('section')
                )
                results.append(result)
        
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:max_results]
    
    def _contextual_search(self, query: str, documents: List[Dict], max_results: int) -> List[EnterpriseSearchResult]:
        """Context-aware search considering document structure"""
        results = []
        
        # Look for documents that contain query terms in important positions
        for doc in documents:
            content = doc['content']
            section = doc.get('section', '')
            
            relevance = 0.0
            
            # Higher weight for matches in section titles
            if section and any(term in section.lower() for term in query.lower().split()):
                relevance += 0.8
            
            # Higher weight for matches at beginning of content
            first_paragraph = content.split('\n\n')[0] if '\n\n' in content else content[:200]
            if any(term in first_paragraph.lower() for term in query.lower().split()):
                relevance += 0.6
            
            # Regular content matching
            if any(term in content.lower() for term in query.lower().split()):
                relevance += 0.4
            
            if relevance > 0:
                result = EnterpriseSearchResult(
                    content=content,
                    source=doc.get('source', 'Unknown'),
                    relevance=relevance,
                    page=doc.get('page'),
                    section=doc.get('section')
                )
                results.append(result)
        
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:max_results]
    
    def _get_context_terms(self, query: str) -> List[str]:
        """Get contextually related terms for better search"""
        context_map = {
            'board': ['director', 'meeting', 'vote', 'member', 'association'],
            'meeting': ['notice', 'quorum', 'vote', 'agenda', 'minutes'],
            'vote': ['ballot', 'proxy', 'majority', 'election', 'member'],
            'fee': ['assessment', 'payment', 'dues', 'collection', 'lien'],
            'property': ['lot', 'common', 'maintenance', 'restriction', 'covenant'],
            'member': ['owner', 'resident', 'association', 'rights', 'obligation']
        }
        
        related_terms = []
        query_lower = query.lower()
        
        for key, terms in context_map.items():
            if key in query_lower:
                related_terms.extend(terms)
        
        return related_terms

# Singleton instance
_search_engine_instance = None

def get_enterprise_search_engine() -> EnterpriseSearchEngine:
    """Get singleton enterprise search engine"""
    global _search_engine_instance
    if _search_engine_instance is None:
        _search_engine_instance = EnterpriseSearchEngine()
    return _search_engine_instance
