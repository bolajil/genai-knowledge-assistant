"""
VaultMind Authentication API
JWT-based authentication with multi-tenant support

Phase 3: API-First Architecture
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel, EmailStr, Field

from app.auth.tenant_auth_manager import get_tenant_auth_manager, TenantAuthManager
from app.auth.models import UserRole
from api.middleware.tenant import get_tenant_context, TenantContext, require_role

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class LoginRequest(BaseModel):
    """Login request body"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    tenant_id: Optional[str] = Field(None, description="Tenant ID (optional if in header)")


class LoginResponse(BaseModel):
    """Login response with JWT token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    department_ids: List[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    """User information response"""
    id: str
    username: str
    email: str
    role: str
    tenant_id: str
    departments: List[dict]
    is_active: bool


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8)


# ==================== Endpoints ====================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
):
    """
    Authenticate user and return JWT token.
    
    Requires either:
    - `tenant_id` in request body, or
    - `X-Tenant-ID` header
    """
    auth_manager = get_tenant_auth_manager()
    
    # Get tenant ID
    tenant_id = request.tenant_id or x_tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="tenant_id is required (in body or X-Tenant-ID header)"
        )
    
    # Authenticate
    auth_result = auth_manager.authenticate(
        tenant_id=tenant_id,
        username=request.username,
        password=request.password
    )
    
    if not auth_result:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    user, token = auth_result
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=3600,  # 1 hour
        user={
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value
        }
    )


@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    """
    Register a new user in the tenant.
    
    Requires `X-Tenant-ID` header.
    """
    auth_manager = get_tenant_auth_manager()
    
    # Create user
    user = auth_manager.create_user(
        tenant_id=x_tenant_id,
        username=request.username,
        email=request.email,
        password=request.password,
        role=UserRole.USER,
        department_ids=request.department_ids
    )
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Failed to create user (username or email may already exist)"
        )
    
    # Get departments
    departments = auth_manager.get_user_departments(str(user.id))
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.value,
        tenant_id=str(user.tenant_id),
        departments=[
            {"id": str(d.id), "name": d.name, "display_name": d.display_name}
            for d in departments
        ],
        is_active=user.is_active
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    Get current authenticated user information.
    
    Requires valid JWT token in Authorization header.
    """
    if not tenant.user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    auth_manager = get_tenant_auth_manager()
    user = auth_manager.get_user_by_id(tenant.user_id)
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    departments = auth_manager.get_user_departments(tenant.user_id)
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.value,
        tenant_id=str(user.tenant_id),
        departments=[
            {"id": str(d.id), "name": d.name, "display_name": d.display_name}
            for d in departments
        ],
        is_active=user.is_active
    )


@router.post("/refresh")
async def refresh_token(
    request: RefreshRequest,
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    Refresh JWT token using refresh token.
    """
    auth_manager = get_tenant_auth_manager()
    
    new_token = auth_manager.refresh_token(request.refresh_token)
    
    if not new_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )
    
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": 3600
    }


@router.post("/logout")
async def logout(
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    Logout and invalidate current session.
    """
    auth_manager = get_tenant_auth_manager()
    
    # Get token from header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        auth_manager.invalidate_token(token)
    
    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    Change current user's password.
    """
    if not tenant.user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    auth_manager = get_tenant_auth_manager()
    
    success = auth_manager.change_password(
        user_id=tenant.user_id,
        current_password=request.current_password,
        new_password=request.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )
    
    return {"message": "Password changed successfully"}


@router.get("/departments")
async def list_departments(
    tenant: TenantContext = Depends(get_tenant_context)
):
    """
    List all departments in the current tenant.
    """
    auth_manager = get_tenant_auth_manager()
    departments = auth_manager.get_departments_for_tenant(tenant.tenant_id)
    
    return {
        "departments": [
            {
                "id": str(d.id),
                "name": d.name,
                "display_name": d.display_name,
                "description": d.description
            }
            for d in departments
        ]
    }
