"""
Query-to-Content-Type Matching System
====================================
Matches user queries to appropriate content types and retrieval strategies.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class QueryType(Enum):
    PROCEDURAL = "procedural"  # How to do something
    DEFINITIONAL = "definitional"  # What is something
    REQUIREMENTS = "requirements"  # What's needed/required
    GOVERNANCE = "governance"  # Rules, regulations, compliance
    TECHNICAL = "technical"  # Technical specifications
    FULL_SECTION = "full_section"  # Complete section content

class ContentType(Enum):
    LEGAL_PROCEDURE = "legal_procedure"
    TECHNICAL_PROCEDURE = "technical_procedure"
    DEFINITION = "definition"
    REQUIREMENT_LIST = "requirement_list"
    GOVERNANCE_RULE = "governance_rule"
    COMPLETE_SECTION = "complete_section"

class QueryContentMatcher:
    """Match queries to appropriate content types and retrieval strategies."""
    
    def __init__(self):
        self.query_patterns = {
            QueryType.PROCEDURAL: [
                r'how\s+to\s+',
                r'procedures?\s+for',
                r'steps?\s+to',
                r'process\s+for',
                r'method\s+for',
                r'way\s+to',
            ],
            QueryType.DEFINITIONAL: [
                r'what\s+is\s+',
                r'define\s+',
                r'definition\s+of',
                r'meaning\s+of',
                r'explain\s+',
            ],
            QueryType.REQUIREMENTS: [
                r'requirements?\s+for',
                r'what\s+is\s+required',
                r'must\s+have',
                r'needed\s+for',
                r'necessary\s+for',
            ],
            QueryType.GOVERNANCE: [
                r'rules?\s+for',
                r'regulations?\s+for',
                r'policy\s+on',
                r'compliance\s+',
                r'governance\s+',
            ],
            QueryType.TECHNICAL: [
                r'configuration\s+',
                r'setup\s+',
                r'installation\s+',
                r'technical\s+',
                r'system\s+',
            ],
            QueryType.FULL_SECTION: [
                r'print\s+out',
                r'show\s+me\s+all',
                r'complete\s+section',
                r'full\s+text',
                r'entire\s+section',
            ]
        }
        
        self.content_strategies = {
            QueryType.PROCEDURAL: {
                'focus': 'step_by_step_content',
                'keywords': ['step', 'procedure', 'process', 'method'],
                'structure_priority': 'sequential',
                'min_content_length': 200
            },
            QueryType.DEFINITIONAL: {
                'focus': 'explanatory_content',
                'keywords': ['definition', 'meaning', 'explanation'],
                'structure_priority': 'conceptual',
                'min_content_length': 100
            },
            QueryType.REQUIREMENTS: {
                'focus': 'requirement_lists',
                'keywords': ['must', 'shall', 'required', 'mandatory'],
                'structure_priority': 'list_based',
                'min_content_length': 150
            },
            QueryType.GOVERNANCE: {
                'focus': 'rule_content',
                'keywords': ['rule', 'regulation', 'policy', 'compliance'],
                'structure_priority': 'hierarchical',
                'min_content_length': 200
            },
            QueryType.TECHNICAL: {
                'focus': 'technical_specifications',
                'keywords': ['configuration', 'setup', 'technical', 'system'],
                'structure_priority': 'structured',
                'min_content_length': 150
            },
            QueryType.FULL_SECTION: {
                'focus': 'complete_sections',
                'keywords': ['section', 'article', 'complete'],
                'structure_priority': 'comprehensive',
                'min_content_length': 500
            }
        }
    
    def analyze_query(self, query: str) -> Dict:
        """Analyze query to determine type and content strategy."""
        query_lower = query.lower()
        
        # Detect query type
        query_type = self._detect_query_type(query_lower)
        
        # Get content strategy
        strategy = self.content_strategies.get(query_type, self.content_strategies[QueryType.FULL_SECTION])
        
        # Extract key terms
        key_terms = self._extract_key_terms(query)
        
        # Determine content type
        content_type = self._map_to_content_type(query_type, key_terms)
        
        return {
            'query_type': query_type,
            'content_type': content_type,
            'strategy': strategy,
            'key_terms': key_terms,
            'retrieval_hints': self._generate_retrieval_hints(query_type, key_terms)
        }
    
    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of query based on patterns."""
        scores = {}
        
        for query_type, patterns in self.query_patterns.items():
            score = sum(1 for pattern in patterns if re.search(pattern, query, re.IGNORECASE))
            if score > 0:
                scores[query_type] = score
        
        if not scores:
            return QueryType.FULL_SECTION  # Default
        
        return max(scores, key=scores.get)
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from query."""
        # Remove common words and extract meaningful terms
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        key_terms = [word for word in words if word not in common_words]
        
        return key_terms[:10]  # Top 10 key terms
    
    def _map_to_content_type(self, query_type: QueryType, key_terms: List[str]) -> ContentType:
        """Map query type and terms to specific content type."""
        # Check for legal/governance terms
        legal_terms = {'board', 'director', 'bylaw', 'article', 'section', 'meeting', 'vote', 'quorum'}
        technical_terms = {'system', 'configuration', 'setup', 'installation', 'technical'}
        
        has_legal = any(term in legal_terms for term in key_terms)
        has_technical = any(term in technical_terms for term in key_terms)
        
        if query_type == QueryType.PROCEDURAL:
            return ContentType.LEGAL_PROCEDURE if has_legal else ContentType.TECHNICAL_PROCEDURE
        elif query_type == QueryType.DEFINITIONAL:
            return ContentType.DEFINITION
        elif query_type == QueryType.REQUIREMENTS:
            return ContentType.REQUIREMENT_LIST
        elif query_type == QueryType.GOVERNANCE:
            return ContentType.GOVERNANCE_RULE
        else:
            return ContentType.COMPLETE_SECTION
    
    def _generate_retrieval_hints(self, query_type: QueryType, key_terms: List[str]) -> Dict:
        """Generate hints for retrieval optimization."""
        hints = {
            'prioritize_sections': [],
            'content_filters': [],
            'structure_requirements': [],
            'quality_thresholds': {}
        }
        
        if query_type == QueryType.PROCEDURAL:
            hints['prioritize_sections'] = ['procedure', 'process', 'method', 'step']
            hints['content_filters'] = ['sequential_content', 'numbered_lists']
            hints['structure_requirements'] = ['preserve_order', 'include_steps']
            hints['quality_thresholds'] = {'min_words': 200, 'min_sentences': 5}
        
        elif query_type == QueryType.REQUIREMENTS:
            hints['prioritize_sections'] = ['requirement', 'mandatory', 'must', 'shall']
            hints['content_filters'] = ['requirement_lists', 'mandatory_content']
            hints['structure_requirements'] = ['preserve_lists', 'highlight_requirements']
            hints['quality_thresholds'] = {'min_words': 150, 'min_requirements': 3}
        
        elif query_type == QueryType.FULL_SECTION:
            hints['prioritize_sections'] = key_terms
            hints['content_filters'] = ['complete_sections', 'full_content']
            hints['structure_requirements'] = ['preserve_hierarchy', 'include_subsections']
            hints['quality_thresholds'] = {'min_words': 500, 'min_paragraphs': 3}
        
        return hints

def match_query_to_content_strategy(query: str) -> Dict:
    """
    Main function to match query to appropriate content retrieval strategy.
    """
    matcher = QueryContentMatcher()
    analysis = matcher.analyze_query(query)
    
    logger.info(f"Query analysis: {analysis['query_type'].value} -> {analysis['content_type'].value}")
    
    return analysis

def optimize_retrieval_for_query(query: str, chunks: List[Dict]) -> List[Dict]:
    """
    Optimize chunk selection and ranking based on query analysis.
    """
    analysis = match_query_to_content_strategy(query)
    strategy = analysis['strategy']
    hints = analysis['retrieval_hints']
    
    optimized_chunks = []
    
    for chunk in chunks:
        # Calculate optimization score
        score = chunk.get('confidence_score', 0.0)
        
        # Apply content-specific scoring
        content = chunk.get('content', '').lower()
        
        # Boost score for relevant keywords
        for keyword in strategy['keywords']:
            if keyword in content:
                score += 0.2
        
        # Apply minimum content length filter
        word_count = chunk.get('word_count', len(content.split()))
        if word_count >= strategy['min_content_length']:
            score += 0.1
        
        # Check quality thresholds
        quality_thresholds = hints['quality_thresholds']
        meets_quality = True
        
        for threshold_name, threshold_value in quality_thresholds.items():
            if threshold_name == 'min_words' and word_count < threshold_value:
                meets_quality = False
            elif threshold_name == 'min_sentences' and content.count('.') < threshold_value:
                meets_quality = False
        
        if meets_quality:
            chunk['optimization_score'] = score
            chunk['query_match_type'] = analysis['query_type'].value
            chunk['content_type'] = analysis['content_type'].value
            optimized_chunks.append(chunk)
    
    # Sort by optimization score
    optimized_chunks.sort(key=lambda x: x.get('optimization_score', 0), reverse=True)
    
    logger.info(f"Optimized {len(optimized_chunks)} chunks for {analysis['query_type'].value} query")
    
    return optimized_chunks

if __name__ == "__main__":
    # Test the matcher
    test_queries = [
        "Procedures for Board meetings and actions outside of meetings",
        "What is a quorum?",
        "Requirements for director elections",
        "Print out Section 2 about board meetings"
    ]
    
    for query in test_queries:
        analysis = match_query_to_content_strategy(query)
        print(f"\nQuery: {query}")
        print(f"Type: {analysis['query_type'].value}")
        print(f"Content: {analysis['content_type'].value}")
        print(f"Strategy: {analysis['strategy']['focus']}")
