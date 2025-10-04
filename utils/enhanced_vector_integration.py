"""
Enhanced Vector Integration for All Tabs

Universal integration layer that provides granular section retrieval
across all tabs using vector database with same embeddings.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class EnhancedVectorIntegration:
    """
    Universal integration for detailed section retrieval across all tabs
    """
    
    def __init__(self):
        """Initialize the enhanced vector integration"""
        self.supported_tabs = [
            'query_assistant',
            'chat_assistant', 
            'agent_assistant_enhanced',
            'multi_content_enhanced',
            'enhanced_research'
        ]
    
    def get_detailed_response(self, query: str, index_name: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Get detailed response with granular section extraction for any tab
        
        Args:
            query: User query
            index_name: Index to search
            max_results: Maximum results to return
            
        Returns:
            Enhanced response with detailed sections
        """
        try:
            # Use comprehensive document retrieval with section extraction
            from utils.comprehensive_document_retrieval import retrieve_comprehensive_information
            
            logger.info(f"Enhanced vector integration for query: '{query}' in index: '{index_name}'")
            
            # Get comprehensive results with detailed sections
            comprehensive_results = retrieve_comprehensive_information(query, index_name, max_results)
            
            if comprehensive_results:
                # Check if detailed extraction was used
                has_detailed_extraction = any(
                    result.get('metadata', {}).get('detailed_extraction', False) 
                    for result in comprehensive_results
                )
                
                # Build enhanced context
                context_sections = []
                source_documents = []
                
                for result in comprehensive_results:
                    # Format for context
                    section_text = f"**{result.get('section', 'Section')}** (Page {result.get('page', 'N/A')})\n{result.get('content', '')}"
                    context_sections.append(section_text)
                    
                    # Format for source documents
                    source_documents.append({
                        'page_content': result.get('content', ''),
                        'metadata': {
                            'source': result.get('source', f'{index_name}/extracted_text.txt'),
                            'page': result.get('page', 'N/A'),
                            'section': result.get('section', 'N/A'),
                            'confidence_score': result.get('confidence_score', 0.0),
                            'section_type': result.get('metadata', {}).get('section_type', 'general'),
                            'word_count': result.get('metadata', {}).get('word_count', 0),
                            'has_procedures': result.get('metadata', {}).get('has_procedures', False),
                            'has_requirements': result.get('metadata', {}).get('has_requirements', False),
                            'detailed_extraction': has_detailed_extraction
                        }
                    })
                
                return {
                    'success': True,
                    'results': comprehensive_results,
                    'context_text': '\n\n'.join(context_sections),
                    'source_documents': source_documents,
                    'retrieval_method': 'enhanced_detailed' if has_detailed_extraction else 'comprehensive',
                    'total_results': len(comprehensive_results)
                }
            
            else:
                return {
                    'success': False,
                    'error': f'No relevant content found in index: {index_name}',
                    'results': [],
                    'source_documents': []
                }
                
        except Exception as e:
            logger.error(f"Enhanced vector integration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'source_documents': []
            }
    
    def create_enhanced_prompt(self, query: str, context_text: str, query_type: str = 'general') -> str:
        """
        Create enhanced prompt based on query type and context
        
        Args:
            query: User query
            context_text: Retrieved context
            query_type: Type of query ('procedures', 'requirements', 'definitions', etc.)
            
        Returns:
            Enhanced prompt for LLM
        """
        
        base_instruction = "Based on the following detailed document sections, provide a comprehensive answer to the user's question."
        
        if 'procedure' in query.lower() or 'how to' in query.lower():
            specific_instruction = "Focus on step-by-step procedures and processes. Include all relevant requirements and guidelines."
        elif 'requirement' in query.lower() or 'must' in query.lower():
            specific_instruction = "Focus on specific requirements, obligations, and compliance details. Highlight what is mandatory vs optional."
        elif 'definition' in query.lower() or 'what is' in query.lower():
            specific_instruction = "Provide clear definitions and explanations. Include context and examples where available."
        elif 'print out' in query.lower() or 'show me' in query.lower():
            specific_instruction = "Provide the complete, detailed content as requested. Include all relevant text and formatting."
        else:
            specific_instruction = "Provide detailed, accurate information addressing all aspects of the question."
        
        return f"""{base_instruction}

{specific_instruction}

User Question: {query}

Document Sections:
{context_text}

Please provide a detailed response based solely on the document content above. Include specific references to sections and pages where relevant. Ensure your answer is comprehensive and actionable."""

    def format_response_for_tab(self, response_data: Dict[str, Any], tab_name: str) -> Dict[str, Any]:
        """
        Format response appropriately for specific tab
        
        Args:
            response_data: Raw response data
            tab_name: Name of the requesting tab
            
        Returns:
            Formatted response for the specific tab
        """
        
        if not response_data.get('success', False):
            return response_data
        
        # Tab-specific formatting
        if tab_name == 'query_assistant':
            return {
                'comprehensive_results': response_data['results'],
                'source_documents': response_data['source_documents'],
                'context_text': response_data['context_text'],
                'retrieval_method': response_data['retrieval_method']
            }
        
        elif tab_name == 'chat_assistant':
            return {
                'context_text': response_data['context_text'],
                'source_documents': response_data['source_documents'],
                'enhanced_context': True
            }
        
        elif tab_name == 'agent_assistant_enhanced':
            return {
                'result': response_data.get('llm_response', ''),
                'source_documents': response_data['source_documents'],
                'retrieval_method': response_data['retrieval_method'],
                'enhanced_features_used': ['detailed_section_extraction', 'granular_retrieval']
            }
        
        elif tab_name in ['multi_content_enhanced', 'enhanced_research']:
            return {
                'results': response_data['results'],
                'enhanced_context': response_data['context_text'],
                'source_metadata': [doc['metadata'] for doc in response_data['source_documents']],
                'retrieval_quality': 'enhanced'
            }
        
        else:
            # Generic format for other tabs
            return response_data

# Global instance
_enhanced_integration = None

def get_enhanced_vector_integration() -> EnhancedVectorIntegration:
    """Get the global enhanced vector integration instance"""
    global _enhanced_integration
    if _enhanced_integration is None:
        _enhanced_integration = EnhancedVectorIntegration()
    return _enhanced_integration

def get_detailed_response_for_tab(query: str, index_name: str, tab_name: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Convenience function to get detailed response for any tab
    
    Args:
        query: User query
        index_name: Index to search
        tab_name: Name of requesting tab
        max_results: Maximum results to return
        
    Returns:
        Tab-specific formatted response with detailed sections
    """
    integration = get_enhanced_vector_integration()
    
    # Get detailed response
    response_data = integration.get_detailed_response(query, index_name, max_results)
    
    # Format for specific tab
    return integration.format_response_for_tab(response_data, tab_name)

def create_enhanced_llm_prompt(query: str, context_text: str, query_type: str = 'general') -> str:
    """
    Convenience function to create enhanced LLM prompt
    
    Args:
        query: User query
        context_text: Retrieved context
        query_type: Type of query
        
    Returns:
        Enhanced prompt for LLM processing
    """
    integration = get_enhanced_vector_integration()
    return integration.create_enhanced_prompt(query, context_text, query_type)
