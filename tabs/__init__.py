"""Tabs package: resilient import layer for Streamlit dashboard.
If a tab module fails to import (e.g., due to merge conflicts), we expose a stub
renderer that shows an error inside the tab instead of crashing the whole app.

Enhanced: add a lazy loader so that once a file is fixed, the tab can recover on
the next render without restarting the Streamlit process (which caches modules).
"""

import sys
import importlib
from pathlib import Path

# Ensure project root on path
sys.path.append(str(Path(__file__).resolve().parent.parent))

def _stub_renderer(name: str):
    def _render_stub(*args, **kwargs):
        try:
            import streamlit as st
            st.error(f"Tab '{name}' is temporarily unavailable due to a load error.")
            st.info("Please resolve merge conflicts or module errors in the corresponding file and rerun the app.")
        except Exception:
            pass
    return _render_stub

def _lazy_renderer(module_path: str, func_name: str, friendly_name: str):
    """Attempt to import and call the real renderer on each invocation.
    Uses importlib.reload to avoid stale modules when files are fixed at runtime.
    Falls back to an inline error if import/call fails.
    """
    def _render(*args, **kwargs):
        try:
            if module_path in sys.modules:
                mod = importlib.reload(sys.modules[module_path])
            else:
                mod = importlib.import_module(module_path)
            func = getattr(mod, func_name)
            return func(*args, **kwargs)
        except Exception as e:
            try:
                import streamlit as st
                st.error(f"Tab '{friendly_name}' is temporarily unavailable due to a load error.")
                st.caption(str(e))
            except Exception:
                pass
    return _render

# Document Ingestion (always lazy to ensure recovery without full restart)
render_document_ingestion = _lazy_renderer(
    "tabs.document_ingestion_fixed",
    "render_document_ingestion",
    "Document Ingestion",
)

# Query Assistant (classic single-query implementation; keep lazy for recovery)
render_query_assistant = _lazy_renderer(
    "tabs.query_assistant",
    "render_query_assistant",
    "Query Assistant",
)

# Chat Assistant (enhanced)
try:
    from .chat_assistant_enhanced import render_chat_assistant
except Exception:
    render_chat_assistant = _stub_renderer("Chat Assistant")

# Agent Assistant (enhanced, always lazy)
render_agent_assistant = _lazy_renderer(
    "tabs.agent_assistant_enhanced",
    "render_agent_assistant",
    "Agent Assistant",
)

# MCP Dashboard
try:
    from .mcp_dashboard import render_mcp_dashboard
except Exception:
    render_mcp_dashboard = _stub_renderer("MCP Dashboard")

# Multi-Content (basic)
try:
    from .multi_content_dashboard import render_multi_content_dashboard
except Exception:
    render_multi_content_dashboard = _stub_renderer("Multi-Content")

# Multi-Content (enhanced)
try:
    from .multi_content_enhanced import render_multi_content_enhanced
except Exception:
    render_multi_content_enhanced = _stub_renderer("Multi-Content Enhanced")

# Tool Requests
try:
    from .tool_requests import render_tool_requests
except Exception:
    render_tool_requests = _stub_renderer("Tool Requests")

# Admin Panel
try:
    from .admin_panel import render_admin_panel
except Exception:
    render_admin_panel = _stub_renderer("Admin Panel")

# User Permissions
try:
    from .user_permissions_tab import render_user_permissions_tab
except Exception:
    render_user_permissions_tab = _stub_renderer("Permissions")

# Enhanced Research
try:
    from .enhanced_research import render_enhanced_research
except Exception:
    render_enhanced_research = _stub_renderer("Enhanced Research")


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
