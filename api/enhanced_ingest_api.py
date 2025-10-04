"""
Enhanced Document Ingest API

This module provides API endpoints for ingesting documents into the knowledge base.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any, Union
import logging
import os
from pathlib import Path
import shutil
from datetime import datetime
import json
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the enhanced document processor
try:
    from utils.enhanced_document_processor import get_document_processor
    document_processor = get_document_processor()
    DOCUMENT_PROCESSOR_AVAILABLE = True
except ImportError:
    logger.error("Enhanced document processor not available.")
    DOCUMENT_PROCESSOR_AVAILABLE = False
    document_processor = None

# Create FastAPI app
app = FastAPI(
    title="VaultMIND Document Ingest API",
    description="API for ingesting documents into the VaultMIND knowledge base",
    version="1.0.0"
)

# Configure upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "VaultMIND Document Ingest API"}

@app.get("/status")
async def status():
    """Get the status of the document processor"""
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        return {
            "status": "error",
            "message": "Document processor not available"
        }
    
    return {
        "status": "ready",
        "message": "Document processor is available",
        "supported_file_types": list(document_processor.file_handlers.keys()) if hasattr(document_processor, 'file_handlers') else []
    }

@app.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    index_name: Optional[str] = Form(None),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    tags: Optional[str] = Form(None)
):
    """
    Ingest a single file into the knowledge base
    
    Args:
        file: The file to ingest
        index_name: Optional name for the vector index
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        tags: Comma-separated list of tags
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document processor not available")
    
    # Process tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
    
    try:
        # Save the uploaded file
        file_path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved uploaded file to {file_path}")
        
        # Process the file
        result = document_processor.process_file(
            file_path=file_path,
            index_name=index_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            tags=tag_list
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    
    except Exception as e:
        logger.error(f"Error ingesting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/text")
async def ingest_text(request: Request):
    """
    Ingest text content into the knowledge base
    
    Request body should contain:
    {
        "content": "Text content to ingest",
        "index_name": "optional_index_name",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "tags": ["tag1", "tag2"],
        "title": "Optional document title"
    }
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document processor not available")
    
    try:
        # Parse request
        data = await request.json()
        
        content = data.get("content")
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        index_name = data.get("index_name")
        chunk_size = data.get("chunk_size", 500)
        chunk_overlap = data.get("chunk_overlap", 50)
        tags = data.get("tags", [])
        title = data.get("title", f"Untitled Document {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Save the content to a temporary file
        file_path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{title.replace(' ', '_')}.txt"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Saved text content to {file_path}")
        
        # Process the file
        result = document_processor.process_file(
            file_path=file_path,
            index_name=index_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            tags=tags,
            custom_metadata={"title": title}
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    
    except Exception as e:
        logger.error(f"Error ingesting text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/url")
async def ingest_url(request: Request):
    """
    Ingest content from a URL
    
    Request body should contain:
    {
        "url": "https://example.com/document.pdf",
        "index_name": "optional_index_name",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "tags": ["tag1", "tag2"]
    }
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document processor not available")
    
    try:
        # Parse request
        data = await request.json()
        
        url = data.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Check if we have the requests library
        try:
            import requests
        except ImportError:
            raise HTTPException(status_code=503, detail="Requests library not available")
        
        # Download the content
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to download content from URL: {response.status_code}")
        
        # Get the filename from the URL
        filename = url.split("/")[-1]
        if not filename:
            filename = f"download_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Save the content to a file
        file_path = UPLOAD_DIR / filename
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded content from {url} to {file_path}")
        
        # Process the file
        result = document_processor.process_file(
            file_path=file_path,
            index_name=data.get("index_name"),
            chunk_size=data.get("chunk_size", 500),
            chunk_overlap=data.get("chunk_overlap", 50),
            tags=data.get("tags", []),
            custom_metadata={"source_url": url}
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    
    except Exception as e:
        logger.error(f"Error ingesting URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/folder")
async def ingest_folder(request: Request):
    """
    Ingest all files in a folder
    
    Request body should contain:
    {
        "folder_path": "/path/to/folder",
        "index_name": "optional_index_name",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "tags": ["tag1", "tag2"],
        "file_types": [".pdf", ".txt"],
        "recursive": true
    }
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document processor not available")
    
    try:
        # Parse request
        data = await request.json()
        
        folder_path = data.get("folder_path")
        if not folder_path:
            raise HTTPException(status_code=400, detail="Folder path is required")
        
        # Check if the folder exists
        folder_path = Path(folder_path)
        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Folder not found: {folder_path}")
        
        # Process the folder
        result = document_processor.process_directory(
            directory_path=folder_path,
            index_name=data.get("index_name"),
            chunk_size=data.get("chunk_size", 500),
            chunk_overlap=data.get("chunk_overlap", 50),
            recursive=data.get("recursive", True),
            tags=data.get("tags", []),
            file_types=data.get("file_types")
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error ingesting folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents(tag: Optional[str] = None, file_type: Optional[str] = None):
    """
    List all indexed documents, optionally filtered by tag or file type
    
    Args:
        tag: Filter by tag
        file_type: Filter by file type
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document processor not available")
    
    try:
        documents = document_processor.list_documents(tag, file_type)
        return {
            "status": "success",
            "count": len(documents),
            "documents": documents
        }
    
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document from the knowledge base
    
    Args:
        doc_id: Document ID to delete
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document processor not available")
    
    try:
        success = document_processor.remove_document(doc_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")
        
        return {
            "status": "success",
            "message": f"Document {doc_id} deleted successfully"
        }
    
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
