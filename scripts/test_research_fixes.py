"""
Test script for enhanced research module fixes
"""
import os
import sys
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

def test_enhanced_research():
    """Test the enhanced research module"""
    try:
        from utils.unified_content_generator import generate_research_content
        logger.info("Successfully imported generate_research_content from unified_content_generator")
        
        result = generate_research_content(
            task="Test query",
            operation="Research Topic",
            knowledge_sources=["Indexed Documents"]
        )
        
        logger.info("Successfully generated research content")
        print("\n--- First 500 characters of the result ---")
        print(result[:500])
        print("\n--- End of preview ---")
        return True
        
    except Exception as e:
        logger.error(f"Error testing enhanced research: {str(e)}")
        traceback.print_exc()
        return False

def test_research_modules():
    """Check if research modules exist and can be imported"""
    modules = [
        "utils.unified_content_generator",
        "utils.enhanced_research"
    ]
    
    results = {}
    
    for module_name in modules:
        try:
            __import__(module_name)
            results[module_name] = "Successfully imported"
        except Exception as e:
            results[module_name] = f"Error importing: {str(e)}"
    
    return results

if __name__ == "__main__":
    logger.info("Testing research modules...")
    module_results = test_research_modules()
    
    print("\n--- Module Import Test Results ---")
    for module, result in module_results.items():
        print(f"{module}: {result}")
    
    print("\n--- Testing Enhanced Research Content Generation ---")
    success = test_enhanced_research()
    
    if success:
        print("\nSUCCESS: Enhanced research content generation is working!")
    else:
        print("\nFAILED: Enhanced research content generation has issues.")
