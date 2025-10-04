"""
Enhanced Document Processor
==========================

A comprehensive document processing system that handles multiple file formats,
maintains metadata, and creates optimized vector embeddings.
"""

import os
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime
import concurrent.futures
import mimetypes
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import document processing libraries with graceful fallbacks
try:
    from langchain_community.document_loaders import (
        PyPDFLoader, 
        TextLoader,
        CSVLoader, 
        UnstructuredHTMLLoader,
        UnstructuredMarkdownLoader,
        Docx2txtLoader,
        UnstructuredExcelLoader
    )
    DOCUMENT_LOADERS_AVAILABLE = True
except ImportError:
    logger.warning("LangChain document loaders not available. Install with: pip install langchain-community")
    DOCUMENT_LOADERS_AVAILABLE = False

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    TEXT_SPLITTER_AVAILABLE = True
except ImportError:
    logger.warning("LangChain text splitter not available. Install with: pip install langchain")
    TEXT_SPLITTER_AVAILABLE = False

# Try to import vector database with graceful fallbacks
try:
    from utils.vector_db_init import get_any_vector_db_provider
    VECTOR_DB_AVAILABLE = True
except ImportError:
    logger.warning("Vector database provider not available.")
    VECTOR_DB_AVAILABLE = False

# Default configuration
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_METADATA_PATH = Path("data/metadata")
DEFAULT_VECTOR_ROOT = Path("data/faiss_index")

class DocumentMetadata:
    """Class to manage document metadata"""
    
    def __init__(self, metadata_dir: Path = DEFAULT_METADATA_PATH):
        """Initialize the metadata manager"""
        self.metadata_dir = metadata_dir
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.metadata_dir / "document_metadata.json"
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        """Load the metadata from the file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                return {}
        return {}
    
    def save_metadata(self):
        """Save the metadata to the file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def add_document(self, 
                    doc_id: str, 
                    filename: str, 
                    file_path: str,
                    file_type: str,
                    chunk_count: int,
                    index_name: str,
                    tags: List[str] = None,
                    custom_metadata: Dict = None) -> Dict:
        """Add a document to the metadata store"""
        if doc_id not in self.metadata:
            self.metadata[doc_id] = {
                "filename": filename,
                "file_path": file_path,
                "file_type": file_type,
                "chunk_count": chunk_count,
                "index_name": index_name,
                "ingestion_date": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "tags": tags or [],
                "custom_metadata": custom_metadata or {}
            }
        else:
            # Update existing document
            self.metadata[doc_id]["chunk_count"] = chunk_count
            self.metadata[doc_id]["last_updated"] = datetime.now().isoformat()
            if tags:
                self.metadata[doc_id]["tags"] = list(set(self.metadata[doc_id]["tags"] + tags))
            if custom_metadata:
                self.metadata[doc_id]["custom_metadata"].update(custom_metadata)
        
        self.save_metadata()
        return self.metadata[doc_id]
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document from the metadata store"""
        return self.metadata.get(doc_id)
    
    def list_documents(self, tag: str = None, file_type: str = None) -> List[Dict]:
        """List all documents, optionally filtered by tag or file type"""
        docs = []
        for doc_id, doc_metadata in self.metadata.items():
            if tag and tag not in doc_metadata.get("tags", []):
                continue
            if file_type and doc_metadata.get("file_type") != file_type:
                continue
            docs.append({"doc_id": doc_id, **doc_metadata})
        return docs
    
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the metadata store"""
        if doc_id in self.metadata:
            del self.metadata[doc_id]
            self.save_metadata()
            return True
        return False
    
    def update_tags(self, doc_id: str, tags: List[str], replace: bool = False) -> bool:
        """Update the tags for a document"""
        if doc_id in self.metadata:
            if replace:
                self.metadata[doc_id]["tags"] = tags
            else:
                self.metadata[doc_id]["tags"] = list(set(self.metadata[doc_id]["tags"] + tags))
            self.metadata[doc_id]["last_updated"] = datetime.now().isoformat()
            self.save_metadata()
            return True
        return False

    def get_all_metadata(self) -> Dict:
        """Return a shallow copy of the entire metadata dictionary.

        This method is used by modules like `utils/enhanced_metadata_search.py` to
        read the full metadata store without accessing internal attributes directly.
        """
        try:
            return dict(self.metadata)
        except Exception:
            # As a safe fallback, return the original reference (read-only usage expected)
            return self.metadata


class EnhancedDocumentProcessor:
    """Enhanced document processor with multi-format support and metadata tracking"""
    
    def __init__(self, 
                vector_root: Path = DEFAULT_VECTOR_ROOT,
                metadata_dir: Path = DEFAULT_METADATA_PATH):
        """Initialize the document processor"""
        self.vector_root = vector_root
        self.vector_root.mkdir(parents=True, exist_ok=True)
        
        # Initialize metadata manager
        self.metadata_manager = DocumentMetadata(metadata_dir)
        
        # Initialize vector database provider if available
        if VECTOR_DB_AVAILABLE:
            self.vector_db_provider = get_any_vector_db_provider()
        else:
            self.vector_db_provider = None
            logger.warning("Vector database provider not available. Document ingestion will be limited.")
        
        # Register file type handlers
        self.file_handlers = self._register_file_handlers()
    
    def _register_file_handlers(self) -> Dict:
        """Register handlers for different file types"""
        if not DOCUMENT_LOADERS_AVAILABLE:
            return {}
            
        return {
            ".pdf": {"loader": PyPDFLoader, "content_type": "document"},
            ".txt": {"loader": TextLoader, "content_type": "text"},
            ".csv": {"loader": CSVLoader, "content_type": "tabular"},
            ".html": {"loader": UnstructuredHTMLLoader, "content_type": "document"},
            ".md": {"loader": UnstructuredMarkdownLoader, "content_type": "document"},
            ".docx": {"loader": Docx2txtLoader, "content_type": "document"},
            ".xlsx": {"loader": UnstructuredExcelLoader, "content_type": "tabular"},
            ".xls": {"loader": UnstructuredExcelLoader, "content_type": "tabular"},
        }
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate a unique document ID based on the file path and content hash"""
        file_path_obj = Path(file_path)
        
        try:
            # Use file path and modification time for ID generation
            file_stat = file_path_obj.stat()
            unique_string = f"{file_path}:{file_stat.st_mtime}"
            return hashlib.md5(unique_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error generating document ID: {e}")
            # Fallback to just the file path
            return hashlib.md5(file_path.encode()).hexdigest()
    
    def _get_file_handler(self, file_path: Path) -> Optional[Dict]:
        """Get the appropriate file handler for a file"""
        if not DOCUMENT_LOADERS_AVAILABLE:
            logger.error("Document loaders not available. Cannot process file.")
            return None
            
        file_ext = file_path.suffix.lower()
        handler = self.file_handlers.get(file_ext)
        
        if not handler:
            logger.warning(f"No handler registered for file type: {file_ext}")
            # Try to guess the mime type and use a fallback handler
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            if mime_type and 'text/' in mime_type:
                logger.info(f"Using text loader for {file_path} with mime type {mime_type}")
                return {"loader": TextLoader, "content_type": "text"}
        
        return handler
    
    def process_file(self, 
                    file_path: Union[str, Path], 
                    index_name: str = None,
                    chunk_size: int = DEFAULT_CHUNK_SIZE,
                    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
                    tags: List[str] = None,
                    custom_metadata: Dict = None) -> Dict:
        """
        Process a single file and add it to the vector database
        
        Args:
            file_path: Path to the file to process
            index_name: Name of the vector index to use (defaults to file stem)
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            tags: List of tags to associate with the document
            custom_metadata: Additional metadata to store with the document
            
        Returns:
            Dictionary with document metadata and processing status
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"status": "error", "message": f"File not found: {file_path}"}
        
        # Generate a document ID
        doc_id = self._generate_document_id(str(file_path))
        
        # Use file stem as index name if not provided
        if not index_name:
            index_name = file_path.stem + "_index"
        
        # Get the file handler
        handler = self._get_file_handler(file_path)
        if not handler:
            return {
                "status": "error", 
                "message": f"Unsupported file type: {file_path.suffix}",
                "doc_id": doc_id
            }
        
        try:
            # Load the document
            loader = handler["loader"](str(file_path))
            docs = loader.load()
            logger.info(f"Loaded {len(docs)} pages/sections from {file_path.name}")
            
            # Split the text into chunks if the text splitter is available
            if TEXT_SPLITTER_AVAILABLE:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size, 
                    chunk_overlap=chunk_overlap
                )
                chunks = splitter.split_documents(docs)
                logger.info(f"Split into {len(chunks)} chunks")
            else:
                # Use the documents as-is if no text splitter
                chunks = docs
                logger.warning("Text splitter not available. Using document sections as-is.")
            
            # Add to vector database if available
            used_backend = None
            if self.vector_db_provider and hasattr(self.vector_db_provider, 'add_documents'):
                # Attempt Weaviate (or configured backend) via provider
                try:
                    success = self.vector_db_provider.add_documents(chunks, index_name)
                except Exception as ingest_err:
                    logger.warning(f"Vector DB provider ingestion raised error: {ingest_err}")
                    success = False
                if success:
                    used_backend = "weaviate"
                    logger.info(f"Added {len(chunks)} chunks to Weaviate collection '{index_name}'")
                else:
                    logger.warning("Vector DB provider ingestion failed or disabled. Falling back to local FAISS index.")

            if used_backend is None and VECTOR_DB_AVAILABLE:
                # Fallback to FAISS directly
                from langchain_community.vectorstores import FAISS
                from langchain_huggingface import HuggingFaceEmbeddings

                try:
                    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                    db = FAISS.from_documents(chunks, embeddings)
                    index_dir = self.vector_root / index_name
                    index_dir.mkdir(parents=True, exist_ok=True)
                    db.save_local(str(index_dir))
                    used_backend = "faiss"
                    logger.info(f"Saved FAISS index to {index_dir}")
                except Exception as e:
                    logger.error(f"Error creating FAISS index: {e}")
                    return {
                        "status": "error", 
                        "message": f"Error creating vector index: {e}",
                        "doc_id": doc_id
                    }
            else:
                logger.warning("Vector database not available. Document will be processed but not indexed.")
            
            # Add document to metadata store
            file_type = handler["content_type"]
            metadata = self.metadata_manager.add_document(
                doc_id=doc_id,
                filename=file_path.name,
                file_path=str(file_path),
                file_type=file_type,
                chunk_count=len(chunks),
                index_name=index_name,
                tags=tags or [],
                custom_metadata={**(custom_metadata or {}), "vector_backend": used_backend or "unknown"}
            )
            
            return {
                "status": "success",
                "doc_id": doc_id,
                "filename": file_path.name,
                "index_name": index_name,
                "chunk_count": len(chunks),
                "file_type": file_type,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "doc_id": doc_id
            }
    
    def process_directory(self, 
                         directory_path: Union[str, Path],
                         index_name: str = None,
                         chunk_size: int = DEFAULT_CHUNK_SIZE,
                         chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
                         recursive: bool = True,
                         tags: List[str] = None,
                         file_types: List[str] = None,
                         max_workers: int = 4) -> Dict:
        """
        Process all files in a directory
        
        Args:
            directory_path: Path to the directory
            index_name: Name of the vector index (defaults to directory name)
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            recursive: Whether to process subdirectories
            tags: List of tags to associate with all documents
            file_types: List of file extensions to process (e.g., ['.pdf', '.txt'])
            max_workers: Maximum number of worker threads for parallel processing
            
        Returns:
            Dictionary with processing results
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            return {"status": "error", "message": f"Directory not found: {directory_path}"}
        
        # Use directory name as index name if not provided
        if not index_name:
            index_name = directory_path.name + "_index"
        
        # Get list of supported file types if none specified
        if not file_types:
            file_types = list(self.file_handlers.keys())
        
        # Find all matching files
        files_to_process = []
        if recursive:
            for file_type in file_types:
                files_to_process.extend(directory_path.glob(f"**/*{file_type}"))
        else:
            for file_type in file_types:
                files_to_process.extend(directory_path.glob(f"*{file_type}"))
        
        logger.info(f"Found {len(files_to_process)} files to process in {directory_path}")
        
        if not files_to_process:
            return {
                "status": "warning",
                "message": f"No supported files found in {directory_path}",
                "processed": 0,
                "failed": 0
            }
        
        # Process files in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(
                    self.process_file, 
                    file_path, 
                    index_name, 
                    chunk_size, 
                    chunk_overlap,
                    tags,
                    {"source_directory": str(directory_path)}
                ): file_path for file_path in files_to_process
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result["status"] == "success":
                        logger.info(f"Successfully processed {file_path.name}")
                    else:
                        logger.error(f"Failed to process {file_path.name}: {result.get('message')}")
                except Exception as e:
                    logger.error(f"Exception processing {file_path.name}: {e}")
                    results.append({
                        "status": "error",
                        "message": str(e),
                        "filename": file_path.name
                    })
        
        # Summarize results
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") != "success"]
        
        return {
            "status": "success" if len(failed) == 0 else "partial",
            "message": f"Processed {len(successful)}/{len(results)} files successfully",
            "index_name": index_name,
            "processed": len(successful),
            "failed": len(failed),
            "successful_files": [r.get("filename") for r in successful],
            "failed_files": [r.get("filename") for r in failed],
            "details": results
        }
    
    def list_documents(self, tag: str = None, file_type: str = None) -> List[Dict]:
        """List all indexed documents, optionally filtered by tag or file type"""
        return self.metadata_manager.list_documents(tag, file_type)
    
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the index and metadata"""
        # Get document metadata
        doc_metadata = self.metadata_manager.get_document(doc_id)
        if not doc_metadata:
            logger.warning(f"Document not found: {doc_id}")
            return False
        
        # Remove from vector database if possible
        if self.vector_db_provider and hasattr(self.vector_db_provider, 'remove_documents'):
            try:
                self.vector_db_provider.remove_documents(doc_id, doc_metadata["index_name"])
                logger.info(f"Removed document {doc_id} from vector database")
            except Exception as e:
                logger.error(f"Error removing document from vector database: {e}")
        
        # Remove from metadata store
        return self.metadata_manager.remove_document(doc_id)

# Create a singleton instance
_document_processor = None

def get_document_processor() -> EnhancedDocumentProcessor:
    """Get the singleton document processor instance"""
    global _document_processor
    
    if _document_processor is None:
        _document_processor = EnhancedDocumentProcessor()
    
    return _document_processor
