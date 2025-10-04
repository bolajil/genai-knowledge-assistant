"""
Simple FastAPI server for VaultMind - No complex dependencies
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple request models
class IngestRequest(BaseModel):
    content: str
    index_name: str = "default"
    chunk_size: int = 1500
    chunk_overlap: int = 500

class QueryRequest(BaseModel):
    query: str
    index_name: str = "default"
    top_k: int = 5
    provider: str = "openai"

# Create FastAPI app
app = FastAPI(
    title="VaultMind GenAI Knowledge Assistant",
    description="Simple API for document ingestion and querying",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "online",
        "service": "VaultMind GenAI Knowledge Assistant",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "ingest": "/ingest",
            "query": "/query"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "vaultmind-api"}

@app.post("/ingest")
async def ingest(payload: IngestRequest):
    """
    Ingest documents into the vector store
    """
    try:
        from utils.ingest_helpers import ingest_text
        
        chunk_count = ingest_text(
            content=payload.content,
            index_name=payload.index_name,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap
        )
        
        return {
            "status": "success",
            "message": f"Ingested content into index '{payload.index_name}'",
            "chunks": chunk_count,
            "index": payload.index_name
        }
        
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/query")
async def query(payload: QueryRequest):
    """
    Query the vector store and get AI-generated answers
    """
    try:
        from utils.query_helpers import query_index
        from utils.query_llm import synthesize_answer
        
        # Get relevant documents
        results = query_index(
            query=payload.query,
            index_name=payload.index_name,
            top_k=payload.top_k
        )
        
        # Synthesize answer if we have results
        if results:
            answer = synthesize_answer(
                query=payload.query,
                context_docs=results,
                provider=payload.provider
            )
        else:
            answer = "No relevant information found in the knowledge base."
        
        return {
            "status": "success",
            "query": payload.query,
            "index": payload.index_name,
            "provider": payload.provider,
            "answer": answer,
            "sources_count": len(results),
            "sources": results[:3]  # Return top 3 sources
        }
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/indexes")
async def list_indexes():
    """
    List available indexes/collections
    """
    try:
        # Try to get available indexes
        from utils.unified_index_manager import get_available_indexes
        indexes = get_available_indexes()
        return {
            "status": "success",
            "indexes": indexes,
            "count": len(indexes)
        }
    except Exception as e:
        logger.warning(f"Could not list indexes: {e}")
        return {
            "status": "success",
            "indexes": ["default"],
            "count": 1,
            "note": "Using default index"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
