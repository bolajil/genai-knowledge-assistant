"""
Enhanced Query API

This module provides API endpoints for querying the knowledge base.
"""

from fastapi import FastAPI, HTTPException, Request, Depends, Query as QueryParam
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any, Union
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the enhanced query processor
try:
    from utils.enhanced_query_processor import get_query_processor
    query_processor = get_query_processor()
    QUERY_PROCESSOR_AVAILABLE = True
except ImportError:
    logger.error("Enhanced query processor not available.")
    QUERY_PROCESSOR_AVAILABLE = False
    query_processor = None

# Create FastAPI app
app = FastAPI(
    title="VaultMIND Query API",
    description="API for querying the VaultMIND knowledge base",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "VaultMIND Query API"}

@app.get("/status")
async def status():
    """Get the status of the query processor"""
    if not QUERY_PROCESSOR_AVAILABLE:
        return {
            "status": "error",
            "message": "Query processor not available"
        }
    
    return {
        "status": "ready",
        "message": "Query processor is available"
    }

@app.post("/query")
async def query(request: Request):
    """
    Query the knowledge base
    
    Request body should contain:
    {
        "query": "Your search query",
        "index_name": "optional_index_name",
        "top_k": 5,
        "relevance_threshold": 0.6,
        "filters": {"field": "value"},
        "deduplicate": true
    }
    """
    if not QUERY_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Query processor not available")
    
    try:
        # Parse request
        data = await request.json()
        
        query_text = data.get("query")
        if not query_text:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Perform the search
        results = query_processor.search(
            query=query_text,
            index_name=data.get("index_name"),
            top_k=data.get("top_k", 5),
            relevance_threshold=data.get("relevance_threshold", 0.6),
            filters=data.get("filters"),
            deduplicate=data.get("deduplicate", True)
        )
        
        # Convert results to dictionaries
        result_dicts = [result.to_dict() for result in results]
        
        return {
            "status": "success",
            "query": query_text,
            "result_count": len(results),
            "results": result_dicts
        }
    
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/answer")
async def query_and_answer(request: Request):
    """
    Query the knowledge base and generate an answer using an LLM
    
    Request body should contain:
    {
        "query": "Your search query",
        "index_name": "optional_index_name",
        "top_k": 5,
        "relevance_threshold": 0.6,
        "filters": {"field": "value"},
        "provider": "openai"
    }
    """
    if not QUERY_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Query processor not available")
    
    try:
        # Parse request
        data = await request.json()
        
        query_text = data.get("query")
        if not query_text:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Perform the search
        results = query_processor.search(
            query=query_text,
            index_name=data.get("index_name"),
            top_k=data.get("top_k", 5),
            relevance_threshold=data.get("relevance_threshold", 0.6),
            filters=data.get("filters"),
            deduplicate=True
        )
        
        # Generate an answer
        answer = query_processor.synthesize_answer(
            query=query_text,
            results=results,
            provider=data.get("provider", "openai")
        )
        
        # Convert results to dictionaries
        result_dicts = [result.to_dict() for result in results]
        
        return {
            "status": "success",
            "query": query_text,
            "answer": answer,
            "result_count": len(results),
            "results": result_dicts
        }
    
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/feedback")
async def submit_feedback(request: Request):
    """
    Submit feedback on query results
    
    Request body should contain:
    {
        "query": "The original search query",
        "result_ids": ["id1", "id2"],
        "helpful": true,
        "comments": "Optional user comments"
    }
    """
    if not QUERY_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Query processor not available")
    
    try:
        # Parse request
        data = await request.json()
        
        query_text = data.get("query")
        if not query_text:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Create mock results from result IDs
        results = []
        for result_id in data.get("result_ids", []):
            results.append(query_processor.QueryResult(
                content="",
                source=result_id,
                relevance=0.0,
                doc_id=result_id
            ))
        
        # Track the feedback
        feedback = query_processor.track_feedback(
            query=query_text,
            results=results,
            helpful=data.get("helpful", True),
            comments=data.get("comments")
        )
        
        return {
            "status": "success",
            "message": "Feedback submitted successfully",
            "feedback_id": feedback.get("feedback_id")
        }
    
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/query/expand")
async def expand_query(query: str = QueryParam(..., description="The query to expand")):
    """
    Expand a query with synonyms and related terms
    
    Args:
        query: The query to expand
    """
    if not QUERY_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Query processor not available")
    
    try:
        # Expand the query
        expansions = query_processor.query_preprocessor.expand_query(query)
        
        return {
            "status": "success",
            "original_query": query,
            "expansions": expansions,
            "count": len(expansions)
        }
    
    except Exception as e:
        logger.error(f"Error expanding query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
