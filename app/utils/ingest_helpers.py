# utils/ingest_helpers.py

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
#from utils.ingest_helpers import ingest_text
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from pathlib import Path
from app.utils.embeddings import get_embeddings
from typing import Dict, Any, Optional, List
import json
import logging

logger = logging.getLogger(__name__)

EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"
INDEX_ROOT = Path("data/faiss_index")
PARENT_STORE_ROOT = Path("data/parent_chunks")

def ingest_text(content: str, index_name: str, chunk_size=500, chunk_overlap=50):
    """Legacy flat chunking - kept for backward compatibility"""
    doc = Document(page_content=content)
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.split_documents([doc])

    embeddings = get_embeddings()
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(INDEX_ROOT / index_name)

    return len(docs)


def ingest_text_hierarchical(
    content: str,
    index_name: str,
    dept_id: str = None,
    source: str = None,
    document_id: str = None,
    metadata: Dict[str, Any] = None,
    parent_chunk_size: int = 1024,
    child_chunk_size: int = 256
) -> Dict[str, Any]:
    """
    Ingest text using hierarchical parent-child chunking.
    
    This is the recommended method for enterprise documents.
    - Parent chunks (1024 tokens) stored separately for context retrieval
    - Child chunks (256 tokens) indexed for precision search
    - Auto-merging enabled when ≥2 children from same parent retrieved
    
    Args:
        content: Document text content
        index_name: Name for the FAISS index
        dept_id: Department ID for namespace isolation
        source: Document source (filename, URL)
        document_id: Unique document identifier
        metadata: Additional metadata to attach
        parent_chunk_size: Token size for parent chunks
        child_chunk_size: Token size for child chunks
    
    Returns:
        Dict with ingestion stats
    """
    try:
        from utils.hierarchical_chunker import (
            HierarchicalChunker,
            get_auto_merging_retriever
        )
        
        # Initialize chunker with specified sizes
        chunker = HierarchicalChunker(
            parent_chunk_size=parent_chunk_size,
            child_chunk_size=child_chunk_size
        )
        
        # Chunk the document
        parents, children = chunker.chunk_document(
            text=content,
            document_id=document_id,
            dept_id=dept_id,
            source=source,
            additional_metadata=metadata
        )
        
        if not children:
            logger.warning("No chunks generated from document")
            return {'status': 'error', 'message': 'No chunks generated'}
        
        # Prepare child documents for FAISS indexing
        child_docs = []
        for child in children:
            doc = Document(
                page_content=child.content,
                metadata={
                    'chunk_id': child.chunk_id,
                    'parent_id': child.parent_id,
                    'chunk_type': 'child',
                    'dept_id': dept_id,
                    'source': source,
                    **child.metadata
                }
            )
            child_docs.append(doc)
        
        # Create FAISS index from child chunks
        embeddings = get_embeddings()
        db = FAISS.from_documents(child_docs, embeddings)
        
        # Save FAISS index
        index_path = INDEX_ROOT / index_name
        index_path.parent.mkdir(parents=True, exist_ok=True)
        db.save_local(str(index_path))
        
        # Save parent chunks separately for auto-merging retrieval
        parent_store_path = PARENT_STORE_ROOT / index_name
        parent_store_path.mkdir(parents=True, exist_ok=True)
        
        parent_data = {
            parent.chunk_id: parent.to_dict() for parent in parents
        }
        
        with open(parent_store_path / "parents.json", 'w') as f:
            json.dump(parent_data, f)
        
        # Register parents with auto-merging retriever
        retriever = get_auto_merging_retriever()
        retriever.register_parents(parents)
        
        # Get stats
        stats = chunker.get_stats(parents, children)
        
        logger.info(f"Hierarchical ingestion complete: {stats}")
        
        return {
            'status': 'success',
            'index_name': index_name,
            'dept_id': dept_id,
            'parent_count': len(parents),
            'child_count': len(children),
            'stats': stats
        }
        
    except ImportError as e:
        logger.warning(f"Hierarchical chunker not available, falling back to flat: {e}")
        # Fallback to flat chunking
        num_chunks = ingest_text(content, index_name)
        return {
            'status': 'success',
            'index_name': index_name,
            'chunk_count': num_chunks,
            'method': 'flat_fallback'
        }
    except Exception as e:
        logger.error(f"Hierarchical ingestion failed: {e}")
        return {'status': 'error', 'message': str(e)}


def load_parent_chunks(index_name: str) -> Dict[str, Any]:
    """Load parent chunks for an index"""
    parent_store_path = PARENT_STORE_ROOT / index_name / "parents.json"
    
    if parent_store_path.exists():
        with open(parent_store_path, 'r') as f:
            return json.load(f)
    return {}
