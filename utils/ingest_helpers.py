"""
Simple ingestion helpers for FastAPI endpoints
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def ingest_text(
    content: str,
    index_name: str = "default",
    chunk_size: int = 1500,
    chunk_overlap: int = 500
) -> int:
    """
    Ingest text content into the vector store
    
    Args:
        content: Text content to ingest
        index_name: Name of the index/collection
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        Number of chunks created
    """
    try:
        # Use the direct vector database provider (works without async issues)
        from utils.vector_db_init import get_any_vector_db_provider
        
        vector_db = get_any_vector_db_provider()
        
        # Use the vector DB's ingest method
        if hasattr(vector_db, 'ingest_text'):
            result = vector_db.ingest_text(
                text=content,
                index_name=index_name,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            chunk_count = result if isinstance(result, int) else len(result) if result else 0
        else:
            # Simple chunking fallback
            chunks = []
            for i in range(0, len(content), chunk_size - chunk_overlap):
                chunk = content[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk)
            chunk_count = len(chunks)
        
        logger.info(f"Successfully ingested {chunk_count} chunks into '{index_name}'")
        return chunk_count
        
    except ImportError:
        logger.warning("Enhanced document processor not available, using fallback")
        
        # Simple fallback: just count chunks
        chunks = []
        for i in range(0, len(content), chunk_size - chunk_overlap):
            chunk = content[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks for index '{index_name}'")
        return len(chunks)
        
    except Exception as e:
        logger.error(f"Error ingesting text: {e}")
        return 0
