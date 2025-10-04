"""
Ingestion Queue - Celery Task System
====================================

Async task queue for document ingestion using Celery + Redis.
Provides non-blocking UI, automatic retries, and progress tracking.

P0 Critical Fix #1: Async Processing with Celery
"""

from celery import Celery, Task
from celery.result import AsyncResult
from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Celery configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

# Initialize Celery app
celery_app = Celery(
    'vaultmind_ingestion',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # Results expire after 24 hours
)


class IngestionTask(Task):
    """Base task class with custom error handling"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Task {task_id} failed: {exc}")
        logger.error(f"Error info: {einfo}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        logger.warning(f"Task {task_id} retrying: {exc}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(f"Task {task_id} completed successfully")


@celery_app.task(
    bind=True,
    base=IngestionTask,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes max
    retry_jitter=True
)
def async_ingest_document(self,
                         collection_name: str,
                         file_content_b64: str,  # Base64 encoded
                         file_name: str,
                         username: str,
                         document_type: str,
                         backend: str = "weaviate",
                         chunk_size: int = 1500,
                         chunk_overlap: int = 300,
                         use_semantic_chunking: bool = True,
                         **kwargs) -> Dict[str, Any]:
    """
    Async task for document ingestion with retry logic
    
    Args:
        self: Task instance (bound)
        collection_name: Target collection/index name
        file_content_b64: Base64 encoded file content
        file_name: Original filename
        username: User who initiated ingestion
        document_type: Type of document (PDF, TEXT, URL)
        backend: Storage backend (weaviate, faiss, both)
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        use_semantic_chunking: Use semantic chunking strategy
        **kwargs: Additional parameters
        
    Returns:
        Dictionary with ingestion results
    """
    import base64
    
    task_id = self.request.id
    start_time = time.time()
    
    logger.info(f"Starting ingestion task {task_id} for {file_name}")
    
    # Update task state to PROGRESS
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 0,
            'total': 100,
            'status': 'Initializing...',
            'filename': file_name
        }
    )
    
    try:
        # Decode file content
        file_content = base64.b64decode(file_content_b64)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': 'Validating file...',
                'filename': file_name
            }
        )
        
        # Validate file (P0 Fix #2)
        from utils.ingestion_validator import get_ingestion_validator
        from pathlib import Path
        
        validator = get_ingestion_validator()
        is_valid, errors, metadata = validator.validate_file(
            Path(file_name),
            file_content,
            file_name
        )
        
        if not is_valid:
            error_msg = f"Validation failed: {'; '.join(errors)}"
            logger.error(f"Task {task_id}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'validation_errors': errors,
                'task_id': task_id
            }
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 25,
                'total': 100,
                'status': 'Processing document...',
                'filename': file_name,
                'validation': 'passed'
            }
        )
        
        # Route to appropriate backend
        result = None
        
        if backend in ('weaviate', 'both'):
            # Weaviate ingestion
            result = _ingest_to_weaviate(
                self,
                collection_name,
                file_content,
                file_name,
                username,
                document_type,
                chunk_size,
                chunk_overlap,
                use_semantic_chunking
            )
        
        if backend in ('faiss', 'both'):
            # FAISS ingestion
            faiss_result = _ingest_to_faiss(
                self,
                collection_name,
                file_content,
                file_name,
                username,
                document_type,
                chunk_size,
                chunk_overlap
            )
            
            if result is None:
                result = faiss_result
            else:
                # Merge results
                result['faiss_result'] = faiss_result
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Final result
        if result and result.get('success'):
            result.update({
                'task_id': task_id,
                'duration_ms': duration_ms,
                'completed_at': datetime.utcnow().isoformat(),
                'validation_metadata': metadata
            })
            
            logger.info(f"Task {task_id} completed in {duration_ms}ms")
            return result
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'Ingestion failed'
            logger.error(f"Task {task_id} failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'task_id': task_id,
                'duration_ms': duration_ms
            }
        
    except Exception as e:
        logger.error(f"Task {task_id} exception: {e}", exc_info=True)
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {task_id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)
        else:
            return {
                'success': False,
                'error': f"Task failed after {self.max_retries} retries: {str(e)}",
                'task_id': task_id
            }


def _ingest_to_weaviate(task: Task,
                       collection_name: str,
                       file_content: bytes,
                       file_name: str,
                       username: str,
                       document_type: str,
                       chunk_size: int,
                       chunk_overlap: int,
                       use_semantic_chunking: bool) -> Dict[str, Any]:
    """Helper function to ingest to Weaviate"""
    try:
        from utils.weaviate_ingestion_helper import get_weaviate_ingestion_helper
        
        task.update_state(
            state='PROGRESS',
            meta={
                'current': 40,
                'total': 100,
                'status': 'Connecting to Weaviate...',
                'filename': file_name
            }
        )
        
        helper = get_weaviate_ingestion_helper()
        
        # Test connection
        if not helper.test_connection():
            return {
                'success': False,
                'error': 'Weaviate connection failed'
            }
        
        task.update_state(
            state='PROGRESS',
            meta={
                'current': 50,
                'total': 100,
                'status': 'Ingesting to Weaviate...',
                'filename': file_name
            }
        )
        
        # Ingest based on document type
        if document_type.upper() == 'PDF':
            result = helper.ingest_pdf_document(
                collection_name=collection_name,
                file_content=file_content,
                file_name=file_name,
                username=username,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_semantic_chunking=use_semantic_chunking
            )
        elif document_type.upper() in ('TEXT', 'TXT'):
            text_content = file_content.decode('utf-8', errors='ignore')
            result = helper.ingest_text_document(
                collection_name=collection_name,
                text_content=text_content,
                file_name=file_name,
                username=username,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_semantic_chunking=use_semantic_chunking
            )
        else:
            return {
                'success': False,
                'error': f'Unsupported document type: {document_type}'
            }
        
        task.update_state(
            state='PROGRESS',
            meta={
                'current': 90,
                'total': 100,
                'status': 'Finalizing...',
                'filename': file_name
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Weaviate ingestion error: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'Weaviate ingestion failed: {str(e)}'
        }


def _ingest_to_faiss(task: Task,
                    index_name: str,
                    file_content: bytes,
                    file_name: str,
                    username: str,
                    document_type: str,
                    chunk_size: int,
                    chunk_overlap: int) -> Dict[str, Any]:
    """Helper function to ingest to FAISS"""
    try:
        from pathlib import Path
        from tabs.document_ingestion import _build_faiss_index_from_text
        
        task.update_state(
            state='PROGRESS',
            meta={
                'current': 60,
                'total': 100,
                'status': 'Building FAISS index...',
                'filename': file_name
            }
        )
        
        # Extract text
        if document_type.upper() == 'PDF':
            # Use PDF extraction
            try:
                from pypdf import PdfReader
                import io
                reader = PdfReader(io.BytesIO(file_content))
                text_content = ""
                for page in reader.pages:
                    text_content += page.extract_text() or ""
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                text_content = file_content.decode('utf-8', errors='ignore')
        else:
            text_content = file_content.decode('utf-8', errors='ignore')
        
        # Build FAISS index
        faiss_target = Path("data") / "faiss_index" / index_name
        faiss_target.mkdir(parents=True, exist_ok=True)
        
        _build_faiss_index_from_text(text_content, index_name, faiss_target)
        
        task.update_state(
            state='PROGRESS',
            meta={
                'current': 95,
                'total': 100,
                'status': 'FAISS index complete',
                'filename': file_name
            }
        )
        
        return {
            'success': True,
            'index_name': index_name,
            'index_path': str(faiss_target),
            'backend': 'faiss'
        }
        
    except Exception as e:
        logger.error(f"FAISS ingestion error: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'FAISS ingestion failed: {str(e)}'
        }


@celery_app.task
def get_ingestion_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of an ingestion task
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Dictionary with task status and progress
    """
    task = AsyncResult(task_id, app=celery_app)
    
    response = {
        'task_id': task_id,
        'status': task.state,
        'ready': task.ready(),
        'successful': task.successful() if task.ready() else None,
    }
    
    if task.state == 'PENDING':
        response['progress'] = 0
        response['message'] = 'Task is waiting to start...'
    elif task.state == 'PROGRESS':
        info = task.info or {}
        response['progress'] = info.get('current', 0)
        response['total'] = info.get('total', 100)
        response['message'] = info.get('status', 'Processing...')
        response['filename'] = info.get('filename', '')
    elif task.state == 'SUCCESS':
        response['progress'] = 100
        response['message'] = 'Ingestion completed successfully'
        response['result'] = task.result
    elif task.state == 'FAILURE':
        response['progress'] = 0
        response['message'] = 'Ingestion failed'
        response['error'] = str(task.info)
    elif task.state == 'RETRY':
        response['progress'] = 0
        response['message'] = 'Retrying after error...'
    
    return response


@celery_app.task
def cleanup_old_results(days: int = 7) -> Dict[str, Any]:
    """
    Cleanup old task results from Redis
    
    Args:
        days: Remove results older than this many days
        
    Returns:
        Cleanup statistics
    """
    # This would require iterating through Redis keys
    # Implementation depends on your Redis setup
    logger.info(f"Cleanup task triggered for results older than {days} days")
    return {
        'status': 'completed',
        'days': days
    }


# Health check task
@celery_app.task
def health_check() -> Dict[str, Any]:
    """Health check task to verify Celery is working"""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'worker': 'active'
    }
