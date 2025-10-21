# VaultMind GenAI Knowledge Assistant - Modular Dashboard
# This version uses separate tab files for better organization

import os
import sys
from pathlib import Path
import streamlit as st
import logging
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# Import authentication components
from app.auth.auth_ui import AuthUI
from app.auth.authentication import AuthenticationManager, UserRole
from app.auth.enterprise_auth_simple import EnterpriseAuth
from app.middleware.auth_middleware import AuthMiddleware, auth_middleware

# Initialize auth manager
auth_manager = AuthenticationManager()

# Calculate absolute path to project root
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv()
# Also load provider-specific env files if present
try:
    from pathlib import Path as _PathLoader
    _wv_env = _PathLoader("config/weaviate.env")
    if _wv_env.exists():
        load_dotenv(dotenv_path=str(_wv_env), override=True)
    _storage_env = _PathLoader("config/storage.env")
    if _storage_env.exists():
        load_dotenv(dotenv_path=str(_storage_env), override=True)
except Exception:
    pass

if not os.getenv("OPENAI_API_KEY"):
    # Do not stop the app; some providers (Ollama, others) may still be usable
    st.warning("OPENAI_API_KEY not found. OpenAI models may be unavailable. Configure .env to enable them.")

# Import simple vector manager (direct implementation)
from utils.simple_vector_manager import get_simple_indexes, get_simple_vector_status

# Use simple vector manager functions
def get_unified_indexes(force_refresh=False):
    return get_simple_indexes()

def get_vector_db_status():
    return get_simple_vector_status()

# Global sidebar configuration panel
def render_global_sidebar(available_indexes: list):
    """Render the left sidebar with global configuration and status.
    Includes comprehensive AI Model list (detected + full catalog),
    knowledge base selection, backend selector, and basic settings.
    Selections are stored in st.session_state for tabs to consume.
    """
    import streamlit as st
    from itertools import chain
    # Title and helper text
    st.sidebar.header("Configuration")
    st.sidebar.caption("Customize your AI assistant settings")

    # Build AI model catalog
    try:
        from utils.llm_config import (
            get_available_llm_models,
            get_default_llm_model,
            validate_llm_setup,
        )
        detected = get_available_llm_models() or []
        default_model = get_default_llm_model() if detected else None
    except Exception:
        detected, default_model = [], None

    # Full catalog regardless of API keys (names aligned with utils/llm_config)
    full_catalog = [
        # OpenAI
        "OpenAI GPT-4", "OpenAI GPT-4 Turbo", "OpenAI GPT-3.5 Turbo",
        # Anthropic
        "Anthropic Claude 3 Opus", "Anthropic Claude 3 Sonnet", "Anthropic Claude 3 Haiku",
        # Mistral
        "Mistral Large", "Mistral Medium", "Mistral Small",
        # DeepSeek
        "DeepSeek Chat", "DeepSeek Coder",
        # Groq (match LLMConfig display names)
        "Llama 3 70B (Groq)", "Mixtral 8x7B (Groq)",
        # Ollama local (match LLMConfig display names)
        "Llama 3 8B (Ollama)", "Llama 3 70B (Ollama)", "Mistral 7B (Ollama)", "Phi-3 (Ollama)", "Code Llama (Ollama)",
    ]

    # Merge detected + full catalog, preserve order and uniqueness
    combined = []
    seen = set()
    SENTINELS = {
        "No LLM models available - Please check API keys in .env file",
        "No models available",
    }
    for name in chain(detected, full_catalog):
        if name and name not in seen and name not in SENTINELS:
            seen.add(name)
            combined.append(name)

    # Choose default model (persist prior selection if any)
    prior = st.session_state.get("global_model")
    if prior and prior in combined:
        default_model = prior
    elif not default_model or default_model not in combined:
        default_model = combined[0] if combined else "OpenAI GPT-4"

    st.session_state["global_model"] = st.sidebar.selectbox(
        "AI Model",
        combined if combined else ["OpenAI GPT-4"],
        index=(combined.index(default_model) if default_model in combined else 0),
        key="sidebar_ai_model",
    )

    # Knowledge Base section
    st.sidebar.subheader("Knowledge Base")
    st.session_state["enable_document_kb"] = st.sidebar.toggle(
        "Enable document knowledge",
        value=st.session_state.get("enable_document_kb", True),
        key="sidebar_enable_kb",
    )

    kb_value = None
    if st.session_state["enable_document_kb"]:
        # Merge Weaviate collections and local indexes
        kb_options = []
        try:
            from utils.weaviate_manager import get_weaviate_manager
            try:
                wm = get_weaviate_manager()
                colls = wm.list_collections() or []
                kb_options.extend(colls)
            except Exception:
                pass
        except Exception:
            pass
        try:
            if available_indexes:
                for idx in available_indexes:
                    if idx and idx not in kb_options:
                        kb_options.append(idx)
        except Exception:
            pass
        if not kb_options:
            kb_options = ["default_faiss"]
        kb_value = st.sidebar.selectbox(
            "Choose source",
            kb_options,
            key="sidebar_kb_selector",
            help="Select a Weaviate collection or local FAISS index",
        )
    st.session_state["global_kb"] = kb_value

    # Search backend selector
    st.sidebar.subheader("Search Backend")
    backend_options = ["Weaviate (Cloud Vector DB)", "FAISS (Local Index)", "Both"]
    default_backend_idx = 1
    try:
        import weaviate  # noqa: F401
        default_backend_idx = 0
    except Exception:
        default_backend_idx = 1
    st.session_state["global_backend"] = st.sidebar.selectbox(
        "Backend",
        backend_options,
        index=default_backend_idx,
        key="sidebar_backend_selector",
    )

    # General settings
    st.sidebar.subheader("Settings")
    st.session_state["conversation_memory"] = st.sidebar.toggle(
        "Conversation memory",
        value=st.session_state.get("conversation_memory", True),
        key="sidebar_conv_memory",
    )
    st.session_state["ui_mode"] = st.sidebar.selectbox(
        "Mode",
        ["Advanced", "Basic"],
        index=0 if st.session_state.get("ui_mode", "Advanced") == "Advanced" else 1,
        key="sidebar_ui_mode",
    )

    # System Status
    st.sidebar.subheader("System Status")
    # LLM status
    try:
        from utils.llm_config import validate_llm_setup as _validate
        ok, msg = _validate(st.session_state["global_model"])  # type: ignore[arg-type]
        if ok:
            st.sidebar.success(f"LLM: {msg}")
        else:
            st.sidebar.warning(f"LLM: {msg}")
    except Exception:
        st.sidebar.info("LLM status unavailable")

    # Vector DB status
    try:
        status, message = get_vector_db_status()
        if status == "Ready":
            st.sidebar.success(message)
        else:
            st.sidebar.error(message)
    except Exception:
        st.sidebar.info("Vector DB status unavailable")

    # Mark that the global sidebar has been rendered to avoid duplicates from tabs
    try:
        st.session_state["_global_sidebar_rendered"] = True
    except Exception:
        pass

# Import tab modules
from tabs import (
    render_document_ingestion,
    render_query_assistant,
    render_agent_assistant,
    render_mcp_dashboard,
    render_multi_content_dashboard,
    render_tool_requests,
    render_admin_panel,
    render_user_permissions_tab,
)

# Import multi-vector tabs
MULTI_VECTOR_IMPORT_ERROR_MESSAGE = ""
try:
    from tabs.multi_vector_document_ingestion import render_multi_vector_document_ingestion
    from tabs.multi_vector_query_assistant import render_multi_vector_query_assistant
    from utils.multi_vector_ui_components import render_vector_store_health_dashboard
    MULTI_VECTOR_AVAILABLE = True
except ImportError as e:
    MULTI_VECTOR_AVAILABLE = False
    MULTI_VECTOR_IMPORT_ERROR_MESSAGE = str(e)
    print(f"Multi-vector components not available: {e}")

from tabs.storage_settings import render_storage_settings
from utils.multi_vector_storage_manager import close_global_manager

# Import enhanced chat assistant
from tabs.chat_assistant_enhanced import render_chat_assistant
ENHANCED_CHAT_AVAILABLE = True

# Proactively reset the global multi-vector manager each rerun so config/code changes apply
try:
    close_global_manager()
except Exception:
    pass

# Page configuration
st.set_page_config(
    page_title="VaultMind GenAI Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .tab-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .metric-container {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Authentication check
if not st.session_state.get('authenticated', False):
    # Use enterprise authentication
    from app.auth.enterprise_auth_integration import get_enterprise_auth
    from app.auth.enterprise_auth_simple import EnterpriseAuth
    
    enterprise_auth = get_enterprise_auth()
    simple_auth = EnterpriseAuth()
    
    # Render enterprise login page
    if simple_auth.render_login_page():
        st.rerun()
    st.stop()

# Get authenticated user and permissions
user_dict = st.session_state.user
permissions = auth_middleware.get_user_permissions()

# Convert user dict to an object with attributes for compatibility
class UserObj:
    def __init__(self, user):
        self.username = user.get('username', 'Unknown')
        self.email = user.get('email', 'No email')
        role = user.get('role', 'viewer')
        class Role:
            def __init__(self, value):
                self.value = value
        self.role = Role(role)
        
    # Add get method for compatibility with dict-style access
    def get(self, key, default=None):
        if key == 'username':
            return self.username
        elif key == 'email':
            return self.email
        elif key == 'role':
            return self.role.value
        return default
        
user = UserObj(user_dict)

# Header with logo and title
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<h1 class="main-header">🧠 VaultMind GenAI Knowledge Assistant</h1>', unsafe_allow_html=True)

# Welcome message
st.markdown(f"**Welcome back, {user.get('username', 'User')}!** | Role: {user.get('role', 'user').title()} | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
# Quick status indicator for multi-vector availability
st.caption(f"Multi-Vector components: {'Available ✅' if MULTI_VECTOR_AVAILABLE else 'Unavailable ❌'}")
if not MULTI_VECTOR_AVAILABLE and MULTI_VECTOR_IMPORT_ERROR_MESSAGE:
    st.caption(f"Import error: {MULTI_VECTOR_IMPORT_ERROR_MESSAGE}")
from pathlib import Path as _Path
st.caption(f"Dashboard file: {_Path(__file__).name} | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# Initialize session state for dynamic index refresh
if 'last_index_refresh' not in st.session_state:
    st.session_state.last_index_refresh = 0

# Force refresh indexes if requested
force_refresh = st.session_state.get('force_index_refresh', False)
if force_refresh:
    st.session_state.force_index_refresh = False
    st.session_state.last_index_refresh += 1

available_indexes = get_unified_indexes(force_refresh=force_refresh)

# Define INDEX_ROOT for compatibility with legacy functions
INDEX_ROOT = PROJECT_ROOT / "data" / "indexes"

# Render global sidebar (left panel) with configuration/status
try:
    render_global_sidebar(available_indexes)
except Exception:
    # Fail gracefully; tabs will still render
    pass

# Tab configuration based on user role
# Allow exposing Weaviate Settings to all via env flag
WV_SETTINGS_FOR_ALL = os.getenv("WEAVIATE_SETTINGS_FOR_ALL", "false").lower() in ("1", "true", "yes")
tab_config = {
    "ingest": ("📄 Ingest Document", True),  # Available to all authenticated users
    "query": ("🔍 Query Assistant", True),  # Available to all roles
    "chat": ("💬 Chat Assistant", True),   # Available to all roles
    "agent": ("🤖 Agent Assistant", True),  # Available to all authenticated users
    "research": ("📚 Enhanced Research", True),  # Research tab - available to all users
    "mcp": ("📊 MCP Dashboard", True),  # Available to all authenticated users
    "multicontent": ("🌐 Multi-Content", permissions.get('can_manage_content', False)),
    "tool_requests": ("🛠️ Tool Requests", True),  # Available to all authenticated users
    "permissions": ("🔒 Permissions", True),  # My Access & Requests - available to all authenticated users
    "storage_settings": ("🔌 Storage Settings", permissions.get('can_manage_users', False) or WV_SETTINGS_FOR_ALL),
    "admin": ("⚙️ Admin Panel", permissions.get('can_manage_users', False))
}

# Always add multi-vector tabs; content will show setup guidance if unavailable
tab_config.update({
    "multi_ingest": ("🚀 Multi-Vector Ingest", True),  # Available to all roles
    "multi_query": ("🔍 Multi-Vector Query", True),  # Available to all roles
    "vector_health": ("📊 Vector Store Health", True)  # Available to all roles
})

# Filter tabs based on permissions
available_tabs = {key: label for key, (label, allowed) in tab_config.items() if allowed}

# Fallback: Ensure at least basic tabs are available
if not available_tabs:
    logger.warning("No tabs available, providing fallback tabs")
    available_tabs = {
        "query": "🔍 Query Assistant",
        "chat": "💬 Chat Assistant",
        "ingest": "📄 Ingest Document"
    }

# Debug: Show what tabs are available
logger.info(f"Available tabs for user: {list(available_tabs.keys())}")
logger.info(f"User permissions: {permissions}")
logger.info(f"Multi-vector available: {MULTI_VECTOR_AVAILABLE}")

# Create tabs
if available_tabs:
    tab_names = list(available_tabs.values())
    tab_objects = st.tabs(tab_names)
    
    # Create tab dictionary for easy access
    tab_dict = {key: tab_objects[i] for i, key in enumerate(available_tabs.keys())}
    
    # Render each tab using imported functions
    if "ingest" in tab_dict:
        with tab_dict["ingest"]:
            render_document_ingestion(user, permissions, auth_middleware, available_indexes, INDEX_ROOT, PROJECT_ROOT)
    if "query" in tab_dict:
        with tab_dict["query"]:
            render_query_assistant(user, permissions, auth_middleware, available_indexes)
    if "chat" in tab_dict:
        with tab_dict["chat"]:
            render_chat_assistant(user, permissions, auth_middleware)
    if "agent" in tab_dict:
        with tab_dict["agent"]:
            render_agent_assistant(user, permissions, auth_middleware, available_indexes)
    if "research" in tab_dict:
        with tab_dict["research"]:
            try:
                from tabs import render_enhanced_research
                render_enhanced_research()
                logger.info("Enhanced Research tab rendered successfully")
            except Exception as e:
                st.error(f"Error loading Enhanced Research tab: {str(e)}")
                logger.error(f"Failed to render Enhanced Research tab: {str(e)}")
    if "mcp" in tab_dict:
        with tab_dict["mcp"]:
            render_mcp_dashboard(user, permissions, auth_middleware)
    if "multicontent" in tab_dict:
        with tab_dict["multicontent"]:
            try:
                from tabs.multi_content_enhanced import render_multi_content_enhanced
                render_multi_content_enhanced(user, permissions, auth_middleware, available_indexes)
                logger.info("Enhanced Multi-Content tab rendered successfully")
            except Exception as e:
                # Show error details and force enhanced version to work
                st.error(f"Enhanced Multi-Content loading error: {str(e)}")
                st.info("Attempting to load enhanced version with basic permissions...")
                try:
                    # Force load enhanced version with simplified parameters
                    from tabs.multi_content_enhanced import render_multi_content_enhanced
                    # Create basic permissions if missing
                    if not permissions:
                        permissions = {'can_access_admin_features': True}
                    render_multi_content_enhanced(user, permissions, auth_middleware, available_indexes or [])
                except Exception as e2:
                    st.error(f"Both enhanced and fallback failed: {str(e2)}")
                    # Last resort - show basic functionality (avoid duplicate keys)
                    st.header("🌐 Multi-Content Dashboard")
                    st.markdown("**Basic Excel functionality available**")
                    uploaded = st.file_uploader(
                        "📁 Upload Excel File",
                        type=["xlsx", "xls"],
                        key="excel_basic_uploader",
                        help="Upload a small Excel file to preview"
                    )
                    if uploaded is not None:
                        try:
                            sheets = pd.read_excel(uploaded, sheet_name=None, engine="openpyxl")
                            sheet_names = list(sheets.keys()) or ["Sheet1"]
                            sel = st.selectbox(
                                "Select sheet",
                                options=sheet_names,
                                key="excel_basic_sheet_select"
                            )
                            st.dataframe(sheets.get(sel), use_container_width=True)
                        except Exception as _excel_err:
                            st.error(f"Excel preview failed: {_excel_err}")
                logger.error(f"Failed to render Enhanced Multi-Content tab: {str(e)}")
    if "storage_settings" in tab_dict:
        with tab_dict["storage_settings"]:
            render_storage_settings(form_key_prefix="storage_settings_top")
    if "admin" in tab_dict:
        with tab_dict["admin"]:
            render_admin_panel(user, permissions, auth_middleware)
    
    # Multi-vector tabs
    if "multi_ingest" in tab_dict:
        with tab_dict["multi_ingest"]:
            if MULTI_VECTOR_AVAILABLE:
                render_multi_vector_document_ingestion()
            else:
                # Try a lazy import fallback so we can still render if environment recovered
                try:
                    from tabs.multi_vector_document_ingestion import render_multi_vector_document_ingestion as _lazy_mv_ingest
                    from utils.multi_vector_ui_components import render_vector_store_health_dashboard as _lazy_mv_health
                    _lazy_mv_ingest()
                except Exception as _e:
                    st.header("🚀 Multi-Vector Ingest")
                    st.info("Multi-vector components are not available in this environment.")
                    if MULTI_VECTOR_IMPORT_ERROR_MESSAGE:
                        st.caption(f"Import error: {MULTI_VECTOR_IMPORT_ERROR_MESSAGE}")
                    st.caption(f"Runtime import: {_e}")
                    st.markdown("- Ensure optional dependencies are installed (see `config/multi_vector_config.yml`)\n- Restart the app after installation\n- Check logs for 'Multi-vector components not available' import errors")
    if "multi_query" in tab_dict:
        with tab_dict["multi_query"]:
            if MULTI_VECTOR_AVAILABLE:
                render_multi_vector_query_assistant()
            else:
                try:
                    from tabs.multi_vector_query_assistant import render_multi_vector_query_assistant as _lazy_mv_query
                    _lazy_mv_query()
                except Exception as _e:
                    st.header("🔍 Multi-Vector Query")
                    st.info("Multi-vector components are not available in this environment.")
                    if MULTI_VECTOR_IMPORT_ERROR_MESSAGE:
                        st.caption(f"Import error: {MULTI_VECTOR_IMPORT_ERROR_MESSAGE}")
                    st.caption(f"Runtime import: {_e}")
                    st.markdown("- Install optional adapters as needed (Pinecone, Qdrant, etc.)\n- Configure `config/multi_vector_config.yml` and restart")
    if "vector_health" in tab_dict:
        with tab_dict["vector_health"]:
            if MULTI_VECTOR_AVAILABLE:
                render_vector_store_health_dashboard()
            else:
                try:
                    from utils.multi_vector_ui_components import render_vector_store_health_dashboard as _lazy_mv_health
                    _lazy_mv_health()
                except Exception as _e:
                    st.header("📊 Vector Store Health")
                    st.info("Multi-vector components are not available in this environment.")
                    if MULTI_VECTOR_IMPORT_ERROR_MESSAGE:
                        st.caption(f"Import error: {MULTI_VECTOR_IMPORT_ERROR_MESSAGE}")
                    st.caption(f"Runtime import: {_e}")
                    st.markdown("- Once configured, this dashboard will display per-store health and collection counts")

else:
    st.error("No tabs available for your current role. Please contact an administrator.")

# Footer with security info
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### ⚙️ System Status")
    st.success("✅ Authenticated Session")
    # Display Vector DB Status from the unified manager
    status, message = get_vector_db_status()
    if status == "Ready":
        st.success(f"Vector DB: {message}")
    else:
        st.error(f"Vector DB: {message}")

with col2:
    st.markdown("### 📊 Session Info")
    st.write(f"User: {user.get('username', 'Unknown')}")
    st.write(f"Email: {user.get('email', 'No email')}")

with col3:
    st.markdown("### 🛡️ Actions")
    active_permissions = [k.replace('can_', '').title() for k, v in permissions.items() if v]
    for perm in active_permissions[:2]:  # Show first 2
        st.write(f"✅ {perm}")
    if len(active_permissions) > 2:
        st.write(f"... and {len(active_permissions) - 2} more")
    
    # Enterprise logout with security features
    if st.button("🔐 Secure Logout", type="primary"):
        enterprise_auth = EnterpriseAuth()
        enterprise_auth.logout()
        st.rerun()
