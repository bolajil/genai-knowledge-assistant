import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
from app.auth.auth_ui import AuthUI
from app.auth.security_setup import security_setup_dashboard
from utils.weaviate_manager import get_weaviate_manager, WeaviateManager
from tabs.storage_settings import render_storage_settings

@st.cache_data(ttl=300)  # Cache for 5 minutes
def _check_admin_permissions(user_role):
    """Cached permission check"""
    return user_role == 'admin'

def render_admin_panel(user, permissions, auth_middleware):
    """Admin Panel Tab - Admin only with performance optimizations"""
    
    # Optimized permission check with caching
    user_role = user.role.value if hasattr(user, 'role') else user.get('role', 'viewer')
    if not _check_admin_permissions(user_role):
        st.error("🚫 Access Denied: Admin privileges required")
        return
    
    # Log action only once per session
    if 'admin_panel_accessed' not in st.session_state:
        auth_middleware.log_user_action("ACCESS_ADMIN_PANEL")
        st.session_state.admin_panel_accessed = True
    
    # Enhanced enterprise tabs with index management and Storage settings
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 User Management", "🛡️ Security Setup", "🎯 Enterprise Permissions", "📁 Index Management", "🔌 Storage Settings"
    ])
    
    # Use session state to track active tab and avoid unnecessary renders
    if 'active_admin_tab' not in st.session_state:
        st.session_state.active_admin_tab = 0
    
    with tab1:
        if st.session_state.get('active_admin_tab', 0) == 0 or tab1:
            AuthUI.admin_panel_optimized()
    
    with tab2:
        if st.session_state.get('active_admin_tab', 0) == 1 or tab2:
            security_setup_dashboard.render_optimized()
    
    with tab3:
        if st.session_state.get('active_admin_tab', 0) == 2 or tab3:
            from app.auth.enterprise_ui import enterprise_ui
            enterprise_ui.render_admin_permission_management()
    
    with tab4:
        try:
            from tabs.index_management import render_index_management
            render_index_management()
        except Exception as e:
            st.error(f"Error loading index management: {str(e)}")
            st.write("**Alternative Index Management:**")
            render_simple_index_management()

    with tab5:
        try:
            render_storage_settings(form_key_prefix="storage_settings_admin")
        except Exception as e:
            st.error(f"Error loading Storage settings: {str(e)}")

def render_simple_index_management():
    """Simple index management interface as fallback"""
    st.title("📁 Index Management")
    st.markdown("Manage your document indexes")
    
    try:
        import os
        from pathlib import Path
        import shutil
        
        # Get all available indexes
        indexes = {}
        
        # Check FAISS indexes
        faiss_dir = Path("data/faiss_index")
        if faiss_dir.exists():
            indexes['FAISS'] = []
            for item in faiss_dir.iterdir():
                if item.is_dir() and item.name.endswith('_index'):
                    index_name = item.name.replace('_index', '')
                    indexes['FAISS'].append((index_name, str(item)))
        
        # Check directory indexes
        dir_indexes = Path("data/indexes")
        if dir_indexes.exists():
            indexes['Directory'] = []
            for item in dir_indexes.iterdir():
                if item.is_dir():
                    index_name = item.name.replace('_index', '')
                    indexes['Directory'].append((index_name, str(item)))
        
        # Display indexes with delete options
        for index_type, index_list in indexes.items():
            if index_list:
                st.subheader(f"{index_type} Indexes ({len(index_list)})")
                
                for index_name, index_path in index_list:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        # Calculate size
                        try:
                            total_size = sum(f.stat().st_size for f in Path(index_path).rglob('*') if f.is_file())
                            size_mb = total_size / (1024 * 1024)
                            st.write(f"**{index_name}** - {size_mb:.1f} MB")
                        except:
                            st.write(f"**{index_name}** - Size unknown")
                    
                    with col2:
                        if st.button("ℹ️ Info", key=f"info_{index_name}_{index_type}"):
                            st.info(f"Path: {index_path}")
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_{index_name}_{index_type}"):
                            # Confirmation in session state
                            st.session_state[f"confirm_delete_{index_name}"] = True
                    
                    # Show confirmation dialog if needed
                    if st.session_state.get(f"confirm_delete_{index_name}", False):
                        st.warning(f"⚠️ Delete '{index_name}'? This cannot be undone!")
                        col_yes, col_no = st.columns(2)
                        
                        with col_yes:
                            if st.button("✅ Yes", key=f"yes_{index_name}"):
                                try:
                                    shutil.rmtree(index_path)
                                    st.success(f"Deleted '{index_name}' successfully!")
                                    st.session_state[f"confirm_delete_{index_name}"] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting '{index_name}': {str(e)}")
                        
                        with col_no:
                            if st.button("❌ No", key=f"no_{index_name}"):
                                st.session_state[f"confirm_delete_{index_name}"] = False
                                st.rerun()
        
        if not any(indexes.values()):
            st.info("No indexes found")
    
    except Exception as e:
        st.error(f"Error in index management: {str(e)}")

def _bool_env(val: str, default: bool) -> bool:
    if val is None:
        return default
    v = str(val).lower()
    return v in ("1", "true", "yes", "on") if default else v not in ("0", "false", "no", "off")

def render_weaviate_settings(form_key_prefix: str = "wv_settings"):
    """Weaviate Settings UI: edit URL/API key, toggle connection behavior, run preflight, and persist settings."""
    st.title("🔌 Weaviate Settings")
    st.caption("Configure the Weaviate cluster connection. Changes persist to config/weaviate.env.")

    # Load current env overrides (if present)
    env_path = Path("config") / "weaviate.env"
    if env_path.exists():
        try:
            load_dotenv(dotenv_path=str(env_path), override=True)
            st.info(f"Loaded current settings from {env_path}")
        except Exception as e:
            st.warning(f"Could not load {env_path}: {e}")

    # Current values from environment
    cur_url = os.getenv("WEAVIATE_URL", "")
    cur_key = os.getenv("WEAVIATE_API_KEY", "")
    cur_http2 = _bool_env(os.getenv("WEAVIATE_HTTP2"), False)
    cur_tls_verify = _bool_env(os.getenv("WEAVIATE_TLS_VERIFY", "true"), True)
    cur_ca_bundle = os.getenv("WEAVIATE_CA_BUNDLE", "")
    cur_use_network = _bool_env(os.getenv("WEAVIATE_USE_NETWORK_DOMAIN"), False)
    cur_disable_rewrite = _bool_env(os.getenv("WEAVIATE_DISABLE_DOMAIN_REWRITE", "true"), True)
    cur_disable_gcp = _bool_env(os.getenv("WEAVIATE_DISABLE_GCP_PATTERNS"), False)
    cur_pf_init = _bool_env(os.getenv("WEAVIATE_PREFLIGHT_ON_INIT", "true"), True)
    cur_pf_change = _bool_env(os.getenv("WEAVIATE_PREFLIGHT_ON_URL_CHANGE", "true"), True)
    cur_pf_fatal = _bool_env(os.getenv("WEAVIATE_PREFLIGHT_FAIL_FATAL", "false"), False)
    try:
        cur_pf_timeout = float(os.getenv("WEAVIATE_PREFLIGHT_TIMEOUT", "8"))
    except Exception:
        cur_pf_timeout = 8.0

    with st.form(f"{form_key_prefix}_form"):
        url = st.text_input("Weaviate URL", cur_url, placeholder="https://<slug>.c0.<region>.<provider>.weaviate.cloud", key=f"{form_key_prefix}_url")
        api_key = st.text_input("Weaviate API Key", cur_key, type="password", key=f"{form_key_prefix}_apikey")
        cols = st.columns(2)
        with cols[0]:
            http2 = st.checkbox("Enable HTTP/2", value=cur_http2, key=f"{form_key_prefix}_http2")
            tls_verify = st.checkbox("Verify TLS certificates", value=cur_tls_verify, key=f"{form_key_prefix}_tls")
            use_network = st.checkbox("Use weaviate.network domain", value=cur_use_network, key=f"{form_key_prefix}_usenet")
            disable_rewrite = st.checkbox("Disable domain rewrite", value=cur_disable_rewrite, key=f"{form_key_prefix}_norewrite")
        with cols[1]:
            ca_bundle = st.text_input("Custom CA bundle path (optional)", cur_ca_bundle, key=f"{form_key_prefix}_cabundle")
            disable_gcp = st.checkbox("Disable GCP/WCS prefix probing", value=cur_disable_gcp, key=f"{form_key_prefix}_nogcp")
            pf_init = st.checkbox("Preflight on init", value=cur_pf_init, key=f"{form_key_prefix}_pfi")
            pf_change = st.checkbox("Preflight on URL change", value=cur_pf_change, key=f"{form_key_prefix}_pfc")
            pf_fatal = st.checkbox("Fail startup if preflight fails", value=cur_pf_fatal, key=f"{form_key_prefix}_pff")
        pf_timeout = st.number_input("Preflight timeout (seconds)", min_value=2.0, max_value=60.0, step=1.0, value=cur_pf_timeout, key=f"{form_key_prefix}_pft")

        bcols = st.columns(3)
        run_preflight = bcols[0].form_submit_button("▶️ Run Preflight")
        save_btn = bcols[1].form_submit_button("💾 Save Settings")
        apply_btn = bcols[2].form_submit_button("🔁 Apply (Reload)")

    # Helper to render result badges
    def _badge(ok: bool):
        if ok:
            st.success("Preflight passed (basic endpoints reachable)")
        else:
            st.error("Preflight failed. Check URL, TLS settings, or API key.")

    # Handle Preflight run without persisting
    if run_preflight:
        if not url.strip():
            st.warning("Please enter a Weaviate URL")
        else:
            # Temporarily set environment for this preflight
            keys = [
                "WEAVIATE_HTTP2", "WEAVIATE_TLS_VERIFY", "WEAVIATE_CA_BUNDLE",
                "WEAVIATE_USE_NETWORK_DOMAIN", "WEAVIATE_DISABLE_DOMAIN_REWRITE",
                "WEAVIATE_DISABLE_GCP_PATTERNS", "WEAVIATE_PREFLIGHT_TIMEOUT",
            ]
            prev = {k: os.environ.get(k) for k in keys}
            try:
                os.environ["WEAVIATE_HTTP2"] = "true" if http2 else "false"
                os.environ["WEAVIATE_TLS_VERIFY"] = "true" if tls_verify else "false"
                if ca_bundle:
                    os.environ["WEAVIATE_CA_BUNDLE"] = ca_bundle
                else:
                    os.environ.pop("WEAVIATE_CA_BUNDLE", None)
                os.environ["WEAVIATE_USE_NETWORK_DOMAIN"] = "true" if use_network else "false"
                os.environ["WEAVIATE_DISABLE_DOMAIN_REWRITE"] = "true" if disable_rewrite else "false"
                os.environ["WEAVIATE_DISABLE_GCP_PATTERNS"] = "true" if disable_gcp else "false"
                os.environ["WEAVIATE_PREFLIGHT_TIMEOUT"] = str(max(2.0, float(pf_timeout)))

                # Create a temporary manager with the provided URL/API key and run preflight
                temp_mgr = WeaviateManager(url=url, api_key=api_key)
                ok = temp_mgr._run_preflight()
                try:
                    temp_mgr.close()
                except Exception:
                    pass
                _badge(ok)
            except Exception as e:
                st.error(f"Preflight error: {e}")
            finally:
                # Restore environment
                for k, v in prev.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

    # Save settings to config/weaviate.env
    if save_btn:
        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            if env_path.exists():
                backup = env_path.with_suffix(env_path.suffix + ".bak")
                try:
                    backup.write_text(env_path.read_text(encoding="utf-8"), encoding="utf-8")
                    st.info(f"Backed up existing settings to {backup}")
                except Exception:
                    pass
            # Build file content
            lines = {
                "WEAVIATE_URL": url.strip(),
                "WEAVIATE_API_KEY": api_key.strip(),
                "WEAVIATE_HTTP2": "true" if http2 else "false",
                "WEAVIATE_TLS_VERIFY": "true" if tls_verify else "false",
                "WEAVIATE_USE_NETWORK_DOMAIN": "true" if use_network else "false",
                "WEAVIATE_DISABLE_DOMAIN_REWRITE": "true" if disable_rewrite else "false",
                "WEAVIATE_DISABLE_GCP_PATTERNS": "true" if disable_gcp else "false",
                "WEAVIATE_PREFLIGHT_ON_INIT": "true" if pf_init else "false",
                "WEAVIATE_PREFLIGHT_ON_URL_CHANGE": "true" if pf_change else "false",
                "WEAVIATE_PREFLIGHT_FAIL_FATAL": "true" if pf_fatal else "false",
                "WEAVIATE_PREFLIGHT_TIMEOUT": str(max(2.0, float(pf_timeout))),
            }
            if ca_bundle.strip():
                lines["WEAVIATE_CA_BUNDLE"] = ca_bundle.strip()
            content = "\n".join([f"{k}={v}" for k, v in lines.items()]) + "\n"
            env_path.write_text(content, encoding="utf-8")
            st.success(f"Saved settings to {env_path}")
        except Exception as e:
            st.error(f"Failed to save settings: {e}")

    # Apply: reload env and rebuild manager (triggers preflight if enabled)
    if apply_btn:
        try:
            if env_path.exists():
                load_dotenv(dotenv_path=str(env_path), override=True)
            # Touch manager to trigger dynamic rebuild if URL changed
            mgr = get_weaviate_manager()
            st.success("Applied settings and reloaded manager.")
            # Force a rerun so other tabs pick up the new configuration
            st.rerun()
        except Exception as e:
            st.error(f"Failed to apply settings: {e}")
