"""
User Permissions Tab - Enterprise permission management for regular users
"""

import streamlit as st
from app.auth.enterprise_ui import enterprise_ui

def render_user_permissions_tab(user, permissions, auth_middleware):
    """User Permissions Tab - For all authenticated users"""
    
    # Get user info safely
    if isinstance(user, dict):
        user_id = user.get('id', user.get('username', 'unknown'))
        username = user.get('username', 'Unknown')
        role = user.get('role', 'viewer')
    else:
        user_id = str(user.id) if hasattr(user, 'id') else user.username
        username = user.username
        role = user.role.value
    
    # Log access
    auth_middleware.log_user_action("ACCESS_PERMISSIONS_TAB")
    
    # Render enterprise user dashboard
    enterprise_ui.render_user_dashboard(user_id, username, role)
