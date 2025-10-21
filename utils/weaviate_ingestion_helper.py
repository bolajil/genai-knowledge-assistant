"""
Weaviate Ingestion Helper
========================
Helper functions for ingesting documents into Weaviate collections
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import time
import httpx

from utils.weaviate_manager import get_weaviate_manager
from utils.semantic_chunking_strategy import create_semantic_chunks
from sentence_transformers import SentenceTransformer
<<<<<<< HEAD
from io import BytesIO

# Optional PDF page counter
try:
    from PyPDF2 import PdfReader
    PDF_READER_AVAILABLE = True
except Exception:
    PDF_READER_AVAILABLE = False
=======
>>>>>>> clean-master

logger = logging.getLogger(__name__)

class WeaviateIngestionHelper:
    """Helper class for ingesting documents into Weaviate"""
    
    def __init__(self):
        self.weaviate_manager = get_weaviate_manager()
        # Store the last detailed ingestion result for UI diagnostics
        self.last_result: Optional[Dict[str, Any]] = None
    
    def test_connection(self) -> bool:
        """Lightweight connectivity check against Weaviate using direct endpoints.
        Uses WeaviateManager's resilient HTTP client (HTTP/2 off, retries, TLS options).
        """
        base = self.weaviate_manager.url.rstrip('/')
        logger.debug(f"Testing Weaviate connectivity at base: {base}")
        # Prefer readiness first, then schema
        endpoints = [
            f"{base}/v1/.well-known/ready",
            f"{base}/v1/schema",
        ]
        last_err: Optional[Exception] = None
        for url in endpoints:
            try:
                resp = self.weaviate_manager._http_request("GET", url, timeout=30)
                if resp.status_code == 200:
                    logger.info(f"Connectivity OK via {url}")
                    return True
                elif resp.status_code in (401, 403, 204, 405):
                    # Auth/method might be required but endpoint exists
                    logger.info(f"Connectivity OK (auth/method needed) via {url}: {resp.status_code}")
                    return True
                else:
                    logger.debug(f"Connectivity probe to {url} returned {resp.status_code}")
            except Exception as e:
                last_err = e
                logger.debug(f"Connectivity probe failed at {url}: {e}")
        logger.error("Weaviate connectivity checks failed via direct '/v1/.well-known/ready' and '/v1/schema'")
        if last_err:
            logger.debug(f"Last connectivity error: {last_err}")
        return False
    
    def create_collection_for_document(self, 
                                     collection_name: str,
                                     document_type: str,
                                     username: str) -> bool:
        """Create a Weaviate collection for document ingestion"""
        try:
            description = f"Collection for {document_type} documents uploaded by {username}"
            
            # Additional properties for document metadata
            properties = {
                "document_type": {
                    "data_type": "TEXT",
                    "description": "Type of document (PDF, TXT, URL, etc.)"
                },
                "uploaded_by": {
                    "data_type": "TEXT", 
                    "description": "Username who uploaded the document"
                },
                "upload_date": {
                    "data_type": "DATE",
                    "description": "Date when document was uploaded"
                },
                "chunk_index": {
                    "data_type": "INT",
                    "description": "Index of this chunk within the document"
                },
                "total_chunks": {
                    "data_type": "INT",
                    "description": "Total number of chunks in the document"
                },
                "file_name": {
                    "data_type": "TEXT",
                    "description": "Original file name"
                }
            }
            
            return self.weaviate_manager.create_collection(
                collection_name=collection_name,
                description=description,
                properties=properties
            )
            
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {e}")
            return False
    
    def create_collection(self,
                          collection_name: str,
                          description: str = "",
                          properties: Optional[Dict[str, Any]] = None) -> bool:
        """Wrapper to match UI expectations; ensures extended properties exist."""
        try:
            # Ensure extended properties commonly used during ingestion are present
            extended_props = {
                "document_type": {"data_type": "TEXT", "description": "Type of document"},
                "uploaded_by": {"data_type": "TEXT", "description": "Username who uploaded"},
                "upload_date": {"data_type": "DATE", "description": "Upload date"},
                "chunk_index": {"data_type": "INT", "description": "Chunk index"},
                "total_chunks": {"data_type": "INT", "description": "Total number of chunks"},
                "file_name": {"data_type": "TEXT", "description": "Original file name"},
            }
            if properties:
                extended_props.update(properties)
            return self.weaviate_manager.create_collection(
                collection_name=collection_name,
                description=description,
                properties=extended_props,
            )
        except Exception as e:
            logger.error(f"Error creating collection '{collection_name}': {e}")
            return False
    
    def ingest_pdf_document(self,
                           collection_name: str,
                           file_content: bytes,
                           file_name: str,
                           username: str,
                           chunk_size: int = 512,
                           chunk_overlap: int = 100,
                           use_semantic_chunking: bool = True,
                           use_local_embeddings: bool = False,
                           embedding_model: str = "all-MiniLM-L6-v2") -> Dict[str, Any]:
<<<<<<< HEAD
        try:
            # Use robust PDF extraction with quality validation
            from utils.robust_pdf_extractor import extract_text_from_pdf_robust, validate_extraction_quality

            text_content, method = extract_text_from_pdf_robust(file_content, file_name)
            # Attempt to count pages for diagnostics
            page_count: Optional[int] = None
            if PDF_READER_AVAILABLE:
                try:
                    reader = PdfReader(BytesIO(file_content))
                    page_count = len(reader.pages)
                except Exception:
                    page_count = None

            if not text_content:
                logger.error(f"Failed to extract text from PDF: {file_name}")
                return {"success": False, "error": "PDF text extraction failed"}

            # Validate extraction quality
            is_valid, quality, message = validate_extraction_quality(text_content, min_quality=0.5)
            logger.info(
                f"PDF extraction for {file_name}: method={method}, quality={quality:.2f}, valid={is_valid}"
            )

            result = self._ingest_text_content(
=======
        """Ingest PDF document into Weaviate using robust extraction"""
        try:
            # Use robust PDF extraction with quality validation
            from utils.robust_pdf_extractor import extract_text_from_pdf_robust, validate_extraction_quality
            
            text_content, method = extract_text_from_pdf_robust(file_content, file_name)
            
            if not text_content:
                logger.error(f"Failed to extract text from PDF: {file_name}")
                return {"success": False, "error": "PDF text extraction failed"}
            
            # Validate extraction quality
            is_valid, quality, message = validate_extraction_quality(text_content, min_quality=0.5)
            logger.info(f"PDF extraction for {file_name}: method={method}, quality={quality:.2f}, valid={is_valid}")
            
            if not is_valid:
                logger.warning(f"Low quality PDF extraction for {file_name}: {message}")
            
            return self._ingest_text_content(
>>>>>>> clean-master
                collection_name=collection_name,
                text_content=text_content,
                file_name=file_name,
                document_type="PDF",
                username=username,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_semantic_chunking=use_semantic_chunking,
                use_local_embeddings=use_local_embeddings,
<<<<<<< HEAD
                embedding_model=embedding_model,
            )
            if isinstance(result, dict):
                result["page_count"] = page_count
            return result
        except Exception as e:
            logger.error(f"Error ingesting PDF {file_name}: {e}")
            return {"success": False, "error": str(e)}
=======
                embedding_model=embedding_model
            )
            
        except Exception as e:
            logger.error(f"Error ingesting PDF {file_name}: {e}")
            return {"success": False, "error": str(e)}
    
>>>>>>> clean-master
    def ingest_pdf(self,
                   collection_name: str,
                   pdf_file: Any,
                   chunk_size: int = 512,
                   chunk_overlap: int = 100,
                   use_semantic_chunking: bool = True,
                   split_by_headers: bool = True,
                   use_embeddings: bool = True,
                   use_local_embeddings: bool = False,
                   embedding_model: str = "all-MiniLM-L6-v2") -> bool:
        """UI-friendly wrapper; reads bytes from an UploadedFile-like object and ingests."""
        try:
            file_name = getattr(pdf_file, 'name', 'uploaded.pdf')
            file_content = pdf_file.getvalue() if hasattr(pdf_file, 'getvalue') else pdf_file.read()
            result = self.ingest_pdf_document(
                collection_name=collection_name,
                file_content=file_content,
                file_name=file_name,
                username=os.getenv("INGEST_USERNAME", "Unknown"),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_semantic_chunking=use_semantic_chunking,
                use_local_embeddings=use_local_embeddings,
                embedding_model=embedding_model,
            )
            # Persist last result for UI to optionally display details
            self.last_result = result
            return bool(result.get("success"))
        except Exception as e:
            logger.error(f"Error in ingest_pdf wrapper: {e}")
            return False
    
    def ingest_text_document(self,
                           collection_name: str,
                           text_content: str,
                           file_name: str,
                           username: str,
                           chunk_size: int = 512,
                           chunk_overlap: int = 100,
                           use_semantic_chunking: bool = True,
                           use_local_embeddings: bool = False,
                           embedding_model: str = "all-MiniLM-L6-v2") -> Dict[str, Any]:
        """Ingest text document into Weaviate"""
        return self._ingest_text_content(
            collection_name=collection_name,
            text_content=text_content,
            file_name=file_name,
            document_type="TEXT",
            username=username,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            use_semantic_chunking=use_semantic_chunking,
            use_local_embeddings=use_local_embeddings,
            embedding_model=embedding_model
        )
    
    def ingest_text_file(self,
                         collection_name: str,
                         text_file: Any,
                         chunk_size: int = 512,
                         chunk_overlap: int = 100,
                         use_semantic_chunking: bool = True,
                         split_by_headers: bool = True,
                         use_embeddings: bool = True,
                         use_local_embeddings: bool = False,
                         embedding_model: str = "all-MiniLM-L6-v2") -> bool:
        """UI-friendly wrapper for text file ingestion."""
        try:
            file_name = getattr(text_file, 'name', 'uploaded.txt')
            # Try utf-8 first, then latin-1
            raw = text_file.getvalue() if hasattr(text_file, 'getvalue') else text_file.read()
            try:
                text_content = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
            except UnicodeDecodeError:
                text_content = raw.decode("latin-1")
            result = self.ingest_text_document(
                collection_name=collection_name,
                text_content=text_content,
                file_name=file_name,
                username=os.getenv("INGEST_USERNAME", "Unknown"),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_semantic_chunking=use_semantic_chunking,
                use_local_embeddings=use_local_embeddings,
                embedding_model=embedding_model,
            )
            # Persist last result for UI to optionally display details
            self.last_result = result
            return bool(result.get("success"))
        except Exception as e:
            logger.error(f"Error in ingest_text_file wrapper: {e}")
            return False

    def ingest_url(self,
                   collection_name: str,
                   url: str,
                   chunk_size: int = 512,
                   chunk_overlap: int = 100,
                   render_js: bool = False,
                   max_depth: int = 1,
                   use_semantic_chunking: bool = True,
                   split_by_headers: bool = True,
                   use_embeddings: bool = True,
                   use_local_embeddings: bool = False,
                   embedding_model: str = "all-MiniLM-L6-v2") -> bool:
        """UI-friendly wrapper for URL ingestion.

        Note: Parameters like split_by_headers/use_embeddings/max_depth are accepted for
        compatibility with the UI but are not used by the underlying ingestion.
        """
        try:
            result = self.ingest_url_content(
                collection_name=collection_name,
                url=url,
                username=os.getenv("INGEST_USERNAME", "Unknown"),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_semantic_chunking=use_semantic_chunking,
                render_js=render_js,
                use_local_embeddings=use_local_embeddings,
                embedding_model=embedding_model,
            )
            # Persist last result for UI to optionally display details
            self.last_result = result
            return bool(result.get("success"))
        except Exception as e:
            logger.error(f"Error in ingest_url wrapper: {e}")
            return False
    
    def ingest_url_content(self,
                          collection_name: str,
                          url: str,
                          username: str,
                          chunk_size: int = 512,
                          chunk_overlap: int = 100,
                          use_semantic_chunking: bool = True,
                          render_js: bool = False,
                          use_local_embeddings: bool = False,
                          embedding_model: str = "all-MiniLM-L6-v2") -> Dict[str, Any]:
        """Ingest web content into Weaviate"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text(separator='\n', strip=True)
            
            return self._ingest_text_content(
                collection_name=collection_name,
                text_content=text_content,
                file_name=url,
                document_type="URL",
                username=username,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_semantic_chunking=use_semantic_chunking,
                use_local_embeddings=use_local_embeddings,
                embedding_model=embedding_model,
            )
            
        except Exception as e:
            logger.error(f"Error ingesting URL {url}: {e}")
            return {"success": False, "error": str(e)}
    
    def _ingest_text_content(self,
                           collection_name: str,
                           text_content: str,
                           file_name: str,
                           document_type: str,
                           username: str,
                           chunk_size: int,
                           chunk_overlap: int,
                           use_semantic_chunking: bool,
                           use_local_embeddings: bool = False,
                           embedding_model: str = "all-MiniLM-L6-v2") -> Dict[str, Any]:
        """Internal method to ingest text content into Weaviate"""
        try:
            # Create collection if it doesn't exist
            if collection_name not in self.weaviate_manager.list_collections():
                if not self.create_collection_for_document(collection_name, document_type, username):
                    return {"success": False, "error": "Failed to create collection"}
            
            # Create chunks
            chunk_start_ts = time.time()
            if use_semantic_chunking:
                try:
                    chunks = create_semantic_chunks(
                        text_content,
                        document_name=file_name,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
                    chunk_texts = [chunk['content'] for chunk in chunks]
                except Exception as e:
                    logger.warning(f"Semantic chunking failed, using basic chunking: {e}")
                    chunk_texts = self._create_basic_chunks(text_content, chunk_size, chunk_overlap)
            else:
                chunk_texts = self._create_basic_chunks(text_content, chunk_size, chunk_overlap)
            chunking_duration_ms = int((time.time() - chunk_start_ts) * 1000)
            
            logger.debug(f"Prepared {len(chunk_texts)} chunks for collection '{collection_name}' from '{file_name}' using method={'semantic' if use_semantic_chunking else 'basic'}")
            
            # Prepare documents for Weaviate
            documents = []
            upload_date = datetime.now().isoformat()
            
            # Optional: compute local embeddings for each chunk
            vectors = None
            if use_local_embeddings:
                try:
                    model = SentenceTransformer(embedding_model)
                    vectors_np = model.encode(chunk_texts, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=False)
                    # Ensure list of lists for JSON serialization
                    vectors = vectors_np.tolist()
                    logger.info(f"Computed {len(vectors)} local embeddings with model='{embedding_model}' for collection '{collection_name}'")
                except Exception as e:
                    logger.error(f"Local embedding computation failed, proceeding without vectors: {e}")
                    vectors = None

            for i, chunk_text in enumerate(chunk_texts):
                doc = {
                    "content": chunk_text,
                    "source": file_name,
                    "source_type": document_type.lower(),
                    "document_type": document_type,
                    "uploaded_by": username,
                    "upload_date": upload_date,
                    "chunk_index": i + 1,
                    "total_chunks": len(chunk_texts),
                    "file_name": file_name,
                    "metadata": {
                        "chunk_size": len(chunk_text),
                        "original_document_size": len(text_content),
                        "chunking_method": "semantic" if use_semantic_chunking else "basic"
                    }
                }
                # Attach local vector if available
                if vectors is not None and i < len(vectors):
                    # Use default vector field for compatibility; SDK should accept 'vector'
                    doc["vector"] = vectors[i]
                documents.append(doc)
            
            # Add documents to Weaviate with detailed diagnostics
            diag = self.weaviate_manager.add_documents_with_stats(collection_name, documents)

            # Attach additional context and phase timings
            diag = dict(diag) if isinstance(diag, dict) else {"success": bool(diag)}
            diag.setdefault("collection_name", collection_name)
            diag.setdefault("document_type", document_type)
            diag.setdefault("file_name", file_name)
            diag["total_chunks"] = len(chunk_texts)
<<<<<<< HEAD
            # Add text size metrics for UI
            try:
                total_chars = len(text_content or "")
            except Exception:
                total_chars = 0
            diag["total_chars"] = total_chars
            diag["approx_tokens"] = total_chars // 4  # rough heuristic for token estimation
=======
>>>>>>> clean-master
            if "phase_timings_ms" not in diag or not isinstance(diag.get("phase_timings_ms"), dict):
                diag["phase_timings_ms"] = {}
            diag["phase_timings_ms"]["chunking_ms"] = chunking_duration_ms

            # Provide additional diagnostics on failure if needed
            if not diag.get("success", False) and "error" not in diag:
                try:
                    existing = self.weaviate_manager.list_collections()
                    logger.error(f"Failed to add documents: collection '{collection_name}', existing_collections={existing}")
                except Exception:
                    pass

            # Store last result and return
            self.last_result = diag
            return diag
                
        except Exception as e:
            logger.error(f"Error ingesting text content: {e}")
            result = {"success": False, "error": str(e)}
            self.last_result = result
            return result
    
    def _create_basic_chunks(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Create basic text chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            if end > len(text):
                end = len(text)
            
            chunk = text[start:end]
            chunks.append(chunk)
            
            if end == len(text):
                break
                
            start = end - chunk_overlap
        
        return chunks
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection"""
        return self.weaviate_manager.get_collection_stats(collection_name)
    
    def list_available_collections(self) -> List[str]:
        """List all available Weaviate collections"""
        return self.weaviate_manager.list_collections()
    
    def search_collection(self, 
                         collection_name: str, 
                         query: str, 
                         limit: int = 10) -> List[Dict[str, Any]]:
        """Search within a specific collection"""
        return self.weaviate_manager.search(
            collection_name=collection_name,
            query=query,
            limit=limit
        )

# Global instance
_weaviate_ingestion_helper = None

def get_weaviate_ingestion_helper() -> WeaviateIngestionHelper:
    """Get global Weaviate ingestion helper instance"""
    global _weaviate_ingestion_helper
    if _weaviate_ingestion_helper is None:
        _weaviate_ingestion_helper = WeaviateIngestionHelper()
    return _weaviate_ingestion_helper
