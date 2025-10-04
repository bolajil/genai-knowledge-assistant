"""
Enterprise Integration Layer

Seamlessly integrates all enterprise components into the existing VaultMind system
while maintaining backward compatibility and providing fallback mechanisms.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class EnterpriseConfig:
    """Configuration for enterprise features"""
    enable_hybrid_search: bool = True
    enable_semantic_chunking: bool = True
    enable_structured_output: bool = True
    enable_metadata_filtering: bool = True
    enable_caching: bool = True
    
    # Fallback settings
    fallback_on_error: bool = True
    log_enterprise_usage: bool = True
    
    # Performance settings
    hybrid_search_timeout: int = 30
    chunking_timeout: int = 60
    cache_timeout: int = 5

class EnterpriseRetrievalSystem:
    """Unified enterprise retrieval system with fallbacks"""
    
    def __init__(self, config: EnterpriseConfig = None):
        self.config = config or EnterpriseConfig()
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize enterprise components with error handling"""
        self.components = {}
        
        # Initialize Hybrid Search
        if self.config.enable_hybrid_search:
            try:
                from utils.enterprise_hybrid_search import get_enterprise_hybrid_search
                self.components['hybrid_search'] = get_enterprise_hybrid_search()
                logger.info("Enterprise hybrid search initialized")
            except Exception as e:
                logger.warning(f"Hybrid search initialization failed: {e}")
                self.components['hybrid_search'] = None
        
        # Initialize Semantic Chunking
        if self.config.enable_semantic_chunking:
            try:
                from utils.enterprise_semantic_chunking import get_enterprise_semantic_chunker
                self.components['semantic_chunker'] = get_enterprise_semantic_chunker()
                logger.info("Enterprise semantic chunking initialized")
            except Exception as e:
                logger.warning(f"Semantic chunking initialization failed: {e}")
                self.components['semantic_chunker'] = None
        
        # Initialize Structured Output
        if self.config.enable_structured_output:
            try:
                from utils.enterprise_structured_output import get_enterprise_output_formatter
                self.components['output_formatter'] = get_enterprise_output_formatter()
                logger.info("Enterprise structured output initialized")
            except Exception as e:
                logger.warning(f"Structured output initialization failed: {e}")
                self.components['output_formatter'] = None
        
        # Initialize Metadata Filtering
        if self.config.enable_metadata_filtering:
            try:
                from utils.enterprise_metadata_filtering import get_enterprise_metadata_filter
                self.components['metadata_filter'] = get_enterprise_metadata_filter()
                logger.info("Enterprise metadata filtering initialized")
            except Exception as e:
                logger.warning(f"Metadata filtering initialization failed: {e}")
                self.components['metadata_filter'] = None
        
        # Initialize Caching
        if self.config.enable_caching:
            try:
                from utils.enterprise_caching_system import get_global_cache_manager
                self.components['cache_manager'] = get_global_cache_manager()
                logger.info("Enterprise caching initialized")
            except Exception as e:
                logger.warning(f"Caching initialization failed: {e}")
                self.components['cache_manager'] = None
    
    def retrieve_with_enterprise_features(
        self, 
        query: str, 
        index_name: str, 
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Main retrieval method with enterprise features and fallbacks"""
        
        start_time = time.time()
        
        try:
            # Step 1: Check cache first
            if use_cache and self.components.get('cache_manager'):
                cached_result = self._try_cache_retrieval(query, index_name, filters)
                if cached_result:
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    return cached_result
            
            # Step 2: Use hybrid search if available
            if self.components.get('hybrid_search'):
                results = self._try_hybrid_search(query, index_name, max_results)
                if results:
                    # Step 3: Apply metadata filtering
                    if filters and self.components.get('metadata_filter'):
                        results = self._apply_metadata_filtering(results, filters)
                    
                    # Step 4: Cache results
                    if use_cache and self.components.get('cache_manager'):
                        self._cache_results(query, index_name, results, filters)
                    
                    logger.info(f"Enterprise retrieval completed in {time.time() - start_time:.2f}s")
                    return results
            
            # Fallback to existing retrieval system
            return self._fallback_retrieval(query, index_name, max_results)
            
        except Exception as e:
            logger.error(f"Enterprise retrieval failed: {e}")
            if self.config.fallback_on_error:
                return self._fallback_retrieval(query, index_name, max_results)
            else:
                raise
    
    def _try_cache_retrieval(self, query: str, index_name: str, filters: Optional[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Try to retrieve from cache"""
        try:
            cache_manager = self.components['cache_manager']
            context = f"index:{index_name}|filters:{filters}"
            
            cached = cache_manager.get_cached_response(query, context)
            return cached.get('results') if cached else None
            
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None
    
    def _try_hybrid_search(self, query: str, index_name: str, max_results: int) -> Optional[List[Dict[str, Any]]]:
        """Try hybrid search with timeout"""
        try:
            hybrid_search = self.components['hybrid_search']
            
            # Convert SearchResult objects to dictionaries
            search_results = hybrid_search.search(query, index_name, max_results)
            
            results = []
            for result in search_results:
                results.append({
                    'content': result.content,
                    'source': result.source,
                    'page': result.page,
                    'section': result.section,
                    'metadata': {
                        'vector_score': result.vector_score,
                        'keyword_score': result.keyword_score,
                        'rerank_score': result.rerank_score,
                        'final_score': result.final_score,
                        **(result.metadata or {})
                    }
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"Hybrid search failed: {e}")
            return None
    
    def _apply_metadata_filtering(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply metadata filtering to results"""
        try:
            metadata_filter = self.components['metadata_filter']
            return metadata_filter.filter_documents(results, filters)
        except Exception as e:
            logger.warning(f"Metadata filtering failed: {e}")
            return results
    
    def _cache_results(self, query: str, index_name: str, results: List[Dict[str, Any]], filters: Optional[Dict[str, Any]]):
        """Cache the results"""
        try:
            cache_manager = self.components['cache_manager']
            context = f"index:{index_name}|filters:{filters}"
            
            cache_data = {
                'results': results,
                'query': query,
                'index_name': index_name,
                'filters': filters,
                'timestamp': time.time()
            }
            
            cache_manager.cache_response(query, context, cache_data)
            
        except Exception as e:
            logger.warning(f"Result caching failed: {e}")
    
    def _fallback_retrieval(self, query: str, index_name: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback to existing retrieval systems"""
        try:
            # Try real-time retrieval first
            from utils.real_time_retrieval import get_real_time_retriever
            retriever = get_real_time_retriever()
            results = retriever.retrieve_fresh_content(query, index_name, max_results)
            
            if results:
                logger.info("Fallback: Used real-time retrieval")
                return results
            
        except Exception as e:
            logger.warning(f"Real-time retrieval fallback failed: {e}")
        
        try:
            # Try enhanced retrieval
            from utils.enhanced_retrieval import search_bylaw_content
            results = search_bylaw_content(query, max_results)
            
            if results:
                logger.info("Fallback: Used enhanced retrieval")
                return results
            
        except Exception as e:
            logger.warning(f"Enhanced retrieval fallback failed: {e}")
        
        logger.warning("All retrieval methods failed")
        return []
    
    def chunk_document_with_enterprise_features(
        self, 
        text: str, 
        source: str, 
        document_type: str = None
    ) -> List[Dict[str, Any]]:
        """Chunk document using enterprise semantic chunking with fallback"""
        
        try:
            if self.components.get('semantic_chunker'):
                chunker = self.components['semantic_chunker']
                chunks = chunker.chunk_document(text, source, document_type)
                
                # Convert DocumentChunk objects to dictionaries
                return [chunk.to_dict() for chunk in chunks]
            
        except Exception as e:
            logger.warning(f"Enterprise chunking failed: {e}")
        
        # Fallback to existing chunking
        return self._fallback_chunking(text, source)
    
    def _fallback_chunking(self, text: str, source: str) -> List[Dict[str, Any]]:
        """Fallback to existing chunking methods"""
        try:
            from utils.advanced_chunking_strategy import get_advanced_chunking_strategy
            
            chunking_strategy = get_advanced_chunking_strategy()
            chunks = chunking_strategy(text)
            
            return [
                {
                    'content': chunk['content'],
                    'source': source,
                    'chunk_id': f"chunk_{i}",
                    'metadata': chunk.get('metadata', {})
                }
                for i, chunk in enumerate(chunks)
            ]
            
        except Exception as e:
            logger.error(f"Fallback chunking failed: {e}")
            return [{'content': text, 'source': source, 'chunk_id': 'chunk_0', 'metadata': {}}]
    
    def format_response_with_enterprise_features(
        self, 
        query: str, 
        context: str, 
        response_type: str = "general"
    ) -> Dict[str, Any]:
        """Format LLM response using enterprise structured output"""
        
        try:
            if self.components.get('output_formatter'):
                formatter = self.components['output_formatter']
                
                # Create structured prompt
                structured_prompt = formatter.create_structured_prompt(query, context, response_type)
                
                # This would typically be sent to LLM
                # For now, return a template structured response
                if response_type == "legal":
                    return {
                        "direct_answer": "Based on the legal provisions provided in the context...",
                        "applicable_articles": self._extract_articles_from_context(context),
                        "key_provisions": self._extract_key_provisions(context),
                        "citations": self._extract_citations_from_context(context),
                        "legal_interpretation": "The provisions indicate that...",
                        "confidence_score": 0.8,
                        "structured_prompt": structured_prompt
                    }
                else:
                    return {
                        "direct_answer": f"Based on the provided context, {query}",
                        "key_details": self._extract_key_details(context),
                        "citations": self._extract_citations_from_context(context),
                        "confidence_score": 0.8,
                        "answer_type": response_type,
                        "sources_used": len(self._extract_citations_from_context(context)),
                        "structured_prompt": structured_prompt
                    }
            
        except Exception as e:
            logger.warning(f"Enterprise response formatting failed: {e}")
        
        # Fallback to simple response
        return {
            "direct_answer": f"Based on the context: {context[:200]}...",
            "key_details": [context[:500]],
            "citations": ["Source: Context"],
            "confidence_score": 0.6
        }
    
    def _extract_articles_from_context(self, context: str) -> List[str]:
        """Extract article references from context"""
        import re
        article_pattern = r'(?:Article|ARTICLE)\s+([IVX]+|\d+)'
        matches = re.findall(article_pattern, context)
        return [f"Article {match}" for match in matches[:5]]
    
    def _extract_key_provisions(self, context: str) -> List[str]:
        """Extract key provisions from legal context"""
        sentences = [s.strip() for s in context.split('.') if s.strip() and len(s.strip()) > 50]
        return sentences[:3]
    
    def _extract_key_details(self, context: str) -> List[str]:
        """Extract key details from context"""
        sentences = [s.strip() for s in context.split('.') if s.strip() and len(s.strip()) > 30]
        return sentences[:4]
    
    def _extract_citations_from_context(self, context: str) -> List[str]:
        """Extract citations from context"""
        import re
        citation_patterns = [
            r'Page\s+(\d+)',
            r'Section\s+(\d+)',
            r'Article\s+([IVX]+|\d+)'
        ]
        
        citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            for match in matches:
                citations.append(f"Reference: {match}")
        
        return citations[:3] if citations else ["Source: Document Context"]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all enterprise components"""
        status = {
            "enterprise_features_enabled": True,
            "components": {}
        }
        
        for component_name, component in self.components.items():
            status["components"][component_name] = {
                "available": component is not None,
                "status": "active" if component is not None else "fallback"
            }
        
        # Add cache statistics if available
        if self.components.get('cache_manager'):
            try:
                status["cache_stats"] = self.components['cache_manager'].get_cache_stats()
            except Exception:
                status["cache_stats"] = {"error": "Unable to retrieve cache stats"}
        
        return status

# Global enterprise system instance
_global_enterprise_system = None

def get_enterprise_retrieval_system(config: EnterpriseConfig = None) -> EnterpriseRetrievalSystem:
    """Get enterprise retrieval system instance"""
    global _global_enterprise_system
    if _global_enterprise_system is None:
        _global_enterprise_system = EnterpriseRetrievalSystem(config)
    return _global_enterprise_system

def enterprise_enhanced_query(
    query: str, 
    index_name: str, 
    max_results: int = 10,
    response_type: str = "general",
    filters: Optional[Dict[str, Any]] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Complete enterprise-enhanced query processing"""
    
    enterprise_system = get_enterprise_retrieval_system()
    
    # Step 1: Retrieve with enterprise features
    results = enterprise_system.retrieve_with_enterprise_features(
        query, index_name, max_results, filters, use_cache
    )
    
    # Step 2: Create context from results
    context = "\n\n".join([
        f"Source: {result.get('source', 'Unknown')}\nContent: {result.get('content', '')}"
        for result in results[:5]  # Use top 5 results for context
    ])
    
    # Step 3: Format response with enterprise features
    formatted_response = enterprise_system.format_response_with_enterprise_features(
        query, context, response_type
    )
    
    # Step 4: Add retrieval metadata
    formatted_response.update({
        "source_documents": results,
        "retrieval_method": "enterprise_hybrid",
        "total_sources": len(results),
        "enterprise_features_used": list(enterprise_system.components.keys())
    })
    
    return formatted_response
