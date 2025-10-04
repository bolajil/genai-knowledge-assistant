"""
Advanced Re-Ranker with Confidence Threshold

Implements sophisticated re-ranking with confidence filtering to eliminate irrelevant results
and improve retrieval precision for vague queries.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RankedResult:
    """Result with comprehensive ranking scores"""
    content: str
    source: str
    page: Optional[str] = None
    section: Optional[str] = None
    
    # Scoring components
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    rerank_score: float = 0.0
    relevance_score: float = 0.0
    confidence_score: float = 0.0
    
    # Metadata
    query_match: str = ""
    rank_position: int = 0
    metadata: Dict[str, Any] = None

class AdvancedReranker:
    """Advanced re-ranking system with multiple scoring mechanisms"""
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.cross_encoder = None
        self.semantic_scorer = None
        
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize re-ranking models"""
        try:
            from utils.enterprise_hybrid_search import CrossEncoderReranker
            self.cross_encoder = CrossEncoderReranker()
            logger.info("Cross-encoder re-ranker initialized")
        except Exception as e:
            logger.warning(f"Cross-encoder initialization failed: {e}")
        
        try:
            # Initialize semantic similarity scorer if available
            from sentence_transformers import SentenceTransformer
            self.semantic_scorer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Semantic similarity scorer initialized")
        except Exception as e:
            logger.warning(f"Semantic scorer initialization failed: {e}")
    
    def rerank_with_confidence_threshold(
        self, 
        query: str, 
        results: List[Dict[str, Any]], 
        threshold: float = None
    ) -> Tuple[List[RankedResult], Dict[str, Any]]:
        """
        Re-rank results with confidence threshold filtering
        
        Args:
            query: Original user query
            results: List of search results to re-rank
            threshold: Confidence threshold (uses instance default if None)
            
        Returns:
            Tuple of (filtered_results, ranking_metadata)
        """
        if not results:
            return [], {"error": "No results to re-rank"}
        
        threshold = threshold or self.confidence_threshold
        
        try:
            # Step 1: Calculate multiple scoring signals
            scored_results = self._calculate_comprehensive_scores(query, results)
            
            # Step 2: Apply cross-encoder re-ranking if available
            if self.cross_encoder:
                scored_results = self._apply_cross_encoder_reranking(query, scored_results)
            
            # Step 3: Calculate final confidence scores
            scored_results = self._calculate_final_confidence(query, scored_results)
            
            # Step 4: Apply confidence threshold
            filtered_results = self._apply_confidence_filter(scored_results, threshold)
            
            # Step 5: Generate ranking metadata
            ranking_metadata = self._generate_ranking_metadata(
                query, results, scored_results, filtered_results, threshold
            )
            
            return filtered_results, ranking_metadata
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            return self._fallback_ranking(results), {"error": str(e)}
    
    def _calculate_comprehensive_scores(self, query: str, results: List[Dict[str, Any]]) -> List[RankedResult]:
        """Calculate multiple scoring signals for each result"""
        scored_results = []
        
        for i, result in enumerate(results):
            content = result.get('content', '')
            
            # Calculate keyword relevance score
            keyword_score = self._calculate_keyword_relevance(query, content)
            
            # Calculate semantic similarity if available
            semantic_score = self._calculate_semantic_similarity(query, content)
            
            # Calculate content quality score
            quality_score = self._calculate_content_quality(content)
            
            # Calculate source credibility score
            credibility_score = self._calculate_source_credibility(result.get('source', ''))
            
            # Create ranked result
            ranked_result = RankedResult(
                content=content,
                source=result.get('source', ''),
                page=result.get('page'),
                section=result.get('section'),
                semantic_score=semantic_score,
                keyword_score=keyword_score,
                relevance_score=(keyword_score + semantic_score) / 2,
                query_match=result.get('query_match', query),
                rank_position=i,
                metadata={
                    'quality_score': quality_score,
                    'credibility_score': credibility_score,
                    'original_metadata': result.get('metadata', {})
                }
            )
            
            scored_results.append(ranked_result)
        
        return scored_results
    
    def _calculate_keyword_relevance(self, query: str, content: str) -> float:
        """Calculate keyword-based relevance score"""
        try:
            query_words = set(re.findall(r'\b\w+\b', query.lower()))
            content_words = set(re.findall(r'\b\w+\b', content.lower()))
            
            if not query_words:
                return 0.0
            
            # Calculate exact matches
            exact_matches = len(query_words & content_words)
            exact_score = exact_matches / len(query_words)
            
            # Calculate partial matches (stemming-like)
            partial_matches = 0
            for q_word in query_words:
                for c_word in content_words:
                    if len(q_word) > 3 and len(c_word) > 3:
                        if q_word[:4] == c_word[:4] or c_word[:4] == q_word[:4]:
                            partial_matches += 0.5
                            break
            
            partial_score = min(partial_matches / len(query_words), 0.5)
            
            return min(1.0, exact_score + partial_score)
            
        except Exception as e:
            logger.error(f"Keyword relevance calculation failed: {e}")
            return 0.0
    
    def _calculate_semantic_similarity(self, query: str, content: str) -> float:
        """Calculate semantic similarity score"""
        if not self.semantic_scorer:
            return 0.0
        
        try:
            # Encode query and content
            query_embedding = self.semantic_scorer.encode([query])
            content_embedding = self.semantic_scorer.encode([content[:512]])  # Limit content length
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity(query_embedding, content_embedding)[0][0]
            
            return max(0.0, float(similarity))
            
        except Exception as e:
            logger.error(f"Semantic similarity calculation failed: {e}")
            return 0.0
    
    def _calculate_content_quality(self, content: str) -> float:
        """Calculate content quality score based on various factors"""
        try:
            quality_score = 0.5  # Base score
            
            # Length factor (prefer substantial content)
            if len(content) > 200:
                quality_score += 0.2
            if len(content) > 500:
                quality_score += 0.1
            
            # Structure factor (prefer structured content)
            if any(indicator in content.lower() for indicator in ['article', 'section', 'paragraph']):
                quality_score += 0.1
            
            # Completeness factor (prefer complete sentences)
            sentences = content.split('.')
            complete_sentences = sum(1 for s in sentences if len(s.strip()) > 20)
            if complete_sentences >= 2:
                quality_score += 0.1
            
            return min(1.0, quality_score)
            
        except Exception as e:
            logger.error(f"Content quality calculation failed: {e}")
            return 0.5
    
    def _calculate_source_credibility(self, source: str) -> float:
        """Calculate source credibility score"""
        try:
            credibility = 0.5  # Base credibility
            
            # Prefer specific page/section references
            if re.search(r'page\s+\d+', source.lower()):
                credibility += 0.2
            if re.search(r'article\s+[ivx]+', source.lower()):
                credibility += 0.2
            if re.search(r'section\s+\d+', source.lower()):
                credibility += 0.1
            
            return min(1.0, credibility)
            
        except Exception as e:
            logger.error(f"Source credibility calculation failed: {e}")
            return 0.5
    
    def _apply_cross_encoder_reranking(self, query: str, results: List[RankedResult]) -> List[RankedResult]:
        """Apply cross-encoder re-ranking"""
        try:
            # Convert to format expected by cross-encoder
            search_results = []
            for result in results:
                search_result = type('SearchResult', (), {
                    'content': result.content,
                    'vector_score': result.semantic_score,
                    'keyword_score': result.keyword_score,
                    'rerank_score': 0.0,
                    'metadata': result.metadata
                })()
                search_results.append(search_result)
            
            # Apply re-ranking
            reranked = self.cross_encoder.rerank(query, search_results, len(search_results))
            
            # Update rerank scores
            for i, result in enumerate(results):
                if i < len(reranked):
                    result.rerank_score = getattr(reranked[i], 'rerank_score', 0.0)
            
            return results
            
        except Exception as e:
            logger.error(f"Cross-encoder re-ranking failed: {e}")
            return results
    
    def _calculate_final_confidence(self, query: str, results: List[RankedResult]) -> List[RankedResult]:
        """Calculate final confidence scores"""
        for result in results:
            # Weighted combination of all scores
            confidence = (
                result.semantic_score * 0.25 +
                result.keyword_score * 0.25 +
                result.rerank_score * 0.3 +
                result.relevance_score * 0.2
            )
            
            # Apply quality and credibility boosts
            quality_boost = result.metadata.get('quality_score', 0.5) * 0.1
            credibility_boost = result.metadata.get('credibility_score', 0.5) * 0.05
            
            result.confidence_score = min(1.0, confidence + quality_boost + credibility_boost)
        
        # Sort by confidence score
        results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Update rank positions
        for i, result in enumerate(results):
            result.rank_position = i + 1
        
        return results
    
    def _apply_confidence_filter(self, results: List[RankedResult], threshold: float) -> List[RankedResult]:
        """Filter results by confidence threshold"""
        high_confidence = [r for r in results if r.confidence_score >= threshold]
        
        if not high_confidence and results:
            # If no results meet threshold, check if top result is reasonably close
            top_result = results[0]
            if top_result.confidence_score >= threshold - 0.2:  # Allow 0.2 tolerance
                logger.warning(f"No results above threshold {threshold}, returning top result with confidence {top_result.confidence_score:.2f}")
                top_result.metadata['below_threshold_warning'] = True
                return [top_result]
            else:
                logger.warning(f"Top result confidence {top_result.confidence_score:.2f} too low for threshold {threshold}")
                return []
        
        return high_confidence
    
    def _generate_ranking_metadata(
        self, 
        query: str, 
        original_results: List[Dict[str, Any]], 
        scored_results: List[RankedResult], 
        filtered_results: List[RankedResult], 
        threshold: float
    ) -> Dict[str, Any]:
        """Generate comprehensive ranking metadata"""
        
        metadata = {
            'query': query,
            'threshold': threshold,
            'original_count': len(original_results),
            'scored_count': len(scored_results),
            'filtered_count': len(filtered_results),
            'avg_confidence': sum(r.confidence_score for r in scored_results) / len(scored_results) if scored_results else 0,
            'max_confidence': max(r.confidence_score for r in scored_results) if scored_results else 0,
            'min_confidence': min(r.confidence_score for r in scored_results) if scored_results else 0,
            'cross_encoder_used': self.cross_encoder is not None,
            'semantic_scorer_used': self.semantic_scorer is not None
        }
        
        # Add confidence distribution
        if scored_results:
            high_conf = sum(1 for r in scored_results if r.confidence_score >= 0.8)
            med_conf = sum(1 for r in scored_results if 0.5 <= r.confidence_score < 0.8)
            low_conf = sum(1 for r in scored_results if r.confidence_score < 0.5)
            
            metadata['confidence_distribution'] = {
                'high_confidence': high_conf,
                'medium_confidence': med_conf,
                'low_confidence': low_conf
            }
        
        # Add suggestions if results are poor
        if not filtered_results or (filtered_results and filtered_results[0].confidence_score < 0.6):
            metadata['suggestions'] = self._generate_improvement_suggestions(query, scored_results)
        
        return metadata
    
    def _generate_improvement_suggestions(self, query: str, results: List[RankedResult]) -> List[str]:
        """Generate suggestions for improving query results"""
        suggestions = []
        
        # Analyze why results are poor
        if not results:
            suggestions.append("No relevant documents found. Try using different keywords.")
        else:
            top_result = results[0]
            
            if top_result.keyword_score < 0.3:
                suggestions.append("Try using more specific keywords that appear in the documents.")
            
            if top_result.semantic_score < 0.4:
                suggestions.append("Try rephrasing your query using formal legal terminology.")
            
            # Query-specific suggestions
            if "powers" in query.lower():
                suggestions.append("Try: 'Powers of the Board of Directors' or 'Authority and duties of officers'")
            elif "meeting" in query.lower():
                suggestions.append("Try: 'Board meeting requirements' or 'Meeting procedures and protocols'")
            elif len(query.split()) <= 2:
                suggestions.append("Try using a more detailed query with additional context.")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _fallback_ranking(self, results: List[Dict[str, Any]]) -> List[RankedResult]:
        """Fallback ranking when advanced re-ranking fails"""
        fallback_results = []
        
        for i, result in enumerate(results):
            fallback_result = RankedResult(
                content=result.get('content', ''),
                source=result.get('source', ''),
                page=result.get('page'),
                section=result.get('section'),
                confidence_score=0.4,  # Low confidence for fallback
                rank_position=i + 1,
                metadata={'fallback_ranking': True}
            )
            fallback_results.append(fallback_result)
        
        return fallback_results

def get_advanced_reranker(confidence_threshold: float = 0.7) -> AdvancedReranker:
    """Get advanced re-ranker instance"""
    return AdvancedReranker(confidence_threshold)

def rerank_documents_with_threshold(
    query: str, 
    results: List[Dict[str, Any]], 
    threshold: float = 0.7
) -> Tuple[List[RankedResult], Dict[str, Any]]:
    """
    Convenience function to re-rank documents with confidence threshold
    
    Returns:
        Tuple of (filtered_results, ranking_metadata)
    """
    reranker = get_advanced_reranker(threshold)
    return reranker.rerank_with_confidence_threshold(query, results, threshold)
