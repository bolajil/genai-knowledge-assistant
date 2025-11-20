"""
Complete Response Formatter Test Suite
Tests all formatter functionality across all tabs
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.response_writer import rewrite_query_response, ResponseWriter, MarkdownEnhancer
from utils.universal_response_formatter import UniversalResponseFormatter, get_formatter
import time


class FormatterTestSuite:
    """Comprehensive test suite for response formatter"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name: str, func):
        """Run a test"""
        print(f"\n{'='*60}")
        print(f"🧪 Test: {name}")
        print(f"{'='*60}")
        
        try:
            result = func()
            if result:
                print(f"✅ PASSED: {name}")
                self.passed += 1
            else:
                print(f"❌ FAILED: {name}")
                self.failed += 1
            self.tests.append((name, result))
        except Exception as e:
            print(f"❌ ERROR: {name}")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
            self.failed += 1
            self.tests.append((name, False))
    
    def summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print(f"📊 Test Summary")
        print(f"{'='*60}")
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print(f"{'='*60}\n")
        
        if self.failed > 0:
            print("Failed Tests:")
            for name, result in self.tests:
                if not result:
                    print(f"  ❌ {name}")
        
        return self.failed == 0


def test_basic_formatting():
    """Test basic response formatting"""
    raw = "The board has three main powers: legislative, executive, and judicial."
    query = "What powers does the board have?"
    
    formatted = rewrite_query_response(raw, query)
    
    # Check that formatting was applied
    assert len(formatted) > len(raw), "Formatted response should be longer"
    assert "# 🔍 Query Results" in formatted, "Should have main heading"
    assert query in formatted, "Should include original query"
    assert "legislative" in formatted, "Should preserve content"
    
    print(f"✓ Raw length: {len(raw)}")
    print(f"✓ Formatted length: {len(formatted)}")
    print(f"✓ Contains headings: Yes")
    print(f"✓ Preserves content: Yes")
    
    return True


def test_formatting_with_sources():
    """Test formatting with source citations"""
    raw = "The governance framework establishes comprehensive oversight."
    query = "What is the governance framework?"
    sources = [
        {
            'document': 'bylaws.pdf',
            'page': 15,
            'section': 'Article 2',
            'relevance': 0.95
        },
        {
            'document': 'governance.pdf',
            'page': 8,
            'relevance': 0.88
        }
    ]
    
    formatted = rewrite_query_response(raw, query, sources=sources)
    
    # Check source section
    assert "## 📚 Sources" in formatted, "Should have sources section"
    assert "bylaws.pdf" in formatted, "Should include first source"
    assert "governance.pdf" in formatted, "Should include second source"
    assert "95.00%" in formatted or "95%" in formatted, "Should show relevance"
    
    print(f"✓ Sources section present: Yes")
    print(f"✓ All sources included: Yes")
    print(f"✓ Relevance scores shown: Yes")
    
    return True


def test_formatting_with_metadata():
    """Test formatting with metadata"""
    raw = "The policy requires annual reviews."
    query = "What are the review requirements?"
    metadata = {
        'confidence': 0.92,
        'response_time': 1250.5,
        'sources_count': 3,
        'index_used': 'default_faiss'
    }
    
    formatted = rewrite_query_response(raw, query, metadata=metadata)
    
    # Check metadata section
    assert "## ℹ️ Query Information" in formatted, "Should have metadata section"
    assert "92" in formatted, "Should show confidence"
    assert "1250" in formatted, "Should show response time"
    assert "default_faiss" in formatted, "Should show index"
    
    print(f"✓ Metadata section present: Yes")
    print(f"✓ Confidence score shown: Yes")
    print(f"✓ Response time shown: Yes")
    print(f"✓ Index shown: Yes")
    
    return True


def test_complex_response():
    """Test formatting complex response with sections"""
    raw = """
    Executive Summary: The governance framework establishes comprehensive oversight.
    
    Detailed Analysis:
    1. Legislative powers include policy creation
    2. Executive powers cover implementation
    3. Judicial powers handle compliance
    
    Key Points:
    - Balanced power distribution
    - Clear accountability
    - Regular audits required
    """
    
    query = "Explain the governance framework"
    
    formatted = rewrite_query_response(raw, query, enhance=True)
    
    # Check section detection
    assert "Executive Summary" in formatted or "Summary" in formatted, "Should detect summary"
    assert "##" in formatted, "Should have section headings"
    assert "-" in formatted or "*" in formatted, "Should format lists"
    
    print(f"✓ Section detection: Yes")
    print(f"✓ List formatting: Yes")
    print(f"✓ Heading hierarchy: Yes")
    
    return True


def test_universal_formatter():
    """Test universal formatter for cross-tab use"""
    formatter = UniversalResponseFormatter("Test Tab")
    
    raw = "Test response content"
    query = "Test query"
    
    # Test format_response
    formatted = formatter.format_response(raw, query)
    
    assert formatted is not None, "Should return formatted response"
    assert len(formatted) > 0, "Formatted response should not be empty"
    
    print(f"✓ Universal formatter created: Yes")
    print(f"✓ Format response works: Yes")
    
    return True


def test_formatter_factory():
    """Test formatter factory pattern"""
    formatter1 = get_formatter("Query Assistant")
    formatter2 = get_formatter("Chat Assistant")
    formatter3 = get_formatter("Query Assistant")  # Should reuse
    
    assert formatter1 is not None, "Should create formatter"
    assert formatter2 is not None, "Should create different formatter"
    assert formatter1 is formatter3, "Should reuse same formatter"
    assert formatter1 is not formatter2, "Different tabs should have different formatters"
    
    print(f"✓ Formatter factory works: Yes")
    print(f"✓ Formatter reuse works: Yes")
    print(f"✓ Tab isolation works: Yes")
    
    return True


def test_performance():
    """Test formatter performance"""
    raw = "The board has three main powers: legislative, executive, and judicial." * 10
    query = "What powers does the board have?"
    
    # Test rule-based formatting speed
    start = time.time()
    formatted = rewrite_query_response(raw, query, use_llm=False)
    duration = (time.time() - start) * 1000
    
    assert duration < 500, f"Rule-based formatting should be fast (<500ms), got {duration:.2f}ms"
    
    print(f"✓ Rule-based formatting time: {duration:.2f}ms")
    print(f"✓ Performance acceptable: Yes")
    
    return True


def test_markdown_enhancements():
    """Test markdown enhancement features"""
    enhancer = MarkdownEnhancer()
    
    # Test syntax highlighting
    markdown = "```\nprint('hello')\n```"
    enhanced = enhancer.add_syntax_highlighting(markdown)
    assert "```python" in enhanced or "```text" in enhanced, "Should add language"
    
    print(f"✓ Syntax highlighting: Yes")
    
    # Test table beautification
    table = "| A | B |\n|---|---|\n| 1 | 2 |"
    beautified = enhancer.beautify_tables(table)
    assert "|" in beautified, "Should preserve table"
    
    print(f"✓ Table beautification: Yes")
    
    return True


def test_error_handling():
    """Test error handling and fallbacks"""
    # Test with None input
    try:
        formatted = rewrite_query_response("", "")
        assert formatted is not None, "Should handle empty input"
        print(f"✓ Empty input handling: Yes")
    except Exception as e:
        print(f"✗ Empty input handling failed: {e}")
        return False
    
    # Test with invalid sources
    try:
        formatted = rewrite_query_response(
            "test",
            "test",
            sources=[{'invalid': 'source'}]
        )
        assert formatted is not None, "Should handle invalid sources"
        print(f"✓ Invalid sources handling: Yes")
    except Exception as e:
        print(f"✗ Invalid sources handling failed: {e}")
        return False
    
    return True


def test_content_preservation():
    """Test that original content is preserved"""
    raw = """
    Important information about governance:
    - Point 1: Legislative authority
    - Point 2: Executive oversight
    - Point 3: Judicial review
    
    Critical note: All powers must be exercised responsibly.
    """
    
    query = "What are the governance powers?"
    formatted = rewrite_query_response(raw, query)
    
    # Check content preservation
    assert "Legislative authority" in formatted, "Should preserve point 1"
    assert "Executive oversight" in formatted, "Should preserve point 2"
    assert "Judicial review" in formatted, "Should preserve point 3"
    assert "responsibly" in formatted, "Should preserve critical note"
    
    print(f"✓ All content preserved: Yes")
    print(f"✓ No information loss: Yes")
    
    return True


def test_visual_output():
    """Test visual output quality"""
    raw = """
    The governance framework establishes three core powers:
    1. Legislative authority - creating bylaws and budget approval
    2. Executive oversight - operational control
    3. Judicial review - dispute resolution
    
    This creates a balanced system of checks and balances.
    """
    
    query = "What are the governance powers?"
    sources = [
        {'document': 'bylaws.pdf', 'page': 15, 'relevance': 0.95}
    ]
    metadata = {
        'confidence': 0.92,
        'response_time': 1250.5,
        'sources_count': 1,
        'index_used': 'default_faiss'
    }
    
    formatted = rewrite_query_response(
        raw, query, sources=sources, metadata=metadata, enhance=True
    )
    
    print("\n" + "="*60)
    print("VISUAL OUTPUT SAMPLE:")
    print("="*60)
    print(formatted)
    print("="*60)
    
    # Manual verification
    print("\n✓ Visual output generated")
    print("✓ Please verify formatting looks good above")
    
    return True


def run_all_tests():
    """Run all tests"""
    suite = FormatterTestSuite()
    
    print("\n" + "="*60)
    print("🚀 Response Formatter Test Suite")
    print("="*60)
    
    # Run tests
    suite.test("Basic Formatting", test_basic_formatting)
    suite.test("Formatting with Sources", test_formatting_with_sources)
    suite.test("Formatting with Metadata", test_formatting_with_metadata)
    suite.test("Complex Response", test_complex_response)
    suite.test("Universal Formatter", test_universal_formatter)
    suite.test("Formatter Factory", test_formatter_factory)
    suite.test("Performance", test_performance)
    suite.test("Markdown Enhancements", test_markdown_enhancements)
    suite.test("Error Handling", test_error_handling)
    suite.test("Content Preservation", test_content_preservation)
    suite.test("Visual Output", test_visual_output)
    
    # Print summary
    success = suite.summary()
    
    if success:
        print("🎉 All tests passed! Response formatter is ready to use.")
        print("\n📝 Next Steps:")
        print("  1. Run: python scripts/integrate_formatter_all_tabs.py")
        print("  2. Start Streamlit: streamlit run genai_dashboard_modular.py")
        print("  3. Test in Query Assistant tab")
        print("  4. Test in Chat Assistant tab")
        print("  5. Test in Agent Assistant tab")
    else:
        print("⚠️  Some tests failed. Please review errors above.")
    
    return success


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
