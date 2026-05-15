"""
Tests for Input Validator
=========================

Comprehensive test suite for OWASP-compliant input validation.
Tests cover XSS, SQL injection, command injection, and other attack vectors.
"""

import pytest
from utils.security.input_validator import (
    InputValidator,
    validate_search_query,
    validate_collection_name,
    validate_top_k
)


class TestQueryValidation:
    """Test query validation"""
    
    def test_valid_query(self):
        """Test valid query passes validation"""
        valid, error, sanitized = InputValidator.validate_query("What are the board meeting requirements?")
        assert valid is True
        assert error is None
        assert len(sanitized) > 0
    
    def test_query_too_short(self):
        """Test query too short fails validation"""
        valid, error, sanitized = InputValidator.validate_query("ab")
        assert valid is False
        assert "at least 3 characters" in error
    
    def test_query_too_long(self):
        """Test query too long fails validation"""
        long_query = "x" * 1001
        valid, error, sanitized = InputValidator.validate_query(long_query)
        assert valid is False
        assert "too long" in error
    
    def test_empty_query(self):
        """Test empty query fails validation"""
        valid, error, sanitized = InputValidator.validate_query("")
        assert valid is False
        assert "cannot be empty" in error
    
    def test_xss_script_tag(self):
        """Test XSS with script tag is blocked"""
        malicious = "<script>alert('xss')</script>"
        valid, error, sanitized = InputValidator.validate_query(malicious)
        assert valid is False
        assert "XSS" in error or "malicious" in error
    
    def test_xss_javascript_protocol(self):
        """Test XSS with javascript: protocol is blocked"""
        malicious = "javascript:alert('xss')"
        valid, error, sanitized = InputValidator.validate_query(malicious)
        assert valid is False
        assert "malicious" in error
    
    def test_xss_onerror_attribute(self):
        """Test XSS with onerror attribute is blocked"""
        malicious = "<img src=x onerror=alert('xss')>"
        valid, error, sanitized = InputValidator.validate_query(malicious)
        assert valid is False
        assert "malicious" in error
    
    def test_sql_injection_union(self):
        """Test SQL injection with UNION is blocked"""
        malicious = "test' UNION SELECT * FROM users--"
        valid, error, sanitized = InputValidator.validate_query(malicious)
        assert valid is False
        assert "SQL" in error or "malicious" in error
    
    def test_sql_injection_or_equals(self):
        """Test SQL injection with OR 1=1 is blocked"""
        malicious = "test' OR '1'='1"
        valid, error, sanitized = InputValidator.validate_query(malicious)
        assert valid is False
        assert "SQL" in error or "malicious" in error
    
    def test_sql_injection_drop_table(self):
        """Test SQL injection with DROP TABLE is blocked"""
        malicious = "test'; DROP TABLE users;--"
        valid, error, sanitized = InputValidator.validate_query(malicious)
        assert valid is False
        assert "SQL" in error or "malicious" in error
    
    def test_command_injection_pipe(self):
        """Test command injection with pipe is blocked"""
        malicious = "test | cat /etc/passwd"
        valid, error, sanitized = InputValidator.validate_query(malicious)
        assert valid is False
        assert "CMD" in error or "malicious" in error
    
    def test_command_injection_semicolon(self):
        """Test command injection with semicolon is blocked"""
        malicious = "test; rm -rf /"
        valid, error, sanitized = InputValidator.validate_query(malicious)
        assert valid is False
        assert "CMD" in error or "malicious" in error
    
    def test_html_entities_escaped(self):
        """Test HTML entities are properly escaped"""
        query = "What is <b>bold</b> text?"
        valid, error, sanitized = InputValidator.validate_query(query)
        assert valid is True
        assert "&lt;b&gt;" in sanitized or "<b>" not in sanitized
    
    def test_whitespace_normalized(self):
        """Test whitespace is normalized"""
        query = "test    query   with    spaces"
        valid, error, sanitized = InputValidator.validate_query(query)
        assert valid is True
        assert "  " not in sanitized  # No double spaces
    
    def test_control_characters_removed(self):
        """Test control characters are removed"""
        query = "test\x00\x01\x02query"
        valid, error, sanitized = InputValidator.validate_query(query)
        assert valid is True
        assert "\x00" not in sanitized


class TestIndexNameValidation:
    """Test index/collection name validation"""
    
    def test_valid_index_name(self):
        """Test valid index name passes"""
        valid, error = InputValidator.validate_index_name("test_index")
        assert valid is True
        assert error is None
    
    def test_index_name_with_hyphen(self):
        """Test index name with hyphen passes"""
        valid, error = InputValidator.validate_index_name("test-index-123")
        assert valid is True
    
    def test_empty_index_name(self):
        """Test empty index name fails"""
        valid, error = InputValidator.validate_index_name("")
        assert valid is False
        assert "required" in error
    
    def test_index_name_with_special_chars(self):
        """Test index name with special characters fails"""
        valid, error = InputValidator.validate_index_name("test@index")
        assert valid is False
        assert "letters, numbers" in error
    
    def test_index_name_with_spaces(self):
        """Test index name with spaces fails"""
        valid, error = InputValidator.validate_index_name("test index")
        assert valid is False
    
    def test_index_name_too_long(self):
        """Test index name too long fails"""
        long_name = "x" * 101
        valid, error = InputValidator.validate_index_name(long_name)
        assert valid is False
        assert "too long" in error
    
    def test_path_traversal_attempt(self):
        """Test path traversal attempt is blocked"""
        valid, error = InputValidator.validate_index_name("../etc/passwd")
        assert valid is False


class TestIntegerValidation:
    """Test integer validation"""
    
    def test_valid_integer(self):
        """Test valid integer passes"""
        valid, error, value = InputValidator.validate_integer(5, 1, 10)
        assert valid is True
        assert error is None
        assert value == 5
    
    def test_integer_below_minimum(self):
        """Test integer below minimum fails"""
        valid, error, value = InputValidator.validate_integer(0, 1, 10)
        assert valid is False
        assert "at least" in error
        assert value == 1  # Returns min value
    
    def test_integer_above_maximum(self):
        """Test integer above maximum fails"""
        valid, error, value = InputValidator.validate_integer(15, 1, 10)
        assert valid is False
        assert "cannot exceed" in error
        assert value == 10  # Returns max value
    
    def test_non_integer_string(self):
        """Test non-integer string fails"""
        valid, error, value = InputValidator.validate_integer("abc", 1, 10)
        assert valid is False
        assert "valid integer" in error
    
    def test_float_converted_to_int(self):
        """Test float is converted to integer"""
        valid, error, value = InputValidator.validate_integer(5.7, 1, 10)
        assert valid is True
        assert value == 5


class TestURLValidation:
    """Test URL validation"""
    
    def test_valid_http_url(self):
        """Test valid HTTP URL passes"""
        valid, error = InputValidator.validate_url("http://example.com")
        assert valid is True
        assert error is None
    
    def test_valid_https_url(self):
        """Test valid HTTPS URL passes"""
        valid, error = InputValidator.validate_url("https://example.com/path")
        assert valid is True
    
    def test_url_without_scheme(self):
        """Test URL without scheme fails"""
        valid, error = InputValidator.validate_url("example.com")
        assert valid is False
        assert "scheme" in error
    
    def test_javascript_url_blocked(self):
        """Test javascript: URL is blocked"""
        valid, error = InputValidator.validate_url("javascript:alert('xss')")
        assert valid is False
        assert "malicious" in error
    
    def test_data_url_blocked(self):
        """Test data: URL is blocked"""
        valid, error = InputValidator.validate_url("data:text/html,<script>alert('xss')</script>")
        assert valid is False
        assert "malicious" in error
    
    def test_ftp_url_blocked_by_default(self):
        """Test FTP URL is blocked by default"""
        valid, error = InputValidator.validate_url("ftp://example.com")
        assert valid is False
        assert "scheme" in error
    
    def test_custom_allowed_schemes(self):
        """Test custom allowed schemes"""
        valid, error = InputValidator.validate_url("ftp://example.com", allowed_schemes=['ftp'])
        assert valid is True


class TestFilenameValidation:
    """Test filename sanitization"""
    
    def test_valid_filename(self):
        """Test valid filename is unchanged"""
        sanitized = InputValidator.sanitize_filename("document.pdf")
        assert sanitized == "document.pdf"
    
    def test_filename_with_path(self):
        """Test path components are removed"""
        sanitized = InputValidator.sanitize_filename("/path/to/document.pdf")
        assert sanitized == "document.pdf"
    
    def test_filename_with_windows_path(self):
        """Test Windows path components are removed"""
        sanitized = InputValidator.sanitize_filename("C:\\Users\\test\\document.pdf")
        assert sanitized == "document.pdf"
    
    def test_filename_with_special_chars(self):
        """Test special characters are removed"""
        sanitized = InputValidator.sanitize_filename("doc@#$%ument.pdf")
        assert "document" in sanitized
        assert "@" not in sanitized
    
    def test_filename_too_long(self):
        """Test long filename is truncated"""
        long_name = "x" * 300 + ".pdf"
        sanitized = InputValidator.sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".pdf")
    
    def test_empty_filename(self):
        """Test empty filename gets default name"""
        sanitized = InputValidator.sanitize_filename("")
        assert sanitized == "unnamed_file"


class TestEmailValidation:
    """Test email validation"""
    
    def test_valid_email(self):
        """Test valid email passes"""
        valid, error = InputValidator.validate_email("user@example.com")
        assert valid is True
        assert error is None
    
    def test_email_with_plus(self):
        """Test email with plus sign passes"""
        valid, error = InputValidator.validate_email("user+tag@example.com")
        assert valid is True
    
    def test_email_without_at(self):
        """Test email without @ fails"""
        valid, error = InputValidator.validate_email("userexample.com")
        assert valid is False
        assert "format" in error
    
    def test_email_without_domain(self):
        """Test email without domain fails"""
        valid, error = InputValidator.validate_email("user@")
        assert valid is False
    
    def test_email_too_long(self):
        """Test email too long fails"""
        long_email = "x" * 250 + "@example.com"
        valid, error = InputValidator.validate_email(long_email)
        assert valid is False
        assert "length" in error


class TestConvenienceFunctions:
    """Test convenience wrapper functions"""
    
    def test_validate_search_query_wrapper(self):
        """Test validate_search_query convenience function"""
        valid, error, sanitized = validate_search_query("test query")
        assert valid is True
    
    def test_validate_collection_name_wrapper(self):
        """Test validate_collection_name convenience function"""
        valid, error = validate_collection_name("test_collection")
        assert valid is True
    
    def test_validate_top_k_wrapper(self):
        """Test validate_top_k convenience function"""
        valid, error, value = validate_top_k(5)
        assert valid is True
        assert value == 5


# Performance tests
class TestValidationPerformance:
    """Test validation performance"""
    
    def test_query_validation_performance(self, benchmark):
        """Benchmark query validation performance"""
        query = "What are the board meeting requirements?"
        result = benchmark(InputValidator.validate_query, query)
        assert result[0] is True  # Should be valid
    
    def test_xss_detection_performance(self, benchmark):
        """Benchmark XSS detection performance"""
        malicious = "<script>alert('xss')</script>" * 10
        result = benchmark(InputValidator.validate_query, malicious)
        assert result[0] is False  # Should be blocked


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
