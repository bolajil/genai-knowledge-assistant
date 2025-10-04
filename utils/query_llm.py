"""
LLM synthesis helpers for FastAPI endpoints
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def synthesize_answer(
    query: str,
    context_docs: List[Dict[str, Any]],
    provider: str = "openai"
) -> str:
    """
    Synthesize an answer using LLM based on retrieved context
    
    Args:
        query: User query
        context_docs: Retrieved context documents
        provider: LLM provider to use
        
    Returns:
        Synthesized answer string
    """
    try:
        # Use existing LLM config if available
        from utils.llm_config import get_llm_client
        
        llm_client = get_llm_client(provider=provider)
        
        # Build context from documents
        context = "\n\n".join([
            f"Document {i+1}:\n{doc.get('content', '')}"
            for i, doc in enumerate(context_docs[:5])  # Limit to top 5
        ])
        
        # Create prompt
        prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""
        
        # Get LLM response
        response = llm_client.generate(prompt)
        
        return response
        
    except ImportError:
        logger.warning("LLM client not available, returning context summary")
        
        # Fallback: return concatenated context
        if context_docs:
            summary = f"Found {len(context_docs)} relevant documents:\n\n"
            for i, doc in enumerate(context_docs[:3], 1):
                content = doc.get('content', '')[:200]
                summary += f"{i}. {content}...\n\n"
            return summary
        else:
            return "No relevant information found."
        
    except Exception as e:
        logger.error(f"Error synthesizing answer: {e}")
        return f"Error generating answer: {str(e)}"
