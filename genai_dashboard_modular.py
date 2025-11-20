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

# Load sensitive settings from Streamlit secrets into environment (if provided)
# This ensures components like utils/weaviate_manager.py pick up cloud credentials
# instead of defaulting to localhost.
try:
    # st is already imported above
    if hasattr(st, "secrets"):
        _sec = st.secrets
        # Keys we care about for Weaviate and LLMs
        for _k in (
            "WEAVIATE_URL",
            "WEAVIATE_API_KEY",
            "WEAVIATE_PATH_PREFIX",
            "WEAVIATE_FORCE_API_VERSION",
            "WEAVIATE_SKIP_V2",
            "OPENAI_API_KEY",
            "OPENAI_ORG",
            "OPENAI_ORGANIZATION",
        ):
            try:
                if _k in _sec and str(_sec[_k]).strip():
                    os.environ[_k] = str(_sec[_k])
            except Exception:
                # Do not block app startup if a secret key is missing/malformed
                pass
except Exception:
    # Secrets may not be available in local runs; that's fine
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

    # Session-only overrides: user API key and Vector DB
    try:
        if "user_api_key" not in st.session_state:
            st.session_state["user_api_key"] = ""
        if "use_custom_weaviate" not in st.session_state:
            st.session_state["use_custom_weaviate"] = False
    except Exception:
        pass

    with st.sidebar.expander("Bring Your Own Keys (Session)", expanded=False):
        # Track if any provider key changed this run
        key_changes = False

        # OpenAI API Key (session-only)
        user_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.get("user_api_key", ""),
            help="Used only for this session; not stored.",
            key="sidebar_user_openai_key",
        )
        if user_api_key and user_api_key != st.session_state.get("user_api_key", ""):
            st.session_state["user_api_key"] = user_api_key
            os.environ["OPENAI_API_KEY"] = user_api_key
            st.success("OpenAI key applied for this session.")
            key_changes = True

        # Additional provider keys (session-only)
        anth_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=st.session_state.get("user_anthropic_api_key", os.getenv("ANTHROPIC_API_KEY", "")),
            key="sidebar_anthropic_key",
            help="Used only for this session; not stored.",
        )
        if anth_key != st.session_state.get("user_anthropic_api_key", ""):
            st.session_state["user_anthropic_api_key"] = anth_key
            if anth_key:
                os.environ["ANTHROPIC_API_KEY"] = anth_key
            key_changes = True

        mistral_key = st.text_input(
            "Mistral API Key",
            type="password",
            value=st.session_state.get("user_mistral_api_key", os.getenv("MISTRAL_API_KEY", "")),
            key="sidebar_mistral_key",
            help="Used only for this session; not stored.",
        )
        if mistral_key != st.session_state.get("user_mistral_api_key", ""):
            st.session_state["user_mistral_api_key"] = mistral_key
            if mistral_key:
                os.environ["MISTRAL_API_KEY"] = mistral_key
            key_changes = True

        deepseek_key = st.text_input(
            "DeepSeek API Key",
            type="password",
            value=st.session_state.get("user_deepseek_api_key", os.getenv("DEEPSEEK_API_KEY", "")),
            key="sidebar_deepseek_key",
            help="Used only for this session; not stored.",
        )
        if deepseek_key != st.session_state.get("user_deepseek_api_key", ""):
            st.session_state["user_deepseek_api_key"] = deepseek_key
            if deepseek_key:
                os.environ["DEEPSEEK_API_KEY"] = deepseek_key
            key_changes = True

        groq_key = st.text_input(
            "Groq API Key",
            type="password",
            value=st.session_state.get("user_groq_api_key", os.getenv("GROQ_API_KEY", "")),
            key="sidebar_groq_key",
            help="Used only for this session; not stored.",
        )
        if groq_key != st.session_state.get("user_groq_api_key", ""):
            st.session_state["user_groq_api_key"] = groq_key
            if groq_key:
                os.environ["GROQ_API_KEY"] = groq_key
            key_changes = True

        ollama_url = st.text_input(
            "Ollama Base URL",
            value=st.session_state.get("user_ollama_url", os.getenv("OLLAMA_BASE_URL", "")),
            key="sidebar_ollama_url",
            help="Optional. Example: http://localhost:11434",
        )
        if ollama_url != st.session_state.get("user_ollama_url", ""):
            st.session_state["user_ollama_url"] = ollama_url
            if ollama_url:
                os.environ["OLLAMA_BASE_URL"] = ollama_url
            key_changes = True

        # Reload LLM model config if any key changed
        if key_changes:
            try:
                import importlib, utils.llm_config as _llmc
                importlib.reload(_llmc)
                st.info("LLM providers updated for this session.")
            except Exception:
                pass

        # Quick provider test to surface misconfiguration/SDK issues
        cols = st.columns([1,1])
        with cols[0]:
            if st.button("Test LLM", use_container_width=True, key="btn_test_llm"):
                try:
                    # Reload LLM config to pick up any just-entered keys
                    import importlib, utils.llm_config as _llmc
                    _llmc = importlib.reload(_llmc)
                    from utils.enhanced_llm_integration import EnhancedLLMProcessor as _ELP
                    model_to_test = st.session_state.get("global_model") or _llmc.get_default_llm_model()
                    ok, msg = _llmc.validate_llm_setup(model_to_test)
                    if not ok:
                        detected = ", ".join(_llmc.get_available_llm_models() or [])
                        st.error(f"LLM not ready: {msg}. Detected models: {detected if detected else 'none'}. Select a model that matches a configured provider in the dropdown above.")
                    else:
                        proc = _ELP()
                        # Minimal test: one small context chunk
                        test_resp = proc.process_retrieval_results(
                            query="Readiness check: write a concise but complete 3-5 sentence summary of the context. Ensure the answer is at least 120 characters.",
                            retrieval_results=[{"content": "This is a minimal context for an LLM readiness test verifying that provider SDKs and API keys are working correctly.", "source": "diagnostics"}],
                            index_name="diagnostics",
                            model_name=model_to_test,
                        )
                        method = test_resp.get("processing_method")
                        result = (test_resp.get("result") or "").strip()
                        used = test_resp.get("model_used") or model_to_test
                        if method == "enhanced_llm" and len(result) > 100:
                            st.success(f"LLM test OK with {used}.")
                        else:
                            st.warning("Enhanced pipeline fell back. Running direct connectivity diagnostics...")
                            # Direct OpenAI diagnostics if key present
                            import os as _os
                            if _os.getenv("OPENAI_API_KEY"):
                                try:
                                    from openai import OpenAI as _OpenAI
                                    client = _OpenAI(api_key=_os.getenv("OPENAI_API_KEY"))
                                    # 1) List models (sanity check)
                                    try:
                                        _ = client.models.list()
                                        st.info("OpenAI: models.list() succeeded")
                                    except Exception as _ml_err:
                                        st.error(f"OpenAI models.list() failed: {_ml_err}")
                                    # 2) Minimal chat call with fallback chain
                                    messages = [
                                        {"role": "system", "content": "You are a concise assistant."},
                                        {"role": "user", "content": "Say 'ready'"},
                                    ]
                                    diag_models = ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"]
                                    ok_any = False
                                    last_e = None
                                    for _m in diag_models:
                                        try:
                                            r = client.chat.completions.create(model=_m, messages=messages, max_tokens=10)
                                            txt = (r.choices[0].message.content or "").strip()
                                            if txt:
                                                st.success(f"OpenAI chat.completions OK with {_m}: {txt}")
                                                ok_any = True
                                                break
                                        except Exception as _ce:
                                            last_e = _ce
                                            continue
                                    if not ok_any:
                                        st.error(f"OpenAI chat.completions failed for all diag models. Last error: {last_e}")
                                except Exception as _dir_err:
                                    st.error(f"Direct OpenAI diagnostic failed: {_dir_err}")
                            else:
                                st.info("No OPENAI_API_KEY detected in environment for direct diagnostics.")
                except Exception as _e_diag:
                    st.error(f"LLM test failed: {_e_diag}")
        with cols[1]:
            if st.button("Show LLM Diagnostics", use_container_width=True, key="btn_llm_diag"):
                import importlib
                import os as _os
                try:
                    import utils.llm_config as _llmc
                    _llmc = importlib.reload(_llmc)
                except Exception as _e:
                    st.error(f"Failed to reload llm_config: {_e}")
                    _llmc = None
                st.write("- **Selected model**:", st.session_state.get("global_model"))
                if _llmc:
                    ok, msg = _llmc.validate_llm_setup(st.session_state.get("global_model", ""))
                    st.write("- **Validation**:", f"{ok} | {msg}")
                    st.write("- **Detected models**:", _llmc.get_available_llm_models())
                # Masked keys presence
                def _mask(val):
                    if not val:
                        return "" 
                    return f"{val[:4]}...{val[-4:]}"
                st.write("- **Keys**:")
                st.code({
                    "OPENAI_API_KEY": bool(_os.getenv("OPENAI_API_KEY")),
                    "ANTHROPIC_API_KEY": bool(_os.getenv("ANTHROPIC_API_KEY")),
                    "MISTRAL_API_KEY": bool(_os.getenv("MISTRAL_API_KEY")),
                    "DEEPSEEK_API_KEY": bool(_os.getenv("DEEPSEEK_API_KEY")),
                    "GROQ_API_KEY": bool(_os.getenv("GROQ_API_KEY")),
                    "OLLAMA_BASE_URL": bool(_os.getenv("OLLAMA_BASE_URL")),
                }, language="json")
                # Package imports
                pkgs = {
                    "openai": "",
                    "langchain_openai": "",
                    "anthropic": "",
                    "langchain_anthropic": "",
                    "mistralai": "",
                    "langchain_mistralai": "",
                    "groq": "",
                    "langchain_groq": "",
                }
                for mod in list(pkgs.keys()):
                    try:
                        m = __import__(mod)
                        ver = getattr(m, "__version__", "(no __version__)")
                        pkgs[mod] = f"OK {ver}"
                    except Exception as _imp_err:
                        pkgs[mod] = f"ERROR: {_imp_err}"
                st.write("- **Provider packages**:")
                st.code(pkgs, language="json")

        st.divider()
        # Optional Vector DB (Weaviate) override (session-only)
        st.session_state["use_custom_weaviate"] = st.checkbox(
            "Use my Weaviate (session-only)",
            value=st.session_state.get("use_custom_weaviate", False),
            help="Override the default vector DB just for this session.",
            key="sidebar_use_custom_weaviate",
        )
        if st.session_state.get("use_custom_weaviate"):
            w_url = st.text_input(
                "Weaviate URL",
                value=st.session_state.get("user_weaviate_url", os.getenv("WEAVIATE_URL", "")),
                help="Example: https://<slug>.c0.<region>.<provider>.weaviate.cloud",
                key="sidebar_weaviate_url",
            )
            w_api = st.text_input(
                "Weaviate API Key",
                type="password",
                value=st.session_state.get("user_weaviate_api", ""),
                help="Leave blank if not required.",
                key="sidebar_weaviate_api",
            )
            w_prefix = st.text_input(
                "Path Prefix (optional)",
                value=st.session_state.get("user_weaviate_prefix", os.getenv("WEAVIATE_PATH_PREFIX", "")),
                help="E.g., /weaviate or /api",
                key="sidebar_weaviate_prefix",
            )
            w_tenant = st.text_input(
                "Tenant (optional)",
                value=st.session_state.get("user_weaviate_tenant", os.getenv("WEAVIATE_TENANT", "")),
                help="Multi-tenant header value.",
                key="sidebar_weaviate_tenant",
            )
            if st.button("Apply Vector DB", use_container_width=True, key="apply_custom_weaviate"):
                st.session_state["user_weaviate_url"] = w_url
                st.session_state["user_weaviate_api"] = w_api
                st.session_state["user_weaviate_prefix"] = w_prefix
                st.session_state["user_weaviate_tenant"] = w_tenant
                if w_url:
                    os.environ["WEAVIATE_URL"] = w_url
                if w_api is not None:
                    os.environ["WEAVIATE_API_KEY"] = w_api
                os.environ["WEAVIATE_PATH_PREFIX"] = w_prefix or ""
                os.environ["WEAVIATE_TENANT"] = w_tenant or ""
                # Reset managers so new env is used
                try:
                    from utils.multi_vector_storage_manager import close_global_manager as _close_gm
                    _close_gm()
                except Exception:
                    pass
                try:
                    from utils.weaviate_manager import get_weaviate_manager as _get_wm
                    _ = _get_wm()
                except Exception:
                    pass
                st.success("Vector DB settings applied for this session.")
                st.rerun()

        # Optional Local FAISS override (session-only)
        with st.expander("Use my local FAISS (session)", expanded=False):
            faiss_root = st.text_input(
                "FAISS Index Root",
                value=st.session_state.get("user_faiss_root", os.getenv("FAISS_INDEX_ROOT", "data/faiss_index")),
                help="Folder containing FAISS indexes (e.g., index.faiss/index.pkl or subfolders)",
                key="sidebar_faiss_root",
            )
            text_root = st.text_input(
                "Text Index Root",
                value=st.session_state.get("user_text_root", os.getenv("TEXT_INDEX_ROOT", "data/indexes")),
                help="Folder containing extracted_text.txt or text-based indexes",
                key="sidebar_text_root",
            )
            if st.button("Apply Local FAISS Paths", use_container_width=True, key="apply_faiss_roots"):
                st.session_state["user_faiss_root"] = faiss_root
                st.session_state["user_text_root"] = text_root
                if faiss_root:
                    os.environ["FAISS_INDEX_ROOT"] = faiss_root
                if text_root:
                    os.environ["TEXT_INDEX_ROOT"] = text_root
                # Trigger fresh index discovery
                st.session_state["force_index_refresh"] = True
                st.success("Local FAISS paths applied for this session.")
                st.rerun()

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

    # Toggle to only show configured models (avoid selecting models without keys)
    show_configured_only = st.sidebar.toggle(
        "Show configured models only",
        value=st.session_state.get("show_configured_models_only", False),
        key="sidebar_models_configured_only",
        help="If enabled, hides models for providers without keys so validation won't fail."
    )
    st.session_state["show_configured_models_only"] = show_configured_only
    model_choices = (detected if show_configured_only else combined) or ["OpenAI GPT-3.5 Turbo"]

    # Choose default model (persist prior selection if any)
    prior = st.session_state.get("global_model")
    default_pool = model_choices
    if prior and prior in default_pool:
        default_model = prior
    elif not default_model or default_model not in default_pool:
        default_model = default_pool[0]

    st.session_state["global_model"] = st.sidebar.selectbox(
        "AI Model",
        model_choices,
        index=(model_choices.index(default_model) if default_model in model_choices else 0),
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

# Import tab modules with reload so fixes are picked up during reruns
import importlib
import tabs as _tabs_mod
try:
    _tabs_mod = importlib.reload(_tabs_mod)
except Exception:
    # If reload fails, continue with existing module
    pass
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Page configuration
st.set_page_config(
    page_title="VaultMind GenAI Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Logging configured above
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
    "agent_hybrid": ("🧠 Agent (Hybrid)", True),  # NEW: Hybrid agent with LangGraph
    "research": ("📚 Enhanced Research", True),  # Research tab - available to all users
    "mcp": ("📊 MCP Dashboard", True),  # Available to all authenticated users
    "multicontent": ("🌐 Multi-Content", permissions.get('can_manage_content', False)),
    "tool_requests": ("🛠️ Tool Requests", True),  # Available to all authenticated users
    "permissions": ("🔒 Permissions", True),  # My Access & Requests - available to all authenticated users
    "notifications": ("📱 Notifications", True),  # Notification settings - available to all authenticated users
    "storage_settings": ("🔌 Storage Settings", permissions.get('can_manage_users', False) or WV_SETTINGS_FOR_ALL),
    "admin": ("⚙️ Admin Panel", permissions.get('can_manage_users', False))
}

# Always add multi-vector tabs; content will show setup guidance if unavailable
tab_config.update({
    "multi_ingest": ("🚀 Multi-Vector Ingest", True),  # Available to all roles
    "multi_query": ("🔍 Multi-Vector Query", True),  # Available to all roles
    "vector_health": ("📊 Vector Store Health", True),  # Available to all roles
    "system_monitoring": ("🔍 System Monitoring", True)  # Available to all roles - monitoring is useful for everyone
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
    if "agent_hybrid" in tab_dict:
        with tab_dict["agent_hybrid"]:
            try:
                from tabs.agent_assistant_hybrid import render_agent_assistant_hybrid
                render_agent_assistant_hybrid()
                logger.info("Hybrid Agent Assistant tab rendered successfully")
            except Exception as e:
                st.error(f"Error loading Hybrid Agent tab: {str(e)}")
                logger.error(f"Failed to render Hybrid Agent tab: {str(e)}")
                st.info("Make sure to install: pip install langgraph sentence-transformers")
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
    if "tool_requests" in tab_dict:
        with tab_dict["tool_requests"]:
            render_tool_requests(user, permissions, auth_middleware)
    if "permissions" in tab_dict:
        with tab_dict["permissions"]:
            render_user_permissions_tab(user_dict, permissions, auth_middleware)
    if "notifications" in tab_dict:
        with tab_dict["notifications"]:
            try:
                from tabs.notification_settings import render_notification_settings
                render_notification_settings()
                logger.info("Notification Settings tab rendered successfully")
            except Exception as e:
                st.error(f"Error loading Notification Settings tab: {str(e)}")
                logger.error(f"Failed to render Notification Settings tab: {str(e)}")
                st.info("Make sure notification_manager.py is configured properly")
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
    
    # System Monitoring Tab
    if "system_monitoring" in tab_dict:
        with tab_dict["system_monitoring"]:
            try:
                from tabs.system_monitoring import show as render_system_monitoring
                render_system_monitoring()
            except Exception as e:
                st.header("🔍 System Monitoring")
                st.error(f"Error loading System Monitoring tab: {str(e)}")
                logger.error(f"Failed to render System Monitoring tab: {str(e)}")
                st.info("Make sure automation dependencies are installed: pip install -r requirements-automation.txt")

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
