"""
VaultMind GenAI Knowledge Assistant - Database Models
SQLAlchemy models for multi-tenant enterprise deployment

Phase 2: Multi-Tenant Foundation
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid

from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, ForeignKey, 
    Text, Enum as SQLEnum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, Enum):
    """User roles with hierarchical permissions"""
    VIEWER = "viewer"       # Read-only access
    USER = "user"           # Standard user
    POWER_USER = "power_user"  # Advanced features
    ADMIN = "admin"         # Full access


class SensitivityLevel(str, Enum):
    """Document sensitivity classification"""
    PUBLIC = "public"           # Anyone can access
    INTERNAL = "internal"       # Authenticated users only
    CONFIDENTIAL = "confidential"  # Department-restricted
    RESTRICTED = "restricted"   # Admin-only access


class Tenant(Base):
    """
    Tenant represents a top-level organization (e.g., Huron client).
    All data is isolated at the tenant level.
    """
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Settings stored as JSON
    settings = Column(Text, nullable=True)  # JSON config per tenant
    
    # Relationships
    departments = relationship("Department", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant {self.name}>"


class Department(Base):
    """
    Department within a tenant (e.g., Clinical, Finance, HR).
    Documents and users are scoped to departments.
    """
    __tablename__ = "departments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="departments")
    user_departments = relationship("UserDepartment", back_populates="department", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_department"),
        Index("ix_departments_tenant", "tenant_id"),
    )
    
    def __repr__(self):
        return f"<Department {self.name}>"


class User(Base):
    """
    User account with multi-tenant and multi-department support.
    Enhanced from original SQLite schema.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Core fields (preserved from original)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    
    # Status fields (preserved from original)
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps (preserved from original)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # New enterprise fields
    display_name = Column(String(255), nullable=True)
    external_id = Column(String(255), nullable=True)  # For SSO (Okta, SAML)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user_departments = relationship("UserDepartment", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
        Index("ix_users_tenant", "tenant_id"),
        Index("ix_users_email", "email"),
    )
    
    def __repr__(self):
        return f"<User {self.username}>"
    
    @property
    def departments(self) -> List["Department"]:
        """Get all departments this user belongs to"""
        return [ud.department for ud in self.user_departments if ud.is_active]
    
    @property
    def department_ids(self) -> List[str]:
        """Get all department IDs for this user"""
        return [str(ud.department_id) for ud in self.user_departments if ud.is_active]


class UserDepartment(Base):
    """
    Many-to-many relationship between users and departments.
    Users can belong to multiple departments.
    """
    __tablename__ = "user_departments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_primary = Column(Boolean, default=False)  # User's primary department
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_departments")
    department = relationship("Department", back_populates="user_departments")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "department_id", name="uq_user_department"),
        Index("ix_user_departments_user", "user_id"),
        Index("ix_user_departments_dept", "department_id"),
    )


class UserSession(Base):
    """
    User session tracking (preserved from original with enhancements).
    """
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(512), unique=True, nullable=False)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index("ix_sessions_user", "user_id"),
        Index("ix_sessions_token", "session_token"),
        Index("ix_sessions_expires", "expires_at"),
    )


class AuditLog(Base):
    """
    Audit trail for HIPAA compliance.
    Logs all significant actions in the system.
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)  # LOGIN, LOGOUT, DOCUMENT_UPLOAD, QUERY, etc.
    resource_type = Column(String(100), nullable=True)  # document, user, query, etc.
    resource_id = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)  # CREATE, READ, UPDATE, DELETE
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON additional context
    
    # Timestamp (immutable)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_audit_tenant", "tenant_id"),
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_timestamp", "timestamp"),
        Index("ix_audit_event_type", "event_type"),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.event_type} by {self.user_id}>"


# Seed data helper functions
def get_default_departments() -> List[dict]:
    """Default departments for Huron pilot"""
    return [
        {"name": "clinical", "display_name": "Clinical", "description": "Clinical operations and policies"},
        {"name": "finance", "display_name": "Finance", "description": "Financial operations and contracts"},
        {"name": "hr", "display_name": "Human Resources", "description": "HR policies and procedures"},
        {"name": "legal", "display_name": "Legal", "description": "Legal documents and compliance"},
        {"name": "operations", "display_name": "Operations", "description": "General operations"},
    ]
