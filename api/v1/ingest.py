"""
VaultMind Document Ingestion API
Tenant-isolated document upload and processing

Phase 3: API-First Architecture
"""

import logging
import uuid
from typing import Optional, List
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl

from api.middleware.tenant import get_tenant_context, TenantContext, require_role
from utils.tenant_vector_namespace import TenantNamespaceManager, get_namespace_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==================== Request/Response Models ====================

class IngestFileResponse(BaseModel):
    """Response for file ingestion"""
    job_id: str
    status: str
    filename: str
    collection: str
    message: str


class IngestUrlRequest(BaseModel):
    """Request to ingest from URL"""
    url: HttpUrl
    department_id: str
    doc_type: str = "general"
    sensitivity_level: str = Field("internal", pattern="^(public|internal|confidential|restricted)$")
    metadata: Optional[dict] = None


class IngestBulkRequest(BaseModel):
    """Request for bulk ingestion"""
    urls: List[HttpUrl] = Field(..., max_length=50)
    department_id: str
    doc_type: str = "general"
    sensitivity_level: str = "internal"


class IngestStatusResponse(BaseModel):
    """Ingestion job status"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 to 1.0
    documents_processed: int
    documents_total: int
    errors: List[str]
    completed_at: Optional[datetime]


class DocumentMetadata(BaseModel):
    """Document metadata for listing"""
    id: str
    filename: str
    source: str
    doc_type: str
    department_id: str
    sensitivity_level: str
    ingested_at: datetime
    chunk_count: int


# In-memory job tracking (use Redis in production)
_ingestion_jobs = {}


# ==================== Endpoints ====================

@router.post("/file", response_model=IngestFileResponse)
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department_id: str = Form(...),
    doc_type: str = Form("general"),
    sensitivity_level: str = Form("internal"),
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    Upload and ingest a document file.
    
    Supported formats: PDF, DOCX, TXT, MD, CSV, XLSX
    
    The document will be:
    1. Saved to secure storage
    2. Chunked and embedded
    3. Stored in tenant/department-scoped collection
    """
    # Validate department access
    if department_id not in tenant.allowed_department_ids and tenant.role != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"You don't have access to department: {department_id}"
        )
    
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".json"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save file
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Get collection name
    ns = get_namespace_manager()
    collection = ns.get_collection_name(
        tenant_id=tenant.tenant_id,
        department_id=department_id,
        doc_type=doc_type
    )
    
    # Track job
    _ingestion_jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "documents_processed": 0,
        "documents_total": 1,
        "errors": [],
        "completed_at": None
    }
    
    # Start background processing
    background_tasks.add_task(
        _process_file,
        job_id=job_id,
        file_path=str(file_path),
        tenant_id=tenant.tenant_id,
        department_id=department_id,
        doc_type=doc_type,
        sensitivity_level=sensitivity_level,
        uploaded_by=tenant.user_id or "unknown"
    )
    
    return IngestFileResponse(
        job_id=job_id,
        status="pending",
        filename=file.filename,
        collection=collection,
        message="File uploaded. Processing in background."
    )


@router.post("/url", response_model=IngestFileResponse)
async def ingest_url(
    request: IngestUrlRequest,
    background_tasks: BackgroundTasks,
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    Ingest content from a URL.
    
    Supports: Web pages, PDFs, documents
    """
    # Validate department access
    if request.department_id not in tenant.allowed_department_ids and tenant.role != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"You don't have access to department: {request.department_id}"
        )
    
    job_id = str(uuid.uuid4())
    
    ns = get_namespace_manager()
    collection = ns.get_collection_name(
        tenant_id=tenant.tenant_id,
        department_id=request.department_id,
        doc_type=request.doc_type
    )
    
    _ingestion_jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "documents_processed": 0,
        "documents_total": 1,
        "errors": [],
        "completed_at": None
    }
    
    background_tasks.add_task(
        _process_url,
        job_id=job_id,
        url=str(request.url),
        tenant_id=tenant.tenant_id,
        department_id=request.department_id,
        doc_type=request.doc_type,
        sensitivity_level=request.sensitivity_level,
        metadata=request.metadata,
        uploaded_by=tenant.user_id or "unknown"
    )
    
    return IngestFileResponse(
        job_id=job_id,
        status="pending",
        filename=str(request.url),
        collection=collection,
        message="URL submitted. Processing in background."
    )


@router.post("/bulk", response_model=IngestFileResponse)
async def ingest_bulk(
    request: IngestBulkRequest,
    background_tasks: BackgroundTasks,
    tenant: TenantContext = Depends(require_role("manager"))
):
    """
    Bulk ingest multiple URLs.
    
    Requires manager role or higher.
    Maximum 50 URLs per request.
    """
    job_id = str(uuid.uuid4())
    
    ns = get_namespace_manager()
    collection = ns.get_collection_name(
        tenant_id=tenant.tenant_id,
        department_id=request.department_id,
        doc_type=request.doc_type
    )
    
    _ingestion_jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "documents_processed": 0,
        "documents_total": len(request.urls),
        "errors": [],
        "completed_at": None
    }
    
    background_tasks.add_task(
        _process_bulk,
        job_id=job_id,
        urls=[str(u) for u in request.urls],
        tenant_id=tenant.tenant_id,
        department_id=request.department_id,
        doc_type=request.doc_type,
        sensitivity_level=request.sensitivity_level,
        uploaded_by=tenant.user_id or "unknown"
    )
    
    return IngestFileResponse(
        job_id=job_id,
        status="pending",
        filename=f"{len(request.urls)} URLs",
        collection=collection,
        message=f"Bulk ingestion started for {len(request.urls)} URLs."
    )


@router.get("/status/{job_id}", response_model=IngestStatusResponse)
async def get_ingestion_status(
    job_id: str,
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    Get status of an ingestion job.
    """
    if job_id not in _ingestion_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = _ingestion_jobs[job_id]
    
    return IngestStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        documents_processed=job["documents_processed"],
        documents_total=job["documents_total"],
        errors=job["errors"],
        completed_at=job.get("completed_at")
    )


@router.get("/documents")
async def list_documents(
    department_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    List ingested documents for the tenant.
    
    Filters by user's accessible departments.
    """
    # Filter to accessible departments
    accessible_depts = tenant.allowed_department_ids
    if department_id:
        if department_id not in accessible_depts and tenant.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        accessible_depts = [department_id]
    
    # TODO: Implement actual document listing from vector store
    # For now, return placeholder
    return {
        "documents": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    tenant: TenantContext = Depends(require_role("manager"))
):
    """
    Delete an ingested document.
    
    Requires manager role or higher.
    """
    # TODO: Implement document deletion
    return {"message": f"Document {document_id} deleted"}


# ==================== Background Tasks ====================

async def _process_file(
    job_id: str,
    file_path: str,
    tenant_id: str,
    department_id: str,
    doc_type: str,
    sensitivity_level: str,
    uploaded_by: str
):
    """Background task to process uploaded file"""
    try:
        _ingestion_jobs[job_id]["status"] = "processing"
        
        # TODO: Implement actual file processing
        # 1. Load document
        # 2. Chunk content
        # 3. Generate embeddings
        # 4. Store in vector DB with tenant metadata
        
        _ingestion_jobs[job_id]["status"] = "completed"
        _ingestion_jobs[job_id]["progress"] = 1.0
        _ingestion_jobs[job_id]["documents_processed"] = 1
        _ingestion_jobs[job_id]["completed_at"] = datetime.utcnow()
        
        logger.info(f"Completed ingestion job: {job_id}")
        
    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {e}")
        _ingestion_jobs[job_id]["status"] = "failed"
        _ingestion_jobs[job_id]["errors"].append(str(e))


async def _process_url(
    job_id: str,
    url: str,
    tenant_id: str,
    department_id: str,
    doc_type: str,
    sensitivity_level: str,
    metadata: dict,
    uploaded_by: str
):
    """Background task to process URL"""
    try:
        _ingestion_jobs[job_id]["status"] = "processing"
        
        # TODO: Implement URL processing
        
        _ingestion_jobs[job_id]["status"] = "completed"
        _ingestion_jobs[job_id]["progress"] = 1.0
        _ingestion_jobs[job_id]["documents_processed"] = 1
        _ingestion_jobs[job_id]["completed_at"] = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"URL ingestion job {job_id} failed: {e}")
        _ingestion_jobs[job_id]["status"] = "failed"
        _ingestion_jobs[job_id]["errors"].append(str(e))


async def _process_bulk(
    job_id: str,
    urls: List[str],
    tenant_id: str,
    department_id: str,
    doc_type: str,
    sensitivity_level: str,
    uploaded_by: str
):
    """Background task to process bulk URLs"""
    try:
        _ingestion_jobs[job_id]["status"] = "processing"
        
        for i, url in enumerate(urls):
            try:
                # TODO: Process each URL
                _ingestion_jobs[job_id]["documents_processed"] = i + 1
                _ingestion_jobs[job_id]["progress"] = (i + 1) / len(urls)
            except Exception as e:
                _ingestion_jobs[job_id]["errors"].append(f"{url}: {e}")
        
        _ingestion_jobs[job_id]["status"] = "completed"
        _ingestion_jobs[job_id]["completed_at"] = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"Bulk ingestion job {job_id} failed: {e}")
        _ingestion_jobs[job_id]["status"] = "failed"
        _ingestion_jobs[job_id]["errors"].append(str(e))
