"""
Query Complexity Analyzer
Determines whether a query should use LangGraph (complex) or fast retrieval (simple)
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"           # Direct lookup, single concept
    MODERATE = "moderate"       # Multiple concepts, basic comparison
    COMPLEX = "complex"         # Multi-step reasoning, analysis required
    VERY_COMPLEX = "very_complex"  # Deep analysis, multiple documents, synthesis


@dataclass
class ComplexityAnalysis:
    """Result of complexity analysis"""
    complexity: QueryComplexity
    score: float  # 0-100
    reasoning: str
    indicators: Dict[str, bool]
    recommended_approach: str  # "fast" or "langgraph"
    

class QueryComplexityAnalyzer:
    """Analyzes query complexity to route between fast retrieval and LangGraph"""
    
    # Complexity indicators
    COMPARISON_WORDS = [
        'compare', 'contrast', 'difference', 'versus', 'vs', 'better', 'worse',
        'similar', 'dissimilar', 'alike', 'unlike'
    ]
    
    ANALYSIS_WORDS = [
        'analyze', 'evaluate', 'assess', 'examine', 'investigate', 'study',
        'explain why', 'how does', 'what causes', 'implications', 'impact'
    ]
    
    SYNTHESIS_WORDS = [
        'summarize', 'synthesize', 'integrate', 'combine', 'overall',
        'comprehensive', 'complete picture', 'all information'
    ]
    
    REASONING_WORDS = [
        'recommend', 'suggest', 'advise', 'should', 'best approach',
        'strategy', 'plan', 'solution', 'resolve'
    ]
    
    MULTI_STEP_INDICATORS = [
        'first', 'then', 'next', 'finally', 'step by step',
        'process', 'procedure', 'workflow', 'sequence'
    ]
    
    SIMPLE_PATTERNS = [
        r'^what is\b',
        r'^define\b',
        r'^who is\b',
        r'^when\b',
        r'^where\b',
        r'^list\b',
        r'^show\b',
        r'^find\b',
    ]
    
    def __init__(self, 
                 complexity_threshold: float = 50.0,
                 use_langgraph_for_moderate: bool = False):
        """
        Initialize analyzer
        
        Args:
            complexity_threshold: Score above which to use LangGraph (0-100)
            use_langgraph_for_moderate: Whether to use LangGraph for moderate complexity
        """
        self.complexity_threshold = complexity_threshold
        self.use_langgraph_for_moderate = use_langgraph_for_moderate
        
    def analyze(self, query: str) -> ComplexityAnalysis:
        """
        Analyze query complexity
        
        Args:
            query: User query string
            
        Returns:
            ComplexityAnalysis with routing recommendation
        """
        query_lower = query.lower().strip()
        
        # Calculate indicators
        indicators = {
            'has_comparison': self._check_words(query_lower, self.COMPARISON_WORDS),
            'has_analysis': self._check_words(query_lower, self.ANALYSIS_WORDS),
            'has_synthesis': self._check_words(query_lower, self.SYNTHESIS_WORDS),
            'has_reasoning': self._check_words(query_lower, self.REASONING_WORDS),
            'has_multi_step': self._check_words(query_lower, self.MULTI_STEP_INDICATORS),
            'is_simple_pattern': self._check_simple_pattern(query_lower),
            'has_multiple_questions': '?' in query and query.count('?') > 1,
            'is_long_query': len(query.split()) > 20,
            'has_conditional': any(word in query_lower for word in ['if', 'when', 'unless', 'provided']),
            'has_multiple_entities': self._count_entities(query_lower) > 2,
        }
        
        # Calculate complexity score (0-100)
        score = self._calculate_score(indicators)
        
        # Determine complexity level
        complexity = self._determine_complexity(score, indicators)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(indicators, score)
        
        # Recommend approach
        recommended_approach = self._recommend_approach(complexity, score)
        
        return ComplexityAnalysis(
            complexity=complexity,
            score=score,
            reasoning=reasoning,
            indicators=indicators,
            recommended_approach=recommended_approach
        )
    
    def _check_words(self, query: str, word_list: List[str]) -> bool:
        """Check if any words from list are in query"""
        return any(word in query for word in word_list)
    
    def _check_simple_pattern(self, query: str) -> bool:
        """Check if query matches simple patterns"""
        return any(re.match(pattern, query) for pattern in self.SIMPLE_PATTERNS)
    
    def _count_entities(self, query: str) -> int:
        """Estimate number of entities/concepts in query"""
        # Simple heuristic: count capitalized words and quoted phrases
        capitalized = len(re.findall(r'\b[A-Z][a-z]+\b', query))
        quoted = len(re.findall(r'"[^"]+"', query))
        return capitalized + quoted
    
    def _calculate_score(self, indicators: Dict[str, bool]) -> float:
        """Calculate complexity score from indicators"""
        weights = {
            'has_comparison': 15,
            'has_analysis': 20,
            'has_synthesis': 20,
            'has_reasoning': 25,
            'has_multi_step': 15,
            'is_simple_pattern': -30,  # Negative weight
            'has_multiple_questions': 10,
            'is_long_query': 10,
            'has_conditional': 10,
            'has_multiple_entities': 15,
        }
        
        score = 50.0  # Base score
        
        for indicator, value in indicators.items():
            if value:
                score += weights.get(indicator, 0)
        
        # Clamp to 0-100
        return max(0.0, min(100.0, score))
    
    def _determine_complexity(self, score: float, indicators: Dict[str, bool]) -> QueryComplexity:
        """Determine complexity level from score and indicators"""
        # Simple pattern override
        if indicators['is_simple_pattern'] and score < 40:
            return QueryComplexity.SIMPLE
        
        # Score-based determination
        if score < 30:
            return QueryComplexity.SIMPLE
        elif score < 50:
            return QueryComplexity.MODERATE
        elif score < 75:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.VERY_COMPLEX
    
    def _generate_reasoning(self, indicators: Dict[str, bool], score: float) -> str:
        """Generate human-readable reasoning"""
        reasons = []
        
        if indicators['is_simple_pattern']:
            reasons.append("Matches simple query pattern")
        if indicators['has_comparison']:
            reasons.append("Requires comparison between concepts")
        if indicators['has_analysis']:
            reasons.append("Requires analytical reasoning")
        if indicators['has_synthesis']:
            reasons.append("Requires synthesis of multiple sources")
        if indicators['has_reasoning']:
            reasons.append("Requires recommendation or strategic thinking")
        if indicators['has_multi_step']:
            reasons.append("Involves multi-step process")
        if indicators['has_multiple_questions']:
            reasons.append("Contains multiple questions")
        if indicators['is_long_query']:
            reasons.append("Long, detailed query")
        if indicators['has_conditional']:
            reasons.append("Contains conditional logic")
        if indicators['has_multiple_entities']:
            reasons.append("References multiple entities/concepts")
        
        if not reasons:
            reasons.append("Standard information retrieval query")
        
        return f"Complexity score: {score:.1f}/100. " + "; ".join(reasons)
    
    def _recommend_approach(self, complexity: QueryComplexity, score: float) -> str:
        """Recommend fast or langgraph approach"""
        # Simple queries always use fast path
        if complexity == QueryComplexity.SIMPLE:
            return "fast"
        
        # Moderate queries depend on configuration
        if complexity == QueryComplexity.MODERATE:
            if self.use_langgraph_for_moderate:
                return "langgraph"
            else:
                return "fast"
        
        # Complex and very complex use LangGraph
        if complexity in [QueryComplexity.COMPLEX, QueryComplexity.VERY_COMPLEX]:
            return "langgraph"
        
        # Fallback to threshold-based
        return "langgraph" if score >= self.complexity_threshold else "fast"


# Convenience function
def analyze_query_complexity(query: str, 
                            threshold: float = 50.0,
                            use_langgraph_for_moderate: bool = False) -> ComplexityAnalysis:
    """
    Analyze query complexity (convenience function)
    
    Args:
        query: User query
        threshold: Complexity threshold for LangGraph routing
        use_langgraph_for_moderate: Use LangGraph for moderate complexity
        
    Returns:
        ComplexityAnalysis
    """
    analyzer = QueryComplexityAnalyzer(threshold, use_langgraph_for_moderate)
    return analyzer.analyze(query)


if __name__ == "__main__":
    # Test cases
    test_queries = [
        "What is the board structure?",
        "Compare the powers in AWS Bylaws vs ByLaw2000",
        "Analyze the governance implications of the new bylaws and recommend improvements",
        "List all board members",
        "How does the voting process work and what are the quorum requirements?",
        "Provide comprehensive analysis of all board powers, compare with industry standards, and suggest optimization strategy"
    ]
    
    analyzer = QueryComplexityAnalyzer()
    
    print("Query Complexity Analysis\n" + "="*80)
    for query in test_queries:
        result = analyzer.analyze(query)
        print(f"\nQuery: {query}")
        print(f"Complexity: {result.complexity.value.upper()}")
        print(f"Score: {result.score:.1f}/100")
        print(f"Approach: {result.recommended_approach.upper()}")
        print(f"Reasoning: {result.reasoning}")
