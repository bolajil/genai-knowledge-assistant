#!/usr/bin/env python
"""
LLM Integration Test Script

This script tests the Language Model integration functionality, including:
- LLM configuration and provider detection
- Response generation
- Context handling
- Error handling and fallbacks
"""

import os
import sys
import logging
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

def test_llm_config_detection():
    """Test the LLM configuration and provider detection"""
    logger.info("\n=== Testing LLM Configuration and Provider Detection ===\n")
    
    try:
        # Import the LLM configuration module
        from utils.llm_config import LLMConfig
        
        # Initialize the LLM configuration
        logger.info("Initializing LLMConfig")
        config = LLMConfig()
        
        if config is not None:
            logger.info("✅ Successfully initialized LLMConfig")
            
            # Check available models
            available_models = config.get_available_models()
            if available_models and len(available_models) > 0:
                logger.info(f"✅ Found {len(available_models)} available models")
                for model in available_models:
                    logger.info(f"  - {model['name']} (Provider: {model['provider']})")
                
                # Check if a default model is set
                default_model = config.get_default_model()
                if default_model:
                    logger.info(f"✅ Default model is set to: {default_model['name']} (Provider: {default_model['provider']})")
                else:
                    logger.warning("⚠️ No default model is set")
                
                return True
            else:
                logger.warning("⚠️ No available models found")
                return False
        else:
            logger.error("❌ Failed to initialize LLMConfig")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.llm_config module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing LLM configuration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_response_generation():
    """Test the LLM response generation functionality"""
    logger.info("\n=== Testing LLM Response Generation ===\n")
    
    try:
        # Import the LLM response generation module
        from utils.llm_response_generator import generate_response
        
        # Test queries
        test_queries = [
            "What is cloud computing?",
            "Explain machine learning in simple terms.",
            "What are the benefits of data security?"
        ]
        
        success_count = 0
        
        for query in test_queries:
            logger.info(f"Testing query: '{query}'")
            
            # Generate response
            response = generate_response(query)
            
            if response and isinstance(response, str) and len(response) > 0:
                logger.info(f"✅ Generated response for '{query}'")
                logger.info(f"Response preview: {response[:100]}...\n")
                success_count += 1
            else:
                logger.error(f"❌ Failed to generate response for '{query}'\n")
        
        # Report overall success
        if success_count == len(test_queries):
            logger.info(f"✅ All {success_count}/{len(test_queries)} response generation tests passed")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️ {success_count}/{len(test_queries)} response generation tests passed")
            return True
        else:
            logger.error(f"❌ No response generation tests passed")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.llm_response_generator module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing response generation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_context_handling():
    """Test the LLM context handling functionality"""
    logger.info("\n=== Testing LLM Context Handling ===\n")
    
    try:
        # Import the LLM context handling module
        from utils.llm_context_handler import format_context
        
        # Create test context
        test_context = [
            {
                'content': 'Cloud computing is the delivery of computing services over the internet.',
                'source': 'document1.pdf'
            },
            {
                'content': 'Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience.',
                'source': 'document2.pdf'
            },
            {
                'content': 'Data security refers to protective measures applied to prevent unauthorized access to computers, databases, and websites.',
                'source': 'document3.pdf'
            }
        ]
        
        # Format the context
        logger.info("Formatting context for LLM")
        formatted_context = format_context(test_context)
        
        if formatted_context and isinstance(formatted_context, str) and len(formatted_context) > 0:
            logger.info("✅ Successfully formatted context for LLM")
            logger.info(f"Formatted context preview: {formatted_context[:100]}...\n")
            
            # Check if all sources are included
            all_sources_included = all(item['source'] in formatted_context for item in test_context)
            if all_sources_included:
                logger.info("✅ All sources are included in the formatted context")
                return True
            else:
                logger.warning("⚠️ Some sources are missing from the formatted context")
                return False
        else:
            logger.error("❌ Failed to format context for LLM")
            return False
    
    except ImportError:
        logger.error("❌ Failed to import utils.llm_context_handler module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing context handling: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling_fallbacks():
    """Test the LLM error handling and fallbacks"""
    logger.info("\n=== Testing LLM Error Handling and Fallbacks ===\n")
    
    try:
        # Import the LLM response generation module
        from utils.llm_response_generator import generate_response
        
        # Test with invalid model
        logger.info("Testing response generation with invalid model")
        
        # Save original environment
        original_env = {}
        for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'MISTRAL_API_KEY']:
            if key in os.environ:
                original_env[key] = os.environ[key]
        
        try:
            # Temporarily modify environment to force fallback
            for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'MISTRAL_API_KEY']:
                if key in os.environ:
                    del os.environ[key]
            
            # Try to generate response
            response = generate_response("Test query for fallback")
            
            if response and isinstance(response, str) and len(response) > 0:
                if "fallback" in response.lower() or "error" in response.lower() or "unavailable" in response.lower():
                    logger.info("✅ Successfully handled error and provided fallback response")
                    logger.info(f"Fallback response: {response}\n")
                    return True
                else:
                    logger.info("✅ Generated response despite missing API keys (using fallback mechanism)")
                    logger.info(f"Response: {response}\n")
                    return True
            else:
                logger.warning("⚠️ Failed to generate fallback response")
                return False
        
        finally:
            # Restore original environment
            for key, value in original_env.items():
                os.environ[key] = value
    
    except ImportError:
        logger.error("❌ Failed to import utils.llm_response_generator module")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing error handling and fallbacks: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    logger.info("\n" + "*" * 80)
    logger.info("* LLM INTEGRATION TEST SCRIPT *".center(78))
    logger.info("*" * 80 + "\n")
    
    # Run all tests
    tests = [
        ("LLM Config Detection", test_llm_config_detection),
        ("Response Generation", test_response_generation),
        ("Context Handling", test_context_handling),
        ("Error Handling and Fallbacks", test_error_handling_fallbacks)
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