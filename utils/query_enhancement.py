"""
Query Enhancement System

Implements intelligent query expansion and enhancement for better semantic understanding
of user queries in legal/corporate document contexts.
"""

import logging
from typing import List, Dict, Any, Optional
import os
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EnhancedQuery:
    """Enhanced query with metadata"""
    original_query: str
    expanded_queries: List[str]
    query_type: str  # legal, technical, general
    confidence: float
    metadata: Dict[str, Any]

class QueryEnhancer:
    """Intelligent query enhancement for legal/corporate documents"""
    
    def __init__(self):
        self.legal_expansions = {
            "powers": [
                "Powers of the Board of Directors",
                "Authority and duties of the Association",
                "Legal powers granted to members",
                "Executive powers in corporate bylaws",
                "Board authority and responsibilities",
                "Delegation of powers",
                "Powers and duties outlined in articles"
            ],
            "meetings": [
                "Board meeting requirements",
                "Meeting procedures and protocols",
                "Notice requirements for meetings",
                "Quorum requirements",
                "Meeting voting procedures",
                "Special meeting provisions",
                "Annual meeting requirements"
            ],
            "voting": [
                "Voting procedures and requirements",
                "Member voting rights",
                "Board voting protocols",
                "Proxy voting provisions",
                "Majority vote requirements",
                "Special voting procedures",
                "Election procedures"
            ],
            "members": [
                "Member rights and responsibilities",
                "Membership requirements",
                "Member obligations",
                "Member privileges",
                "Member disciplinary procedures",
                "Member admission procedures",
                "Member termination provisions"
            ],
            "board": [
                "Board of Directors composition",
                "Board member qualifications",
                "Board duties and responsibilities",
                "Board meeting procedures",
                "Board election procedures",
                "Board term limits",
                "Board removal procedures"
            ],
            "officers": [
                "Officer roles and responsibilities",
                "Officer election procedures",
                "Officer duties and powers",
                "Officer term limits",
                "Officer removal procedures",
                "Executive officer responsibilities",
                "Officer succession procedures"
            ]
        }
        
        self.context_patterns = {
            "legal": ["bylaw", "article", "section", "provision", "authority", "shall", "whereas"],
            "technical": ["configuration", "setup", "installation", "api", "system", "process"],
            "procedural": ["procedure", "process", "step", "requirement", "protocol", "method"]
        }
    
    def enhance_query(self, user_query: str, document_context: str = "legal") -> EnhancedQuery:
        """
        Enhance a user query with expanded variations and context
        
        Args:
            user_query: Original user query
            document_context: Context type (legal, technical, general)
            
        Returns:
            EnhancedQuery object with expanded queries
        """
        try:
            # Detect query type
            query_type = self._detect_query_type(user_query)
            
            # Generate expanded queries
            expanded_queries = self._generate_expanded_queries(user_query, query_type)
            
            # Calculate confidence
            confidence = self._calculate_confidence(user_query, expanded_queries)
            
            # Create metadata
            metadata = {
                "original_length": len(user_query),
                "expansion_count": len(expanded_queries),
                "detected_keywords": self._extract_keywords(user_query),
                "timestamp": time.time()
            }
            
            return EnhancedQuery(
                original_query=user_query,
                expanded_queries=expanded_queries,
                query_type=query_type,
                confidence=confidence,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Query enhancement failed: {e}")
            # Return basic enhancement as fallback
            return EnhancedQuery(
                original_query=user_query,
                expanded_queries=[user_query],
                query_type="general",
                confidence=0.5,
                metadata={"error": str(e)}
            )
    
    def _detect_query_type(self, query: str) -> str:
        """Detect the type of query based on keywords"""
        query_lower = query.lower()
        
        legal_score = sum(1 for pattern in self.context_patterns["legal"] if pattern in query_lower)
        technical_score = sum(1 for pattern in self.context_patterns["technical"] if pattern in query_lower)
        procedural_score = sum(1 for pattern in self.context_patterns["procedural"] if pattern in query_lower)
        
        if legal_score >= 2:
            return "legal"
        elif technical_score >= 2:
            return "technical"
        elif procedural_score >= 2:
            return "procedural"
        else:
            return "general"
    
    def _generate_expanded_queries(self, query: str, query_type: str) -> List[str]:
        """Generate expanded queries based on the original query"""
        expanded = [query]  # Always include original
        query_lower = query.lower()
        
        # Check for direct keyword matches
        for keyword, expansions in self.legal_expansions.items():
            if keyword in query_lower:
                expanded.extend(expansions[:4])  # Add top 4 expansions
                break
        
        # Add context-based expansions
        if query_type == "legal":
            expanded.extend(self._generate_legal_expansions(query))
        elif query_type == "technical":
            expanded.extend(self._generate_technical_expansions(query))
        
        # Add generic expansions for vague queries
        if self._is_vague_query(query):
            expanded.extend(self._generate_vague_query_expansions(query))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_expanded = []
        for q in expanded:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_expanded.append(q)
        
        return unique_expanded[:8]  # Limit to 8 queries max
    
    def _generate_legal_expansions(self, query: str) -> List[str]:
        """Generate legal document specific expansions"""
        expansions = []
        query_lower = query.lower()
        
        # Add article/section specific searches
        if any(word in query_lower for word in ["about", "regarding", "concerning"]):
            # Extract the main topic
            topic = re.sub(r'\b(about|regarding|concerning|information|all|provide)\b', '', query_lower).strip()
            if topic:
                expansions.extend([
                    f"Article provisions for {topic}",
                    f"Section requirements for {topic}",
                    f"{topic} duties and responsibilities",
                    f"{topic} procedures and protocols"
                ])
        
        # Add bylaw-specific terms
        if "bylaw" not in query_lower:
            expansions.append(f"{query} in bylaws")
            expansions.append(f"Bylaw provisions for {query}")
        
        return expansions[:4]
    
    def _generate_technical_expansions(self, query: str) -> List[str]:
        """Generate technical document specific expansions"""
        expansions = []
        query_lower = query.lower()
        
        # Add technical variations
        expansions.extend([
            f"{query} configuration",
            f"{query} setup procedures",
            f"{query} implementation guide",
            f"How to configure {query}"
        ])
        
        return expansions[:4]
    
    def _generate_vague_query_expansions(self, query: str) -> List[str]:
        """Generate expansions for vague queries"""
        expansions = []
        query_lower = query.lower()
        
        # Common vague query patterns
        if "all information" in query_lower or "everything about" in query_lower:
            topic = re.sub(r'\b(all information about|everything about|provide|all)\b', '', query_lower).strip()
            if topic:
                expansions.extend([
                    f"{topic} definition and scope",
                    f"{topic} requirements and procedures",
                    f"{topic} roles and responsibilities",
                    f"{topic} policies and guidelines"
                ])
        
        return expansions[:4]
    
    def _is_vague_query(self, query: str) -> bool:
        """Check if query is vague and needs expansion"""
        vague_indicators = [
            "all information",
            "everything about",
            "tell me about",
            "what is",
            "explain",
            "describe"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in vague_indicators)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract key terms from the query"""
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
            "of", "with", "by", "about", "all", "information", "provide", "tell", "me"
        }
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords[:5]  # Return top 5 keywords
    
    def _calculate_confidence(self, original_query: str, expanded_queries: List[str]) -> float:
        """Calculate confidence in the query enhancement"""
        base_confidence = 0.5
        
        # Higher confidence for more specific queries
        if len(original_query.split()) > 3:
            base_confidence += 0.2
        
        # Higher confidence if we found good expansions
        if len(expanded_queries) > 3:
            base_confidence += 0.2
        
        # Higher confidence if query contains legal terms
        legal_terms = sum(1 for term in self.context_patterns["legal"] if term in original_query.lower())
        base_confidence += min(legal_terms * 0.1, 0.3)
        
        return min(base_confidence, 1.0)

class AdvancedQueryProcessor:
    """Advanced query processing with LLM-based enhancement"""
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.query_enhancer = QueryEnhancer()
        self.llm_available = False
        
        if use_llm:
            self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM for query enhancement"""
        try:
            # Try to import and initialize LLM
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            
            # Prevent older OpenAI SDKs from receiving unsupported 'project' kwarg
            try:
                os.environ.pop("OPENAI_PROJECT", None)
            except Exception:
                pass
            self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
            
            self.query_expansion_prompt = ChatPromptTemplate.from_template("""
You are a legal document expert. Your task is to rewrite a user's query to be more effective for retrieving relevant excerpts from corporate bylaws and governance documents.

Generate 4-5 optimized search queries. Focus on:
1. Synonyms and related legal concepts
2. Specific section headings they might be found under
3. Alternative phrasings that would appear in formal legal documents
4. More specific terms that capture the user's intent

Original User Query: {query}

Return only the optimized queries, one per line:
""")
            
            self.query_rewriter = self.query_expansion_prompt | self.llm | StrOutputParser()
            self.llm_available = True
            logger.info("LLM-based query enhancement initialized")
            
        except Exception as e:
            logger.warning(f"LLM initialization failed: {e}")
            self.llm_available = False
    
    def enhance_query_with_llm(self, user_query: str) -> List[str]:
        """Enhance query using LLM"""
        if not self.llm_available:
            return [user_query]
        
        try:
            enhanced_queries = self.query_rewriter.invoke({"query": user_query})
            query_list = [q.strip() for q in enhanced_queries.split("\n") if q.strip()]
            
            # Always include original query first
            if user_query not in query_list:
                query_list.insert(0, user_query)
            
            return query_list[:6]  # Limit to 6 queries
            
        except Exception as e:
            logger.error(f"LLM query enhancement failed: {e}")
            return [user_query]
    
    def process_query(self, user_query: str, use_llm_enhancement: bool = True) -> EnhancedQuery:
        """Process query with both rule-based and LLM enhancement"""
        
        # Start with rule-based enhancement
        enhanced_query = self.query_enhancer.enhance_query(user_query)
        
        # Add LLM enhancement if available and requested
        if use_llm_enhancement and self.llm_available:
            try:
                llm_queries = self.enhance_query_with_llm(user_query)
                
                # Combine rule-based and LLM queries
                all_queries = enhanced_query.expanded_queries + llm_queries
                
                # Remove duplicates while preserving order
                seen = set()
                unique_queries = []
                for q in all_queries:
                    if q.lower() not in seen:
                        seen.add(q.lower())
                        unique_queries.append(q)
                
                enhanced_query.expanded_queries = unique_queries[:8]
                enhanced_query.metadata["llm_enhanced"] = True
                enhanced_query.confidence = min(enhanced_query.confidence + 0.2, 1.0)
                
            except Exception as e:
                logger.error(f"LLM enhancement failed: {e}")
                enhanced_query.metadata["llm_error"] = str(e)
        
        return enhanced_query

def get_query_enhancer() -> QueryEnhancer:
    """Get query enhancer instance"""
    return QueryEnhancer()

def get_advanced_query_processor(use_llm: bool = True) -> AdvancedQueryProcessor:
    """Get advanced query processor instance"""
    return AdvancedQueryProcessor(use_llm)

def enhance_user_query(user_query: str, use_llm: bool = True) -> EnhancedQuery:
    """Convenience function to enhance a user query"""
    processor = get_advanced_query_processor(use_llm)
    return processor.process_query(user_query, use_llm)
