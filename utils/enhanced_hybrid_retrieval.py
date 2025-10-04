"""
Enhanced Hybrid Retrieval System

Implements hybrid search with expanded queries, metadata filtering, and confidence thresholding
to solve vague query problems and improve retrieval accuracy.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import time
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    """Enhanced retrieval result with confidence scoring"""
    content: str
    source: str
    page: Optional[str] = None
    section: Optional[str] = None
    confidence_score: float = 0.0
    relevance_score: float = 0.0
    query_match: str = ""  # Which expanded query matched this result
    metadata: Dict[str, Any] = None

class EnhancedHybridRetriever:
    """Enhanced hybrid retriever with query expansion and confidence filtering"""
    
    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self.query_enhancer = None
        self.enterprise_search = None
        self.reranker = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize retrieval components"""
        try:
            from utils.query_enhancement import get_advanced_query_processor
            self.query_enhancer = get_advanced_query_processor(use_llm=True)
            logger.info("Query enhancer initialized")
        except Exception as e:
            logger.warning(f"Query enhancer initialization failed: {e}")
        
        try:
            from utils.enterprise_hybrid_search import get_enterprise_hybrid_search
            self.enterprise_search = get_enterprise_hybrid_search()
            logger.info("Enterprise hybrid search initialized")
        except Exception as e:
            logger.warning(f"Enterprise search initialization failed: {e}")
        
        try:
            from utils.enterprise_hybrid_search import CrossEncoderReranker
            self.reranker = CrossEncoderReranker()
            logger.info("Cross-encoder re-ranker initialized")
        except Exception as e:
            logger.warning(f"Re-ranker initialization failed: {e}")
    
    def retrieve_with_expanded_queries(
        self,
        query: str,
        index_name: str,
        max_results: int = 5,
        confidence_threshold: float = 0.2,  # Lower threshold for better recall
        use_metadata_filtering: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search with expanded queries and confidence filtering
        
        Args:
            query: Original user query
            index_name: Index to search
            max_results: Maximum results to return
            filter_dict: Metadata filters to apply
            use_confidence_threshold: Whether to apply confidence filtering
            
        Returns:
            List of high-confidence retrieval results
        """
        try:
            # Step 1: Enhance the query
            enhanced_query = self._enhance_query(user_query)
            
            # Step 2: Search with each expanded query
            all_results = self._search_multiple_queries(
                enhanced_query.expanded_queries, 
                index_name, 
                max_results * 2,  # Get more results for filtering
                filter_dict
            )
            
            # Step 3: Re-rank and score results
            scored_results = self._score_and_rerank_results(
                user_query, 
                all_results, 
                enhanced_query
            )
            
            # Step 4: Apply confidence threshold
            if use_confidence_threshold:
                filtered_results = self._apply_confidence_threshold(scored_results)
            else:
                filtered_results = scored_results
            
            # Step 5: Handle no results scenario
            if not filtered_results:
                return self._handle_no_results(user_query, index_name, enhanced_query)
            
            return filtered_results[:max_results]
            
        except Exception as e:
            logger.error(f"Enhanced hybrid retrieval failed: {e}")
            return self._fallback_search(user_query, index_name, max_results)
    
    def _enhance_query(self, user_query: str):
        """Enhance query using query enhancer"""
        if self.query_enhancer:
            try:
                return self.query_enhancer.process_query(user_query, use_llm_enhancement=True)
            except Exception as e:
                logger.error(f"Query enhancement failed: {e}")
        
        # Fallback: basic enhancement
        from utils.query_enhancement import QueryEnhancer
        basic_enhancer = QueryEnhancer()
        return basic_enhancer.enhance_query(user_query)
    
    def _search_multiple_queries(
        self, 
        expanded_queries: List[str], 
        index_name: str, 
        max_results_per_query: int,
        filter_dict: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search with multiple expanded queries"""
        all_results = []
        
        for i, query in enumerate(expanded_queries):
            try:
                # Use enterprise search if available
                if self.enterprise_search:
                    results = self.enterprise_search.search(query, index_name, max_results_per_query // 2)
                    
                    # Convert SearchResult objects to dictionaries
                    for result in results:
                        result_dict = {
                            'content': result.content,
                            'source': result.source,
                            'page': result.page,
                            'section': result.section,
                            'metadata': result.metadata or {},
                            'query_match': query,
                            'query_index': i,
                            'vector_score': getattr(result, 'vector_score', 0.0),
                            'keyword_score': getattr(result, 'keyword_score', 0.0),
                            'rerank_score': getattr(result, 'rerank_score', 0.0)
                        }
                        all_results.append(result_dict)
                else:
                    # Fallback to basic search
                    results = self._fallback_search_single(query, index_name, max_results_per_query // 2)
                    all_results.extend(results)
                    
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")
                continue
        
        # Remove duplicates based on content hash
        return self._deduplicate_results(all_results)
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on content"""
        seen_hashes = set()
        unique_results = []
        
        for result in results:
            content_hash = hashlib.md5(result['content'][:500].encode()).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _score_and_rerank_results(
        self, 
        original_query: str, 
        results: List[Dict[str, Any]], 
        enhanced_query
    ) -> List[RetrievalResult]:
        """Score and re-rank results using multiple signals"""
        scored_results = []
        
        for result in results:
            # Calculate base confidence from existing scores
            base_confidence = self._calculate_base_confidence(result)
            
            # Calculate query relevance
            relevance_score = self._calculate_query_relevance(
                original_query, 
                result['content'], 
                result.get('query_match', '')
            )
            
            # Apply query index penalty (prefer results from earlier, more specific queries)
            query_penalty = result.get('query_index', 0) * 0.05
            final_confidence = max(0.0, base_confidence - query_penalty)
            
            scored_result = RetrievalResult(
                content=result['content'],
                source=result['source'],
                page=result.get('page'),
                section=result.get('section'),
                confidence_score=final_confidence,
                relevance_score=relevance_score,
                query_match=result.get('query_match', ''),
                metadata=result.get('metadata', {})
            )
            
            scored_results.append(scored_result)
        
        # Re-rank using cross-encoder if available
        if self.reranker:
            try:
                # Convert to format expected by reranker
                rerank_input = []
                for result in scored_results:
                    rerank_input.append(type('SearchResult', (), {
                        'content': result.content,
                        'confidence_score': result.confidence_score,
                        'relevance_score': result.relevance_score
                    })())
                
                reranked = self.reranker.rerank(original_query, rerank_input, len(rerank_input))
                
                # Update confidence scores with rerank scores
                for i, result in enumerate(scored_results):
                    if i < len(reranked):
                        rerank_boost = getattr(reranked[i], 'rerank_score', 0) * 0.3
                        result.confidence_score = min(1.0, result.confidence_score + rerank_boost)
                
            except Exception as e:
                logger.error(f"Re-ranking failed: {e}")
        
        # Sort by confidence score
        scored_results.sort(key=lambda x: x.confidence_score, reverse=True)
        return scored_results
    
    def _calculate_base_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate base confidence from search scores"""
        vector_score = result.get('vector_score', 0.0)
        keyword_score = result.get('keyword_score', 0.0)
        rerank_score = result.get('rerank_score', 0.0)
        
        # Weighted combination of scores
        base_confidence = (
            vector_score * 0.4 +
            keyword_score * 0.3 +
            rerank_score * 0.3
        )
        
        return min(1.0, base_confidence)
    
    def _calculate_query_relevance(self, original_query: str, content: str, matched_query: str) -> float:
        """Calculate relevance between query and content"""
        try:
            # Simple relevance calculation based on keyword overlap
            original_words = set(original_query.lower().split())
            content_words = set(content.lower().split())
            matched_words = set(matched_query.lower().split()) if matched_query else set()
            
            # Calculate overlap scores
            original_overlap = len(original_words & content_words) / len(original_words) if original_words else 0
            matched_overlap = len(matched_words & content_words) / len(matched_words) if matched_words else 0
            
            # Combine scores
            relevance = (original_overlap * 0.7 + matched_overlap * 0.3)
            return min(1.0, relevance)
            
        except Exception as e:
            logger.error(f"Relevance calculation failed: {e}")
            return 0.5
    
    def _apply_confidence_threshold(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Filter results by confidence threshold"""
        filtered = [r for r in results if r.confidence_score >= self.confidence_threshold]
        
        if not filtered and results:
            # If no results meet threshold, return top result with warning
            logger.warning(f"No results above confidence threshold {self.confidence_threshold}")
            logger.warning(f"Returning top result with confidence {results[0].confidence_score:.2f}")
            return [results[0]]
        
        return filtered
    
    def _handle_no_results(self, user_query: str, index_name: str, enhanced_query) -> List[RetrievalResult]:
        """Handle scenario when no confident results are found"""
        logger.warning(f"No confident results found for query: '{user_query}'")
        
        # Try with lower threshold
        lower_threshold_results = self.search_with_expanded_queries(
            user_query, 
            index_name, 
            max_results=3,
            use_confidence_threshold=False
        )
        
        if lower_threshold_results:
            # Return with warning metadata
            for result in lower_threshold_results:
                result.metadata['low_confidence_warning'] = True
                result.metadata['suggestion'] = self._generate_query_suggestion(user_query, enhanced_query)
            
            return lower_threshold_results[:1]  # Return only top result
        
        # No results at all - return empty with suggestion
        return []
    
    def _generate_query_suggestion(self, original_query: str, enhanced_query) -> str:
        """Generate suggestion for better query"""
        suggestions = []
        
        if hasattr(enhanced_query, 'expanded_queries') and len(enhanced_query.expanded_queries) > 1:
            # Suggest one of the expanded queries
            suggestions.append(f"Try: '{enhanced_query.expanded_queries[1]}'")
        
        # Generic suggestions based on query type
        if "powers" in original_query.lower():
            suggestions.append("Try: 'Powers of the Board of Directors' or 'Authority and duties'")
        elif "meeting" in original_query.lower():
            suggestions.append("Try: 'Board meeting requirements' or 'Meeting procedures'")
        
        return suggestions[0] if suggestions else "Try being more specific in your query"
    
    def _fallback_search(self, user_query: str, index_name: str, max_results: int) -> List[RetrievalResult]:
        """Fallback search when enhanced search fails"""
        try:
            from utils.real_time_retrieval import get_real_time_retriever
            retriever = get_real_time_retriever()
            results = retriever.retrieve_fresh_content(user_query, index_name, max_results)
            
            # Convert to RetrievalResult format
            fallback_results = []
            for result in results:
                fallback_results.append(RetrievalResult(
                    content=result.get('content', ''),
                    source=result.get('source', ''),
                    page=result.get('page'),
                    section=result.get('section'),
                    confidence_score=0.4,  # Lower confidence for fallback
                    relevance_score=0.4,
                    query_match=user_query,
                    metadata={'fallback_search': True}
                ))
            
            return fallback_results
            
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
    
    def _fallback_search_single(self, query: str, index_name: str, max_results: int) -> List[Dict[str, Any]]:
        """Single query fallback search"""
        try:
            from utils.real_time_retrieval import get_real_time_retriever
            retriever = get_real_time_retriever()
            results = retriever.retrieve_fresh_content(query, index_name, max_results)
            
            # Add query match information
            for result in results:
                result['query_match'] = query
                result['query_index'] = 0
            
            return results
            
        except Exception as e:
            logger.error(f"Single query fallback failed: {e}")
            return []

def get_enhanced_hybrid_retriever(confidence_threshold: float = 0.5) -> EnhancedHybridRetriever:
    """Get enhanced hybrid retriever instance"""
    return EnhancedHybridRetriever(confidence_threshold)

def search_with_query_enhancement(
    user_query: str, 
    index_name: str, 
    max_results: int = 10,
    confidence_threshold: float = 0.5,
    filter_dict: Optional[Dict[str, Any]] = None
) -> Tuple[List[RetrievalResult], Dict[str, Any]]:
    """
    Convenience function for enhanced search with query expansion
    
    Returns:
        Tuple of (results, metadata) where metadata contains search info
    """
    retriever = get_enhanced_hybrid_retriever(confidence_threshold)
    
    start_time = time.time()
    results = retriever.search_with_expanded_queries(
        user_query, 
        index_name, 
        max_results, 
        filter_dict
    )
    search_time = time.time() - start_time
    
    # Generate search metadata
    metadata = {
        'search_time': search_time,
        'total_results': len(results),
        'confidence_threshold': confidence_threshold,
        'avg_confidence': sum(r.confidence_score for r in results) / len(results) if results else 0,
        'high_confidence_count': sum(1 for r in results if r.confidence_score >= 0.7),
        'query_suggestions': []
    }
    
    # Add suggestions if results are low quality
    if not results or (results and results[0].confidence_score < 0.6):
        metadata['query_suggestions'] = [
            "Try being more specific in your query",
            "Include relevant section or article names",
            "Use formal legal terminology"
        ]
    
    return results, metadata
