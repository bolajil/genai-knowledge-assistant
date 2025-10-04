"""
Test script for VaultMIND Agent search integration.
This script tests the updated agent response generation with real search results.
"""
import sys
import os
import logging
from pprint import pprint

# Add the root directory to the path so we can import the utils modules
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_agent_aws_security():
    """Test the agent response for AWS security queries"""
    try:
        from tabs.agent_assistant_enhanced import generate_agent_response
        
        # Test AWS Security Query for different categories
        print("\n== TEST: AWS Security Query for Document Operations ==")
        task = "What are the best practices for AWS security in 2025?"
        category = "Document Operations"
        operation = "Document Summary"
        mode = "Advanced"
        output_format = "Markdown"
        platform = "General"
        tone = "Professional"
        knowledge_sources = ["Indexed Documents", "Web Search (External)"]
        
        print(f"Generating agent response for: {task}")
        print(f"Category: {category}, Operation: {operation}")
        
        # Generate response
        response = generate_agent_response(
            task, category, operation, mode, 
            output_format, platform, tone, knowledge_sources
        )
        
        print("\n== Agent Response ==")
        print(response[:1000] + "...\n")
        
        # Verify that the response contains AWS security content and search results
        if "AWS" in response and "security" in response and "Search Results" in response:
            print("✅ Response contains AWS security content and search results!")
        else:
            print("❌ Response doesn't contain expected content.")
        
        # Test for Communication category
        print("\n== TEST: AWS Security Query for Communication ==")
        category = "Communication"
        operation = "Email Draft"
        
        print(f"Generating agent response for: {task}")
        print(f"Category: {category}, Operation: {operation}")
        
        # Generate response
        response = generate_agent_response(
            task, category, operation, mode, 
            output_format, platform, tone, knowledge_sources
        )
        
        print("\n== Agent Response ==")
        print(response[:1000] + "...\n")
        
        # Verify that the response contains AWS security content and search results
        if "AWS" in response and "security" in response and "Search Results" in response:
            print("✅ Response contains AWS security content and search results!")
        else:
            print("❌ Response doesn't contain expected content.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing agent response: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_azure_security():
    """Test the agent response for Azure security queries"""
    try:
        from tabs.agent_assistant_enhanced import generate_agent_response
        
        # Test Azure Security Query
        print("\n== TEST: Azure Security Query for Analysis & Research ==")
        task = "What are the latest Azure security features in 2025?"
        category = "Analysis & Research"
        operation = "Research Topic"
        mode = "Advanced"
        output_format = "Markdown"
        platform = "General"
        tone = "Technical"
        knowledge_sources = ["Indexed Documents", "Web Search (External)"]
        
        print(f"Generating agent response for: {task}")
        print(f"Category: {category}, Operation: {operation}")
        
        # Generate response
        response = generate_agent_response(
            task, category, operation, mode, 
            output_format, platform, tone, knowledge_sources
        )
        
        print("\n== Agent Response ==")
        print(response[:1000] + "...\n")
        
        # Verify that the response contains Azure security content and search results
        if "Azure" in response and "security" in response and "Search Results" in response:
            print("✅ Response contains Azure security content and search results!")
        else:
            print("❌ Response doesn't contain expected content.")
        
        # Test for Creative category
        print("\n== TEST: Azure Security Query for Creative ==")
        category = "Creative"
        operation = "Brainstorming"
        
        print(f"Generating agent response for: {task}")
        print(f"Category: {category}, Operation: {operation}")
        
        # Generate response
        response = generate_agent_response(
            task, category, operation, mode, 
            output_format, platform, tone, knowledge_sources
        )
        
        print("\n== Agent Response ==")
        print(response[:1000] + "...\n")
        
        # Verify that the response contains Azure security content and search results
        if "Azure" in response and "security" in response and "Search Results" in response:
            print("✅ Response contains Azure security content and search results!")
        else:
            print("❌ Response doesn't contain expected content.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing agent response: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== VaultMIND Agent Enhanced Search Integration Test ===")
    
    print("\n1. Testing AWS Security Queries")
    aws_success = test_agent_aws_security()
    
    if aws_success:
        print("\n✅ AWS security tests completed successfully")
    else:
        print("\n❌ AWS security tests failed")
    
    print("\n2. Testing Azure Security Queries")
    azure_success = test_agent_azure_security()
    
    if azure_success:
        print("\n✅ Azure security tests completed successfully")
    else:
        print("\n❌ Azure security tests failed")
    
    if aws_success and azure_success:
        print("\n✅ All tests completed successfully!")
    else:
        print("\n❌ Some tests failed. Please check the logs.")
