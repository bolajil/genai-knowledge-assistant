#!/usr/bin/env python
"""
Enhanced Research CLI Tool

A command-line utility for testing the optimized Enhanced Research module
without needing to run the full application.
"""

import os
import sys
import time
import argparse
import logging
from typing import List, Dict, Any, Optional

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_available_modules() -> List[str]:
    """Get available research module implementations"""
    modules = []
    
    # Check for original module
    utils_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "utils"
    )
    
    if os.path.exists(os.path.join(utils_path, "enhanced_research.py")):
        modules.append("original")
    
    if os.path.exists(os.path.join(utils_path, "enhanced_research_optimized.py")):
        modules.append("optimized")
    
    return modules

def run_research_query(
    module_type: str,
    query: str,
    operation: str,
    sources: List[str],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run a research query using the specified module
    
    Args:
        module_type: Type of module to use ('original' or 'optimized')
        query: Research query string
        operation: Research operation type
        sources: List of knowledge sources to query
        verbose: Whether to print verbose output
        
    Returns:
        Dict with execution results and metrics
    """
    result = {
        "module_type": module_type,
        "query": query,
        "operation": operation,
        "sources": sources,
        "success": False,
        "execution_time": 0,
        "content_size": 0,
        "error": None
    }
    
    try:
        # Dynamically import the appropriate module
        if module_type == "original":
            try:
                utils_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "utils"
            )
            
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "enhanced_research",
                os.path.join(utils_path, "enhanced_research.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            generate_enhanced_research_content = module.generate_enhanced_research_content
            except ImportError:
                result["error"] = "Original module not found"
                return result
        else:  # optimized
            try:
                utils_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "utils"
                )
                
                if os.path.exists(os.path.join(utils_path, "enhanced_research_optimized.py")):
                    # Import dynamically using importlib to avoid path issues
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        "enhanced_research_optimized",
                        os.path.join(utils_path, "enhanced_research_optimized.py")
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    generate_enhanced_research_content = module.generate_enhanced_research_content
                else:
                    # Try importing from new_enhanced_research if the file doesn't exist yet
                    spec = importlib.util.spec_from_file_location(
                        "new_enhanced_research",
                        os.path.join(utils_path, "new_enhanced_research.py")
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    generate_enhanced_research_content = module.generate_enhanced_research_content
            except ImportError:
                result["error"] = "Optimized module not found"
                return result
        
        # Time the execution
        start_time = time.time()
        
        if verbose:
            logger.info(f"Running query with {module_type} module: {query}")
            logger.info(f"Operation: {operation}")
            logger.info(f"Sources: {', '.join(sources)}")
        
        # Generate research content
        content = generate_enhanced_research_content(
            task=query,
            operation=operation,
            knowledge_sources=sources
        )
        
        # Record execution time and content size
        end_time = time.time()
        result["execution_time"] = end_time - start_time
        result["content_size"] = len(content)
        result["success"] = True
        
        if verbose:
            logger.info(f"Execution time: {result['execution_time']:.4f} seconds")
            logger.info(f"Content size: {result['content_size']} bytes")
            
            # Print a sample of the content
            content_sample = content[:500] + "..." if len(content) > 500 else content
            logger.info(f"Content sample:\n{content_sample}")
        
        # Store content in result if requested
        if verbose:
            result["content"] = content
        
    except Exception as e:
        result["error"] = str(e)
        if verbose:
            logger.error(f"Error running query: {str(e)}")
    
    return result

def compare_modules(
    query: str,
    operation: str,
    sources: List[str],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Compare original and optimized modules
    
    Args:
        query: Research query string
        operation: Research operation type
        sources: List of knowledge sources to query
        verbose: Whether to print verbose output
        
    Returns:
        Dict with comparison results
    """
    # Check available modules
    available_modules = get_available_modules()
    
    if "original" not in available_modules:
        logger.error("Original module not found. Cannot compare.")
        return {"error": "Original module not found"}
    
    if "optimized" not in available_modules:
        logger.error("Optimized module not found. Cannot compare.")
        return {"error": "Optimized module not found"}
    
    # Run with original module
    logger.info("Running query with original module...")
    original_result = run_research_query(
        "original", query, operation, sources, verbose
    )
    
    # Run with optimized module
    logger.info("Running query with optimized module...")
    optimized_result = run_research_query(
        "optimized", query, operation, sources, verbose
    )
    
    # Compare results
    comparison = {
        "query": query,
        "operation": operation,
        "sources": sources,
        "original": original_result,
        "optimized": optimized_result
    }
    
    # Calculate improvements
    if original_result["success"] and optimized_result["success"]:
        time_diff = original_result["execution_time"] - optimized_result["execution_time"]
        time_pct = (time_diff / original_result["execution_time"]) * 100 if original_result["execution_time"] > 0 else 0
        
        size_diff = original_result["content_size"] - optimized_result["content_size"]
        size_pct = (size_diff / original_result["content_size"]) * 100 if original_result["content_size"] > 0 else 0
        
        comparison["improvements"] = {
            "time_diff": time_diff,
            "time_pct": time_pct,
            "size_diff": size_diff,
            "size_pct": size_pct
        }
        
        logger.info(f"Time improvement: {time_diff:.4f}s ({time_pct:.2f}%)")
        logger.info(f"Size difference: {size_diff} bytes ({size_pct:.2f}%)")
    
    return comparison

def print_test_cases() -> None:
    """Print available test cases"""
    test_cases = [
        {
            "name": "Simple Query",
            "query": "Benefits of cloud computing",
            "operation": "Research Topic",
            "sources": ["Indexed Documents"]
        },
        {
            "name": "Multi-source Query",
            "query": "AWS security best practices for enterprise",
            "operation": "Research Topic",
            "sources": ["Indexed Documents", "Web Search (External)", "Structured Data (External)"]
        },
        {
            "name": "Complex Analysis",
            "query": "Machine learning implementation for fraud detection in financial services",
            "operation": "Problem Solving",
            "sources": ["Indexed Documents", "Web Search (External)"]
        },
        {
            "name": "Technical Deep Dive",
            "query": "Serverless architecture advantages and implementation challenges",
            "operation": "Technical Deep Dive",
            "sources": ["Indexed Documents", "Code Repositories"]
        },
        {
            "name": "Comparative Analysis",
            "query": "AWS vs Azure vs Google Cloud for enterprise applications",
            "operation": "Comparative Analysis",
            "sources": ["Indexed Documents", "Structured Data (External)"]
        }
    ]
    
    print("\nAvailable Test Cases:")
    print("---------------------")
    
    for i, test in enumerate(test_cases, 1):
        print(f"{i}. {test['name']}")
        print(f"   Query: {test['query']}")
        print(f"   Operation: {test['operation']}")
        print(f"   Sources: {', '.join(test['sources'])}")
        print()

def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Enhanced Research CLI Tool"
    )
    
    # Command options
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument(
        "--query", 
        help="Run a single research query"
    )
    command_group.add_argument(
        "--compare",
        help="Compare original and optimized modules",
        action="store_true"
    )
    command_group.add_argument(
        "--list-test-cases",
        help="List available test cases",
        action="store_true"
    )
    
    # Query options
    parser.add_argument(
        "--operation",
        help="Research operation type",
        choices=["Research Topic", "Problem Solving", "Comparative Analysis", 
                 "Technical Deep Dive", "Data Analysis"],
        default="Research Topic"
    )
    parser.add_argument(
        "--sources",
        help="Knowledge sources to query (comma-separated)",
        default="Indexed Documents"
    )
    parser.add_argument(
        "--module",
        help="Module type to use",
        choices=["original", "optimized"],
        default="optimized"
    )
    
    # Other options
    parser.add_argument(
        "--verbose",
        help="Print verbose output",
        action="store_true"
    )
    parser.add_argument(
        "--test-case",
        help="Use a predefined test case (1-5)",
        type=int,
        choices=range(1, 6)
    )
    
    args = parser.parse_args()
    
    # List test cases if requested
    if args.list_test_cases:
        print_test_cases()
        return 0
    
    # Get available modules
    available_modules = get_available_modules()
    logger.info(f"Available modules: {', '.join(available_modules)}")
    
    # Check if requested module is available
    if args.module not in available_modules:
        logger.error(f"Requested module '{args.module}' is not available.")
        return 1
    
    # Use test case if specified
    if args.test_case is not None:
        test_cases = [
            {
                "query": "Benefits of cloud computing",
                "operation": "Research Topic",
                "sources": ["Indexed Documents"]
            },
            {
                "query": "AWS security best practices for enterprise",
                "operation": "Research Topic",
                "sources": ["Indexed Documents", "Web Search (External)", "Structured Data (External)"]
            },
            {
                "query": "Machine learning implementation for fraud detection in financial services",
                "operation": "Problem Solving",
                "sources": ["Indexed Documents", "Web Search (External)"]
            },
            {
                "query": "Serverless architecture advantages and implementation challenges",
                "operation": "Technical Deep Dive",
                "sources": ["Indexed Documents", "Code Repositories"]
            },
            {
                "query": "AWS vs Azure vs Google Cloud for enterprise applications",
                "operation": "Comparative Analysis",
                "sources": ["Indexed Documents", "Structured Data (External)"]
            }
        ]
        
        test_case = test_cases[args.test_case - 1]
        query = test_case["query"]
        operation = test_case["operation"]
        sources = test_case["sources"]
        
        logger.info(f"Using test case {args.test_case}:")
        logger.info(f"  Query: {query}")
        logger.info(f"  Operation: {operation}")
        logger.info(f"  Sources: {', '.join(sources)}")
    else:
        # Parse command line arguments
        query = args.query
        operation = args.operation
        sources = args.sources.split(",")
    
    # Run the appropriate command
    if args.compare:
        if "original" not in available_modules or "optimized" not in available_modules:
            logger.error("Both original and optimized modules must be available to compare.")
            return 1
            
        if args.query:
            query = args.query
            
        logger.info("Comparing original and optimized modules...")
        comparison = compare_modules(
            query, operation, sources, args.verbose
        )
        
        # Print comparison summary
        if "error" in comparison:
            logger.error(f"Comparison failed: {comparison['error']}")
            return 1
            
        if "improvements" in comparison:
            improvements = comparison["improvements"]
            print("\nPerformance Comparison Summary:")
            print("-------------------------------")
            print(f"Query: {query}")
            print(f"Operation: {operation}")
            print(f"Sources: {', '.join(sources)}")
            print()
            print(f"Original execution time: {comparison['original']['execution_time']:.4f}s")
            print(f"Optimized execution time: {comparison['optimized']['execution_time']:.4f}s")
            
            speed_up = "faster" if improvements["time_pct"] > 0 else "slower"
            print(f"Time difference: {abs(improvements['time_pct']):.2f}% {speed_up}")
            
            if abs(improvements["size_pct"]) > 1:
                size_diff = "smaller" if improvements["size_pct"] > 0 else "larger"
                print(f"Content size difference: {abs(improvements['size_pct']):.2f}% {size_diff}")
            else:
                print("Content size: Approximately the same")
    else:
        # Run a single query
        result = run_research_query(
            args.module, query, operation, sources, args.verbose
        )
        
        if not result["success"]:
            logger.error(f"Query failed: {result['error']}")
            return 1
            
        print("\nQuery Results:")
        print("-------------")
        print(f"Module: {args.module}")
        print(f"Query: {query}")
        print(f"Operation: {operation}")
        print(f"Sources: {', '.join(sources)}")
        print(f"Execution time: {result['execution_time']:.4f}s")
        print(f"Content size: {result['content_size']} bytes")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
