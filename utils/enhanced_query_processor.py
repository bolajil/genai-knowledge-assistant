"""
Enhanced Query Processor
=======================

A comprehensive query processing system that combines semantic search with
keyword search, metadata filtering, and result formatting.
"""

import os
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union, Set, Callable
from pathlib import Path
import json
from datetime import datetime
import hashlib
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import vector database with graceful fallbacks
try:
    from utils.vector_db_init import get_any_vector_db_provider, VECTOR_DB_AVAILABLE
    vector_db_provider = get_any_vector_db_provider()
except ImportError:
    logger.warning("Vector database provider not available.")
    VECTOR_DB_AVAILABLE = False
    vector_db_provider = None

# Try to import the document metadata manager
try:
    from utils.enhanced_document_processor import DocumentMetadata, DEFAULT_METADATA_PATH
    metadata_manager = DocumentMetadata()
    METADATA_AVAILABLE = True
except ImportError:
    logger.warning("Document metadata manager not available.")
    METADATA_AVAILABLE = False
    metadata_manager = None
    
# Try to import the enhanced metadata search engine
try:
    from utils.enhanced_metadata_search import get_metadata_search_engine
    metadata_search_engine = get_metadata_search_engine()
    METADATA_SEARCH_AVAILABLE = True
    logger.info("Enhanced metadata search engine initialized successfully")
except ImportError:
    logger.warning("Enhanced metadata search engine not available.")
    METADATA_SEARCH_AVAILABLE = False
    metadata_search_engine = None

# Try to import LLM providers
try:
    from query_llm import synthesize_answer
    LLM_AVAILABLE = True
except ImportError:
    logger.warning("LLM query module not available.")
    LLM_AVAILABLE = False

# Default configuration
DEFAULT_TOP_K = 5
DEFAULT_RELEVANCE_THRESHOLD = 0.6

class QueryPreprocessor:
    """Class to preprocess and expand queries"""
    
    def __init__(self):
        """Initialize the query preprocessor"""
        # Basic stopwords to remove from queries if needed
        self.stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'which', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'to',
            'at', 'in', 'on', 'by', 'with', 'about', 'against', 'between', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'from', 'up',
            'down', 'of', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both',
            'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't',
            'can', 'will', 'just', 'don', 'should', 'now'
        }
        
        # Patterns to detect and parse special query syntax
        self.special_patterns = {
            "exact_match": r'"([^"]+)"',
            "field_filter": r'(\w+):(\w+)',
            "date_range": r'date:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})',
            "negation": r'-(\w+)',
        }
    
    def preprocess_query(self, query: str) -> Dict:
        """
        Preprocess a query to extract filters, special patterns, and clean text
        
        Args:
            query: The raw query string
            
        Returns:
            Dict with preprocessed query components
        """
        # Extract special patterns
        special_matches = {}
        
        # Extract exact phrases (text in quotes)
        exact_matches = re.findall(self.special_patterns["exact_match"], query)
        if exact_matches:
            special_matches["exact_phrases"] = exact_matches
            # Remove the exact matches from the query for further processing
            for match in exact_matches:
                query = query.replace(f'"{match}"', f" {match} ")
        
        # Extract field filters (field:value)
        field_filters = re.findall(self.special_patterns["field_filter"], query)
        if field_filters:
            filters = {}
            for field, value in field_filters:
                filters[field] = value
                # Remove the filters from the query
                query = query.replace(f"{field}:{value}", " ")
            special_matches["filters"] = filters
        
        # Extract date ranges
        date_ranges = re.findall(self.special_patterns["date_range"], query)
        if date_ranges:
            special_matches["date_ranges"] = date_ranges
            # Remove date ranges from the query
            for date_range in date_ranges:
                query = query.replace(f"date:{date_range[0]}..{date_range[1]}", " ")
        
        # Extract negations (words with - prefix)
        negations = re.findall(self.special_patterns["negation"], query)
        if negations:
            special_matches["negations"] = negations
            # Remove negations from the query
            for negation in negations:
                query = query.replace(f"-{negation}", " ")
        
        # Clean up the query
        clean_query = query.strip()
        
        # Normalize whitespace
        clean_query = re.sub(r'\s+', ' ', clean_query)
        
        return {
            "original_query": query,
            "clean_query": clean_query,
            "special_matches": special_matches
        }
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand a query with synonyms and related terms to improve recall
        
        Args:
            query: The processed query string
            
        Returns:
            List of expanded query variations
        """
        # Simple query expansion with common synonyms
        # In a production system, this would use a more sophisticated approach
        expansions = [query]
        
        # Extract key terms (non-stopwords)
        terms = [term.lower() for term in query.split() if term.lower() not in self.stopwords]
        
        # Some basic business/cloud computing expansions
        # This would ideally come from a domain-specific thesaurus or embedding model
        expansions_dict = {
            "aws": ["amazon web services", "amazon cloud", "ec2", "s3"],
            "cloud": ["aws", "azure", "gcp", "cloud computing", "cloud platform"],
            "security": ["cybersecurity", "protection", "safeguard", "defense"],
            "cost": ["price", "expense", "billing", "financial", "budget"],
            "infrastructure": ["architecture", "framework", "foundation", "structure"],
            "data": ["information", "records", "statistics", "figures"],
            "customer": ["client", "user", "consumer", "buyer"],
            "service": ["offering", "solution", "product"],
            "instance": ["server", "vm", "virtual machine", "compute"],
            "storage": ["s3", "database", "warehouse", "repository"],
            "deploy": ["launch", "implement", "roll out", "provision"],
            "monitor": ["observe", "track", "supervise", "analyze"],
            "application": ["app", "program", "software", "system"],
            "network": ["connectivity", "connection", "communication", "internet"],
            "performance": ["speed", "efficiency", "responsiveness", "throughput"]
        }
        
        # Generate expansions for each key term
        for term in terms:
            if term in expansions_dict:
                for synonym in expansions_dict[term]:
                    # Replace the term with its synonym
                    expanded_query = query.replace(term, synonym)
                    if expanded_query != query and expanded_query not in expansions:
                        expansions.append(expanded_query)
        
        return expansions


class QueryResult:
    """Class to represent a query result"""
    
    def __init__(self, 
                content: str, 
                source: str, 
                relevance: float,
                metadata: Dict = None,
                doc_id: str = None,
                chunk_id: str = None):
        """Initialize a query result"""
        self.content = content
        self.source = source
        self.relevance = relevance
        self.metadata = metadata or {}
        self.doc_id = doc_id
        self.chunk_id = chunk_id
        
        # Track when this result was generated
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "content": self.content,
            "source": self.source,
            "relevance": self.relevance,
            "metadata": self.metadata,
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QueryResult':
        """Create from dictionary"""
        return cls(
            content=data["content"],
            source=data["source"],
            relevance=data["relevance"],
            metadata=data.get("metadata"),
            doc_id=data.get("doc_id"),
            chunk_id=data.get("chunk_id")
        )


class EnhancedQueryProcessor:
    """Enhanced query processor with advanced search capabilities"""
    
    def __init__(self):
        """Initialize the query processor"""
        self.query_preprocessor = QueryPreprocessor()
        
        # Initialize query cache
        self.query_cache = {}
        self.max_cache_size = 100
        
        # Initialize feedback tracking
        self.feedback_tracking = {}
    
    def _search_vector_database(self, 
                               query: str, 
                               index_name: str = None, 
                               top_k: int = DEFAULT_TOP_K,
                               relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD) -> List[QueryResult]:
        """
        Search the vector database
        
        Args:
            query: The query string
            index_name: Name of the index to search (None for all available indexes)
            top_k: Maximum number of results to return
            relevance_threshold: Minimum relevance score to include in results
            
        Returns:
            List of QueryResult objects
        """
        if not VECTOR_DB_AVAILABLE or not vector_db_provider:
            logger.warning("Vector database not available. Cannot perform semantic search.")
            return []
        
        try:
            # Search specific index if provided
            if index_name:
                results = vector_db_provider.search_index(query, index_name, top_k)
            else:
                # Search all indexes
                results = vector_db_provider.search(query, top_k)
            
            # Convert to QueryResult objects
            query_results = []
            for result in results:
                # Extract content and metadata
                if isinstance(result, dict):
                    content = result.get("content", "")
                    metadata = result.get("metadata", {})
                    source = metadata.get("source", "Unknown")
                    relevance = metadata.get("score", 0.0)
                    doc_id = metadata.get("doc_id")
                    chunk_id = metadata.get("chunk_id")
                else:
                    # Handle custom result objects (like from mock provider)
                    content = getattr(result, "content", "")
                    source = getattr(result, "source", "Unknown")
                    relevance = getattr(result, "relevance", 0.0)
                    metadata = getattr(result, "metadata", {})
                    doc_id = getattr(result, "doc_id", None)
                    chunk_id = getattr(result, "chunk_id", None)
                
                # Filter by relevance threshold
                if relevance >= relevance_threshold:
                    query_results.append(QueryResult(
                        content=content,
                        source=source,
                        relevance=relevance,
                        metadata=metadata,
                        doc_id=doc_id,
                        chunk_id=chunk_id
                    ))
            
            return query_results
        
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return []
    
    def _filter_results_by_metadata(self, 
                                  results: List[QueryResult], 
                                  filters: Dict) -> List[QueryResult]:
        """
        Filter results based on metadata filters
        
        Args:
            results: List of QueryResult objects
            filters: Dictionary of metadata field:value filters
            
        Returns:
            Filtered list of QueryResult objects
        """
        if not filters:
            return results
        
        filtered_results = []
        for result in results:
            match = True
            for field, value in filters.items():
                # Check if the field exists in metadata and matches the value
                if field not in result.metadata or result.metadata[field] != value:
                    match = False
                    break
            
            if match:
                filtered_results.append(result)
        
        return filtered_results
    
    def _deduplicate_results(self, results: List[QueryResult]) -> List[QueryResult]:
        """
        Remove duplicate results based on content similarity
        
        Args:
            results: List of QueryResult objects
            
        Returns:
            Deduplicated list of QueryResult objects
        """
        if not results:
            return []
        
        # Use a simple hash-based approach for deduplication
        seen_hashes = set()
        deduplicated = []
        
        for result in results:
            # Create a hash of the content (simplified approach)
            content_hash = hashlib.md5(result.content.encode()).hexdigest()
            
            # Check if we've seen this content before
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduplicated.append(result)
        
        return deduplicated
    
    def search(self, 
              query: str, 
              index_name: str = None, 
              top_k: int = DEFAULT_TOP_K,
              relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
              filters: Dict = None,
              deduplicate: bool = True,
              use_cache: bool = True,
              use_metadata_search: bool = True) -> List[QueryResult]:
        """
        Search for documents matching the query
        
        Args:
            query: The query string
            index_name: Name of the index to search (None for all available indexes)
            top_k: Maximum number of results to return
            relevance_threshold: Minimum relevance score to include in results
            filters: Dictionary of metadata field:value filters
            deduplicate: Whether to remove duplicate results
            use_cache: Whether to use and update the query cache
            use_metadata_search: Whether to use enhanced metadata search
            
        Returns:
            List of QueryResult objects
        """
        # Generate cache key
        cache_key = f"{query}:{index_name}:{top_k}:{relevance_threshold}:{json.dumps(filters or {})}"
        
        # Check cache
        if use_cache and cache_key in self.query_cache:
            logger.info(f"Cache hit for query: {query}")
            return self.query_cache[cache_key]
        
        # Preprocess the query
        processed_query = self.query_preprocessor.preprocess_query(query)
        clean_query = processed_query["clean_query"]
        special_matches = processed_query["special_matches"]
        
        # Extract filters from special matches and combine with explicit filters
        query_filters = special_matches.get("filters", {})
        if filters:
            query_filters.update(filters)
        
        # Check for metadata search patterns in the query
        metadata_filtered_docs = None
        if use_metadata_search and METADATA_SEARCH_AVAILABLE and metadata_search_engine:
            try:
                # Look for metadata search patterns in the query
                metadata_matches = re.findall(r'(type|date|size|author|category|source):([^\s]+)', query)
                if metadata_matches:
                    logger.info(f"Found metadata search patterns in query: {metadata_matches}")
                    # Extract metadata query part
                    metadata_query_parts = []
                    for field, value in metadata_matches:
                        metadata_query_parts.append(f"{field}:{value}")
                    metadata_query = " ".join(metadata_query_parts)
                    
                    # Execute metadata search
                    doc_ids = metadata_search_engine.execute_metadata_query(metadata_query)
                    if doc_ids:
                        logger.info(f"Metadata search found {len(doc_ids)} matching documents")
                        metadata_filtered_docs = doc_ids
                        
                        # Remove metadata patterns from the query for vector search
                        for pattern in metadata_query_parts:
                            clean_query = clean_query.replace(pattern, "").strip()
            except Exception as e:
                logger.error(f"Error in metadata search: {e}")
        
        # Search the vector database
        results = self._search_vector_database(
            clean_query, 
            index_name, 
            top_k,
            relevance_threshold
        )
        
        # Filter results by metadata if needed
        if query_filters:
            results = self._filter_results_by_metadata(results, query_filters)
        
        # Apply metadata document filtering if available
        if metadata_filtered_docs:
            results = [r for r in results if r.doc_id in metadata_filtered_docs]
        
        # Deduplicate results if requested
        if deduplicate:
            results = self._deduplicate_results(results)
        
        # Update cache
        if use_cache:
            # Limit cache size
            if len(self.query_cache) >= self.max_cache_size:
                # Remove oldest entries
                oldest_keys = sorted(self.query_cache.keys())[:len(self.query_cache) // 2]
                for key in oldest_keys:
                    del self.query_cache[key]
            
            self.query_cache[cache_key] = results
        
        return results
    
    def synthesize_answer(self, 
                         query: str,
                         results: List[QueryResult],
                         provider: str = "openai") -> str:
        """
        Synthesize an answer from search results using an LLM
        
        Args:
            query: The original query string
            results: List of QueryResult objects
            provider: LLM provider to use
            
        Returns:
            Synthesized answer text
        """
        if not LLM_AVAILABLE:
            logger.warning("LLM query module not available. Cannot synthesize answer.")
            return "LLM processing not available. Here are the raw search results."
        
        try:
            # Extract content from results
            chunks = [result.content for result in results]
            
            # Synthesize an answer
            answer = synthesize_answer(query, chunks, provider)
            return answer
        
        except Exception as e:
            logger.error(f"Error synthesizing answer: {e}")
            return f"Error generating answer: {str(e)}"
    
    def track_feedback(self, 
                      query: str, 
                      results: List[QueryResult], 
                      helpful: bool,
                      comments: str = None) -> Dict:
        """
        Track user feedback on search results
        
        Args:
            query: The query string
            results: The search results
            helpful: Whether the results were helpful
            comments: Optional user comments
            
        Returns:
            Feedback tracking information
        """
        # Generate a feedback ID
        feedback_id = hashlib.md5(f"{query}:{datetime.now().isoformat()}".encode()).hexdigest()
        
        # Store the feedback
        feedback = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "helpful": helpful,
            "comments": comments,
            "result_count": len(results),
            "result_sources": [result.source for result in results]
        }
        
        self.feedback_tracking[feedback_id] = feedback
        
        # Save feedback to a file
        try:
            feedback_dir = Path("data/feedback")
            feedback_dir.mkdir(parents=True, exist_ok=True)
            
            feedback_file = feedback_dir / "query_feedback.json"
            
            # Load existing feedback
            existing_feedback = {}
            if feedback_file.exists():
                with open(feedback_file, 'r') as f:
                    existing_feedback = json.load(f)
            
            # Add new feedback
            existing_feedback[feedback_id] = feedback
            
            # Save updated feedback
            with open(feedback_file, 'w') as f:
                json.dump(existing_feedback, f, indent=2)
            
            logger.info(f"Saved feedback with ID: {feedback_id}")
            
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
        
        return feedback

# Create a singleton instance
_query_processor = None

def get_query_processor() -> EnhancedQueryProcessor:
    """Get the singleton query processor instance"""
    global _query_processor
    
    if _query_processor is None:
        _query_processor = EnhancedQueryProcessor()
    
    return _query_processor
