"""
VaultMind Admin API
Tenant and user administration

Phase 3: API-First Architecture
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, EmailStr

from api.middleware.tenant import get_tenant_context, TenantContext, require_role
from app.auth.tenant_auth_manager import get_tenant_auth_manager
from app.auth.models import UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class TenantResponse(BaseModel):
    """Tenant information"""
    id: str
    name: str
    display_name: str
    is_active: bool
    created_at: datetime


class DepartmentCreate(BaseModel):
    """Create department request"""
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    """Department information"""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    is_active: bool


class UserCreate(BaseModel):
    """Create user request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = "user"
    department_ids: List[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Update user request"""
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    department_ids: Optional[List[str]] = None


class UserResponse(BaseModel):
    """User information"""
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    departments: List[DepartmentResponse]
    created_at: datetime
    last_login: Optional[datetime]


class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: str
    event_type: str
    user_id: Optional[str]
    resource_type: str
    resource_id: Optional[str]
    action: str
    details: dict
    ip_address: Optional[str]
    timestamp: datetime


class AuditLogResponse(BaseModel):
    """Audit log query response"""
    entries: List[AuditLogEntry]
    total: int
    limit: int
    offset: int


# ==================== Tenant Endpoints ====================

@router.get("/tenant", response_model=TenantResponse)
async def get_current_tenant(
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    Get current tenant information.
    """
    auth_manager = get_tenant_auth_manager()
    tenant_obj = auth_manager.get_tenant_by_id(tenant.tenant_id)
    
    if not tenant_obj:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return TenantResponse(
        id=str(tenant_obj.id),
        name=tenant_obj.name,
        display_name=tenant_obj.display_name,
        is_active=tenant_obj.is_active,
        created_at=tenant_obj.created_at
    )


# ==================== Department Endpoints ====================

@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    List all departments in the tenant.
    """
    auth_manager = get_tenant_auth_manager()
    departments = auth_manager.get_departments_for_tenant(tenant.tenant_id)
    
    return [
        DepartmentResponse(
            id=str(d.id),
            name=d.name,
            display_name=d.display_name,
            description=d.description,
            is_active=d.is_active
        )
        for d in departments
    ]


@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    request: DepartmentCreate,
    tenant: TenantContext = Depends(require_role("admin"))
):
    """
    Create a new department.
    
    Requires admin role.
    """
    auth_manager = get_tenant_auth_manager()
    
    dept = auth_manager.create_department(
        tenant_id=tenant.tenant_id,
        name=request.name,
        display_name=request.display_name,
        description=request.description
    )
    
    if not dept:
        raise HTTPException(
            status_code=400,
            detail="Failed to create department (may already exist)"
        )
    
    return DepartmentResponse(
        id=str(dept.id),
        name=dept.name,
        display_name=dept.display_name,
        description=dept.description,
        is_active=dept.is_active
    )


@router.delete("/departments/{department_id}")
async def delete_department(
    department_id: str,
    tenant: TenantContext = Depends(require_role("admin"))
):
    """
    Deactivate a department.
    
    Requires admin role.
    """
    # TODO: Implement department deactivation
    return {"message": f"Department {department_id} deactivated"}


# ==================== User Endpoints ====================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    department_id: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(require_role("manager"))
):
    """
    List users in the tenant.
    
    Requires manager role or higher.
    """
    # TODO: Implement user listing with filters
    return []


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    tenant: TenantContext = Depends(require_role("admin"))
):
    """
    Create a new user.
    
    Requires admin role.
    """
    auth_manager = get_tenant_auth_manager()
    
    user = auth_manager.create_user(
        tenant_id=tenant.tenant_id,
        username=request.username,
        email=request.email,
        password=request.password,
        role=UserRole(request.role),
        department_ids=request.department_ids
    )
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Failed to create user (username or email may exist)"
        )
    
    departments = auth_manager.get_user_departments(str(user.id))
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        departments=[
            DepartmentResponse(
                id=str(d.id),
                name=d.name,
                display_name=d.display_name,
                description=d.description,
                is_active=d.is_active
            )
            for d in departments
        ],
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    tenant: TenantContext = Depends(require_role("manager"))
):
    """
    Get user by ID.
    
    Requires manager role or higher.
    """
    auth_manager = get_tenant_auth_manager()
    user = auth_manager.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify same tenant
    if str(user.tenant_id) != tenant.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    departments = auth_manager.get_user_departments(user_id)
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        departments=[
            DepartmentResponse(
                id=str(d.id),
                name=d.name,
                display_name=d.display_name,
                description=d.description,
                is_active=d.is_active
            )
            for d in departments
        ],
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    tenant: TenantContext = Depends(require_role("admin"))
):
    """
    Update user.
    
    Requires admin role.
    """
    # TODO: Implement user update
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    tenant: TenantContext = Depends(require_role("admin"))
):
    """
    Deactivate user.
    
    Requires admin role.
    """
    # TODO: Implement user deactivation
    return {"message": f"User {user_id} deactivated"}


# ==================== Audit Log Endpoints ====================

@router.get("/audit-logs", response_model=AuditLogResponse)
async def get_audit_logs(
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(require_role("admin"))
):
    """
    Query audit logs.
    
    Requires admin role. HIPAA compliant audit trail.
    """
    # TODO: Implement audit log query
    return AuditLogResponse(
        entries=[],
        total=0,
        limit=limit,
        offset=offset
    )


@router.get("/audit-logs/export")
async def export_audit_logs(
    start_date: datetime,
    end_date: datetime,
    format: str = Query("csv", pattern="^(csv|json)$"),
    tenant: TenantContext = Depends(require_role("admin"))
):
    """
    Export audit logs for compliance reporting.
    
    Requires admin role.
    """
    # TODO: Implement audit log export
    return {"message": "Export initiated", "format": format}


# ==================== System Stats ====================

@router.get("/stats")
async def get_system_stats(
    tenant: TenantContext = Depends(require_role("manager"))
):
    """
    Get system statistics for the tenant.
    
    Requires manager role.
    """
    auth_manager = get_tenant_auth_manager()
    departments = auth_manager.get_departments_for_tenant(tenant.tenant_id)
    
    return {
        "tenant_id": tenant.tenant_id,
        "departments_count": len(departments),
        "users_count": 0,  # TODO: Count users
        "documents_count": 0,  # TODO: Count documents
        "queries_today": 0,  # TODO: Count queries
        "storage_used_mb": 0.0  # TODO: Calculate storage
    }
