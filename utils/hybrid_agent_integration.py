"""
Hybrid Agent Integration
Integrates hybrid query orchestrator into Agent Assistant tab
"""

import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
except ImportError:
    pass  # python-dotenv not installed

logger = logging.getLogger(__name__)

# Global instances
_orchestrator_instance = None
_langgraph_agent_instance = None


def initialize_hybrid_system(index_names: List[str], 
                            complexity_threshold: float = 50.0,
                            use_langgraph_for_moderate: bool = False) -> bool:
    """
    Initialize the hybrid query system
    
    Args:
        index_names: List of FAISS index names
        complexity_threshold: Complexity threshold for routing
        use_langgraph_for_moderate: Use LangGraph for moderate queries
        
    Returns:
        True if initialization successful
    """
    global _orchestrator_instance, _langgraph_agent_instance
    
    try:
        # Import dependencies
        from app.utils.langgraph_agent import EnhancedLangGraphAgent
        from utils.hybrid_query_orchestrator import HybridQueryOrchestrator
        from utils.unified_document_retrieval import search_documents
        
        # Check if OpenAI API key is available
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not found. LangGraph will not be available.")
            return False
        
        # Initialize LangGraph agent
        logger.info(f"Initializing LangGraph agent with indexes: {index_names}")
        _langgraph_agent_instance = EnhancedLangGraphAgent(
            index_names=index_names,
            llm_model="gpt-3.5-turbo",
            temperature=0.1,
            max_iterations=5
        )
        
        # Define fast retrieval function
        def fast_retrieval(query: str, index_name: str) -> str:
            """Fast retrieval using unified document retrieval"""
            try:
                results = search_documents(query, index_name, max_results=5)
                
                if not results:
                    return "No relevant documents found."
                
                # Format results
                formatted = []
                for i, result in enumerate(results, 1):
                    content = result.get('content', '')[:500]
                    source = result.get('source', 'Unknown')
                    page = result.get('metadata', {}).get('page', 'N/A')
                    formatted.append(f"[{i}] Source: {source}, Page: {page}\n{content}")
                
                return "\n\n".join(formatted)
                
            except Exception as e:
                logger.error(f"Fast retrieval error: {e}")
                return f"Error in fast retrieval: {str(e)}"
        
        # Initialize orchestrator
        logger.info("Initializing hybrid orchestrator")
        _orchestrator_instance = HybridQueryOrchestrator(
            fast_retrieval_func=fast_retrieval,
            langgraph_agent=_langgraph_agent_instance,
            complexity_threshold=complexity_threshold,
            use_langgraph_for_moderate=use_langgraph_for_moderate,
            enable_fallback=True,
            max_fast_time=5.0,
            max_langgraph_time=30.0
        )
        
        logger.info("Hybrid system initialized successfully")
        return True
        
    except ImportError as e:
        logger.error(f"Missing dependencies for hybrid system: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize hybrid system: {e}")
        return False


def query_hybrid_system(query: str,
                       index_name: str = "default_faiss",
                       force_approach: Optional[str] = None) -> Dict[str, Any]:
    """
    Query the hybrid system
    
    Args:
        query: User query
        index_name: Index name for fast retrieval
        force_approach: Force "fast" or "langgraph"
        
    Returns:
        Dict with response and metadata
    """
    global _orchestrator_instance
    
    if not _orchestrator_instance:
        return {
            "response": "Hybrid system not initialized. Using fallback.",
            "approach": "error",
            "success": False,
            "error": "System not initialized"
        }
    
    try:
        result = _orchestrator_instance.query(
            user_query=query,
            index_name=index_name,
            force_approach=force_approach
        )
        
        return {
            "response": result.response,
            "approach": result.approach_used,
            "complexity_score": result.complexity_analysis.score if result.complexity_analysis else None,
            "complexity_reasoning": result.complexity_analysis.reasoning if result.complexity_analysis else None,
            "execution_time": result.execution_time,
            "success": result.success,
            "reasoning_steps": result.reasoning_steps,
            "error": result.error
        }
        
    except Exception as e:
        logger.error(f"Error querying hybrid system: {e}")
        return {
            "response": f"Error: {str(e)}",
            "approach": "error",
            "success": False,
            "error": str(e)
        }


def get_hybrid_statistics() -> Dict[str, Any]:
    """Get hybrid system statistics"""
    global _orchestrator_instance
    
    if not _orchestrator_instance:
        return {"error": "System not initialized"}
    
    try:
        return _orchestrator_instance.get_statistics()
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"error": str(e)}


def is_hybrid_available() -> bool:
    """Check if hybrid system is available"""
    global _orchestrator_instance
    return _orchestrator_instance is not None


def reset_hybrid_metrics():
    """Reset hybrid system metrics"""
    global _orchestrator_instance
    
    if _orchestrator_instance:
        _orchestrator_instance.reset_metrics()
        logger.info("Hybrid metrics reset")


def export_hybrid_metrics(filepath: str) -> bool:
    """Export metrics to file"""
    global _orchestrator_instance
    
    if not _orchestrator_instance:
        return False
    
    try:
        return _orchestrator_instance.export_metrics(filepath)
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        return False


# Streamlit UI helpers
def render_complexity_badge(complexity_score: float) -> str:
    """Render complexity badge HTML"""
    if complexity_score < 30:
        color = "green"
        label = "Simple"
    elif complexity_score < 50:
        color = "blue"
        label = "Moderate"
    elif complexity_score < 75:
        color = "orange"
        label = "Complex"
    else:
        color = "red"
        label = "Very Complex"
    
    return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">{label} ({complexity_score:.0f})</span>'


def render_approach_badge(approach: str) -> str:
    """Render approach badge HTML"""
    colors = {
        "fast": "green",
        "langgraph": "purple",
        "fast_fallback": "orange",
        "error": "red"
    }
    
    color = colors.get(approach, "gray")
    label = approach.replace("_", " ").title()
    
    return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">{label}</span>'


def format_reasoning_steps(steps: List[Dict[str, str]]) -> str:
    """Format reasoning steps for display"""
    if not steps:
        return "No reasoning steps available"
    
    formatted = ["**Reasoning Steps:**\n"]
    for i, step in enumerate(steps, 1):
        step_type = step.get("type", "Unknown")
        content = step.get("content", "")
        formatted.append(f"{i}. **{step_type}**: {content}")
    
    return "\n".join(formatted)


# Configuration helpers
def get_available_indexes() -> List[str]:
    """Get list of available FAISS indexes"""
    try:
        from utils.simple_vector_manager import get_simple_indexes
        indexes = get_simple_indexes()
        
        # Handle both list and dict return types
        if isinstance(indexes, list):
            # If it's a list of dicts
            if indexes and isinstance(indexes[0], dict):
                return [idx['name'] for idx in indexes]
            # If it's a list of strings
            elif indexes and isinstance(indexes[0], str):
                return indexes
        elif isinstance(indexes, dict):
            # If it's a dict, get the values or keys
            if 'indexes' in indexes:
                return indexes['indexes']
            return list(indexes.keys())
        
        return []
    except Exception as e:
        logger.error(f"Error getting indexes: {e}")
        # Fallback to checking directory
        index_dir = Path("data/faiss_index")
        if index_dir.exists():
            return [d.name for d in index_dir.iterdir() if d.is_dir()]
        return []


def validate_configuration() -> Dict[str, Any]:
    """Validate hybrid system configuration"""
    validation = {
        "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "available_indexes": get_available_indexes(),
        "langgraph_available": False,
        "orchestrator_initialized": is_hybrid_available()
    }
    
    # Check LangGraph availability
    try:
        from langgraph.prebuilt import create_react_agent
        validation["langgraph_available"] = True
    except ImportError:
        validation["langgraph_available"] = False
    
    validation["ready"] = (
        validation["openai_api_key"] and 
        validation["langgraph_available"] and 
        len(validation["available_indexes"]) > 0
    )
    
    return validation


if __name__ == "__main__":
    # Test initialization
    logging.basicConfig(level=logging.INFO)
    
    print("Hybrid Agent Integration Test")
    print("="*80)
    
    # Validate configuration
    config = validate_configuration()
    print("\nConfiguration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    if config["ready"]:
        print("\n✓ System ready for initialization")
        
        # Initialize
        indexes = config["available_indexes"][:3]  # Use first 3 indexes
        success = initialize_hybrid_system(indexes)
        
        if success:
            print("✓ Hybrid system initialized")
            
            # Test query
            test_query = "What are the board powers?"
            print(f"\nTest Query: {test_query}")
            
            result = query_hybrid_system(test_query, indexes[0])
            print(f"Approach: {result['approach']}")
            print(f"Success: {result['success']}")
            print(f"Response: {result['response'][:200]}...")
            
            # Statistics
            stats = get_hybrid_statistics()
            print(f"\nStatistics: {stats}")
        else:
            print("✗ Failed to initialize hybrid system")
    else:
        print("\n✗ System not ready. Check configuration.")
