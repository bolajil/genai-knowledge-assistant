"""
Query Expansion Utility
=======================
Expands queries with synonyms and related terms to improve search recall.
"""

from typing import List, Set, Dict
import re


class QueryExpander:
    """Expand queries with synonyms and related terms"""
    
    # Domain-specific synonym mappings
    SYNONYMS = {
        # Board/Governance terms
        'powers': ['authority', 'responsibilities', 'duties', 'rights', 'jurisdiction', 'mandate'],
        'board': ['board of directors', 'directors', 'governing body', 'board members'],
        'board members': ['directors', 'board of directors', 'board'],
        'duties': ['responsibilities', 'obligations', 'tasks', 'functions', 'powers'],
        'authority': ['powers', 'jurisdiction', 'mandate', 'control'],
        
        # Meeting terms
        'meeting': ['session', 'assembly', 'gathering', 'conference'],
        'quorum': ['minimum attendance', 'required presence'],
        'vote': ['ballot', 'poll', 'election', 'decision'],
        'notice': ['notification', 'announcement', 'communication'],
        
        # Election terms
        'election': ['vote', 'ballot', 'selection', 'appointment'],
        'term': ['period', 'duration', 'tenure'],
        'vacancy': ['opening', 'empty position', 'unfilled position'],
        
        # Document terms
        'bylaws': ['articles', 'constitution', 'rules', 'regulations'],
        'policy': ['procedure', 'guideline', 'rule', 'protocol'],
        'amendment': ['change', 'modification', 'revision', 'update'],
        
        # Action terms
        'approve': ['ratify', 'authorize', 'endorse', 'accept'],
        'reject': ['disapprove', 'veto', 'deny', 'refuse'],
        'delegate': ['assign', 'transfer', 'authorize', 'empower'],
        'remove': ['dismiss', 'terminate', 'discharge', 'oust'],
    }
    
    # Common phrase expansions
    PHRASE_EXPANSIONS = {
        'powers of board': ['board powers', 'board authority', 'board responsibilities'],
        'board meeting': ['meeting of the board', 'board session'],
        'special meeting': ['extraordinary meeting', 'emergency meeting'],
        'annual meeting': ['yearly meeting', 'annual session'],
        'right to vote': ['voting rights', 'voting privileges'],
    }
    
    @staticmethod
    def expand_query(query: str, max_variations: int = 10) -> List[str]:
        """
        Expand a query with synonyms and related terms.
        
        Args:
            query: Original search query
            max_variations: Maximum number of variations to return
            
        Returns:
            List of query variations including the original
        """
        variations = {query.strip()}  # Use set to avoid duplicates
        query_lower = query.lower()
        
        # Check for phrase expansions first
        for phrase, expansions in QueryExpander.PHRASE_EXPANSIONS.items():
            if phrase in query_lower:
                for expansion in expansions:
                    # Replace phrase with expansion (case-insensitive)
                    pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                    new_query = pattern.sub(expansion, query)
                    variations.add(new_query)
        
        # Expand individual terms
        words = query.split()
        for i, word in enumerate(words):
            word_lower = word.lower().strip('.,!?;:')
            
            # Check if word has synonyms
            if word_lower in QueryExpander.SYNONYMS:
                for synonym in QueryExpander.SYNONYMS[word_lower]:
                    # Create new query with synonym
                    new_words = words.copy()
                    new_words[i] = synonym
                    variations.add(' '.join(new_words))
        
        # Convert to list and limit
        result = list(variations)[:max_variations]
        
        # Ensure original query is first
        if query in result:
            result.remove(query)
        result.insert(0, query)
        
        return result
    
    @staticmethod
    def expand_with_context(query: str, context: str = 'general') -> List[str]:
        """
        Expand query with context-specific variations.
        
        Args:
            query: Original search query
            context: Context type ('bylaws', 'policy', 'meeting', 'general')
            
        Returns:
            List of context-aware query variations
        """
        variations = QueryExpander.expand_query(query)
        
        # Add context-specific prefixes/suffixes
        context_additions = []
        
        if context == 'bylaws':
            context_additions = [
                f"{query} in bylaws",
                f"bylaw regarding {query}",
                f"{query} provisions"
            ]
        elif context == 'policy':
            context_additions = [
                f"{query} policy",
                f"policy on {query}",
                f"{query} procedures"
            ]
        elif context == 'meeting':
            context_additions = [
                f"{query} at meetings",
                f"meeting {query}",
                f"{query} during meetings"
            ]
        
        # Combine and deduplicate
        all_variations = list(set(variations + context_additions))
        return all_variations[:15]  # Limit to 15 variations
    
    @staticmethod
    def extract_key_terms(query: str) -> List[str]:
        """
        Extract key terms from a query for focused search.
        
        Args:
            query: Search query
            
        Returns:
            List of key terms
        """
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'what',
            'which', 'who', 'when', 'where', 'why', 'how'
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter stop words and short words
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        return key_terms
    
    @staticmethod
    def rewrite_query(query: str) -> str:
        """
        Rewrite query for better search performance.
        
        Args:
            query: Original query
            
        Returns:
            Rewritten query
        """
        # Convert questions to statements
        query = query.strip()
        
        # Remove question words at the start
        question_words = ['what', 'who', 'when', 'where', 'why', 'how', 'which']
        words = query.lower().split()
        
        if words and words[0] in question_words:
            # Remove question word
            words = words[1:]
            
            # Remove auxiliary verbs
            if words and words[0] in ['is', 'are', 'was', 'were', 'do', 'does', 'did']:
                words = words[1:]
            
            query = ' '.join(words)
        
        # Remove question mark
        query = query.rstrip('?')
        
        # Capitalize first letter
        if query:
            query = query[0].upper() + query[1:]
        
        return query.strip()


# Convenience functions
def expand_query(query: str, max_variations: int = 10) -> List[str]:
    """Expand query - convenience function"""
    return QueryExpander.expand_query(query, max_variations)


def rewrite_query(query: str) -> str:
    """Rewrite query - convenience function"""
    return QueryExpander.rewrite_query(query)


def extract_key_terms(query: str) -> List[str]:
    """Extract key terms - convenience function"""
    return QueryExpander.extract_key_terms(query)
