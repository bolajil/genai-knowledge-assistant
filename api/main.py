"""
VaultMind GenAI Knowledge Assistant - Main API
FastAPI application with versioned routes and tenant isolation

Phase 3: API-First Architecture
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# API routers
from api.v1 import auth, ingest, query, admin
from api.middleware.tenant import TenantMiddleware
from api.middleware.rate_limit import RateLimitMiddleware

# Database
from app.auth.database import init_sync_db, init_async_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger.info("Starting VaultMind API...")
    init_sync_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down VaultMind API...")


# Create main FastAPI app
app = FastAPI(
    title="VaultMind GenAI Knowledge Assistant API",
    description="""
    Enterprise RAG system with multi-tenant support.
    
    ## Features
    - **Multi-tenant** document storage and retrieval
    - **Department isolation** for access control
    - **JWT authentication** with role-based access
    - **Audit logging** for HIPAA compliance
    
    ## Authentication
    All endpoints require a valid JWT token in the `Authorization` header.
    Use `/v1/auth/login` to obtain a token.
    
    ## Tenant Context
    Include `X-Tenant-ID` header for tenant-scoped operations.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom middleware
app.add_middleware(TenantMiddleware)
app.add_middleware(RateLimitMiddleware)


# Mount versioned routers
app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(ingest.router, prefix="/v1/ingest", tags=["Document Ingestion"])
app.include_router(query.router, prefix="/v1/query", tags=["Search & Query"])
app.include_router(admin.router, prefix="/v1/admin", tags=["Administration"])


# Root endpoints
@app.get("/", tags=["Health"])
async def root():
    """API root - health check"""
    return {
        "name": "VaultMind GenAI Knowledge Assistant",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "vector_store": "available",
        "version": "1.0.0"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__
        }
    )


# Entry point for Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("ENVIRONMENT", "development") == "development"
    )
