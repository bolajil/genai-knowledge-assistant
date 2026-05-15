"""
VaultMind GenAI Knowledge Assistant - Multi-Tenant Authentication Manager
Enhanced authentication with tenant and department isolation

Phase 2: Multi-Tenant Foundation
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
import uuid

import bcrypt
import jwt
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session, joinedload

from .models import (
    User, Tenant, Department, UserDepartment, UserSession, AuditLog,
    UserRole, SensitivityLevel, get_default_departments
)
from .database import get_sync_session, init_sync_db

logger = logging.getLogger(__name__)


@dataclass
class AuthenticatedUser:
    """Enhanced user object with tenant and department info"""
    id: str
    username: str
    email: str
    role: UserRole
    tenant_id: str
    tenant_name: str
    department_ids: List[str]
    primary_department_id: Optional[str]
    is_active: bool
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    @property
    def is_power_user(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.POWER_USER]
    
    def can_access_department(self, department_id: str) -> bool:
        """Check if user can access a specific department"""
        if self.is_admin:
            return True  # Admins can access all departments in their tenant
        return department_id in self.department_ids
    
    def to_jwt_claims(self) -> Dict:
        """Convert to JWT claims"""
        return {
            'user_id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'tenant_id': self.tenant_id,
            'department_ids': self.department_ids,
            'primary_department_id': self.primary_department_id,
        }


class TenantAuthManager:
    """
    Multi-tenant authentication manager.
    Provides tenant-isolated user management and authentication.
    """
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("JWT_SECRET_KEY must be set in production!")
            # Development fallback with warning
            logger.warning("Using development JWT secret - NOT FOR PRODUCTION")
            self.secret_key = "dev-secret-key-not-for-production"
        
        self.token_expiry_hours = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))
        self._session = None
        
        # Initialize database
        try:
            init_sync_db()
        except Exception as e:
            logger.warning(f"Database init skipped: {e}")
    
    @property
    def session(self) -> Session:
        """Get database session"""
        if self._session is None or not self._session.is_active:
            self._session = get_sync_session()
        return self._session
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    # ==================== Tenant Management ====================
    
    def create_tenant(self, name: str, display_name: str, 
                      create_default_departments: bool = True) -> Optional[Tenant]:
        """Create a new tenant with optional default departments"""
        try:
            tenant = Tenant(
                name=name.lower().replace(" ", "_"),
                display_name=display_name,
                is_active=True
            )
            self.session.add(tenant)
            self.session.flush()  # Get the ID
            
            # Create default departments
            if create_default_departments:
                for dept_data in get_default_departments():
                    dept = Department(
                        tenant_id=tenant.id,
                        name=dept_data["name"],
                        display_name=dept_data["display_name"],
                        description=dept_data.get("description"),
                        is_active=True
                    )
                    self.session.add(dept)
            
            self.session.commit()
            logger.info(f"Created tenant: {name}")
            return tenant
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating tenant: {e}")
            return None
    
    def get_tenant_by_name(self, name: str) -> Optional[Tenant]:
        """Get tenant by name"""
        return self.session.execute(
            select(Tenant).where(Tenant.name == name.lower())
        ).scalar_one_or_none()
    
    def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.session.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        ).scalar_one_or_none()
    
    # ==================== Department Management ====================
    
    def get_departments_for_tenant(self, tenant_id: str) -> List[Department]:
        """Get all departments for a tenant"""
        result = self.session.execute(
            select(Department)
            .where(and_(
                Department.tenant_id == uuid.UUID(tenant_id),
                Department.is_active == True
            ))
            .order_by(Department.display_name)
        )
        return list(result.scalars().all())
    
    def get_department_by_name(self, tenant_id: str, name: str) -> Optional[Department]:
        """Get department by name within a tenant"""
        return self.session.execute(
            select(Department).where(and_(
                Department.tenant_id == uuid.UUID(tenant_id),
                Department.name == name.lower()
            ))
        ).scalar_one_or_none()
    
    def create_department(
        self,
        tenant_id: str,
        name: str,
        display_name: str = None,
        description: str = None
    ) -> Optional[Department]:
        """
        Create a new department within a tenant.
        
        Args:
            tenant_id: Parent tenant ID
            name: Department name (will be lowercased)
            display_name: Human-readable name
            description: Department description
            
        Returns:
            Created Department or None if failed
        """
        try:
            dept = Department(
                tenant_id=uuid.UUID(tenant_id),
                name=name.lower().replace(" ", "_"),
                display_name=display_name or name.title(),
                description=description,
                is_active=True
            )
            self.session.add(dept)
            self.session.commit()
            
            logger.info(f"Created department: {name} in tenant: {tenant_id}")
            return dept
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating department: {e}")
            return None
    
    def ensure_department(
        self,
        tenant_id: str,
        name: str,
        display_name: str = None,
        description: str = None
    ) -> Optional[Department]:
        """
        Get department if exists, create if not.
        
        Args:
            tenant_id: Parent tenant ID
            name: Department name
            display_name: Human-readable name (used if creating)
            description: Description (used if creating)
            
        Returns:
            Existing or newly created Department
        """
        # Check if exists
        dept = self.get_department_by_name(tenant_id, name)
        if dept:
            return dept
        
        # Create new
        return self.create_department(
            tenant_id=tenant_id,
            name=name,
            display_name=display_name,
            description=description
        )
    
    # ==================== User Management ====================
    
    def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
        department_ids: List[str] = None,
        display_name: str = None
    ) -> Optional[User]:
        """Create a new user within a tenant"""
        try:
            user = User(
                tenant_id=uuid.UUID(tenant_id),
                username=username.lower(),
                email=email.lower(),
                password_hash=self._hash_password(password),
                role=role,
                display_name=display_name or username,
                is_active=True
            )
            self.session.add(user)
            self.session.flush()  # Get the ID
            
            # Assign to departments
            if department_ids:
                for i, dept_id in enumerate(department_ids):
                    user_dept = UserDepartment(
                        user_id=user.id,
                        department_id=uuid.UUID(dept_id),
                        is_active=True,
                        is_primary=(i == 0)  # First department is primary
                    )
                    self.session.add(user_dept)
            
            self.session.commit()
            
            # Audit log
            self._log_event(
                tenant_id=tenant_id,
                user_id=str(user.id),
                event_type="USER_CREATE",
                resource_type="user",
                resource_id=str(user.id),
                action="CREATE",
                details=f"Created user: {username}"
            )
            
            logger.info(f"Created user: {username} in tenant: {tenant_id}")
            return user
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating user: {e}")
            return None
    
    def authenticate(
        self,
        tenant_name: str,
        username: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Optional[AuthenticatedUser]:
        """Authenticate user within a tenant"""
        try:
            # Get tenant
            tenant = self.get_tenant_by_name(tenant_name)
            if not tenant or not tenant.is_active:
                logger.warning(f"Invalid tenant: {tenant_name}")
                return None
            
            # Find user
            user = self.session.execute(
                select(User)
                .options(joinedload(User.user_departments).joinedload(UserDepartment.department))
                .where(and_(
                    User.tenant_id == tenant.id,
                    User.username == username.lower(),
                    User.is_active == True
                ))
            ).unique().scalar_one_or_none()
            
            if not user:
                logger.warning(f"User not found: {username}")
                return None
            
            # Check if locked
            if user.locked_until and datetime.utcnow() < user.locked_until:
                logger.warning(f"Account locked: {username}")
                return None
            
            # Verify password
            if not self._verify_password(password, user.password_hash):
                # Increment failed attempts
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                self.session.commit()
                
                self._log_event(
                    tenant_id=str(tenant.id),
                    user_id=str(user.id),
                    event_type="LOGIN_FAILED",
                    resource_type="user",
                    resource_id=str(user.id),
                    action="AUTHENTICATE",
                    details=f"Failed login attempt #{user.failed_login_attempts}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                return None
            
            # Successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            self.session.commit()
            
            # Get department info
            department_ids = []
            primary_dept_id = None
            for ud in user.user_departments:
                if ud.is_active:
                    department_ids.append(str(ud.department_id))
                    if ud.is_primary:
                        primary_dept_id = str(ud.department_id)
            
            # Create authenticated user object
            auth_user = AuthenticatedUser(
                id=str(user.id),
                username=user.username,
                email=user.email,
                role=user.role,
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                department_ids=department_ids,
                primary_department_id=primary_dept_id,
                is_active=user.is_active,
                mfa_enabled=user.mfa_enabled,
                created_at=user.created_at,
                last_login=user.last_login
            )
            
            # Audit log
            self._log_event(
                tenant_id=str(tenant.id),
                user_id=str(user.id),
                event_type="LOGIN",
                resource_type="user",
                resource_id=str(user.id),
                action="AUTHENTICATE",
                details="Successful login",
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return auth_user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def generate_token(self, user: AuthenticatedUser) -> str:
        """Generate JWT token for authenticated user"""
        payload = {
            **user.to_jwt_claims(),
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None
    
    def get_user_from_token(self, token: str) -> Optional[AuthenticatedUser]:
        """Get authenticated user from JWT token"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        return AuthenticatedUser(
            id=payload['user_id'],
            username=payload['username'],
            email=payload['email'],
            role=UserRole(payload['role']),
            tenant_id=payload['tenant_id'],
            tenant_name=payload.get('tenant_name', ''),
            department_ids=payload.get('department_ids', []),
            primary_department_id=payload.get('primary_department_id'),
            is_active=True,
            mfa_enabled=False,
            created_at=datetime.utcnow()
        )
    
    # ==================== Department Assignment ====================
    
    def assign_user_to_department(
        self,
        user_id: str,
        department_id: str,
        is_primary: bool = False
    ) -> bool:
        """Assign user to a department"""
        try:
            # Check if assignment exists
            existing = self.session.execute(
                select(UserDepartment).where(and_(
                    UserDepartment.user_id == uuid.UUID(user_id),
                    UserDepartment.department_id == uuid.UUID(department_id)
                ))
            ).scalar_one_or_none()
            
            if existing:
                existing.is_active = True
                existing.is_primary = is_primary
            else:
                user_dept = UserDepartment(
                    user_id=uuid.UUID(user_id),
                    department_id=uuid.UUID(department_id),
                    is_active=True,
                    is_primary=is_primary
                )
                self.session.add(user_dept)
            
            # If setting as primary, unset other primaries
            if is_primary:
                self.session.execute(
                    UserDepartment.__table__.update()
                    .where(and_(
                        UserDepartment.user_id == uuid.UUID(user_id),
                        UserDepartment.department_id != uuid.UUID(department_id)
                    ))
                    .values(is_primary=False)
                )
            
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error assigning department: {e}")
            return False
    
    def get_user_departments(self, user_id: str) -> List[Department]:
        """Get all departments for a user"""
        result = self.session.execute(
            select(Department)
            .join(UserDepartment)
            .where(and_(
                UserDepartment.user_id == uuid.UUID(user_id),
                UserDepartment.is_active == True,
                Department.is_active == True
            ))
        )
        return list(result.scalars().all())
    
    # ==================== Audit Logging ====================
    
    def _log_event(
        self,
        event_type: str,
        action: str,
        tenant_id: str = None,
        user_id: str = None,
        department_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        details: str = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        """Log an audit event"""
        try:
            log = AuditLog(
                tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
                user_id=uuid.UUID(user_id) if user_id else None,
                department_id=uuid.UUID(department_id) if department_id else None,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            self.session.add(log)
            self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")
    
    # ==================== Initialization Helpers ====================
    
    def ensure_default_tenant(self, tenant_name: str = "default") -> Tenant:
        """Ensure a default tenant exists for development"""
        tenant = self.get_tenant_by_name(tenant_name)
        if not tenant:
            tenant = self.create_tenant(
                name=tenant_name,
                display_name="Default Tenant",
                create_default_departments=True
            )
        return tenant
    
    def ensure_admin_user(
        self,
        tenant_id: str,
        username: str = "admin",
        email: str = "admin@vaultmind.ai",
        password: str = "VaultMind2025!"
    ) -> Optional[User]:
        """Ensure admin user exists in tenant"""
        existing = self.session.execute(
            select(User).where(and_(
                User.tenant_id == uuid.UUID(tenant_id),
                User.username == username
            ))
        ).scalar_one_or_none()
        
        if existing:
            return existing
        
        # Get all department IDs for admin
        departments = self.get_departments_for_tenant(tenant_id)
        dept_ids = [str(d.id) for d in departments]
        
        return self.create_user(
            tenant_id=tenant_id,
            username=username,
            email=email,
            password=password,
            role=UserRole.ADMIN,
            department_ids=dept_ids,
            display_name="System Administrator"
        )


# Singleton instance
_tenant_auth_manager = None

def get_tenant_auth_manager() -> TenantAuthManager:
    """Get singleton TenantAuthManager instance"""
    global _tenant_auth_manager
    if _tenant_auth_manager is None:
        _tenant_auth_manager = TenantAuthManager()
    return _tenant_auth_manager
