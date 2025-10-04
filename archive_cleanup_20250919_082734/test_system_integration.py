#!/usr/bin/env python
"""
System Integration Test Script

This script tests the integration of all components in the VaultMIND Knowledge Assistant system, including:
- End-to-end query processing
- Document ingestion to query flow
- ByLaw content access integration
- LLM response generation with context
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

def test_end_to_end_query_processing():
    """Test the end-to-end query processing flow"""
    logger.info("\n=== Testing End-to-End Query Processing ===\n")
    
    try:
        # Import the query processing modules
        from tabs.query_assistant import process_query
        
        # Test queries
        test_queries = [
            "What is cloud computing?",
            "Explain machine learning in simple terms.",
            "What are the benefits of data security?"
        ]
        
        success_count = 0
        
        for query in test_queries:
            logger.info(f"Testing query: '{query}'")
            
            # Process the query
            response = process_query(query)
            
            if response and isinstance(response, (str, dict)) and (isinstance(response, str) and len(response) > 0 or isinstance(response, dict) and response.get('response')):
                logger.info(f"✅ Successfully processed query: '{query}'")
                
                # Extract the response text
                response_text = response if isinstance(response, str) else response.get('response', '')
                logger.info(f"Response preview: {response_text[:100]}...\n")
                
                success_count += 1
            else:
                logger.error(f"❌ Failed to process query: '{query}'\n")
        
        # Report overall success
        if success_count == len(test_queries):
            logger.info(f"✅ All {success_count}/{len(test_queries)} query processing tests passed")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️ {success_count}/{len(test_queries)} query processing tests passed")
            return True
        else:
            logger.error(f"❌ No query processing tests passed")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import tabs.query_assistant module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing end-to-end query processing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_document_ingestion_to_query_flow():
    """Test the flow from document ingestion to query"""
    logger.info("\n=== Testing Document Ingestion to Query Flow ===\n")
    
    try:
        # Import the document ingestion and query modules
        from tabs.document_ingestion import process_document
        from tabs.query_assistant import query_index
        
        # Create a temporary test document
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"Cloud computing is the delivery of computing services over the internet.\n" * 10)
            temp_file.write(b"Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience.\n" * 10)
            temp_file.write(b"Data security refers to protective measures applied to prevent unauthorized access to computers, databases, and websites.\n" * 10)
            temp_file_path = temp_file.name
        
        try:
            # Create a test index name
            test_index_name = f"test_integration_{os.path.basename(temp_file_path)}"
            
            # Process the document
            logger.info(f"Processing test document: {temp_file_path} into index: {test_index_name}")
            ingest_result = process_document(temp_file_path, test_index_name)
            
            if ingest_result and isinstance(ingest_result, dict) and ingest_result.get('success', False):
                logger.info(f"✅ Successfully ingested document: {ingest_result}")
                
                # Test queries against the new index
                test_queries = [
                    "What is cloud computing?",
                    "Explain machine learning.",
                    "What is data security?"
                ]
                
                success_count = 0
                
                for query in test_queries:
                    logger.info(f"Testing query: '{query}' against index: '{test_index_name}'")
                    
                    # Query the index
                    results = query_index(query, test_index_name, top_k=3)
                    
                    if results and len(results) > 0:
                        logger.info(f"✅ Query returned {len(results)} results")
                        
                        # Check if the results contain relevant content
                        relevant_terms = query.lower().split()
                        content = ""
                        
                        if isinstance(results[0], dict) and 'content' in results[0]:
                            content = results[0]['content'].lower()
                        elif hasattr(results[0], 'content'):
                            content = results[0].content.lower()
                        else:
                            content = str(results[0]).lower()
                        
                        if any(term in content for term in relevant_terms):
                            logger.info(f"✅ Results contain relevant content for '{query}'")
                            logger.info(f"Content preview: {content[:100]}...\n")
                            success_count += 1
                        else:
                            logger.warning(f"⚠️ Results may not contain relevant content for '{query}'")
                            logger.info(f"Content preview: {content[:100]}...\n")
                            success_count += 0.5  # Partial success
                    else:
                        logger.error(f"❌ Query returned no results for '{query}'\n")
                
                # Report overall success
                if success_count == len(test_queries):
                    logger.info(f"✅ All {success_count}/{len(test_queries)} ingestion-to-query tests passed")
                    return True
                elif success_count > 0:
                    logger.warning(f"⚠️ {success_count}/{len(test_queries)} ingestion-to-query tests passed")
                    return True
                else:
                    logger.error(f"❌ No ingestion-to-query tests passed")
                    return False
            else:
                logger.error(f"❌ Failed to ingest document: {ingest_result}")
                return False
        
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
    
    except ImportError:
        logger.error("❌ Failed to import required modules")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing document ingestion to query flow: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bylaw_integration_with_llm():
    """Test the integration of ByLaw content access with LLM response generation"""
    logger.info("\n=== Testing ByLaw Integration with LLM ===\n")
    
    try:
        # Import the ByLaw and LLM integration modules
        from utils.bylaw_query_patch import is_bylaw_query
        from utils.direct_bylaws_retriever import search_bylaws
        from utils.enhanced_llm_bylaw_patch import get_bylaw_enhanced_response
        
        # Test queries
        test_queries = [
            "Tell me about board meetings",
            "How do directors vote electronically?",
            "What is the quorum for board meetings?"
        ]
        
        success_count = 0
        
        for query in test_queries:
            logger.info(f"Testing ByLaw query: '{query}'")
            
            # Check if it's a ByLaw query
            is_bylaw = is_bylaw_query(query, "ByLawS2_index")
            
            if is_bylaw:
                logger.info(f"✅ Query '{query}' detected as ByLaw query")
                
                # Search for ByLaw content
                results = search_bylaws(query, max_results=3)
                
                if results and len(results) > 0:
                    logger.info(f"✅ Found {len(results)} ByLaw results for '{query}'")
                    
                    # Generate enhanced response
                    response = get_bylaw_enhanced_response(query, results)
                    
                    if response and isinstance(response, dict) and 'result' in response:
                        logger.info(f"✅ Generated enhanced response for '{query}'")
                        logger.info(f"Response preview: {response['result'][:100]}...\n")
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ Failed to generate enhanced response for '{query}'")
                        logger.info(f"Response: {response}\n")
                else:
                    logger.warning(f"⚠️ No ByLaw results found for '{query}'\n")
            else:
                logger.warning(f"⚠️ Query '{query}' not detected as ByLaw query\n")
        
        # Report overall success
        if success_count == len(test_queries):
            logger.info(f"✅ All {success_count}/{len(test_queries)} ByLaw integration tests passed")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️ {success_count}/{len(test_queries)} ByLaw integration tests passed")
            return True
        else:
            logger.error(f"❌ No ByLaw integration tests passed")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import required modules")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing ByLaw integration with LLM: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_history_management():
    """Test the chat history management functionality"""
    logger.info("\n=== Testing Chat History Management ===\n")
    
    try:
        # Import the chat history management module
        from tabs.chat_assistant import ChatHistory
        
        # Initialize chat history
        logger.info("Initializing ChatHistory")
        chat_history = ChatHistory()
        
        if chat_history is not None:
            logger.info("✅ Successfully initialized ChatHistory")
            
            # Test adding messages
            logger.info("Testing adding messages to chat history")
            
            # Add user message
            chat_history.add_user_message("What is cloud computing?")
            
            # Add assistant message
            chat_history.add_assistant_message("Cloud computing is the delivery of computing services over the internet.")
            
            # Get the history
            history = chat_history.get_history()
            
            if history and len(history) == 2:
                logger.info(f"✅ Chat history contains {len(history)} messages")
                
                # Check message types
                if history[0]['role'] == 'user' and history[1]['role'] == 'assistant':
                    logger.info("✅ Chat history contains correct message types")
                    
                    # Test clearing history
                    logger.info("Testing clearing chat history")
                    chat_history.clear()
                    
                    # Check if history is cleared
                    cleared_history = chat_history.get_history()
                    if not cleared_history or len(cleared_history) == 0:
                        logger.info("✅ Chat history successfully cleared")
                        return True
                    else:
                        logger.error("❌ Failed to clear chat history")
                        return False
                else:
                    logger.error("❌ Chat history contains incorrect message types")
                    return False
            else:
                logger.error(f"❌ Chat history contains {len(history) if history else 0} messages, expected 2")
                return False
        else:
            logger.error("❌ Failed to initialize ChatHistory")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import tabs.chat_assistant module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing chat history management: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    logger.info("\n" + "*" * 80)
    logger.info("* SYSTEM INTEGRATION TEST SCRIPT *".center(78))
    logger.info("*" * 80 + "\n")
    
    # Run all tests
    tests = [
        ("End-to-End Query Processing", test_end_to_end_query_processing),
        ("Document Ingestion to Query Flow", test_document_ingestion_to_query_flow),
        ("ByLaw Integration with LLM", test_bylaw_integration_with_llm),
        ("Chat History Management", test_chat_history_management)
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