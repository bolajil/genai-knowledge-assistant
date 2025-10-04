"""
Demo script to demonstrate the enhanced research and multi-source search functionality.
"""

import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_demo(task: str, operation: str, knowledge_sources: List[str]):
    """
    Run a demonstration of the enhanced research capabilities.
    
    Args:
        task: The research task or query
        operation: The type of operation (Research Topic, Data Analysis, etc.)
        knowledge_sources: List of knowledge sources to search
    """
    logger.info(f"Running enhanced research demo for task: {task}")
    logger.info(f"Operation: {operation}")
    logger.info(f"Knowledge sources: {', '.join(knowledge_sources)}")
    
    try:
        # Import the modules
        from utils.enhanced_multi_source_search import (
            perform_multi_source_search,
            format_search_results_for_agent,
            get_available_sources
        )
        from utils.new_enhanced_research import generate_enhanced_research_content
        
        # Get available sources
        available_sources = get_available_sources()
        logger.info(f"Available sources: {', '.join(available_sources)}")
        
        # Filter sources to only use those that are available
        valid_sources = [source for source in knowledge_sources if source in available_sources]
        
        if len(valid_sources) != len(knowledge_sources):
            logger.warning(f"Some requested sources are not available. Using: {', '.join(valid_sources)}")
        
        # Generate the research content
        research_content = generate_enhanced_research_content(
            task=task,
            operation=operation,
            knowledge_sources=valid_sources
        )
        
        # Output the content
        print("\n" + "="*80)
        print(f"ENHANCED RESEARCH RESULT FOR: {task}")
        print("="*80)
        print(research_content)
        print("="*80 + "\n")
        
        return research_content
        
    except Exception as e:
        logger.error(f"Error in demo: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage
    tasks = [
        {
            "task": "AWS cloud cost optimization strategies for enterprise deployments",
            "operation": "Research Topic",
            "knowledge_sources": ["FAISS Vector Index", "Web Search (External)", "AWS Documentation (External)"]
        },
        {
            "task": "Security compliance requirements for financial services in the cloud",
            "operation": "Problem Solving",
            "knowledge_sources": ["VaultMind Knowledge Base", "Technical Documentation"]
        },
        {
            "task": "Emerging trends in multi-cloud deployment models",
            "operation": "Trend Identification",
            "knowledge_sources": ["Web Search (External)", "Enterprise Wiki"]
        }
    ]
    
    # Run demo for each task
    for i, task_info in enumerate(tasks, 1):
        print(f"\nRunning demo {i}/{len(tasks)}: {task_info['task']}")
        run_demo(
            task=task_info["task"],
            operation=task_info["operation"],
            knowledge_sources=task_info["knowledge_sources"]
        )
