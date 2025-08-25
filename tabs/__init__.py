# Tab modules for VaultMind GenAI Knowledge Assistant

from .document_ingestion import render_document_ingestion
from .query_assistant import render_query_assistant
from .chat_assistant import render_chat_assistant  # Using enhanced chat assistant

# Import agent configuration
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import the simple query assistant (direct import for easier access)
from .query_assistant_simple import render_query_assistant as render_simple_query_assistant
print("Simple Multi-Source Query Assistant loaded successfully")

try:
    # Try to import the agent configuration
    from config.agent_config import USE_ENHANCED_AGENT
    
    # Choose which agent assistant to use based on configuration
    if USE_ENHANCED_AGENT:
        from .agent_assistant_enhanced import render_agent_assistant
        print("Using enhanced Agent Assistant with multi-source search capabilities")
    else:
        from .agent_assistant_simple import render_agent_assistant
        print("Using standard Agent Assistant")
except ImportError:
    # Fallback to simple agent if config not found
    from .agent_assistant_simple import render_agent_assistant
    print("Agent config not found. Using standard Agent Assistant")

from .mcp_dashboard_simple import render_mcp_dashboard
from .multi_content_dashboard import render_multi_content_dashboard
from .tool_requests import render_tool_requests
from .admin_panel import render_admin_panel

# Import the enhanced research tab
try:
    from .enhanced_research import render_enhanced_research
    print("Enhanced Research tab loaded successfully")
    ENHANCED_RESEARCH_AVAILABLE = True
except ImportError as e:
    print(f"Error loading Enhanced Research tab: {str(e)}")
    ENHANCED_RESEARCH_AVAILABLE = False

# Set debug mode
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vaultmind")
logger.info("Loading VaultMind modules with enhanced Chat Assistant")

__all__ = [
    'render_document_ingestion',
    'render_query_assistant', 
    'render_chat_assistant',
    'render_agent_assistant',
    'render_mcp_dashboard',
    'render_multi_content_dashboard',
    'render_tool_requests',
    'render_admin_panel',
    'render_enhanced_research'
]
