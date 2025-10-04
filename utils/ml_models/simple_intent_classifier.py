"""
Simple Intent Classifier (No TensorFlow Required)
Uses rule-based pattern matching for query intent classification
"""

import re
from typing import Dict

class SimpleIntentClassifier:
    """Rule-based intent classifier that works without ML models"""
    
    INTENT_PATTERNS = {
        'factual': [
            r'\bwhat\s+is\b',
            r'\bwhat\s+are\b',
            r'\bwho\s+is\b',
            r'\bwhen\s+did\b',
            r'\bwhere\s+is\b',
            r'\bdefine\b',
            r'\bdefinition\b',
        ],
        'analytical': [
            r'\bwhy\b',
            r'\bhow\s+does\b',
            r'\bexplain\b',
            r'\banalyze\b',
            r'\breason\b',
            r'\bcause\b',
            r'\bimpact\b',
            r'\beffect\b',
        ],
        'procedural': [
            r'\bhow\s+to\b',
            r'\bhow\s+do\s+i\b',
            r'\bsteps\b',
            r'\bprocess\b',
            r'\bprocedure\b',
            r'\bguide\b',
            r'\binstructions\b',
        ],
        'comparative': [
            r'\bcompare\b',
            r'\bdifference\b',
            r'\bvs\b',
            r'\bversus\b',
            r'\bbetter\b',
            r'\bworse\b',
            r'\bcontrast\b',
        ],
        'exploratory': [
            r'\btell\s+me\s+about\b',
            r'\binformation\s+about\b',
            r'\boverview\b',
            r'\bsummary\b',
            r'\bdescribe\b',
            r'\bprovide\s+information\b',
        ]
    }
    
    def classify_intent(self, query: str) -> Dict:
        """Classify query intent using pattern matching"""
        query_lower = query.lower()
        
        # Score each intent
        scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            scores[intent] = score
        
        # Get top intent
        if max(scores.values()) == 0:
            # Default to exploratory if no patterns match
            top_intent = 'exploratory'
            confidence = 0.6
        else:
            top_intent = max(scores, key=scores.get)
            # Calculate confidence based on matches
            total_matches = sum(scores.values())
            confidence = min(0.95, 0.7 + (scores[top_intent] / max(total_matches, 1)) * 0.25)
        
        # Calculate all intent probabilities
        total = sum(scores.values()) or 1
        all_intents = {
            intent: score / total if total > 0 else 0.2
            for intent, score in scores.items()
        }
        
        return {
            'intent': top_intent,
            'confidence': confidence,
            'all_intents': all_intents,
            'query': query
        }
    
    def get_retrieval_strategy(self, intent: str) -> Dict:
        """Get recommended retrieval strategy based on intent"""
        strategies = {
            'factual': {
                'search_type': 'precise',
                'top_k': 3,
                'use_reranking': True,
                'response_style': 'concise',
                'include_sources': True
            },
            'analytical': {
                'search_type': 'comprehensive',
                'top_k': 7,
                'use_reranking': True,
                'response_style': 'detailed_reasoning',
                'include_sources': True
            },
            'procedural': {
                'search_type': 'structured',
                'top_k': 5,
                'use_reranking': True,
                'response_style': 'step_by_step',
                'include_sources': True
            },
            'comparative': {
                'search_type': 'multi_aspect',
                'top_k': 10,
                'use_reranking': True,
                'response_style': 'comparative_analysis',
                'include_sources': True
            },
            'exploratory': {
                'search_type': 'broad',
                'top_k': 15,
                'use_reranking': False,
                'response_style': 'comprehensive_overview',
                'include_sources': True
            }
        }
        
        return strategies.get(intent, strategies['factual'])


# Singleton instance
_simple_classifier = None

def get_simple_intent_classifier() -> SimpleIntentClassifier:
    """Get or create singleton instance"""
    global _simple_classifier
    if _simple_classifier is None:
        _simple_classifier = SimpleIntentClassifier()
    return _simple_classifier
