"""
Hybrid Query Orchestrator
Intelligently routes queries between fast retrieval and LangGraph agent
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from utils.query_complexity_analyzer import QueryComplexityAnalyzer, ComplexityAnalysis, QueryComplexity

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for query execution"""
    query: str
    approach: str  # "fast" or "langgraph"
    complexity_score: float
    execution_time: float
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    

@dataclass
class HybridResponse:
    """Response from hybrid orchestrator"""
    response: str
    approach_used: str
    complexity_analysis: ComplexityAnalysis
    execution_time: float
    success: bool
    reasoning_steps: List[Dict[str, str]] = field(default_factory=list)
    metrics: Optional[QueryMetrics] = None
    error: Optional[str] = None


class HybridQueryOrchestrator:
    """
    Orchestrates query routing between fast retrieval and LangGraph agent
    Provides intelligent routing, fallback, and performance monitoring
    """
    
    def __init__(self,
                 fast_retrieval_func,
                 langgraph_agent,
                 complexity_threshold: float = 50.0,
                 use_langgraph_for_moderate: bool = False,
                 enable_fallback: bool = True,
                 max_fast_time: float = 5.0,
                 max_langgraph_time: float = 30.0):
        """
        Initialize hybrid orchestrator
        
        Args:
            fast_retrieval_func: Function for fast retrieval (query, index_name) -> str
            langgraph_agent: EnhancedLangGraphAgent instance
            complexity_threshold: Score threshold for LangGraph routing
            use_langgraph_for_moderate: Use LangGraph for moderate complexity
            enable_fallback: Enable fallback to fast retrieval if LangGraph fails
            max_fast_time: Max time for fast retrieval (seconds)
            max_langgraph_time: Max time for LangGraph (seconds)
        """
        self.fast_retrieval_func = fast_retrieval_func
        self.langgraph_agent = langgraph_agent
        self.complexity_threshold = complexity_threshold
        self.use_langgraph_for_moderate = use_langgraph_for_moderate
        self.enable_fallback = enable_fallback
        self.max_fast_time = max_fast_time
        self.max_langgraph_time = max_langgraph_time
        
        # Initialize analyzer
        self.analyzer = QueryComplexityAnalyzer(
            complexity_threshold=complexity_threshold,
            use_langgraph_for_moderate=use_langgraph_for_moderate
        )
        
        # Metrics tracking
        self.query_history: List[QueryMetrics] = []
        self.total_queries = 0
        self.fast_queries = 0
        self.langgraph_queries = 0
        self.fallback_count = 0
        
        logger.info("Hybrid Query Orchestrator initialized")
    
    def query(self, 
              user_query: str,
              index_name: str = "default_faiss",
              force_approach: Optional[str] = None,
              chat_history: Optional[List] = None) -> HybridResponse:
        """
        Process query with intelligent routing
        
        Args:
            user_query: User's query string
            index_name: Index name for fast retrieval
            force_approach: Force "fast" or "langgraph" (overrides analysis)
            chat_history: Chat history for LangGraph
            
        Returns:
            HybridResponse with result and metadata
        """
        start_time = time.time()
        self.total_queries += 1
        
        try:
            # Analyze complexity
            complexity_analysis = self.analyzer.analyze(user_query)
            
            # Determine approach
            if force_approach:
                approach = force_approach
                logger.info(f"Forced approach: {approach}")
            else:
                approach = complexity_analysis.recommended_approach
                logger.info(f"Recommended approach: {approach} (score: {complexity_analysis.score:.1f})")
            
            # Route query
            if approach == "langgraph":
                response = self._query_langgraph(user_query, chat_history)
                self.langgraph_queries += 1
            else:
                response = self._query_fast(user_query, index_name)
                self.fast_queries += 1
            
            execution_time = time.time() - start_time
            
            # Check if we should fallback
            if not response.success and self.enable_fallback and approach == "langgraph":
                logger.warning("LangGraph failed, falling back to fast retrieval")
                response = self._query_fast(user_query, index_name)
                approach = "fast_fallback"
                self.fallback_count += 1
                execution_time = time.time() - start_time
            
            # Create metrics
            metrics = QueryMetrics(
                query=user_query,
                approach=approach,
                complexity_score=complexity_analysis.score,
                execution_time=execution_time,
                success=response.success,
                error=response.error
            )
            self.query_history.append(metrics)
            
            # Build final response
            return HybridResponse(
                response=response.response,
                approach_used=approach,
                complexity_analysis=complexity_analysis,
                execution_time=execution_time,
                success=response.success,
                reasoning_steps=response.reasoning_steps,
                metrics=metrics,
                error=response.error
            )
            
        except Exception as e:
            logger.error(f"Error in hybrid orchestrator: {e}")
            execution_time = time.time() - start_time
            
            return HybridResponse(
                response=f"Error processing query: {str(e)}",
                approach_used="error",
                complexity_analysis=None,
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
    
    def _query_fast(self, query: str, index_name: str) -> HybridResponse:
        """Execute fast retrieval"""
        try:
            start_time = time.time()
            
            # Call fast retrieval function
            result = self.fast_retrieval_func(query, index_name)
            
            execution_time = time.time() - start_time
            
            # Check timeout
            if execution_time > self.max_fast_time:
                logger.warning(f"Fast retrieval exceeded max time: {execution_time:.2f}s")
            
            return HybridResponse(
                response=result,
                approach_used="fast",
                complexity_analysis=None,
                execution_time=execution_time,
                success=True,
                reasoning_steps=[{"step": "fast_retrieval", "result": "completed"}]
            )
            
        except Exception as e:
            logger.error(f"Fast retrieval error: {e}")
            return HybridResponse(
                response=f"Fast retrieval failed: {str(e)}",
                approach_used="fast",
                complexity_analysis=None,
                execution_time=0,
                success=False,
                error=str(e)
            )
    
    def _query_langgraph(self, query: str, chat_history: Optional[List] = None) -> HybridResponse:
        """Execute LangGraph agent"""
        try:
            start_time = time.time()
            
            # Query agent
            result = self.langgraph_agent.query(query, chat_history)
            
            execution_time = time.time() - start_time
            
            # Check timeout
            if execution_time > self.max_langgraph_time:
                logger.warning(f"LangGraph exceeded max time: {execution_time:.2f}s")
            
            return HybridResponse(
                response=result.get("response", "No response"),
                approach_used="langgraph",
                complexity_analysis=None,
                execution_time=execution_time,
                success=result.get("success", False),
                reasoning_steps=result.get("steps", []),
                error=result.get("error")
            )
            
        except Exception as e:
            logger.error(f"LangGraph error: {e}")
            return HybridResponse(
                response=f"LangGraph agent failed: {str(e)}",
                approach_used="langgraph",
                complexity_analysis=None,
                execution_time=0,
                success=False,
                error=str(e)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if self.total_queries == 0:
            return {
                "total_queries": 0,
                "message": "No queries processed yet"
            }
        
        # Calculate averages
        fast_times = [m.execution_time for m in self.query_history if m.approach == "fast"]
        langgraph_times = [m.execution_time for m in self.query_history if m.approach == "langgraph"]
        
        avg_fast_time = sum(fast_times) / len(fast_times) if fast_times else 0
        avg_langgraph_time = sum(langgraph_times) / len(langgraph_times) if langgraph_times else 0
        
        success_rate = sum(1 for m in self.query_history if m.success) / len(self.query_history) * 100
        
        return {
            "total_queries": self.total_queries,
            "fast_queries": self.fast_queries,
            "langgraph_queries": self.langgraph_queries,
            "fallback_count": self.fallback_count,
            "fast_percentage": (self.fast_queries / self.total_queries * 100) if self.total_queries > 0 else 0,
            "langgraph_percentage": (self.langgraph_queries / self.total_queries * 100) if self.total_queries > 0 else 0,
            "avg_fast_time": avg_fast_time,
            "avg_langgraph_time": avg_langgraph_time,
            "success_rate": success_rate,
            "recent_queries": [
                {
                    "query": m.query[:50] + "..." if len(m.query) > 50 else m.query,
                    "approach": m.approach,
                    "time": f"{m.execution_time:.2f}s",
                    "success": m.success
                }
                for m in self.query_history[-10:]
            ]
        }
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        try:
            metrics_data = {
                "statistics": self.get_statistics(),
                "query_history": [
                    {
                        "query": m.query,
                        "approach": m.approach,
                        "complexity_score": m.complexity_score,
                        "execution_time": m.execution_time,
                        "success": m.success,
                        "error": m.error,
                        "timestamp": m.timestamp.isoformat()
                    }
                    for m in self.query_history
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            logger.info(f"Metrics exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return False
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.query_history.clear()
        self.total_queries = 0
        self.fast_queries = 0
        self.langgraph_queries = 0
        self.fallback_count = 0
        logger.info("Metrics reset")


# Convenience function
def create_hybrid_orchestrator(fast_retrieval_func,
                               langgraph_agent,
                               **kwargs) -> HybridQueryOrchestrator:
    """
    Create hybrid orchestrator (convenience function)
    
    Args:
        fast_retrieval_func: Fast retrieval function
        langgraph_agent: LangGraph agent instance
        **kwargs: Additional configuration
        
    Returns:
        HybridQueryOrchestrator instance
    """
    return HybridQueryOrchestrator(
        fast_retrieval_func=fast_retrieval_func,
        langgraph_agent=langgraph_agent,
        **kwargs
    )


if __name__ == "__main__":
    # Test with mock functions
    def mock_fast_retrieval(query, index_name):
        return f"Fast retrieval result for: {query}"
    
    class MockAgent:
        def query(self, question, chat_history=None):
            return {
                "response": f"LangGraph result for: {question}",
                "success": True,
                "steps": [{"step": 1, "action": "search"}]
            }
    
    orchestrator = HybridQueryOrchestrator(
        fast_retrieval_func=mock_fast_retrieval,
        langgraph_agent=MockAgent()
    )
    
    # Test queries
    test_queries = [
        "What is the board structure?",
        "Compare AWS Bylaws and ByLaw2000 governance models",
        "List all members"
    ]
    
    print("Hybrid Query Orchestrator Test\n" + "="*80)
    for query in test_queries:
        result = orchestrator.query(query, "test_index")
        print(f"\nQuery: {query}")
        print(f"Approach: {result.approach_used}")
        print(f"Time: {result.execution_time:.3f}s")
        print(f"Response: {result.response[:100]}...")
    
    print("\n" + "="*80)
    print("Statistics:")
    stats = orchestrator.get_statistics()
    print(json.dumps(stats, indent=2))
