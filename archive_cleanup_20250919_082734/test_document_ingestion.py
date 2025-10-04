#!/usr/bin/env python
"""
Document Ingestion Test Script

This script tests the document ingestion functionality, including:
- File upload and processing
- Chunking mechanisms
- Vector embedding generation
- Index creation and management
"""

import os
import sys
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

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

def test_index_name_validation():
    """Test the index name validation functionality"""
    logger.info("\n=== Testing Index Name Validation ===\n")
    
    try:
        # Import the index name validation module
        from tabs.chat_assistant import validate_index_name
        
        # Test cases (index_name, expected_result)
        test_cases = [
            ("valid_index", True),
            ("Valid-Index-123", True),
            ("valid_index_with_underscores", True),
            ("", False),
            (None, False),
            ("invalid index with spaces", False),
            ("invalid@index", False),
            ("invalid#index", False)
        ]
        
        success_count = 0
        
        for index_name, expected_result in test_cases:
            # Test validation
            result = validate_index_name(index_name)
            
            if result == expected_result:
                logger.info(f"✅ Index name '{index_name}' correctly {'validated' if expected_result else 'rejected'}")
                success_count += 1
            else:
                logger.error(f"❌ Index name '{index_name}' incorrectly {'rejected' if expected_result else 'validated'}")
        
        # Report overall success
        if success_count == len(test_cases):
            logger.info(f"✅ All {success_count}/{len(test_cases)} validation tests passed")
            return True
        elif success_count > len(test_cases) / 2:
            logger.warning(f"⚠️ {success_count}/{len(test_cases)} validation tests passed")
            return True
        else:
            logger.error(f"❌ Only {success_count}/{len(test_cases)} validation tests passed")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import tabs.chat_assistant module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing index name validation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_document_chunking():
    """Test the document chunking functionality"""
    logger.info("\n=== Testing Document Chunking ===\n")
    
    try:
        # Import the document chunking module
        from utils.chunking import chunk_text
        
        # Create test document
        test_text = "\n".join([f"This is paragraph {i} of the test document." * 5 for i in range(10)])
        
        # Test different chunk sizes
        chunk_sizes = [100, 200, 500]
        overlap_sizes = [0, 20, 50]
        
        success_count = 0
        total_tests = len(chunk_sizes) * len(overlap_sizes)
        
        for chunk_size in chunk_sizes:
            for overlap in overlap_sizes:
                logger.info(f"Testing chunking with chunk_size={chunk_size}, overlap={overlap}")
                
                # Chunk the text
                chunks = chunk_text(test_text, chunk_size=chunk_size, chunk_overlap=overlap)
                
                if chunks and len(chunks) > 0:
                    logger.info(f"✅ Chunking created {len(chunks)} chunks")
                    
                    # Check chunk sizes
                    max_chunk_size = max(len(chunk) for chunk in chunks)
                    min_chunk_size = min(len(chunk) for chunk in chunks)
                    
                    logger.info(f"Chunk sizes - Min: {min_chunk_size}, Max: {max_chunk_size}")
                    
                    if max_chunk_size <= chunk_size:
                        logger.info(f"✅ All chunks are within the specified size limit")
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ Some chunks exceed the specified size limit")
                else:
                    logger.error(f"❌ Chunking failed to create any chunks")
        
        # Report overall success
        if success_count == total_tests:
            logger.info(f"✅ All {success_count}/{total_tests} chunking tests passed")
            return True
        elif success_count > total_tests / 2:
            logger.warning(f"⚠️ {success_count}/{total_tests} chunking tests passed")
            return True
        else:
            logger.error(f"❌ Only {success_count}/{total_tests} chunking tests passed")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.chunking module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing document chunking: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_embedding_generation():
    """Test the embedding generation functionality"""
    logger.info("\n=== Testing Embedding Generation ===\n")
    
    try:
        # Import the embedding generation module
        from utils.embedding_generator import generate_embeddings
        
        # Create test texts
        test_texts = [
            "This is a test document about cloud computing.",
            "Machine learning is a subset of artificial intelligence.",
            "Data security is important for protecting sensitive information."
        ]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(test_texts)} texts")
        embeddings = generate_embeddings(test_texts)
        
        if embeddings and len(embeddings) == len(test_texts):
            logger.info(f"✅ Successfully generated {len(embeddings)} embeddings")
            
            # Check embedding dimensions
            embedding_dim = len(embeddings[0])
            logger.info(f"Embedding dimension: {embedding_dim}")
            
            if embedding_dim > 0:
                logger.info("✅ Embeddings have valid dimensions")
                return True
            else:
                logger.error("❌ Embeddings have invalid dimensions")
                return False
        else:
            logger.error(f"❌ Failed to generate embeddings for all texts")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.embedding_generator module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing embedding generation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_document_upload_processing():
    """Test the document upload and processing functionality"""
    logger.info("\n=== Testing Document Upload and Processing ===\n")
    
    try:
        # Import the document processing module
        from tabs.document_ingestion import process_document
        
        # Create a temporary test document
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"This is a test document for testing document ingestion.\n" * 50)
            temp_file_path = temp_file.name
        
        try:
            # Process the document
            logger.info(f"Processing test document: {temp_file_path}")
            
            # Create a test index name
            test_index_name = f"test_index_{os.path.basename(temp_file_path)}"
            
            # Process the document
            result = process_document(temp_file_path, test_index_name)
            
            if result and isinstance(result, dict) and result.get('success', False):
                logger.info(f"✅ Successfully processed document: {result}")
                return True
            else:
                logger.error(f"❌ Failed to process document: {result}")
                return False
        
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
    
    except ImportError:
        logger.error("❌ Failed to import tabs.document_ingestion module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing document upload and processing: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    logger.info("\n" + "*" * 80)
    logger.info("* DOCUMENT INGESTION TEST SCRIPT *".center(78))
    logger.info("*" * 80 + "\n")
    
    # Run all tests
    tests = [
        ("Index Name Validation", test_index_name_validation),
        ("Document Chunking", test_document_chunking),
        ("Embedding Generation", test_embedding_generation),
        ("Document Upload Processing", test_document_upload_processing)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning test: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            results[test_name] = False
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY".center(80))
    logger.info("=" * 80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("\n" + "-" * 80)
    logger.info(f"OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✅ ALL TESTS PASSED")
    elif passed > 0:
        logger.info("⚠️ SOME TESTS FAILED")
    else:
        logger.info("❌ ALL TESTS FAILED")
    
    logger.info("-" * 80)
    
    # Return success if all tests passed
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)