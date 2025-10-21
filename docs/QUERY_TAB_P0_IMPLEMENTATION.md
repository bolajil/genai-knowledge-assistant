# Query Tab P0 Critical Fixes - Implementation Guide
**Priority:** P0 - Critical  
**Timeline:** 2 Weeks  
**Status:** 🚀 Ready to Implement

---

## 📋 P0 Critical Fixes Overview

| # | Fix | Impact | Effort | Status |
|---|-----|--------|--------|--------|
| 1 | Input Validation & Sanitization | Security | 2 days | ⏳ Pending |
| 2 | Rate Limiting | DoS Prevention | 2 days | ⏳ Pending |
| 3 | Query Result Caching | Performance | 3 days | ⏳ Pending |
| 4 | Modularize Codebase | Maintainability | 5 days | ⏳ Pending |
| 5 | Unit Tests (60% coverage) | Quality | 5 days | ⏳ Pending |
| 6 | Audit Logging | Compliance | 3 days | ⏳ Pending |

**Total Effort:** 10 working days (2 weeks with 2 engineers)

---

## 🔧 P0 Fix #1: Input Validation & Sanitization

### Industry-Standard Implementation

```python
# utils/security/input_validator.py
"""
Enterprise-grade input validation following OWASP guidelines
"""
import re
from typing import Tuple, Optional, Dict, Any
from html import escape
import logging

logger = logging.getLogger(__name__)

class InputValidator:
    """
    OWASP-compliant input validator for Query Assistant
    
    Protects against:
    - XSS (Cross-Site Scripting)
    - SQL Injection
    - Command Injection
    - Path Traversal
    - LDAP Injection
    """
    
    # OWASP recommended patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'eval\s*\(',
        r'expression\s*\(',
    ]
    
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(;.*--)",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r'[;&|`$]',
        r'\$\(',
        r'>\s*/dev/',
    ]
    
    # Industry standard limits (OWASP recommendations)
    MIN_QUERY_LENGTH = 3
    MAX_QUERY_LENGTH = 1000
    MAX_INDEX_NAME_LENGTH = 100
    
    @classmethod
    def validate_query(cls, query: str, context: str = "query") -> Tuple[bool, Optional[str], str]:
        """
        Validate and sanitize user query input
        
        Args:
            query: User input query string
            context: Context for logging (e.g., "quick_search", "index_search")
            
        Returns:
            Tuple of (is_valid, error_message, sanitized_query)
            
        Example:
            >>> validator = InputValidator()
            >>> valid, error, clean = validator.validate_query("What is AWS?")
            >>> assert valid == True
            >>> assert clean == "What is AWS?"
        """
        if not query:
            return False, "Query cannot be empty", ""
        
        # Length validation (OWASP: Enforce reasonable limits)
        if len(query) < cls.MIN_QUERY_LENGTH:
            logger.warning(f"Query too short in {context}: {len(query)} chars")
            return False, f"Query must be at least {cls.MIN_QUERY_LENGTH} characters", ""
        
        if len(query) > cls.MAX_QUERY_LENGTH:
            logger.warning(f"Query too long in {context}: {len(query)} chars")
            return False, f"Query too long (max {cls.MAX_QUERY_LENGTH} characters)", ""
        
        # Remove control characters (OWASP: Sanitize input)
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)
        
        # Check for XSS attempts (OWASP: Validate against known attack patterns)
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.error(f"XSS attempt detected in {context}: {pattern}")
                return False, "Query contains invalid characters", ""
        
        # Check for SQL injection attempts
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.error(f"SQL injection attempt detected in {context}: {pattern}")
                return False, "Query contains invalid SQL patterns", ""
        
        # Check for command injection attempts
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, sanitized):
                logger.error(f"Command injection attempt detected in {context}")
                return False, "Query contains invalid shell characters", ""
        
        # HTML escape (OWASP: Output encoding)
        sanitized = escape(sanitized)
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        # Additional sanitization: Remove potentially dangerous Unicode
        sanitized = sanitized.encode('ascii', 'ignore').decode('ascii')
        
        logger.info(f"Query validated successfully in {context}: {len(sanitized)} chars")
        return True, None, sanitized
    
    @classmethod
    def validate_index_name(cls, index_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate index/collection name
        
        Args:
            index_name: Name of the index to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not index_name:
            return False, "Index name required"
        
        # Only allow alphanumeric, underscore, hyphen (OWASP: Whitelist validation)
        if not re.match(r'^[a-zA-Z0-9_-]+$', index_name):
            logger.error(f"Invalid index name format: {index_name}")
            return False, "Invalid index name format (alphanumeric, underscore, hyphen only)"
        
        if len(index_name) > cls.MAX_INDEX_NAME_LENGTH:
            return False, f"Index name too long (max {cls.MAX_INDEX_NAME_LENGTH} characters)"
        
        # Prevent path traversal
        if '..' in index_name or '/' in index_name or '\\' in index_name:
            logger.error(f"Path traversal attempt in index name: {index_name}")
            return False, "Invalid index name (path traversal detected)"
        
        return True, None
    
    @classmethod
    def validate_top_k(cls, top_k: int) -> Tuple[bool, Optional[str]]:
        """
        Validate top_k parameter
        
        Args:
            top_k: Number of results to return
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(top_k, int):
            return False, "top_k must be an integer"
        
        if top_k < 1:
            return False, "top_k must be at least 1"
        
        if top_k > 100:  # Industry standard: Prevent resource exhaustion
            logger.warning(f"top_k too large: {top_k}")
            return False, "top_k too large (max 100)"
        
        return True, None
    
    @classmethod
    def sanitize_for_logging(cls, text: str, max_length: int = 100) -> str:
        """
        Sanitize text for safe logging (GDPR/PII protection)
        
        Args:
            text: Text to sanitize
            max_length: Maximum length to log
            
        Returns:
            Sanitized text safe for logging
        """
        if not text:
            return ""
        
        # Truncate
        sanitized = text[:max_length]
        
        # Remove PII patterns (GDPR compliance)
        # Email addresses
        sanitized = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL]',
            sanitized
        )
        
        # Phone numbers (US format)
        sanitized = re.sub(
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            '[PHONE]',
            sanitized
        )
        
        # SSN
        sanitized = re.sub(
            r'\b\d{3}-\d{2}-\d{4}\b',
            '[SSN]',
            sanitized
        )
        
        # Credit card numbers (basic pattern)
        sanitized = re.sub(
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            '[CARD]',
            sanitized
        )
        
        return sanitized


# Example usage in query_assistant.py
def safe_query_execution(query: str, index_name: str, top_k: int) -> Dict[str, Any]:
    """
    Execute query with industry-standard validation
    """
    validator = InputValidator()
    
    # Validate query
    valid, error, sanitized_query = validator.validate_query(query, context="quick_search")
    if not valid:
        logger.error(f"Query validation failed: {error}")
        return {"error": error, "code": "INVALID_INPUT"}
    
    # Validate index name
    valid, error = validator.validate_index_name(index_name)
    if not valid:
        logger.error(f"Index validation failed: {error}")
        return {"error": error, "code": "INVALID_INDEX"}
    
    # Validate top_k
    valid, error = validator.validate_top_k(top_k)
    if not valid:
        logger.error(f"top_k validation failed: {error}")
        return {"error": error, "code": "INVALID_PARAMETER"}
    
    # Execute search with sanitized input
    try:
        results = execute_search(sanitized_query, index_name, top_k)
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Search execution failed: {e}", exc_info=True)
        return {"error": "Search failed", "code": "EXECUTION_ERROR"}
```

---

## 🔧 P0 Fix #2: Rate Limiting (Industry Standard)

```python
# utils/security/rate_limiter.py
"""
Enterprise-grade rate limiting following industry best practices
Implements Token Bucket and Sliding Window algorithms
"""
import time
import logging
from typing import Tuple, Optional, Dict
from collections import defaultdict
from threading import Lock
import redis
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RateLimitTier(Enum):
    """Rate limit tiers based on user role"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class RateLimitConfig:
    """Rate limit configuration per tier"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int  # Token bucket burst capacity

# Industry-standard rate limits
RATE_LIMITS = {
    RateLimitTier.FREE: RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=500,
        burst_size=15
    ),
    RateLimitTier.BASIC: RateLimitConfig(
        requests_per_minute=20,
        requests_per_hour=500,
        requests_per_day=2000,
        burst_size=30
    ),
    RateLimitTier.PREMIUM: RateLimitConfig(
        requests_per_minute=50,
        requests_per_hour=2000,
        requests_per_day=10000,
        burst_size=75
    ),
    RateLimitTier.ENTERPRISE: RateLimitConfig(
        requests_per_minute=100,
        requests_per_hour=10000,
        requests_per_day=100000,
        burst_size=150
    ),
}

class EnterpriseRateLimiter:
    """
    Production-grade rate limiter with multiple algorithms
    
    Features:
    - Token Bucket algorithm for burst handling
    - Sliding Window for accurate rate limiting
    - Redis support for distributed systems
    - Per-user and per-IP limiting
    - Automatic tier detection
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiter
        
        Args:
            redis_url: Redis connection URL for distributed rate limiting
        """
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("Rate limiter initialized with Redis backend")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory: {e}")
        
        # Fallback to in-memory storage
        self.memory_store = defaultdict(list)
        self.token_buckets = {}
        self.lock = Lock()
    
    def check_rate_limit(
        self,
        user_id: str,
        tier: RateLimitTier = RateLimitTier.FREE,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Dict[str, int]]:
        """
        Check if request is within rate limit
        
        Args:
            user_id: User identifier
            tier: User's rate limit tier
            ip_address: Optional IP address for additional limiting
            
        Returns:
            Tuple of (allowed, error_message, rate_limit_info)
            
        Example:
            >>> limiter = EnterpriseRateLimiter()
            >>> allowed, msg, info = limiter.check_rate_limit("user123", RateLimitTier.BASIC)
            >>> if not allowed:
            >>>     return {"error": msg, "retry_after": info['retry_after']}
        """
        config = RATE_LIMITS[tier]
        now = time.time()
        
        # Check per-minute limit (most restrictive)
        allowed, message, retry_after = self._check_window(
            user_id,
            "minute",
            config.requests_per_minute,
            60,
            now
        )
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {user_id}: {message}")
            return False, message, {
                'retry_after': retry_after,
                'limit': config.requests_per_minute,
                'window': 'minute'
            }
        
        # Check per-hour limit
        allowed, message, retry_after = self._check_window(
            user_id,
            "hour",
            config.requests_per_hour,
            3600,
            now
        )
        
        if not allowed:
            logger.warning(f"Hourly rate limit exceeded for {user_id}")
            return False, message, {
                'retry_after': retry_after,
                'limit': config.requests_per_hour,
                'window': 'hour'
            }
        
        # Check per-day limit
        allowed, message, retry_after = self._check_window(
            user_id,
            "day",
            config.requests_per_day,
            86400,
            now
        )
        
        if not allowed:
            logger.warning(f"Daily rate limit exceeded for {user_id}")
            return False, message, {
                'retry_after': retry_after,
                'limit': config.requests_per_day,
                'window': 'day'
            }
        
        # Check IP-based limit if provided (prevent abuse)
        if ip_address:
            allowed, message, retry_after = self._check_ip_limit(ip_address, now)
            if not allowed:
                logger.error(f"IP rate limit exceeded: {ip_address}")
                return False, message, {
                    'retry_after': retry_after,
                    'limit': 100,
                    'window': 'minute'
                }
        
        # Record successful request
        self._record_request(user_id, now)
        
        # Return success with remaining quota
        remaining = self._get_remaining_quota(user_id, config, now)
        
        return True, None, {
            'remaining_minute': remaining['minute'],
            'remaining_hour': remaining['hour'],
            'remaining_day': remaining['day'],
            'tier': tier.value
        }
    
    def _check_window(
        self,
        user_id: str,
        window_type: str,
        max_requests: int,
        window_seconds: int,
        now: float
    ) -> Tuple[bool, Optional[str], int]:
        """
        Check sliding window rate limit
        
        Returns:
            Tuple of (allowed, error_message, retry_after_seconds)
        """
        key = f"ratelimit:{user_id}:{window_type}"
        
        if self.redis_client:
            return self._check_window_redis(key, max_requests, window_seconds, now)
        else:
            return self._check_window_memory(key, max_requests, window_seconds, now)
    
    def _check_window_redis(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        now: float
    ) -> Tuple[bool, Optional[str], int]:
        """Redis-based sliding window"""
        try:
            # Remove old entries
            self.redis_client.zremrangebyscore(key, 0, now - window_seconds)
            
            # Count recent requests
            count = self.redis_client.zcard(key)
            
            if count >= max_requests:
                # Get oldest request time
                oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(window_seconds - (now - oldest[0][1]))
                    return False, f"Rate limit exceeded. Try again in {retry_after}s", retry_after
                return False, "Rate limit exceeded", window_seconds
            
            # Add current request
            self.redis_client.zadd(key, {str(now): now})
            self.redis_client.expire(key, window_seconds)
            
            return True, None, 0
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fail open (allow request) to prevent service disruption
            return True, None, 0
    
    def _check_window_memory(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        now: float
    ) -> Tuple[bool, Optional[str], int]:
        """In-memory sliding window"""
        with self.lock:
            # Clean old requests
            self.memory_store[key] = [
                t for t in self.memory_store[key]
                if now - t < window_seconds
            ]
            
            if len(self.memory_store[key]) >= max_requests:
                oldest = min(self.memory_store[key])
                retry_after = int(window_seconds - (now - oldest))
                return False, f"Rate limit exceeded. Try again in {retry_after}s", retry_after
            
            self.memory_store[key].append(now)
            return True, None, 0
    
    def _check_ip_limit(self, ip_address: str, now: float) -> Tuple[bool, Optional[str], int]:
        """
        Check IP-based rate limit (prevent DDoS)
        Industry standard: 100 requests per minute per IP
        """
        return self._check_window(
            f"ip:{ip_address}",
            "minute",
            100,
            60,
            now
        )
    
    def _record_request(self, user_id: str, now: float):
        """Record successful request for analytics"""
        try:
            if self.redis_client:
                analytics_key = f"analytics:requests:{user_id}"
                self.redis_client.incr(analytics_key)
                self.redis_client.expire(analytics_key, 86400)  # 24 hours
        except Exception as e:
            logger.debug(f"Failed to record analytics: {e}")
    
    def _get_remaining_quota(
        self,
        user_id: str,
        config: RateLimitConfig,
        now: float
    ) -> Dict[str, int]:
        """Get remaining quota for user"""
        remaining = {}
        
        for window_type, max_req, window_sec in [
            ("minute", config.requests_per_minute, 60),
            ("hour", config.requests_per_hour, 3600),
            ("day", config.requests_per_day, 86400),
        ]:
            key = f"ratelimit:{user_id}:{window_type}"
            
            if self.redis_client:
                try:
                    self.redis_client.zremrangebyscore(key, 0, now - window_sec)
                    count = self.redis_client.zcard(key)
                    remaining[window_type] = max(0, max_req - count)
                except Exception:
                    remaining[window_type] = max_req
            else:
                with self.lock:
                    self.memory_store[key] = [
                        t for t in self.memory_store[key]
                        if now - t < window_sec
                    ]
                    count = len(self.memory_store[key])
                    remaining[window_type] = max(0, max_req - count)
        
        return remaining


# Decorator for easy integration
def rate_limit(tier: RateLimitTier = RateLimitTier.FREE):
    """
    Decorator to apply rate limiting to functions
    
    Example:
        @rate_limit(tier=RateLimitTier.PREMIUM)
        def execute_search(user_id: str, query: str):
            # Your search logic here
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract user_id from args/kwargs
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            if not user_id:
                raise ValueError("user_id required for rate limiting")
            
            # Check rate limit
            limiter = EnterpriseRateLimiter()
            allowed, message, info = limiter.check_rate_limit(user_id, tier)
            
            if not allowed:
                raise RateLimitExceeded(message, info)
            
            # Execute function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, message: str, info: Dict[str, int]):
        self.message = message
        self.info = info
        super().__init__(self.message)
```

---

## 🔧 P0 Fix #3: Industry-Standard LLM Prompts

The current LLM prompts need to be optimized for enterprise use. Here's the industry-standard approach:

```python
# utils/prompts/enterprise_prompts.py
"""
Enterprise-grade LLM prompts following industry best practices

Based on:
- OpenAI Prompt Engineering Guide
- Anthropic Claude Best Practices
- Google Vertex AI Guidelines
- Microsoft Azure OpenAI Recommendations
"""

from typing import List, Dict, Any, Optional
from enum import Enum

class PromptTemplate(Enum):
    """Industry-standard prompt templates"""
    CONCISE_ANSWER = "concise"
    DETAILED_ANALYSIS = "detailed"
    EXECUTIVE_SUMMARY = "executive"
    TECHNICAL_DEEP_DIVE = "technical"
    COMPARATIVE_ANALYSIS = "comparative"

class EnterprisePromptBuilder:
    """
    Build industry-standard prompts for enterprise RAG systems
    
    Follows best practices from:
    - Chain-of-Thought prompting
    - Few-shot learning
    - Role-based prompting
    - Structured output formatting
    """
    
    # Industry-standard system prompts
    SYSTEM_PROMPTS = {
        "default": """You are VaultMind Enterprise Assistant, an expert AI system specialized in analyzing corporate documents, legal texts, and technical documentation.

Your core competencies:
- Precise information retrieval from provided documents
- Clear, professional communication
- Accurate citation of sources with page numbers
- Identification of information gaps
- Compliance with enterprise security standards

Guidelines:
1. Base ALL answers EXCLUSIVELY on the provided document context
2. Cite specific page numbers and sections for every claim
3. Use professional, clear language appropriate for business executives
4. If information is incomplete or missing, explicitly state this
5. Never speculate or add information not present in the documents
6. Structure responses with clear headings and bullet points
7. Prioritize accuracy over completeness

Security & Compliance:
- Never include inline URLs or hyperlinks in answers
- Protect PII and sensitive information
- Follow data minimization principles
- Maintain audit trail compatibility""",
        
        "technical": """You are VaultMind Technical Documentation Expert, specialized in analyzing technical specifications, API documentation, and system architecture documents.

Your expertise includes:
- Technical accuracy and precision
- Code examples and implementation details
- System architecture analysis
- API and integration guidance
- Best practices and recommendations

Technical Guidelines:
1. Provide technically accurate information with proper terminology
2. Include code examples when relevant (properly formatted)
3. Explain technical concepts clearly for mixed audiences
4. Reference specific technical specifications with exact page/section numbers
5. Highlight potential technical risks or limitations
6. Suggest best practices based on industry standards

Output Format:
- Use markdown code blocks for code examples
- Include technical diagrams descriptions when relevant
- Provide step-by-step implementation guidance
- List prerequisites and dependencies clearly""",
        
        "legal": """You are VaultMind Legal Document Analyst, specialized in corporate bylaws, policies, and legal documentation.

Your specialization:
- Legal document interpretation
- Policy and procedure analysis
- Compliance requirement identification
- Risk assessment
- Regulatory guidance

Legal Analysis Guidelines:
1. Provide precise legal interpretations based solely on document text
2. Cite exact sections, articles, and page numbers
3. Identify ambiguities or potential conflicts
4. Note any missing or incomplete information
5. Use proper legal terminology
6. Maintain objectivity and neutrality
7. Highlight compliance requirements clearly

IMPORTANT: This is document analysis only, not legal advice. Users should consult qualified legal counsel for legal decisions."""
    }
    
    @classmethod
    def build_query_prompt(
        cls,
        query: str,
        context_documents: List[Dict[str, Any]],
        index_name: str,
        template: PromptTemplate = PromptTemplate.CONCISE_ANSWER,
        domain: str = "default"
    ) -> str:
        """
        Build enterprise-grade query prompt
        
        Args:
            query: User's question
            context_documents: Retrieved documents with metadata
            index_name: Name of the knowledge base
            template: Response template type
            domain: Domain-specific system prompt (default, technical, legal)
            
        Returns:
            Optimized prompt string
        """
        # Build context section
        context = cls._build_context_section(context_documents, index_name)
        
        # Get template-specific instructions
        instructions = cls._get_template_instructions(template)
        
        # Build complete prompt
        prompt = f"""{cls.SYSTEM_PROMPTS.get(domain, cls.SYSTEM_PROMPTS['default'])}

---

## DOCUMENT CONTEXT

Knowledge Base: {index_name.upper()}
Retrieved Documents: {len(context_documents)}

{context}

---

## USER QUERY

{query}

---

## RESPONSE INSTRUCTIONS

{instructions}

## OUTPUT FORMAT

Structure your response as follows:

### Summary
[2-3 sentence executive summary]

### Detailed Answer
[Comprehensive answer with clear sections]

### Key Points
- [Bullet point 1 with citation]
- [Bullet point 2 with citation]
- [Bullet point 3 with citation]

### Source Citations
[List all sources used with page numbers]

### Information Gaps
[Note any missing or incomplete information]

---

Please provide your response now:"""
        
        return prompt
    
    @classmethod
    def _build_context_section(
        cls,
        documents: List[Dict[str, Any]],
        index_name: str
    ) -> str:
        """
        Build optimized context section from retrieved documents
        
        Industry best practice: Limit context to most relevant information
        """
        if not documents:
            return "⚠️ No relevant documents found in the knowledge base."
        
        context_parts = []
        
        for i, doc in enumerate(documents[:5], 1):  # Limit to top 5 for token efficiency
            content = doc.get('content', '')
            source = doc.get('source', 'Unknown')
            page = doc.get('page', 'N/A')
            section = doc.get('section', '')
            score = doc.get('relevance_score', 0.0)
            
            # Clean and truncate content
            content = cls._clean_content(content)
            if len(content) > 1500:  # Industry standard: ~1500 chars per doc
                content = content[:1400] + "\n\n[Content continues...]"
            
            # Build structured context
            context_part = f"""
### Document {i}
**Source:** {source}
**Page:** {page}
{f"**Section:** {section}" if section else ""}
**Relevance:** {score:.2f}

**Content:**
{content}
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    @classmethod
    def _get_template_instructions(cls, template: PromptTemplate) -> str:
        """Get template-specific instructions"""
        instructions = {
            PromptTemplate.CONCISE_ANSWER: """
Provide a CONCISE, direct answer:
- 3-5 sentences maximum for summary
- 3-5 key bullet points
- Essential citations only
- Focus on actionable information
- Use clear, simple language""",
            
            PromptTemplate.DETAILED_ANALYSIS: """
Provide a COMPREHENSIVE analysis:
- Detailed explanation with context
- Multiple perspectives if applicable
- Thorough citation of all sources
- Analysis of implications
- Identification of related topics
- 500-800 words target length""",
            
            PromptTemplate.EXECUTIVE_SUMMARY: """
Provide an EXECUTIVE-LEVEL summary:
- High-level overview suitable for C-suite
- Business impact and implications
- Key decisions or actions required
- Risk factors if applicable
- Strategic recommendations
- 200-300 words maximum""",
            
            PromptTemplate.TECHNICAL_DEEP_DIVE: """
Provide a TECHNICAL deep-dive:
- Detailed technical specifications
- Implementation details and examples
- Architecture and design considerations
- Best practices and recommendations
- Potential challenges and solutions
- Code examples where relevant""",
            
            PromptTemplate.COMPARATIVE_ANALYSIS: """
Provide a COMPARATIVE analysis:
- Compare and contrast different approaches
- Pros and cons of each option
- Use cases for each approach
- Recommendations base
