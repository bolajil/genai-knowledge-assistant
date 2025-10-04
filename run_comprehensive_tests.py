#!/usr/bin/env python
"""
Comprehensive Test Suite for VaultMIND Knowledge Assistant

This script runs a comprehensive set of tests to verify the functionality
of the VaultMIND Knowledge Assistant system, including:
- Vector database functionality and fallback mechanisms
- Document ingestion and retrieval
- ByLaw content access and fixes
- LLM integration
- System component integration
"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import importlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to the path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Test results tracking
test_results = {
    "vector_db": {"passed": 0, "failed": 0, "skipped": 0},
    "document_ingestion": {"passed": 0, "failed": 0, "skipped": 0},
    "bylaw_access": {"passed": 0, "failed": 0, "skipped": 0},
    "llm_integration": {"passed": 0, "failed": 0, "skipped": 0},
    "system_integration": {"passed": 0, "failed": 0, "skipped": 0},
}

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def print_subheader(title: str):
    """Print a formatted subheader"""
    print("\n" + "-" * 80)
    print(f" {title} ".center(80, "-"))
    print("-" * 80)

def print_result(test_name: str, success: bool, message: str = ""):
    """Print a test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}" + (f": {message}" if message else ""))
    return success

def test_vector_db_functionality():
    """Test vector database functionality and fallback mechanisms"""
    print_header("Vector Database Functionality Tests")
    
    # Test 1: Check if vector database provider is available
    print_subheader("Testing Vector DB Provider Availability")
    try:
        from utils.vector_db_init import get_any_vector_db_provider
        provider = get_any_vector_db_provider()
        
        if provider is None:
            print_result("Vector DB Provider", False, "Provider is None")
            test_results["vector_db"]["failed"] += 1
        else:
            print_result("Vector DB Provider", True, "Provider initialized successfully")
            test_results["vector_db"]["passed"] += 1
            
            # Test 2: Check vector database status
            status, message = provider.get_vector_db_status()
            print_result("Vector DB Status", status == "Ready", f"Status: {status}, Message: {message}")
            test_results["vector_db"]["passed" if status == "Ready" else "failed"] += 1
            
            # Test 3: Get available indexes
            indexes = provider.get_available_indexes()
            print_result("Available Indexes", len(indexes) > 0, f"Found {len(indexes)} indexes: {indexes}")
            test_results["vector_db"]["passed" if len(indexes) > 0 else "failed"] += 1
            
            # Test 4: Test search functionality
            if len(indexes) > 0:
                results = provider.search_index("test query", indexes[0], top_k=2)
                print_result("Search Functionality", isinstance(results, list), 
                             f"Search returned {len(results)} results")
                test_results["vector_db"]["passed" if isinstance(results, list) else "failed"] += 1
            else:
                print_result("Search Functionality", False, "No indexes available for testing")
                test_results["vector_db"]["skipped"] += 1
    
    except Exception as e:
        print_result("Vector DB Provider", False, f"Error: {str(e)}")
        test_results["vector_db"]["failed"] += 1
        import traceback
        traceback.print_exc()
    
    # Test 5: Check fallback mechanism (mock provider)
    print_subheader("Testing Fallback Mechanism")
    try:
        from utils.mock_vector_db_provider import get_mock_vector_db_provider
        mock_provider = get_mock_vector_db_provider()
        
        if mock_provider is None:
            print_result("Mock Vector DB Provider", False, "Mock provider is None")
            test_results["vector_db"]["failed"] += 1
        else:
            print_result("Mock Vector DB Provider", True, "Mock provider initialized successfully")
            test_results["vector_db"]["passed"] += 1
            
            # Test mock search
            mock_results = mock_provider.search("cloud security", max_results=2)
            print_result("Mock Search", len(mock_results) > 0, 
                         f"Mock search returned {len(mock_results)} results")
            test_results["vector_db"]["passed" if len(mock_results) > 0 else "failed"] += 1
    
    except Exception as e:
        print_result("Mock Vector DB Provider", False, f"Error: {str(e)}")
        test_results["vector_db"]["failed"] += 1
        import traceback
        traceback.print_exc()

def test_document_ingestion():
    """Test document ingestion and retrieval capabilities"""
    print_header("Document Ingestion and Retrieval Tests")
    
    # Test 1: Check if the chunking fix is working
    print_subheader("Testing Document Chunking")
    try:
        # Import the chunking module
        from utils.chunking_fix import chunk_document
        
        # Test with a sample document
        sample_text = """This is a test document for chunking.
It has multiple paragraphs.

This is the second paragraph.
It also has multiple lines.

This is the third paragraph with some special terms like WAIVER OF NOTICE."""
        
        chunks = chunk_document(sample_text)
        
        # Check if chunking works
        chunking_success = len(chunks) > 0
        print_result("Document Chunking", chunking_success, 
                     f"Chunking produced {len(chunks)} chunks")
        test_results["document_ingestion"]["passed" if chunking_success else "failed"] += 1
        
        # Check if special terms are preserved
        special_term_preserved = any("WAIVER OF NOTICE" in chunk for chunk in chunks)
        print_result("Special Term Preservation", special_term_preserved, 
                     "'WAIVER OF NOTICE' term is preserved")
        test_results["document_ingestion"]["passed" if special_term_preserved else "failed"] += 1
        
    except Exception as e:
        print_result("Document Chunking", False, f"Error: {str(e)}")
        test_results["document_ingestion"]["failed"] += 1
        import traceback
        traceback.print_exc()
    
    # Test 2: Check index name validation
    print_subheader("Testing Index Name Validation")
    try:
        # Try to import the validation function
        validation_module = importlib.import_module("utils.index_validation")
        validate_index_name = getattr(validation_module, "validate_index_name", None)
        
        if validate_index_name:
            # Test with various index names
            test_cases = [
                ("", "default_index"),  # Empty string should return default
                ("valid_index", "valid_index"),  # Valid name should be unchanged
                ("Invalid Name", "invalid_name"),  # Spaces should be replaced
            ]
            
            for input_name, expected_output in test_cases:
                result = validate_index_name(input_name)
                success = result == expected_output
                print_result(f"Validate '{input_name}'", success, 
                             f"Expected: '{expected_output}', Got: '{result}'")
                test_results["document_ingestion"]["passed" if success else "failed"] += 1
        else:
            print_result("Index Name Validation", False, "validate_index_name function not found")
            test_results["document_ingestion"]["skipped"] += 1
    
    except ImportError:
        print_result("Index Name Validation", False, "utils.index_validation module not found")
        test_results["document_ingestion"]["skipped"] += 1
    except Exception as e:
        print_result("Index Name Validation", False, f"Error: {str(e)}")
        test_results["document_ingestion"]["failed"] += 1

def test_bylaw_content_access():
    """Test ByLaw content access and fixes"""
    print_header("ByLaw Content Access Tests")
    
    # Test 1: Check if direct ByLaw retrieval works
    print_subheader("Testing Direct ByLaw Retrieval")
    try:
        from utils.direct_bylaws_retriever import search_bylaws
        
        # Test with a relevant query
        results = search_bylaws("board meeting")
        
        retrieval_success = len(results) > 0
        print_result("Direct ByLaw Retrieval", retrieval_success, 
                     f"Retrieved {len(results)} results")
        test_results["bylaw_access"]["passed" if retrieval_success else "failed"] += 1
        
        if retrieval_success:
            # Check content quality
            content_preview = results[0]['content'][:50] + "..."
            print(f"Content preview: {content_preview}")
    
    except ImportError:
        print_result("Direct ByLaw Retrieval", False, "utils.direct_bylaws_retriever module not found")
        test_results["bylaw_access"]["skipped"] += 1
    except Exception as e:
        print_result("Direct ByLaw Retrieval", False, f"Error: {str(e)}")
        test_results["bylaw_access"]["failed"] += 1
        import traceback
        traceback.print_exc()
    
    # Test 2: Check if ByLaw query detection works
    print_subheader("Testing ByLaw Query Detection")
    try:
        from utils.bylaw_query_patch import is_bylaw_query
        
        # Test with various queries
        test_queries = [
            ("Tell me about board meetings", True),
            ("How do directors vote electronically?", True),
            ("What is cloud computing?", False),
        ]
        
        for query, expected_result in test_queries:
            result = is_bylaw_query(query, "ByLawS2_index")
            success = result == expected_result
            print_result(f"Query: '{query}'", success, 
                         f"Expected: {expected_result}, Got: {result}")
            test_results["bylaw_access"]["passed" if success else "failed"] += 1
    
    except ImportError:
        print_result("ByLaw Query Detection", False, "utils.bylaw_query_patch module not found")
        test_results["bylaw_access"]["skipped"] += 1
    except Exception as e:
        print_result("ByLaw Query Detection", False, f"Error: {str(e)}")
        test_results["bylaw_access"]["failed"] += 1

def test_llm_integration():
    """Test LLM integration and response generation"""
    print_header("LLM Integration Tests")
    
    # Test 1: Check if LLM configuration is available
    print_subheader("Testing LLM Configuration")
    try:
        from utils.llm_config import LLMConfig
        
        # Initialize LLM config
        llm_config = LLMConfig()
        
        # Check if any models are available
        models_available = len(llm_config.available_models) > 0
        print_result("LLM Models Available", models_available, 
                     f"Found {len(llm_config.available_models)} models")
        test_results["llm_integration"]["passed" if models_available else "failed"] += 1
        
        if models_available:
            # Print available models
            for model in llm_config.available_models:
                print(f"  - {model['name']} ({model['provider']})")
    
    except ImportError:
        print_result("LLM Configuration", False, "utils.llm_config module not found")
        test_results["llm_integration"]["skipped"] += 1
    except Exception as e:
        print_result("LLM Configuration", False, f"Error: {str(e)}")
        test_results["llm_integration"]["failed"] += 1
        import traceback
        traceback.print_exc()
    
    # Test 2: Check if enhanced LLM ByLaw patch works
    print_subheader("Testing Enhanced LLM ByLaw Patch")
    try:
        from utils.enhanced_llm_bylaw_patch import get_bylaw_enhanced_response
        
        # Create mock search results
        mock_results = [
            {
                'content': 'This is a test document about board meetings',
                'source': 'test.pdf',
                'metadata': {'source': 'test.pdf'}
            }
        ]
        
        # Get enhanced response
        response = get_bylaw_enhanced_response("board meeting", mock_results)
        
        # Check if response is valid
        response_valid = isinstance(response, dict) and 'result' in response
        print_result("Enhanced LLM Response", response_valid, 
                     "Response has the expected format")
        test_results["llm_integration"]["passed" if response_valid else "failed"] += 1
    
    except ImportError:
        print_result("Enhanced LLM ByLaw Patch", False, "utils.enhanced_llm_bylaw_patch module not found")
        test_results["llm_integration"]["skipped"] += 1
    except Exception as e:
        print_result("Enhanced LLM ByLaw Patch", False, f"Error: {str(e)}")
        test_results["llm_integration"]["failed"] += 1

def test_system_integration():
    """Test system integration with all components"""
    print_header("System Integration Tests")
    
    # Test 1: Check if the main application can be imported
    print_subheader("Testing Main Application Import")
    try:
        import genai_dashboard
        print_result("Main Application Import", True, "genai_dashboard module imported successfully")
        test_results["system_integration"]["passed"] += 1
    except ImportError:
        print_result("Main Application Import", False, "genai_dashboard module not found")
        test_results["system_integration"]["failed"] += 1
    except Exception as e:
        print_result("Main Application Import", False, f"Error: {str(e)}")
        test_results["system_integration"]["failed"] += 1
    
    # Test 2: Check if the document retrieval fix can be applied
    print_subheader("Testing Document Retrieval Fix")
    try:
        from fix_document_retrieval import apply_fixes
        
        # Don't actually apply the fixes, just check if the function exists
        print_result("Document Retrieval Fix", callable(apply_fixes), 
                     "apply_fixes function is available")
        test_results["system_integration"]["passed" if callable(apply_fixes) else "failed"] += 1
    
    except ImportError:
        print_result("Document Retrieval Fix", False, "fix_document_retrieval module not found")
        test_results["system_integration"]["failed"] += 1
    except Exception as e:
        print_result("Document Retrieval Fix", False, f"Error: {str(e)}")
        test_results["system_integration"]["failed"] += 1
    
    # Test 3: Check if the ByLaw fix can be applied
    print_subheader("Testing ByLaw Fix")
    try:
        # Try to import the ByLaw fix module
        bylaw_fix_module = importlib.import_module("run_bylaw_fix")
        
        # Check if the main function exists
        main_func = getattr(bylaw_fix_module, "main", None)
        
        print_result("ByLaw Fix", callable(main_func), 
                     "main function is available")
        test_results["system_integration"]["passed" if callable(main_func) else "failed"] += 1
    
    except ImportError:
        print_result("ByLaw Fix", False, "run_bylaw_fix module not found")
        test_results["system_integration"]["failed"] += 1
    except Exception as e:
        print_result("ByLaw Fix", False, f"Error: {str(e)}")
        test_results["system_integration"]["failed"] += 1

def print_summary():
    """Print a summary of all test results"""
    print_header("Test Summary")
    
    total_passed = sum(results["passed"] for results in test_results.values())
    total_failed = sum(results["failed"] for results in test_results.values())
    total_skipped = sum(results["skipped"] for results in test_results.values())
    total_tests = total_passed + total_failed + total_skipped
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)")
    print(f"Failed: {total_failed} ({total_failed/total_tests*100:.1f}%)")
    print(f"Skipped: {total_skipped} ({total_skipped/total_tests*100:.1f}%)")
    
    print("\nResults by Category:")
    for category, results in test_results.items():
        category_total = results["passed"] + results["failed"] + results["skipped"]
        if category_total > 0:
            pass_rate = results["passed"] / category_total * 100
            print(f"  {category}: {results['passed']}/{category_total} passed ({pass_rate:.1f}%)")

def main():
    """Main function"""
    print("\n" + "*" * 80)
    print(" VAULTMIND KNOWLEDGE ASSISTANT - COMPREHENSIVE TEST SUITE ".center(80, "*"))
    print("*" * 80 + "\n")
    
    print("Starting tests at", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Run all tests
    test_vector_db_functionality()
    test_document_ingestion()
    test_bylaw_content_access()
    test_llm_integration()
    test_system_integration()
    
    # Print summary
    print_summary()
    
    # Return success if no tests failed
    total_failed = sum(results["failed"] for results in test_results.values())
    return total_failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)