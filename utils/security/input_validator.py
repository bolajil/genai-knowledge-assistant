"""
OWASP-Compliant Input Validation
================================

Industry-standard input validation and sanitization following OWASP guidelines.
Protects against XSS, SQL injection, command injection, and other attacks.

References:
- OWASP Input Validation Cheat Sheet
- OWASP XSS Prevention Cheat Sheet
- CWE-79, CWE-89, CWE-78
"""

import re
import logging
from typing import Tuple, Optional, List
from html import escape
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class InputValidator:
    """
    OWASP-compliant input validator for enterprise applications
    
    Implements defense-in-depth strategy:
    1. Whitelist validation (preferred)
    2. Blacklist detection (secondary)
    3. Sanitization (last resort)
    """
    
    # OWASP-recommended dangerous patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<applet[^>]*>',
        r'<meta[^>]*>',
        r'<link[^>]*>',
        r'<style[^>]*>.*?</style>',
        r'vbscript:',
        r'data:text/html',
    ]
    
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(;.*\b(SELECT|INSERT|UPDATE|DELETE)\b)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bEXEC\b.*\()",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r'[;&|`$]',
        r'\$\(',
        r'>\s*/dev/',
        r'<\s*/dev/',
        r'\|\s*\w+',
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\.',
        r'%2e%2e',
        r'\.%2e',
        r'%2e\.',
    ]
    
    @staticmethod
    def validate_query(query: str, max_length: int = 1000) -> Tuple[bool, Optional[str], str]:
        """
        Validate and sanitize search query input
        
        Args:
            query: User query string
            max_length: Maximum allowed length
            
        Returns:
            (is_valid, error_message, sanitized_query)
            
        Security Checks:
        - Length validation
        - XSS pattern detection
        - SQL injection pattern detection
        - Command injection pattern detection
        - Control character removal
        - HTML entity encoding
        """
        if not query:
            return False, "Query cannot be empty", ""
        
        # Length validation
        if len(query) < 3:
            return False, "Query must be at least 3 characters", ""
        
        if len(query) > max_length:
            return False, f"Query too long (max {max_length} characters)", ""
        
        # Remove control characters (except newline, tab, carriage return)
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', query)
        
        # Check for XSS patterns
        for pattern in InputValidator.XSS_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"XSS pattern detected in query: {pattern}")
                return False, "Query contains potentially malicious content (XSS)", ""
        
        # Check for SQL injection patterns
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return False, "Query contains potentially malicious content (SQL)", ""
        
        # Check for command injection patterns
        for pattern in InputValidator.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, sanitized):
                logger.warning(f"Command injection pattern detected: {pattern}")
                return False, "Query contains potentially malicious content (CMD)", ""
        
        # HTML escape to prevent XSS
        sanitized = escape(sanitized)
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        # Final validation
        if not sanitized or len(sanitized.strip()) < 3:
            return False, "Query too short after sanitization", ""
        
        logger.info(f"Query validated successfully: {sanitized[:50]}...")
        return True, None, sanitized
    
    @staticmethod
    def validate_index_name(index_name: str, max_length: int = 100) -> Tuple[bool, Optional[str]]:
        """
        Validate index/collection name
        
        Args:
            index_name: Index or collection name
            max_length: Maximum allowed length
            
        Returns:
            (is_valid, error_message)
            
        Security: Only allows alphanumeric, underscore, hyphen
        """
        if not index_name:
            return False, "Index name required"
        
        # Whitelist validation: only allow safe characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', index_name):
            logger.warning(f"Invalid index name format: {index_name}")
            return False, "Index name can only contain letters, numbers, underscore, and hyphen"
        
        if len(index_name) > max_length:
            return False, f"Index name too long (max {max_length} characters)"
        
        # Check for path traversal attempts
        for pattern in InputValidator.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, index_name, re.IGNORECASE):
                logger.warning(f"Path traversal attempt in index name: {index_name}")
                return False, "Invalid index name format"
        
        return True, None
    
    @staticmethod
    def validate_integer(value: any, min_val: int = 1, max_val: int = 100, 
                        param_name: str = "value") -> Tuple[bool, Optional[str], int]:
        """
        Validate integer input with bounds checking
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            param_name: Parameter name for error messages
            
        Returns:
            (is_valid, error_message, validated_value)
        """
        try:
            int_value = int(value)
            
            if int_value < min_val:
                return False, f"{param_name} must be at least {min_val}", min_val
            
            if int_value > max_val:
                return False, f"{param_name} cannot exceed {max_val}", max_val
            
            return True, None, int_value
            
        except (ValueError, TypeError):
            return False, f"{param_name} must be a valid integer", min_val
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: List[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate URL input
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
            
        Returns:
            (is_valid, error_message)
        """
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme:
                return False, "URL must include a scheme (http:// or https://)"
            
            if parsed.scheme.lower() not in allowed_schemes:
                return False, f"URL scheme must be one of: {', '.join(allowed_schemes)}"
            
            if not parsed.netloc:
                return False, "URL must include a domain"
            
            # Check for suspicious patterns
            if re.search(r'javascript:|data:|vbscript:', url, re.IGNORECASE):
                logger.warning(f"Suspicious URL scheme detected: {url}")
                return False, "URL contains potentially malicious content"
            
            return True, None
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False, "Invalid URL format"
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 255) -> str:
        """
        Sanitize filename for safe file operations
        
        Args:
            filename: Original filename
            max_length: Maximum filename length
            
        Returns:
            Sanitized filename
        """
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Remove dangerous characters
        filename = re.sub(r'[^\w\s.-]', '', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > max_length:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_len = max_length - len(ext) - 1
            filename = f"{name[:max_name_len]}.{ext}" if ext else name[:max_length]
        
        # Ensure not empty
        if not filename:
            filename = "unnamed_file"
        
        return filename
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email address format
        
        Args:
            email: Email address to validate
            
        Returns:
            (is_valid, error_message)
        """
        # RFC 5322 simplified pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not email or len(email) > 254:  # RFC 5321
            return False, "Invalid email length"
        
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        return True, None


# Convenience functions for common validations

def validate_search_query(query: str) -> Tuple[bool, Optional[str], str]:
    """Validate search query - convenience wrapper"""
    return InputValidator.validate_query(query)


def validate_collection_name(name: str) -> Tuple[bool, Optional[str]]:
    """Validate collection/index name - convenience wrapper"""
    return InputValidator.validate_index_name(name)


def validate_top_k(value: any) -> Tuple[bool, Optional[str], int]:
    """Validate top_k parameter - convenience wrapper"""
    return InputValidator.validate_integer(value, min_val=1, max_val=100, param_name="top_k")
