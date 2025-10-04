import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
import streamlit as st
from dotenv import load_dotenv

from utils.multi_vector_storage_manager import close_global_manager


def _get_bool(val: Optional[str], default: bool) -> bool:
    if val is None:
        return default
    v = str(val).lower().strip()
    if default:
        return v in ("1", "true", "yes", "on")
    else:
        return v not in ("0", "false", "no", "off")


def _write_env_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Backup existing
    if path.exists():
        try:
            backup = path.with_suffix(path.suffix + ".bak")
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass
    # Write
    content = "\n".join(f"{k}={v}" for k, v in data.items()) + "\n"
    path.write_text(content, encoding="utf-8")


def render_storage_settings(form_key_prefix: str = "storage_settings"):
    """Unified Storage Settings UI for Weaviate and all cloud vector stores.

    Saves to config/storage.env and applies immediately on request.
    """
    st.title("🔌 Storage Settings")
    st.caption("Configure credentials and endpoints for your vector stores. Settings are saved to config/storage.env. Use 'Apply' to reload.")

    env_path = Path("config") / "storage.env"
    if env_path.exists():
        try:
            load_dotenv(dotenv_path=str(env_path), override=True)
            st.info(f"Loaded current settings from {env_path}")
        except Exception as e:
            st.warning(f"Could not load {env_path}: {e}")

    # Current values
    cur = os.environ.get

    with st.form(f"{form_key_prefix}_form"):
        # Weaviate (basic)
        with st.expander("Weaviate", expanded=False):
            wv_url = st.text_input("Weaviate URL", cur("WEAVIATE_URL", ""), key=f"{form_key_prefix}_wv_url")
            wv_key = st.text_input("Weaviate API Key", cur("WEAVIATE_API_KEY", ""), type="password", key=f"{form_key_prefix}_wv_key")
            wv_prefix = st.text_input(
                "Path Prefix (optional)",
                cur("WEAVIATE_PATH_PREFIX", ""),
                placeholder="/api or /weaviate (leave blank for default)",
                help="Some managed clusters mount REST under a prefix like '/api' or '/weaviate'. If tests show 404 at /v1, try '/api'.",
                key=f"{form_key_prefix}_wv_prefix",
            )

        # AWS OpenSearch
        with st.expander("AWS OpenSearch", expanded=False):
            aws_host = st.text_input("OpenSearch Host", cur("AWS_OPENSEARCH_HOST", ""), placeholder="search-xxx.region.es.amazonaws.com", key=f"{form_key_prefix}_aws_host")
            aws_region = st.text_input("AWS Region", cur("AWS_REGION", "us-east-1"), key=f"{form_key_prefix}_aws_region")
            aws_ak = st.text_input("AWS Access Key ID", cur("AWS_ACCESS_KEY_ID", ""), key=f"{form_key_prefix}_aws_ak")
            aws_sk = st.text_input("AWS Secret Access Key", cur("AWS_SECRET_ACCESS_KEY", ""), type="password", key=f"{form_key_prefix}_aws_sk")
            aws_st = st.text_input("AWS Session Token (if temporary)", cur("AWS_SESSION_TOKEN", ""), type="password", key=f"{form_key_prefix}_aws_st")
            aws_profile = st.text_input("AWS Profile (optional)", cur("AWS_PROFILE", ""), help="If using AWS SSO or a named profile, set it here and leave keys blank.", key=f"{form_key_prefix}_aws_profile")

        # Azure AI Search
        with st.expander("Azure AI Search", expanded=False):
            az_ep = st.text_input("Endpoint", cur("AZURE_SEARCH_ENDPOINT", ""), placeholder="https://<service>.search.windows.net", key=f"{form_key_prefix}_az_ep")
            az_key = st.text_input("API Key", cur("AZURE_SEARCH_API_KEY", ""), type="password", key=f"{form_key_prefix}_az_key")

        # Vertex AI Matching Engine
        with st.expander("Google Vertex AI (Matching Engine)", expanded=False):
            gcp_project = st.text_input("GCP Project ID", cur("GCP_PROJECT_ID", ""), key=f"{form_key_prefix}_gcp_proj")
            gcp_loc = st.text_input("Location", cur("GCP_LOCATION", "us-central1"), key=f"{form_key_prefix}_gcp_loc")
            vex_endpoint = st.text_input("Index Endpoint Resource", cur("VERTEX_AI_INDEX_ENDPOINT", ""), key=f"{form_key_prefix}_vex_ie")
            creds_path = st.text_input("Service Account JSON path", cur("GOOGLE_APPLICATION_CREDENTIALS", ""), key=f"{form_key_prefix}_gcp_creds")

        # Pinecone
        with st.expander("Pinecone", expanded=False):
            pc_key = st.text_input("API Key", cur("PINECONE_API_KEY", ""), type="password", key=f"{form_key_prefix}_pc_key")
            pc_env = st.text_input("Environment (legacy/pods)", cur("PINECONE_ENVIRONMENT", ""), placeholder="us-east-1-aws or us-east1-gcp (optional)", key=f"{form_key_prefix}_pc_env")

        # Qdrant
        with st.expander("Qdrant", expanded=False):
            qd_url = st.text_input("URL", cur("QDRANT_URL", ""), placeholder="https://<cluster>.qdrant.io or http://localhost:6333", key=f"{form_key_prefix}_qd_url")
            qd_key = st.text_input("API Key", cur("QDRANT_API_KEY", ""), type="password", key=f"{form_key_prefix}_qd_key")

        # PGVector
        with st.expander("PGVector (PostgreSQL)", expanded=False):
            pg_host = st.text_input("Host", cur("POSTGRES_HOST", "localhost"), key=f"{form_key_prefix}_pg_host")
            pg_port = st.text_input("Port", cur("POSTGRES_PORT", "5432"), key=f"{form_key_prefix}_pg_port")
            pg_db = st.text_input("Database", cur("POSTGRES_DB", ""), key=f"{form_key_prefix}_pg_db")
            pg_user = st.text_input("User", cur("POSTGRES_USER", ""), key=f"{form_key_prefix}_pg_user")
            pg_pass = st.text_input("Password", cur("POSTGRES_PASSWORD", ""), type="password", key=f"{form_key_prefix}_pg_pass")
            
        # MongoDB
        with st.expander("MongoDB", expanded=False):
            mongo_conn_string = st.text_input("Connection String", cur("MONGODB_CONNECTION_STRING", ""), placeholder="mongodb://username:password@host:port/database", help="Leave empty to use individual connection parameters below", key=f"{form_key_prefix}_mongo_conn")
            mongo_host = st.text_input("Host", cur("MONGODB_HOST", "localhost"), key=f"{form_key_prefix}_mongo_host")
            mongo_port = st.text_input("Port", cur("MONGODB_PORT", "27017"), key=f"{form_key_prefix}_mongo_port")
            mongo_db = st.text_input("Database", cur("MONGODB_DATABASE", "vaultmind"), key=f"{form_key_prefix}_mongo_db")
            mongo_user = st.text_input("Username", cur("MONGODB_USERNAME", "vaultmind"), key=f"{form_key_prefix}_mongo_user")
            mongo_pass = st.text_input("Password", cur("MONGODB_PASSWORD", ""), type="password", key=f"{form_key_prefix}_mongo_pass")

        cols = st.columns(2)
        save_btn = cols[0].form_submit_button("💾 Save Settings")
        apply_btn = cols[1].form_submit_button("🔁 Apply (Reload)")

    if save_btn:
        try:
            data = {
                # Weaviate
                "WEAVIATE_URL": wv_url.strip(),
                "WEAVIATE_API_KEY": wv_key.strip(),
                "WEAVIATE_PATH_PREFIX": wv_prefix.strip(),
                # AWS
                "AWS_OPENSEARCH_HOST": aws_host.strip(),
                "AWS_REGION": aws_region.strip(),
                "AWS_ACCESS_KEY_ID": aws_ak.strip(),
                "AWS_SECRET_ACCESS_KEY": aws_sk.strip(),
                "AWS_SESSION_TOKEN": aws_st.strip(),
                "AWS_PROFILE": aws_profile.strip(),
                # Azure
                "AZURE_SEARCH_ENDPOINT": az_ep.strip(),
                "AZURE_SEARCH_API_KEY": az_key.strip(),
                # Vertex
                "GCP_PROJECT_ID": gcp_project.strip(),
                "GCP_LOCATION": gcp_loc.strip(),
                "VERTEX_AI_INDEX_ENDPOINT": vex_endpoint.strip(),
                "GOOGLE_APPLICATION_CREDENTIALS": creds_path.strip(),
                # Pinecone
                "PINECONE_API_KEY": pc_key.strip(),
                "PINECONE_ENVIRONMENT": pc_env.strip(),
                # Qdrant
                "QDRANT_URL": qd_url.strip(),
                "QDRANT_API_KEY": qd_key.strip(),
                # PGVector
                "POSTGRES_HOST": pg_host.strip(),
                "POSTGRES_PORT": pg_port.strip(),
                "POSTGRES_DB": pg_db.strip(),
                "POSTGRES_USER": pg_user.strip(),
                "POSTGRES_PASSWORD": pg_pass.strip(),
                # MongoDB
                "MONGODB_CONNECTION_STRING": mongo_conn_string.strip(),
                "MONGODB_HOST": mongo_host.strip(),
                "MONGODB_PORT": mongo_port.strip(),
                "MONGODB_DATABASE": mongo_db.strip(),
                "MONGODB_USERNAME": mongo_user.strip(),
                "MONGODB_PASSWORD": mongo_pass.strip(),
            }
            _write_env_file(env_path, data)
            st.success(f"Saved settings to {env_path}")
        except Exception as e:
            st.error(f"Failed to save settings: {e}")

    if apply_btn:
        try:
            if env_path.exists():
                load_dotenv(dotenv_path=str(env_path), override=True)
            # Rebuild the multi-vector manager to pick up new env vars
            close_global_manager()
            st.success("Applied settings and reloaded managers.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to apply settings: {e}")

    # Quick connection tests
    with st.expander("Quick Connection Tests", expanded=False):
        st.caption("Tests use values from config/storage.env. Click 'Save Settings' first if you changed fields above.")
        st.caption(f"Python interpreter: {sys.executable}")
        st.caption(f"Python version: {sys.version.split()[0]}")
        # Inline Path Prefix input to allow quick override + save even if the main expander isn't used
        inline_cols = st.columns([2, 1])
        inline_prefix = inline_cols[0].text_input(
            "Weaviate Path Prefix (for test and optional save)",
            os.environ.get("WEAVIATE_PATH_PREFIX", ""),
            placeholder="/api or /weaviate (leave blank for none)",
            key=f"{form_key_prefix}_wv_prefix_inline",
            help="Some Weaviate Cloud clusters require a prefix like '/api'."
        )
        if inline_cols[1].button("Save Prefix", key=f"{form_key_prefix}_save_wv_prefix"):
            try:
                existing: dict[str, str] = {}
                if env_path.exists():
                    try:
                        for line in env_path.read_text(encoding="utf-8").splitlines():
                            line = line.strip()
                            if not line or line.startswith('#') or '=' not in line:
                                continue
                            k, v = line.split('=', 1)
                            existing[k.strip()] = v
                    except Exception:
                        pass
                # Update prefix
                if inline_prefix.strip():
                    existing["WEAVIATE_PATH_PREFIX"] = inline_prefix.strip()
                else:
                    # If cleared, remove the key if present
                    existing.pop("WEAVIATE_PATH_PREFIX", None)
                _write_env_file(env_path, existing)
                # Load immediately for this session
                load_dotenv(dotenv_path=str(env_path), override=True)
                st.success("Saved WEAVIATE_PATH_PREFIX to config/storage.env. Click 'Apply (Reload)' for full app-wide effect.")
            except Exception as e:
                st.error(f"Failed to save prefix: {e}")
        test_cols = st.columns(2)
        if test_cols[0].button("Test AWS OpenSearch Connection", key=f"{form_key_prefix}_test_aws"):
            try:
                script_path = Path("scripts") / "test_aws_opensearch_connection.py"
                if not script_path.exists():
                    st.error(f"Test script not found: {script_path}")
                else:
                    cmd = [sys.executable or "python", str(script_path), "--verbose"]
                    with st.spinner("Running AWS OpenSearch connectivity test..."):
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                    st.subheader("Test Output")
                    st.code(result.stdout or "(no stdout)", language="bash")
                    if result.stderr:
                        st.caption("stderr:")
                        st.code(result.stderr, language="bash")
                    if result.returncode == 0:
                        st.success("AWS OpenSearch connectivity OK")
                    else:
                        st.error(f"Connectivity test failed (exit code {result.returncode}). See output above.")
            except Exception as e:
                st.error(f"Failed to run test: {e}")

        if test_cols[1].button("Verify AWS Credentials (STS)", key=f"{form_key_prefix}_test_sts"):
            try:
                code = (
                    "import boto3, json; "
                    "c=boto3.client('sts'); print(json.dumps(c.get_caller_identity()))"
                )
                cmd = [sys.executable or "python", "-c", code]
                with st.spinner("Calling STS get_caller_identity()..."):
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                st.subheader("STS Output")
                st.code(result.stdout or "(no stdout)", language="json")
                if result.stderr:
                    st.caption("stderr:")
                    st.code(result.stderr, language="bash")
                if result.returncode == 0:
                    st.success("AWS credentials are valid (STS succeeded)")
                else:
                    st.error(f"STS call failed (exit code {result.returncode}). See output above.")
            except Exception as e:
                st.error(f"Failed to verify credentials: {e}")

        # Weaviate connectivity test (uses WeaviateManager and current env precedence)
        st.subheader("Weaviate Connection Test")
        if st.button("Test Weaviate Connection", key=f"{form_key_prefix}_test_weaviate"):
            try:
                # Ensure latest env is loaded with correct precedence
                if env_path.exists():
                    load_dotenv(dotenv_path=str(env_path), override=True)
                # Apply inline prefix override for this test if provided
                if inline_prefix.strip():
                    os.environ["WEAVIATE_PATH_PREFIX"] = inline_prefix.strip()
                else:
                    os.environ.pop("WEAVIATE_PATH_PREFIX", None)
                from utils.weaviate_manager import get_weaviate_manager
                wm = get_weaviate_manager()
                base = str(getattr(wm, 'url', '')).rstrip('/')
                # Try to discover a working REST prefix (e.g., '', '/api', '/weaviate')
                discovered_prefix = None
                try:
                    discovered_prefix = wm._discover_rest_prefix(force=True)
                except Exception:
                    discovered_prefix = None
                st.write({
                    "WEAVIATE_URL": base,
                    "WEAVIATE_API_KEY_set": bool(os.environ.get("WEAVIATE_API_KEY")),
                    "WEAVIATE_PATH_PREFIX": os.environ.get("WEAVIATE_PATH_PREFIX", ""),
                    "discovered_prefix": discovered_prefix or "(none)",
                })
                with st.spinner("Pinging Weaviate readiness and schema..."):
                    # Build endpoints to probe with optional discovered prefix and known fallbacks
                    ok_ready = False
                    err_ready = None
                    ready_status = None
                    ready_used = None
                    ok_schema = False
                    schema_status = None
                    schema_used = None
                    ready_attempts = []
                    schema_attempts = []

                    def _add_if_unique(lst, url):
                        if url not in lst:
                            lst.append(url)

                    ready_eps = []
                    schema_eps = []
                    if discovered_prefix is not None:
                        _add_if_unique(ready_eps, f"{base}{discovered_prefix}/v1/.well-known/ready")
                        _add_if_unique(schema_eps, f"{base}{discovered_prefix}/v1/schema")
                        _add_if_unique(schema_eps, f"{base}{discovered_prefix}/v2/collections")
                    # Fallbacks
                    for p in ["", "/weaviate", "/api"]:
                        _add_if_unique(ready_eps, f"{base}{p}/v1/.well-known/ready")
                        _add_if_unique(schema_eps, f"{base}{p}/v1/schema")
                        _add_if_unique(schema_eps, f"{base}{p}/v2/collections")

                    # Readiness probe(s)
                    for rep in ready_eps:
                        try:
                            r = wm._http_request("GET", rep, timeout=8)
                            try:
                                ready_attempts.append({"url": rep, "status": r.status_code})
                            except Exception:
                                pass
                            if r.status_code in (200, 201, 204, 401, 403, 405):
                                ok_ready = True
                                ready_status = r.status_code
                                ready_used = rep
                                break
                        except Exception as e:
                            err_ready = str(e)
                            try:
                                ready_attempts.append({"url": rep, "error": str(e)[:160]})
                            except Exception:
                                pass

                    st.write({
                        "ready_endpoint": ready_status if ready_status is not None else "(none)",
                        "ready_url": ready_used or "(none)",
                    })

                    # Schema/Collections probe(s)
                    for sp in schema_eps:
                        try:
                            s = wm._http_request("GET", sp, timeout=10)
                            try:
                                schema_attempts.append({"url": sp, "status": s.status_code})
                            except Exception:
                                pass
                            # 200 means OK; also accept 201 for some deployments
                            if s.status_code in (200, 201):
                                ok_schema = True
                                schema_status = s.status_code
                                schema_used = sp
                                break
                        except Exception:
                            try:
                                schema_attempts.append({"url": sp, "error": "request failed"})
                            except Exception:
                                pass

                    st.write({
                        "schema_endpoint": schema_status if schema_status is not None else "(none)",
                        "schema_url": schema_used or "(none)",
                    })
                    with st.expander("Probe details", expanded=False):
                        st.write({"ready_attempts": ready_attempts})
                        st.write({"schema_attempts": schema_attempts})
                    # List collections
                    collections = []
                    list_err = None
                    try:
                        collections = wm.list_collections()
                    except Exception as e:
                        list_err = str(e)
                    st.subheader("Result")
                    if ok_ready or ok_schema or collections:
                        st.success("Weaviate reachable.")
                        st.write({"collections": collections})
                        if not collections:
                            st.info("No collections yet. Ingest documents in the Ingest Document tab to create one.")
                    else:
                        st.error("Weaviate did not respond as expected. Double-check URL/API key and network access.")
                        if err_ready:
                            st.caption(f"Readiness error: {err_ready}")
                        if list_err:
                            st.caption(f"List collections error: {list_err}")
            except Exception as e:
                st.error(f"Failed to test Weaviate connection: {e}")
                
        # Add Vector Database Connection Tests
        st.subheader("Vector Database Connection Tests")
        st.caption("Test connections to all configured vector databases")
        
        test_cols = st.columns(2)
        
        if test_cols[0].button("Test Vector DB Provider", key=f"{form_key_prefix}_test_vector_db"):
            try:
                script_path = Path("scripts") / "test_vector_db_connections.py"
                if not script_path.exists():
                    st.error(f"Test script not found: {script_path}")
                else:
                    cmd = [sys.executable or "python", str(script_path), "--verbose"]
                    with st.spinner("Testing vector database connections..."):
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                    st.subheader("Vector DB Provider Test Output")
                    st.code(result.stdout or "(no stdout)", language="bash")
                    if result.stderr:
                        st.caption("stderr:")
                        st.code(result.stderr, language="bash")
                    if result.returncode == 0:
                        st.success("Vector database connections verified successfully")
                    else:
                        st.error(f"Connection test failed (exit code {result.returncode}). See output above.")
            except Exception as e:
                st.error(f"Failed to run test: {e}")
                
        if test_cols[1].button("Test Multi-Vector Stores", key=f"{form_key_prefix}_test_multi_vector"):
            try:
                script_path = Path("scripts") / "test_multi_vector_connections.py"
                if not script_path.exists():
                    st.error(f"Test script not found: {script_path}")
                else:
                    cmd = [sys.executable or "python", str(script_path), "--verbose"]
                    with st.spinner("Testing multi-vector store connections..."):
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                    st.subheader("Multi-Vector Store Test Output")
                    st.code(result.stdout or "(no stdout)", language="bash")
                    if result.stderr:
                        st.caption("stderr:")
                        st.code(result.stderr, language="bash")
                    if result.returncode == 0:
                        st.success("Multi-vector store connections verified successfully")
                    else:
                        st.error(f"Connection test failed (exit code {result.returncode}). See output above.")
            except Exception as e:
                st.error(f"Failed to run test: {e}")
                
        # Add MongoDB Connection Test
        test_cols = st.columns(2)
        
        if test_cols[0].button("Test MongoDB Connection", key=f"{form_key_prefix}_test_mongodb"):
            try:
                script_path = Path("scripts") / "test_mongodb_connection.py"
                if not script_path.exists():
                    st.error(f"Test script not found: {script_path}")
                else:
                    cmd = [sys.executable or "python", str(script_path), "--verbose"]
                    with st.spinner("Testing MongoDB connection..."):
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                    st.subheader("MongoDB Connection Test Output")
                    st.code(result.stdout or "(no stdout)", language="bash")
                    if result.stderr:
                        st.caption("stderr:")
                        st.code(result.stderr, language="bash")
                    if result.returncode == 0:
                        st.success("MongoDB connection verified successfully")
                    else:
                        st.error(f"Connection test failed (exit code {result.returncode}). See output above.")
            except Exception as e:
                st.error(f"Failed to run test: {e}")
