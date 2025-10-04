"""
MCP Integration Module
=====================
This module integrates the MCP Logger with the authentication middleware.
"""

import sys
from pathlib import Path
import time
import logging

# Add the project root to the path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import the MCP Logger
try:
    from mcp.logger import mcp_logger
    MCP_LOGGER_AVAILABLE = True
except ImportError:
    MCP_LOGGER_AVAILABLE = False
    logging.warning("MCP Logger not available. Some functionality will be limited.")

def log_user_action_to_mcp(action: str, username: str, user_role: str, details: dict = None):
    """Log a user action to the MCP logger
    
    Args:
        action: The action performed
        username: The username
        user_role: The user role
        details: Additional details about the action
    """
    if MCP_LOGGER_AVAILABLE:
        try:
            mcp_logger.log_operation(
                operation=action,
                username=username,
                user_role=user_role,
                status="success",
                details=details
            )
        except Exception as e:
            logging.error(f"Error logging to MCP: {e}")

def patch_auth_middleware():
    """Patch the auth middleware to log actions to MCP"""
    try:
        from app.middleware.auth_middleware import auth_middleware
        
        # Store the original log_user_action method
        original_log_user_action = auth_middleware.log_user_action
        
        # Create a new log_user_action method that also logs to MCP
        def enhanced_log_user_action(action: str, details: str = ""):
            # Call the original method
            result = original_log_user_action(action, details)
            
            # Also log to MCP if available
            if MCP_LOGGER_AVAILABLE and hasattr(auth_middleware, 'get_current_user'):
                user = auth_middleware.get_current_user()
                if user:
                    if hasattr(user, 'username') and hasattr(user, 'role'):
                        username = user.username
                        role = user.role.value if hasattr(user.role, 'value') else str(user.role)
                    else:
                        username = user.get('username', 'Unknown')
                        role = user.get('role', 'unknown')
                    
                    # Convert details to dict if it's a string
                    details_dict = {"message": details} if isinstance(details, str) else details
                    
                    log_user_action_to_mcp(action, username, role, details_dict)
            
            return result
        
        # Replace the original method with our enhanced version
        auth_middleware.log_user_action = enhanced_log_user_action
        
        logging.info("Successfully patched auth_middleware.log_user_action to integrate with MCP")
        return True
    except Exception as e:
        logging.error(f"Failed to patch auth_middleware: {e}")
        return False

def initialize_mcp_integration():
    """Initialize MCP integration with the auth middleware"""
    if MCP_LOGGER_AVAILABLE:
        patch_successful = patch_auth_middleware()
        if patch_successful:
            logging.info("MCP integration initialized successfully")
        else:
            logging.warning("Failed to initialize MCP integration")
    else:
        logging.warning("MCP Logger not available. MCP integration skipped.")

# Initialize MCP integration when this module is imported
initialize_mcp_integration()
