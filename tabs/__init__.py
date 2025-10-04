# Tab modules for VaultMind GenAI Knowledge Assistant

from .document_ingestion_fixed import render_document_ingestion
from .query_assistant import render_query_assistant
# Import enhanced chat assistant
from .chat_assistant_enhanced import render_chat_assistant

# Import agent configuration
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))


# Import enhanced agent assistant
from .agent_assistant_enhanced import render_agent_assistant

# Import enhanced MCP dashboard
from .mcp_dashboard import render_mcp_dashboard

from .multi_content_dashboard import render_multi_content_dashboard

# Import enhanced multi-content dashboard
from .multi_content_enhanced import render_multi_content_enhanced
from .tool_requests import render_tool_requests
from .admin_panel import render_admin_panel
from .user_permissions_tab import render_user_permissions_tab

# Import the enhanced research tab
from .enhanced_research import render_enhanced_research


__all__ = [
    'render_document_ingestion',
    'render_query_assistant', 
    'render_chat_assistant',
    'render_agent_assistant',
    'render_mcp_dashboard',
    'render_multi_content_dashboard',
    'render_multi_content_enhanced',
    'render_tool_requests',
    'render_admin_panel',
    'render_user_permissions_tab',
    'render_enhanced_research',
]
