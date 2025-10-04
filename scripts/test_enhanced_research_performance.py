"""
Performance Test Script for Enhanced Research Tab

This script compares the performance between the original and optimized
enhanced research implementations.
"""

import time
import logging
import sys
import os
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_performance_tests():
    """Run performance tests comparing original vs optimized implementations"""
    
    print("=" * 80)
    print("ENHANCED RESEARCH PERFORMANCE TEST")
    print("=" * 80)
    
    # Test cases with different complexities
    test_cases = [
        {
            "name": "Simple Query",
            "task": "Benefits of cloud computing",
            "operation": "Research Topic",
            "sources": ["Indexed Documents"]
        },
        {
            "name": "Multi-source Query",
            "task": "AWS security best practices for enterprise",
            "operation": "Research Topic",
            "sources": ["Indexed Documents", "Web Search (External)", "Structured Data (External)"]
        },
        {
            "name": "Complex Analysis",
            "task": "Machine learning implementation for fraud detection in financial services",
            "operation": "Problem Solving",
            "sources": ["Indexed Documents", "Web Search (External)"]
        }
    ]
    
    # Results collection
    results = {}
    
    # Test original implementation
    print("\nTesting Original Implementation:")
    print("-" * 40)
    
    try:
        from utils.enhanced_research import generate_enhanced_research_content as original_generate
        
        original_results = {}
        for test in test_cases:
            print(f"Running test: {test['name']}...")
            start_time = time.time()
            
            # Run the original implementation
            content = original_generate(
                task=test["task"],
                operation=test["operation"],
                knowledge_sources=test["sources"]
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            content_size = len(content)
            
            original_results[test["name"]] = {
                "execution_time": execution_time,
                "content_size": content_size
            }
            
            print(f"  - Execution time: {execution_time:.4f} seconds")
            print(f"  - Content size: {content_size} bytes")
        
        results["original"] = original_results
        
    except ImportError:
        print("Error: Could not import original enhanced research module.")
    
    # Test optimized implementation
    print("\nTesting Optimized Implementation:")
    print("-" * 40)
    
    try:
        from utils.new_enhanced_research import generate_enhanced_research_content as optimized_generate
        
        optimized_results = {}
        for test in test_cases:
            print(f"Running test: {test['name']}...")
            start_time = time.time()
            
            # Run the optimized implementation
            content = optimized_generate(
                task=test["task"],
                operation=test["operation"],
                knowledge_sources=test["sources"]
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            content_size = len(content)
            
            optimized_results[test["name"]] = {
                "execution_time": execution_time,
                "content_size": content_size
            }
            
            print(f"  - Execution time: {execution_time:.4f} seconds")
            print(f"  - Content size: {content_size} bytes")
        
        results["optimized"] = optimized_results
        
    except ImportError:
        print("Error: Could not import optimized enhanced research module.")
    
    # Compare results
    print("\nPerformance Comparison:")
    print("-" * 40)
    
    if "original" in results and "optimized" in results:
        for test_name in test_cases:
            test_name = test_name["name"]
            if test_name in results["original"] and test_name in results["optimized"]:
                original_time = results["original"][test_name]["execution_time"]
                optimized_time = results["optimized"][test_name]["execution_time"]
                
                time_diff = original_time - optimized_time
                improvement_pct = (time_diff / original_time) * 100 if original_time > 0 else 0
                
                print(f"{test_name}:")
                print(f"  - Original: {original_time:.4f}s")
                print(f"  - Optimized: {optimized_time:.4f}s")
                print(f"  - Difference: {time_diff:.4f}s ({improvement_pct:.2f}% {'improvement' if improvement_pct > 0 else 'slower'})")
    else:
        print("Could not compare results because one or both implementations could not be loaded.")
    
    print("\nTab Performance Analysis:")
    print("-" * 40)
    print("To fully compare tab performance, run each implementation in the Streamlit UI")
    print("and observe the differences in load time, responsiveness, and memory usage.")
    
    print("\nSUMMARY OF OPTIMIZATION BENEFITS:")
    print("-" * 40)
    print("1. Parallel processing of knowledge sources")
    print("2. Enhanced caching with TTL and size management")
    print("3. Memory optimization through efficient data storage")
    print("4. Progressive loading of results for better user experience")
    print("5. UI performance improvements through content containment")
    print("6. Graceful error handling and degradation")

if __name__ == "__main__":
    run_performance_tests()
