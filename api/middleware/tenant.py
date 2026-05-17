"""
VaultMind Tenant Middleware
Extracts tenant context from request headers and JWT claims

Phase 3: API-First Architecture
"""

import logging
from typing import Optional, List
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException

import jwt
import os

logger = logging.getLogger(__name__)


@dataclass
class TenantContext:
    """Tenant context extracted from request"""
    tenant_id: str
    tenant_name: str
    user_id: Optional[str] = None
    department_id: Optional[str] = None
    allowed_department_ids: List[str] = None
    role: str = "user"
    
    def __post_init__(self):
        if self.allowed_department_ids is None:
            self.allowed_department_ids = []


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant context from requests.
    
    Extracts from:
    1. X-Tenant-ID header (required for most endpoints)
    2. JWT token claims (user_id, department_ids, role)
    
    Sets request.state.tenant with TenantContext
    """
    
    # Paths that don't require tenant context
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/auth/login",
        "/v1/auth/register",
    }
    
    def __init__(self, app):
        super().__init__(app)
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        if not self.jwt_secret and os.getenv("ENVIRONMENT") == "production":
            raise ValueError("JWT_SECRET_KEY must be set in production")
        elif not self.jwt_secret:
            self.jwt_secret = "dev-secret-key-not-for-production"
    
    async def dispatch(self, request: Request, call_next):
        # Skip public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Extract tenant context
            tenant_context = self._extract_tenant_context(request)
            request.state.tenant = tenant_context
            
            # Log tenant context for audit
            logger.debug(
                f"Request: {request.method} {request.url.path} | "
                f"Tenant: {tenant_context.tenant_id} | "
                f"User: {tenant_context.user_id}"
            )
            
            return await call_next(request)
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    def _extract_tenant_context(self, request: Request) -> TenantContext:
        """Extract tenant context from headers and JWT"""
        
        # Get tenant ID from header
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            # Try to get from JWT claims
            tenant_id = self._get_tenant_from_jwt(request)
        
        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail="X-Tenant-ID header or tenant claim in JWT is required"
            )
        
        # Extract JWT claims
        claims = self._decode_jwt(request)
        
        return TenantContext(
            tenant_id=tenant_id,
            tenant_name=claims.get("tenant_name", tenant_id),
            user_id=claims.get("sub"),
            department_id=claims.get("department_id"),
            allowed_department_ids=claims.get("department_ids", []),
            role=claims.get("role", "user")
        )
    
    def _get_tenant_from_jwt(self, request: Request) -> Optional[str]:
        """Extract tenant_id from JWT token"""
        claims = self._decode_jwt(request)
        return claims.get("tenant_id")
    
    def _decode_jwt(self, request: Request) -> dict:
        """Decode JWT token from Authorization header"""
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return {}
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            claims = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"]
            )
            return claims
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT: {e}")
            return {}


def get_tenant_context(request: Request) -> TenantContext:
    """
    FastAPI dependency to get tenant context from request.
    
    Usage:
        @app.get("/items")
        def list_items(tenant: TenantContext = Depends(get_tenant_context)):
            # tenant.tenant_id, tenant.department_id, etc.
    """
    if not hasattr(request.state, "tenant"):
        raise HTTPException(
            status_code=500,
            detail="Tenant context not available"
        )
    return request.state.tenant


def require_department(department_id: str):
    """
    Dependency factory to require user access to a specific department.
    
    Usage:
        @app.get("/clinical/docs")
        def get_clinical_docs(
            tenant: TenantContext = Depends(require_department("clinical"))
        ):
            ...
    """
    def dependency(request: Request) -> TenantContext:
        tenant = get_tenant_context(request)
        
        if department_id not in tenant.allowed_department_ids:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to department: {department_id}"
            )
        
        return tenant
    
    return dependency


def require_role(role: str):
    """
    Dependency factory to require a specific role.
    
    Usage:
        @app.delete("/users/{id}")
        def delete_user(
            tenant: TenantContext = Depends(require_role("admin"))
        ):
            ...
    """
    ROLE_HIERARCHY = {
        "user": 1,
        "manager": 2,
        "admin": 3,
        "super_admin": 4
    }
    
    def dependency(request: Request) -> TenantContext:
        tenant = get_tenant_context(request)
        
        user_level = ROLE_HIERARCHY.get(tenant.role, 0)
        required_level = ROLE_HIERARCHY.get(role, 999)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' or higher required"
            )
        
        return tenant
    
    return dependency
