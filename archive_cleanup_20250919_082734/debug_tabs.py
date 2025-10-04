"""
Debug Tab Permissions
Quick diagnostic to identify why tabs aren't showing
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def debug_session_state():
    """Debug current session state"""
    st.write("## 🔍 Session State Debug")
    
    st.write("### Authentication Status")
    st.write(f"- Authenticated: {st.session_state.get('authenticated', False)}")
    st.write(f"- User: {st.session_state.get('user', 'None')}")
    
    if st.session_state.get('user'):
        user = st.session_state.user
        if isinstance(user, dict):
            st.write(f"- Username: {user.get('username', 'Unknown')}")
            st.write(f"- Role: {user.get('role', 'Unknown')}")
        else:
            st.write(f"- Username: {getattr(user, 'username', 'Unknown')}")
            st.write(f"- Role: {getattr(user, 'role', 'Unknown')}")

def debug_permissions():
    """Debug permission system"""
    st.write("### Permission System")
    
    try:
        from app.middleware.auth_middleware import auth_middleware
        permissions = auth_middleware.get_user_permissions()
        
        st.write("**Current Permissions:**")
        for perm, value in permissions.items():
            status = "✅" if value else "❌"
            st.write(f"- {status} {perm}: {value}")
            
    except Exception as e:
        st.error(f"Error getting permissions: {e}")

def debug_tab_config():
    """Debug tab configuration"""
    st.write("### Tab Configuration")
    
    try:
        from app.middleware.auth_middleware import auth_middleware
        permissions = auth_middleware.get_user_permissions()
        
        # Recreate tab config logic
        tab_config = {
            "ingest": ("📄 Ingest Document", permissions.get('can_upload', False)),
            "query": ("🔍 Query Assistant", True),
            "chat": ("💬 Chat Assistant", True),
            "agent": ("🤖 Agent Assistant", permissions.get('can_use_agents', False)),
            "research": ("📚 Enhanced Research", True),
            "mcp": ("📊 MCP Dashboard", permissions.get('can_view_mcp', False)),
            "multicontent": ("🌐 Multi-Content", permissions.get('can_manage_content', False)),
            "tool_requests": ("🛠️ Tool Requests", not permissions.get('can_manage_users', False)),
            "weaviate_settings": ("🔌 Weaviate Settings", permissions.get('can_manage_users', False)),
            "admin": ("⚙️ Admin Panel", permissions.get('can_manage_users', False))
        }
        
        # Check multi-vector availability
        try:
            from tabs.multi_vector_document_ingestion import render_multi_vector_document_ingestion
            MULTI_VECTOR_AVAILABLE = True
            st.write("✅ Multi-vector components available")
        except Exception as e:
            MULTI_VECTOR_AVAILABLE = False
            st.write(f"❌ Multi-vector components not available: {e}")
        
        if MULTI_VECTOR_AVAILABLE:
            tab_config.update({
                "multi_ingest": ("🚀 Multi-Vector Ingest", True),
                "multi_query": ("🔍 Multi-Vector Query", True),
                "vector_health": ("📊 Vector Store Health", True)
            })
        
        st.write("**Tab Configuration:**")
        available_count = 0
        for key, (label, allowed) in tab_config.items():
            status = "✅" if allowed else "❌"
            st.write(f"- {status} {key}: {label} (allowed: {allowed})")
            if allowed:
                available_count += 1
        
        st.write(f"**Total available tabs: {available_count}**")
        
        # Filter tabs
        available_tabs = {key: label for key, (label, allowed) in tab_config.items() if allowed}
        st.write(f"**Filtered available tabs: {list(available_tabs.keys())}**")
        
    except Exception as e:
        st.error(f"Error in tab configuration: {e}")

def main():
    st.title("🔧 VaultMind Tab Debug Tool")
    st.write("This tool helps diagnose why tabs aren't showing up.")
    
    debug_session_state()
    debug_permissions()
    debug_tab_config()
    
    st.write("---")
    st.write("### 💡 Quick Fixes")
    
    if st.button("Reset Session State"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Session state cleared! Please refresh the page.")
    
    if st.button("Force Authentication"):
        st.session_state.authenticated = True
        st.session_state.user = {
            'username': 'debug_user',
            'email': 'debug@example.com',
            'role': 'admin'
        }
        st.success("Forced authentication! Please refresh the page.")

if __name__ == "__main__":
    main()
