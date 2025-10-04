"""
Example Integration of ML Models into VaultMind
Shows how to use all three models together in a real workflow
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EnhancedQueryProcessor:
    """
    Enhanced query processor using all ML models
    Demonstrates complete integration workflow
    """
    
    def __init__(self):
        """Initialize all ML models"""
        self.intent_classifier = None
        self.document_classifier = None
        self.quality_checker = None
        
        self._load_models()
    
    def _load_models(self):
        """Load ML models with fallback"""
        try:
            from utils.ml_models.query_intent_classifier import get_query_intent_classifier
            self.intent_classifier = get_query_intent_classifier()
            logger.info("✅ Intent classifier loaded")
        except Exception as e:
            logger.warning(f"Intent classifier not available: {e}")
        
        try:
            from utils.ml_models.document_classifier import get_document_classifier
            self.document_classifier = get_document_classifier()
            logger.info("✅ Document classifier loaded")
        except Exception as e:
            logger.warning(f"Document classifier not available: {e}")
        
        try:
            from utils.ml_models.data_quality_checker import get_data_quality_checker
            self.quality_checker = get_data_quality_checker()
            logger.info("✅ Quality checker loaded")
        except Exception as e:
            logger.warning(f"Quality checker not available: {e}")
    
    def process_query(self, query: str, index_name: str = "default") -> Dict:
        """
        Process query with intent classification
        
        Args:
            query: User query
            index_name: Index to search
            
        Returns:
            Enhanced query results with intent-based routing
        """
        # Step 1: Classify intent
        intent_result = self._classify_intent(query)
        
        # Step 2: Get retrieval strategy based on intent
        strategy = self._get_strategy(intent_result)
        
        # Step 3: Search with strategy
        results = self._search_documents(query, index_name, strategy)
        
        # Step 4: Format response based on intent
        response = self._format_response(query, results, intent_result)
        
        return {
            'query': query,
            'intent': intent_result,
            'strategy': strategy,
            'results': results,
            'response': response
        }
    
    def _classify_intent(self, query: str) -> Dict:
        """Classify query intent"""
        if self.intent_classifier is None:
            return {'intent': 'general', 'confidence': 0.0}
        
        try:
            return self.intent_classifier.classify_intent(query)
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return {'intent': 'general', 'confidence': 0.0}
    
    def _get_strategy(self, intent_result: Dict) -> Dict:
        """Get retrieval strategy based on intent"""
        if self.intent_classifier is None:
            return {'top_k': 5, 'search_type': 'semantic'}
        
        try:
            return self.intent_classifier.get_retrieval_strategy(intent_result['intent'])
        except Exception as e:
            logger.error(f"Strategy retrieval failed: {e}")
            return {'top_k': 5, 'search_type': 'semantic'}
    
    def _search_documents(self, query: str, index_name: str, strategy: Dict) -> List[Dict]:
        """Search documents using strategy"""
        # Use your existing search function
        try:
            from utils.query_helpers import query_index
            
            results = query_index(
                query=query,
                index_name=index_name,
                top_k=strategy.get('top_k', 5)
            )
            
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _format_response(self, query: str, results: List[Dict], intent_result: Dict) -> str:
        """Format response based on intent"""
        intent = intent_result.get('intent', 'general')
        
        if not results:
            return "No relevant information found."
        
        # Format based on intent
        if intent == 'factual':
            return self._format_factual(results)
        elif intent == 'analytical':
            return self._format_analytical(results)
        elif intent == 'procedural':
            return self._format_procedural(results)
        elif intent == 'comparative':
            return self._format_comparative(results)
        else:  # exploratory
            return self._format_exploratory(results)
    
    def _format_factual(self, results: List[Dict]) -> str:
        """Format concise factual answer"""
        top_result = results[0]
        content = top_result.get('content', '')
        
        # Extract first few sentences
        sentences = content.split('.')[:2]
        answer = '. '.join(sentences) + '.'
        
        return f"**Answer**: {answer}\n\n**Source**: {top_result.get('source', 'Unknown')}"
    
    def _format_analytical(self, results: List[Dict]) -> str:
        """Format detailed analytical answer"""
        response = "**Analysis**:\n\n"
        
        for i, result in enumerate(results[:3], 1):
            content = result.get('content', '')
            response += f"{i}. {content[:200]}...\n\n"
        
        response += "\n**Conclusion**: Based on the above information..."
        return response
    
    def _format_procedural(self, results: List[Dict]) -> str:
        """Format step-by-step answer"""
        response = "**Steps**:\n\n"
        
        for i, result in enumerate(results[:5], 1):
            content = result.get('content', '')
            response += f"**Step {i}**: {content[:150]}...\n\n"
        
        return response
    
    def _format_comparative(self, results: List[Dict]) -> str:
        """Format comparative answer"""
        response = "**Comparison**:\n\n"
        response += "| Aspect | Details |\n|--------|--------|\n"
        
        for result in results[:5]:
            content = result.get('content', '')[:100]
            response += f"| {result.get('source', 'Item')} | {content}... |\n"
        
        return response
    
    def _format_exploratory(self, results: List[Dict]) -> str:
        """Format comprehensive overview"""
        response = "**Overview**:\n\n"
        
        for i, result in enumerate(results[:7], 1):
            content = result.get('content', '')
            response += f"### {i}. {result.get('source', 'Section')}\n\n{content[:300]}...\n\n"
        
        return response


class EnhancedDocumentProcessor:
    """
    Enhanced document processor using ML models
    Demonstrates document ingestion with classification and quality checking
    """
    
    def __init__(self):
        """Initialize ML models"""
        self.document_classifier = None
        self.quality_checker = None
        
        self._load_models()
    
    def _load_models(self):
        """Load ML models"""
        try:
            from utils.ml_models.document_classifier import get_document_classifier
            self.document_classifier = get_document_classifier()
            logger.info("✅ Document classifier loaded")
        except Exception as e:
            logger.warning(f"Document classifier not available: {e}")
        
        try:
            from utils.ml_models.data_quality_checker import get_data_quality_checker
            self.quality_checker = get_data_quality_checker()
            logger.info("✅ Quality checker loaded")
        except Exception as e:
            logger.warning(f"Quality checker not available: {e}")
    
    def process_document(self, content: str, filename: str) -> Dict:
        """
        Process document with classification and quality checking
        
        Args:
            content: Document text
            filename: Document filename
            
        Returns:
            Processing results with classification and quality info
        """
        # Step 1: Classify document
        classification = self._classify_document(content)
        
        # Step 2: Check quality
        quality_result = self._check_quality(content)
        
        # Step 3: Decide whether to ingest
        should_ingest = self._should_ingest(quality_result)
        
        # Step 4: Prepare metadata
        metadata = self._prepare_metadata(
            filename,
            classification,
            quality_result
        )
        
        return {
            'filename': filename,
            'classification': classification,
            'quality': quality_result,
            'should_ingest': should_ingest,
            'metadata': metadata,
            'recommendation': self._get_recommendation(classification, quality_result)
        }
    
    def _classify_document(self, content: str) -> Dict:
        """Classify document category"""
        if self.document_classifier is None:
            return {'category': 'general', 'confidence': 0.0}
        
        try:
            return self.document_classifier.classify_document(content)
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return {'category': 'general', 'confidence': 0.0}
    
    def _check_quality(self, content: str) -> Dict:
        """Check document quality"""
        if self.quality_checker is None:
            return {'quality_score': 1.0, 'is_anomaly': False}
        
        try:
            # Generate embedding
            from utils.embedding_generator import generate_embeddings
            embedding = generate_embeddings([content])[0]
            
            return self.quality_checker.check_quality(embedding)
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return {'quality_score': 1.0, 'is_anomaly': False}
    
    def _should_ingest(self, quality_result: Dict) -> bool:
        """Decide whether to ingest document"""
        # Reject anomalies
        if quality_result.get('is_anomaly', False):
            return False
        
        # Reject very low quality
        if quality_result.get('quality_score', 1.0) < 0.3:
            return False
        
        return True
    
    def _prepare_metadata(self, filename: str, classification: Dict, quality: Dict) -> Dict:
        """Prepare enhanced metadata"""
        return {
            'filename': filename,
            'category': classification.get('category', 'general'),
            'classification_confidence': classification.get('confidence', 0.0),
            'keywords': classification.get('metadata', {}).get('keywords', []),
            'quality_score': quality.get('quality_score', 1.0),
            'quality_level': quality.get('quality_level', 'unknown'),
            'auto_classified': True,
            'quality_checked': True
        }
    
    def _get_recommendation(self, classification: Dict, quality: Dict) -> str:
        """Get processing recommendation"""
        if quality.get('is_anomaly', False):
            return "⚠️ Reject: Document appears corrupted or anomalous"
        
        if quality.get('quality_score', 1.0) < 0.3:
            return "⚠️ Reject: Very low quality document"
        
        if quality.get('quality_score', 1.0) < 0.5:
            return "⚠️ Review: Low quality - manual review recommended"
        
        if classification.get('confidence', 0.0) < 0.5:
            return "ℹ️ Accept: Low classification confidence - verify category"
        
        return f"✅ Accept: High quality {classification.get('category', 'general')} document"


# Example usage functions

def example_query_processing():
    """Example: Process a query with intent classification"""
    processor = EnhancedQueryProcessor()
    
    # Example queries
    queries = [
        "What is VaultMind?",
        "Why should I use vector databases?",
        "How to ingest documents?",
        "Compare Pinecone vs Weaviate",
        "Tell me about the system architecture"
    ]
    
    for query in queries:
        result = processor.process_query(query)
        
        print(f"\nQuery: {query}")
        print(f"Intent: {result['intent']['intent']} (confidence: {result['intent']['confidence']:.2%})")
        print(f"Strategy: top_k={result['strategy']['top_k']}, type={result['strategy']['search_type']}")
        print(f"Response: {result['response'][:100]}...")


def example_document_processing():
    """Example: Process a document with classification and quality checking"""
    processor = EnhancedDocumentProcessor()
    
    # Example documents
    documents = [
        ("contract.pdf", "This agreement is entered into between the parties. Terms and conditions apply."),
        ("manual.pdf", "Technical specifications and API documentation for the system."),
        ("report.pdf", "Quarterly financial report with revenue and expense analysis.")
    ]
    
    for filename, content in documents:
        result = processor.process_document(content, filename)
        
        print(f"\nDocument: {filename}")
        print(f"Category: {result['classification']['category']} (confidence: {result['classification']['confidence']:.2%})")
        print(f"Quality: {result['quality']['quality_level']} (score: {result['quality']['quality_score']:.2%})")
        print(f"Recommendation: {result['recommendation']}")


if __name__ == "__main__":
    print("=" * 60)
    print("VaultMind ML Models - Integration Examples")
    print("=" * 60)
    
    print("\n### Query Processing Example ###")
    example_query_processing()
    
    print("\n\n### Document Processing Example ###")
    example_document_processing()
