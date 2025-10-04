"""
VaultMind GenAI Knowledge Assistant - Authentication Middleware
Production-ready middleware for request authentication and authorization
"""

import streamlit as st
from functools import wraps
from typing import Callable, Any
from ..auth.authentication import auth_manager, UserRole
from ..auth.auth_ui import AuthUI
import time

class AuthMiddleware:
    """Authentication and authorization middleware"""
    
    @staticmethod
    def require_auth(func: Callable) -> Callable:
        """Decorator to require authentication for a function"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not AuthUI.require_authentication():
                return None
            return func(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def require_role(role: UserRole):
        """Decorator to require specific role for a function"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not AuthUI.require_authentication():
                    return None
                
                if not AuthUI.require_role(role):
                    AuthUI.access_denied_message(role)
                    return None
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def admin_only(func: Callable) -> Callable:
        """Decorator to require admin role"""
        return AuthMiddleware.require_role(UserRole.ADMIN)(func)
    
    @staticmethod
    def user_or_admin(func: Callable) -> Callable:
        """Decorator to require user or admin role"""
        return AuthMiddleware.require_role(UserRole.USER)(func)
    
    @staticmethod
    def check_session_validity():
        """Check if current session is still valid"""
        if st.session_state.get('authenticated') and st.session_state.get('auth_token'):
            token_data = auth_manager.verify_token(st.session_state.auth_token)
            if not token_data:
                # Token expired or invalid
                st.warning("⚠️ Session expired. Please log in again.")
                AuthUI.logout()
                return False
        return True
    
    @staticmethod
    def log_user_action(action: str, details: str = ""):
        """Log user actions for audit trail"""
        if st.session_state.get('authenticated') and st.session_state.get('user'):
            user = st.session_state.user
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Handle both dict and object user formats
            if isinstance(user, dict):
                username = user.get('username', 'Unknown')
                role = user.get('role', 'viewer')
            else:
                username = user.username
                role = user.role.value
            
            print(f"[{timestamp}] User: {username} | Role: {role} | Action: {action} | Details: {details}")
    
    @staticmethod
    def get_user_permissions() -> dict:
        """Get current user's permissions"""
        if not st.session_state.get('authenticated') or not st.session_state.get('user'):
            return {
                'can_upload': False,
                'can_query': False,
                'can_chat': False,
                'can_use_agents': False,
                'can_manage_users': False,
                'can_view_mcp': False,
                'can_manage_content': False
            }
        
        # Handle both dict and object user formats
        user = st.session_state.user
        if isinstance(user, dict):
            user_role_str = user.get('role', 'viewer')
            user_role = UserRole(user_role_str) if user_role_str in [r.value for r in UserRole] else UserRole.VIEWER
        else:
            user_role = user.role
        
        if user_role == UserRole.ADMIN:
            return {
                'can_upload': True,
                'can_query': True,
                'can_chat': True,
                'can_use_agents': True,
                'can_manage_users': True,
                'can_view_mcp': True,
                'can_manage_content': True
            }
        elif user_role == UserRole.USER:
            return {
                'can_upload': True,
                'can_query': True,
                'can_chat': True,
                'can_use_agents': True,
                'can_manage_users': False,
                'can_view_mcp': False,
                'can_manage_content': False
            }
        else:  # VIEWER
            return {
                'can_upload': True,  # Allow viewers to upload documents
                'can_query': True,
                'can_chat': True,
                'can_use_agents': True,  # Allow viewers to use agents
                'can_manage_users': False,
                'can_view_mcp': True,  # Allow viewers to see MCP dashboard
                'can_manage_content': False
            }

# Global middleware instance
auth_middleware = AuthMiddleware()
