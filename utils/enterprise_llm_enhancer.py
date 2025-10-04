"""
Enterprise LLM Response Enhancer

Advanced LLM response enhancement system that eliminates vague responses
and ensures enterprise-grade quality and comprehensiveness.
"""

import os
import re
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnterpriseResponseEnhancer:
    """Enterprise-grade LLM response enhancement system"""
    
    def __init__(self):
        self.quality_thresholds = {
            'min_word_count': 150,
            'min_sentences': 5,
            'min_specificity_score': 0.7,
            'max_vagueness_score': 0.3
        }
        
        self.vague_indicators = [
            'might', 'could', 'possibly', 'perhaps', 'maybe', 'generally',
            'usually', 'often', 'sometimes', 'appears to', 'seems to',
            'may be', 'it is possible', 'in some cases', 'typically'
        ]
        
        self.specificity_boosters = [
            'specifically', 'exactly', 'precisely', 'according to',
            'as stated in', 'the document specifies', 'clearly indicates',
            'explicitly states', 'section', 'article', 'paragraph'
        ]
    
    def enhance_prompt(self, original_query: str, context_documents: List[Dict]) -> str:
        """Create an enhanced prompt that demands specific, detailed responses"""
        
        # Analyze context to understand document structure
        doc_analysis = self._analyze_documents(context_documents)
        
        enhanced_prompt = f"""
You are an expert enterprise document analyst. Provide a comprehensive, detailed analysis based EXCLUSIVELY on the provided documents.

CRITICAL REQUIREMENTS:
1. NO VAGUE LANGUAGE - Use specific facts, exact quotes, and precise references
2. CITE SPECIFIC SECTIONS - Always reference exact pages, articles, or sections
3. COMPREHENSIVE COVERAGE - Address all relevant aspects found in the documents
4. STRUCTURED RESPONSE - Use clear headings and bullet points for organization
5. QUANTITATIVE DETAILS - Include specific numbers, dates, percentages when available

DOCUMENT CONTEXT:
{doc_analysis['summary']}

ORIGINAL QUERY: {original_query}

RESPONSE STRUCTURE REQUIRED:
## Executive Summary
[2-3 sentences with key findings]

## Detailed Analysis
[Comprehensive analysis with specific references]

## Key Provisions/Requirements
[Bulleted list of specific items with section references]

## Relevant Sections
[Direct quotes from relevant document sections]

## Compliance/Implementation Notes
[Specific actionable information]

REMEMBER: Every statement must be backed by specific document references. Use phrases like:
- "According to Section X.Y..."
- "As specified in Article Z..."
- "The document explicitly states in paragraph..."
- "Page X clearly indicates..."

Provide a response that demonstrates deep understanding and leaves no ambiguity.
"""
        
        return enhanced_prompt
    
    def _analyze_documents(self, documents: List[Dict]) -> Dict[str, Any]:
        """Analyze document structure and content for better prompting"""
        analysis = {
            'total_documents': len(documents),
            'pages_covered': set(),
            'sections_found': [],
            'document_types': set(),
            'key_topics': [],
            'summary': ""
        }
        
        for doc in documents:
            if doc.get('page'):
                analysis['pages_covered'].add(doc['page'])
            
            if doc.get('section'):
                analysis['sections_found'].append(doc['section'])
            
            if doc.get('source'):
                analysis['document_types'].add(doc['source'])
        
        # Create summary
        pages_str = f"Pages {min(analysis['pages_covered'])}-{max(analysis['pages_covered'])}" if analysis['pages_covered'] else "Multiple sections"
        sections_str = f"Including sections: {', '.join(analysis['sections_found'][:3])}" if analysis['sections_found'] else ""
        
        analysis['summary'] = f"Analyzing {analysis['total_documents']} document segments from {pages_str}. {sections_str}"
        
        return analysis
    
    def enhance_response(self, response: str, context_documents: List[Dict]) -> str:
        """Enhance LLM response to meet enterprise standards"""
        
        # Check response quality
        quality_score = self._assess_response_quality(response)
        
        if quality_score < 0.7:
            # Response needs enhancement
            enhanced_response = self._apply_enhancements(response, context_documents)
            return enhanced_response
        
        return response
    
    def _assess_response_quality(self, response: str) -> float:
        """Assess response quality based on enterprise standards"""
        score = 0.0
        
        # Word count check
        word_count = len(response.split())
        if word_count >= self.quality_thresholds['min_word_count']:
            score += 0.2
        
        # Sentence count check
        sentence_count = len([s for s in response.split('.') if s.strip()])
        if sentence_count >= self.quality_thresholds['min_sentences']:
            score += 0.2
        
        # Specificity check
        specificity_score = self._calculate_specificity(response)
        score += specificity_score * 0.3
        
        # Vagueness penalty
        vagueness_score = self._calculate_vagueness(response)
        score += (1 - vagueness_score) * 0.3
        
        return score
    
    def _calculate_specificity(self, text: str) -> float:
        """Calculate how specific the response is"""
        text_lower = text.lower()
        
        specificity_indicators = 0
        total_words = len(text.split())
        
        # Count specific indicators
        for indicator in self.specificity_boosters:
            specificity_indicators += text_lower.count(indicator)
        
        # Count section/page references
        section_refs = len(re.findall(r'(section|article|page|paragraph)\s+\w+', text_lower))
        specificity_indicators += section_refs * 2  # Higher weight for references
        
        # Count numbers and dates
        numbers = len(re.findall(r'\b\d+\b', text))
        specificity_indicators += numbers * 0.5
        
        return min(specificity_indicators / max(total_words * 0.1, 1), 1.0)
    
    def _calculate_vagueness(self, text: str) -> float:
        """Calculate vagueness score (lower is better)"""
        text_lower = text.lower()
        total_words = len(text.split())
        
        vague_count = 0
        for indicator in self.vague_indicators:
            vague_count += text_lower.count(indicator)
        
        return min(vague_count / max(total_words * 0.05, 1), 1.0)
    
    def _apply_enhancements(self, response: str, context_documents: List[Dict]) -> str:
        """Apply enhancements to improve response quality"""
        
        enhanced_response = f"""
## Enhanced Enterprise Analysis

{response}

## Additional Context and Specifications

Based on the comprehensive document analysis, here are additional specific details:

"""
        
        # Add specific document references
        for doc in context_documents[:3]:  # Top 3 most relevant
            if doc.get('section') and doc.get('page'):
                enhanced_response += f"**{doc['section']} (Page {doc['page']})**: "
                enhanced_response += f"{doc['content'][:200]}...\n\n"
        
        enhanced_response += """
## Compliance and Implementation Guidelines

For enterprise implementation, ensure:
- All referenced sections are reviewed in full context
- Legal compliance requirements are verified with appropriate counsel
- Implementation timelines account for all specified procedures
- Stakeholder notifications follow documented requirements

*This analysis is based on specific document content and provides actionable, enterprise-grade guidance.*
"""
        
        return enhanced_response
    
    def create_comprehensive_response(self, query: str, search_results: List[Dict]) -> str:
        """Create a comprehensive response from search results"""
        
        if not search_results:
            return "No relevant information found in the document index. Please verify the query or check if documents have been properly ingested."
        
        # Sort results by relevance
        sorted_results = sorted(search_results, key=lambda x: x.get('relevance', 0), reverse=True)
        
        response = f"## Comprehensive Analysis: {query}\n\n"
        
        # Executive summary from top result
        top_result = sorted_results[0]
        response += f"**Executive Summary**: Based on {top_result.get('source', 'the document')}"
        if top_result.get('page'):
            response += f" (Page {top_result['page']})"
        if top_result.get('section'):
            response += f", specifically {top_result['section']}"
        response += f": {top_result['content'][:300]}...\n\n"
        
        # Detailed findings
        response += "## Detailed Findings\n\n"
        
        for i, result in enumerate(sorted_results[:5], 1):
            response += f"### Finding {i}: "
            if result.get('section'):
                response += f"{result['section']}"
            else:
                response += f"Document Section {i}"
            
            if result.get('page'):
                response += f" (Page {result['page']})"
            
            response += f" - Relevance: {result.get('relevance', 0):.2f}\n\n"
            response += f"{result['content']}\n\n"
            
            if result.get('context'):
                response += f"**Additional Context**: {result['context'][:200]}...\n\n"
        
        # Summary and recommendations
        response += "## Key Takeaways\n\n"
        response += "Based on the comprehensive document analysis:\n"
        
        # Extract key points from all results
        key_points = []
        for result in sorted_results[:3]:
            content = result['content']
            # Extract sentences that seem like key points
            sentences = content.split('.')
            for sentence in sentences:
                if len(sentence.strip()) > 50 and any(word in sentence.lower() for word in ['must', 'shall', 'required', 'responsibility', 'authority']):
                    key_points.append(sentence.strip())
        
        for i, point in enumerate(key_points[:5], 1):
            response += f"{i}. {point}.\n"
        
        response += f"\n*Analysis based on {len(sorted_results)} relevant document sections with comprehensive context.*"
        
        return response

# Singleton instance
_enhancer_instance = None

def get_enterprise_enhancer() -> EnterpriseResponseEnhancer:
    """Get singleton enterprise response enhancer"""
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = EnterpriseResponseEnhancer()
    return _enhancer_instance
