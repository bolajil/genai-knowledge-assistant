"""
Query Assistant Tab
==================
Search and retrieve information from indexed documents using natural language.
Access Level: All Users
"""
import streamlit as st
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from utils.vector_db_provider import get_vector_db_provider
import os
import numpy as np
import re
from utils.web_search import run_web_search

# Optional heavy dependencies (guarded to prevent import-time failure)
try:
    import faiss  # type: ignore
    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# P0 Security Imports
from utils.security import validate_search_query, validate_collection_name, validate_top_k, check_rate_limit
from utils.query_cache import get_cached_result, cache_query_result, get_cache_stats
logger = logging.getLogger(__name__)

# Import feedback system components
from utils.feedback_ui_components import render_feedback_buttons, render_query_insights, initialize_feedback_ui

# Import Query Improvements
from utils.query_result_formatter import QueryResultFormatter
from utils.query_expansion import QueryExpander

# Text cleaning helpers
from utils.text_cleaning import clean_document_text, is_noise_text

# Cache controls
from utils.query_cache import invalidate_query_cache

# Import Weaviate collection selector
try:
    from utils.weaviate_collection_selector import render_collection_selector, render_backend_selector
    WEAVIATE_UI_AVAILABLE = True
except ImportError:
    WEAVIATE_UI_AVAILABLE = False
    def render_backend_selector(key="backend"):
        return "FAISS (Local Index)"
    
    def render_collection_selector(key="collection", label="Select Collection", help_text="", include_all_option=False):
        """Fallback collection selector when weaviate_collection_selector is not available"""
        try:
            from utils.weaviate_manager import get_weaviate_manager
            wm = get_weaviate_manager()
            collections = wm.list_collections() or []
            if collections:
                return st.selectbox(label, collections, key=key, help=help_text)
            else:
                st.warning("No Weaviate collections found")
                return None
        except Exception as e:
            st.error(f"Could not load Weaviate collections: {e}")
            return None

def _get_fallback_results(query: str, top_k: int) -> List[Dict[str, str]]:
    """Fallback results when primary search fails"""
    from datetime import datetime
    return [{
        "content": f"⚠️ Primary search failed. This would show results from '{query}'",
        "source": "Fallback System",
        "metadata": {"fallback": True, "timestamp": datetime.now().isoformat()},
        "relevance_score": 0.5,
        "uuid": ""
    } for _ in range(top_k)]

def query_documents(query: str, index_name: str, top_k: int = 5, backend: str = "Weaviate (Cloud Vector DB)") -> List[Dict[str, str]]:
    """Search documents with automatic fallback"""
    try:
        results = []
        if backend == "FAISS (Local Index)":
            try:
                vdb = get_vector_db_provider()
                results = vdb.search_index(query=query, index_name=index_name, top_k=top_k)
                if not results:
                    logger.warning(f"Primary search empty - using fallback for '{index_name}'")
                    results = _get_fallback_results(query, top_k)
            except Exception as e:
                logger.error(f"Search failed: {e}")
                results = _get_fallback_results(query, top_k)
        else:
            if backend == "Weaviate (Cloud Vector DB)":
                from utils.weaviate_manager import get_weaviate_manager
                wm = get_weaviate_manager()
                return wm.get_documents_for_tab(
                    collection_name=index_name,
                    tab_name="query_assistant",
                    query=query,
                    limit=top_k
                )
            else:
                # Route to local FAISS via VectorDBProvider
                vdb = get_vector_db_provider()
                return vdb.search_index(query=query, index_name=index_name, top_k=top_k)
        return results
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return _get_fallback_results(query, top_k)

def _normalize_content_from_result(r, default_source: str = "") -> Dict[str, str]:
    """Type-agnostic normalization for different result schemas.

    Supports keys like 'content', 'text', 'page_content', 'markdown_content', 'chunk'.
    """
    try:
        if isinstance(r, dict):
            raw_content = (
                r.get('content')
                or r.get('text')
                or r.get('page_content')
                or r.get('markdown_content')
                or r.get('chunk')
                or str(r)
            )
            # Clean and filter noise early
            content = clean_document_text(str(raw_content or ""))
            if content and is_noise_text(content):
                content = ""
            # Normalize source: strip any trailing " - Page X" to avoid duplicate page labels
            src_raw = r.get('source') or r.get('file_path') or default_source or "Unknown"
            try:
                src = re.sub(r"\s*-\s*Page\s*\d+\b", "", str(src_raw), flags=re.IGNORECASE).strip()
            except Exception:
                src = str(src_raw)
            page = r.get('page') or r.get('page_number')
            # Normalize page to numeric or None
            if not (isinstance(page, int) or (isinstance(page, str) and page.isdigit())):
                page = None
            section = r.get('section') or r.get('heading')
            # Normalize relevance score to [0,1] when possible
            score = r.get('relevance_score') or r.get('score') or 0.0
            try:
                s = float(score)
                if s > 1.0:
                    # Treat common percent-style values
                    s = s / 100.0 if s <= 100.0 else min(1.0, s / 100.0)
                if s < 0.0:
                    s = 0.0
            except Exception:
                s = 0.0
            return {
                "content": content,
                "source": str(src or "Unknown"),
                "page": page,
                "section": section,
                "relevance_score": s,
            }
        else:
            return {"content": str(r), "source": default_source or "Unknown", "relevance_score": 0.0}
    except Exception:
        return {"content": str(r), "source": default_source or "Unknown", "relevance_score": 0.0}

def _sanitize_ai_markdown(md: str) -> str:
    """Post-process AI markdown to strip TOC/heading-only noise, dotted leaders, and placeholder pages.

    Keeps section headers like '### Executive Summary', '### Detailed Answer', '### Key Points', '### Information Gaps'.
    """
    if not md or not isinstance(md, str):
        return md
    try:
        # Remove explicit 'Page N/A' placeholders anywhere
        md = re.sub(r"\bPage\s*N/?A\b", "", md, flags=re.IGNORECASE)

        keep_headers = {
            '### executive summary',
            '### detailed answer',
            '### key points',
            '### information gaps',
        }

        lines = md.split('\n')
        cleaned_lines: List[str] = []
        seen_norm = set()

        # Simple verb regex (matches common legal/procedural verbs)
        verb_re = re.compile(r"\b(is|are|shall|must|may|will|has|have|does|do|provide|provides|include|includes|appoint|appoints|elect|elects|vote|votes|conduct|conducts|comply|complies|adopt|adopts|keep|keeps|record|records|preside|presides|delegate|delegates|authorize|authorizes|determine|determines|manage|manages)\b", re.IGNORECASE)

        for raw in lines:
            line = raw.strip()
            if not line:
                cleaned_lines.append("")
                continue

            low = line.lower()
            # Normalize plain section titles to markdown headers
            plain_headers = {
                'executive summary': '### Executive Summary',
                'detailed answer': '### Detailed Answer',
                'key points': '### Key Points',
                'information gaps': '### Information Gaps',
            }
            if low in plain_headers:
                cleaned_lines.append(plain_headers[low])
                continue

            # Rewrite 'From <src>:' prefixes to 'According to <src>, '
            try:
                line = re.sub(r'^(from)\s+([^:]+):\s*', r'According to \2, ', line, flags=re.IGNORECASE)
            except Exception:
                pass
            # Always keep section headers we expect from the model
            if low in keep_headers or low.startswith('## '):
                cleaned_lines.append(line)
                continue

            # Drop obvious noise
            if is_noise_text(line):
                continue
            # Drop dotted leader patterns (TOC)
            if re.search(r"\.{3,}\s*\d+$", line):
                continue
            # Drop pure 'Source:' lines just in case
            if low.startswith('source:'):
                continue
            # Drop continuation-looking lines that start with lowercase (not bullets or numbered)
            if re.match(r"^[a-z]", line) and not re.match(r"^[\-\*\d\)\(]+", line):
                continue
            # Drop lines that look like continuations (start with modal/aux)
            if re.match(r"^(must|shall|should|may|will|has|have|does|do|is|are|and|or|including|such as|e\.g\.)\b", low):
                continue
            # Drop lines that end with ':' and lack verbs (likely list-intros)
            if line.endswith(':') and (not verb_re.search(line)):
                continue
            # Drop ALL-CAPS-ish headings
            if (not any(c.islower() for c in line)) and any(c.isupper() for c in line):
                # keep short acronyms, drop multi-word caps
                if len(line.split()) >= 2:
                    continue
            # Drop short title-like lines without verbs (e.g., headings such as 'Quorum of Board of Directors.')
            if (len(line.split()) <= 8) and (not verb_re.search(line)):
                continue
            # If a bullet or numbered item is entirely heading-like, drop it
            bullet = re.sub(r"^[\-\*\d\.)\(\s]+", "", line)
            if bullet and len(bullet.split()) <= 8 and (not verb_re.search(bullet)) and is_noise_text(bullet):
                continue
            # Deduplicate near-identical lines
            norm = re.sub(r"\W+", " ", line).strip().lower()
            if norm in seen_norm and norm:
                continue
            seen_norm.add(norm)
            cleaned_lines.append(line)

        # Remove consecutive blank lines
        out: List[str] = []
        blank = 0
        for l in cleaned_lines:
            if l.strip() == "":
                blank += 1
                if blank > 1:
                    continue
            else:
                blank = 0
            out.append(l)

        return '\n'.join(out).strip()
    except Exception:
        return md

def _is_weaviate_authorized() -> bool:
    """Cache and return whether Weaviate responds on readiness/schema endpoints.

    Uses prefix-aware probing instead of the deprecated /v1/meta, and accepts
    200/201/204/401/403/405 as positive signals (endpoint exists).
    """
    try:
        if 'qa_weaviate_authorized' in st.session_state:
            val = st.session_state.get('qa_weaviate_authorized')
            if isinstance(val, bool):
                return val
        try:
            from utils.weaviate_manager import get_weaviate_manager
            wm = get_weaviate_manager()
            base = str(getattr(wm, 'url', '')).rstrip('/')
            if not base:
                st.session_state['qa_weaviate_authorized'] = False
                return False
            # Discover prefix if possible, otherwise use env-configured prefix
            try:
                prefix = wm._discover_rest_prefix(force=True) or ''
            except Exception:
                prefix = ''
            # Build candidate endpoints (prefix + fallbacks)
            eps = []
            tried = set()
            def add(u: str):
                if u not in tried:
                    eps.append(u); tried.add(u)
            if prefix:
                add(f"{base}{prefix}/v1/.well-known/ready")
                add(f"{base}{prefix}/v1/schema")
                add(f"{base}{prefix}/v2/collections")
            for p in ['', '/api', '/weaviate']:
                add(f"{base}{p}/v1/.well-known/ready")
                add(f"{base}{p}/v1/schema")
                add(f"{base}{p}/v2/collections")
            ok = False
            for url in eps:
                try:
                    r = wm._http_request("GET", url, timeout=6)
                    if r.status_code in (200, 201, 204, 401, 403, 405):
                        ok = True
                        break
                except Exception:
                    pass
            st.session_state['qa_weaviate_authorized'] = ok
            return ok
        except Exception:
            st.session_state['qa_weaviate_authorized'] = False
            return False
    except Exception:
        return False

def _expand_query_variations(q: str) -> List[str]:
    """Generate lightweight semantic variations without external dependencies.

    Covers common legal/enterprise synonyms to improve recall across data types.
    """
    try:
        base = q.strip()
        vars = {base}
        # Simple noun/verb swaps and synonyms
        replacements = [
            ("Powers", "powers"), ("powers", "authority"), ("powers", "powers and duties"),
            ("Right to Disapprove", "veto"), ("disapprove", "reject"),
            ("members", "directors"), ("board members", "board of directors"),
        ]
        for a, b in replacements:
            if a in base:
                vars.add(base.replace(a, b))
            if a.lower() in base.lower():
                try:
                    # case-insensitive replace (best-effort)
                    import re as _re
                    vars.add(_re.sub(_re.compile(_re.escape(a), _re.IGNORECASE), b, base))
                except Exception:
                    pass
        # Add generic variants
        vars.update({
            base,
            base.replace(" of ", " for "),
            base.replace(" board members", " board"),
            "powers and duties of the board",
            "authority of board members",
            "responsibilities of the board",
        })
        return [v for v in vars if v and len(v) >= 3]
    except Exception:
        return [q]

def _dedupe_results(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Deduplicate results using a hash of normalized content and source."""
    try:
        uniq = []
        seen = set()
        for r in results:
            try:
                content = (r.get('content') or "").strip()
                source = (r.get('source') or "").strip()
                key_raw = (content[:300] + "|" + source).encode('utf-8', errors='ignore')
                import hashlib as _hashlib
                h = _hashlib.md5(key_raw).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                uniq.append(r)
            except Exception:
                uniq.append(r)
        return uniq
    except Exception:
        return results

def _quick_weaviate_search(wm, collection: str, query: str, limit: int) -> List[Dict[str, str]]:
    """Robust Weaviate retrieval with fallbacks and query variations.

    Uses get_documents_for_tab (hybrid + near_text fallback). If empty, tries simple
    variations and returns normalized, deduped results.
    """
    try:
        # First try the normal path
        results = wm.get_documents_for_tab(collection_name=collection, tab_name="query_assistant", query=query, limit=limit) or []
        results = [_normalize_content_from_result(r, collection) for r in results]
        results = [r for r in results if r.get('content') and len(r.get('content').strip()) > 0]
        if results:
            return _dedupe_results(results)

        # If still empty, try variations
        out: List[Dict[str, str]] = []
        for vq in _expand_query_variations(query):
            alt = wm.get_documents_for_tab(collection_name=collection, tab_name="query_assistant", query=vq, limit=limit) or []
            if alt:
                out.extend([_normalize_content_from_result(r, collection) for r in alt])
            if len(out) >= limit:
                break
        out = [r for r in out if r.get('content') and len(r.get('content').strip()) > 0]
        return _dedupe_results(out)[:limit]
    except Exception as e:
        logger.error(f"_quick_weaviate_search failed: {e}")
        return []

def process_query(query: str, index_name: str, backend: str, top_k: int) -> Dict[str, str]:
    """Safe query processing with validation and fallbacks"""
    # Input validation
    if not query or not isinstance(query, str) or len(query.strip()) < 3:
        return {"error": "Query must be at least 3 characters"}
    
    if len(query) > 1000:
        return {"error": "Query too long (max 1000 characters)"}
    
    try:
        # Initialize results
        results = []
        
        # Main query execution
        if backend == "FAISS (Local Index)":
            try:
                results = search_vector_store(query, index_name, top_k)
                if not results:
                    return {"warning": "No results found", "suggestions": [
                        "Try different keywords",
                        "Check index status in Debug tab",
                        "Verify collection has documents"
                    ]}
            except Exception as e:
                logger.error(f"FAISS search failed: {e}", exc_info=True)
                results = _get_fallback_results(query, top_k)
                
        # Format results
        content = "\n\n".join(r.get("content", "") for r in results) if results else ""
        return {"content": content, "results": results}
        
    except Exception as e:
        logger.critical(f"Query processing failed: {e}", exc_info=True)
        return {"error": "System error - please check logs"}

def render_query_assistant(user=None, permissions=None, auth_middleware=None, available_indexes=None):
    """Main query assistant render function"""
    # Safe parameter initialization
    user = user or {}
    permissions = permissions or {}
    available_indexes = available_indexes or []
    
    # Safe auth logging
    if auth_middleware and hasattr(auth_middleware, 'log_user_action'):
        auth_middleware.log_user_action("ACCESS_QUERY_TAB")
    else:
        logger.warning("Auth middleware not available")
    
    # Handle both dict and object user formats
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        role = user.get('role', 'viewer')
        role_display = str(role).title()
    else:
        username = getattr(user, 'username', 'Unknown')
        role = getattr(getattr(user, 'role', None), 'value', 'viewer')
        role_display = str(role).title()
    
    st.header("🔍 Query Assistant")
    st.info(f"👤 Logged in as: **{username}** ({role_display})")
    
    # Default sample indexes if none are available
    sample_indexes = ["enterprise_docs", "aws_documentation", "company_policies", "technical_manuals"]
    
    # Backend selection (support Weaviate, FAISS, or Both)
    backend_actual = st.radio(
        "Search Backend:",
        ["Weaviate (Cloud Vector DB)", "FAISS (Local Index)", "Both"],
        horizontal=True,
        key="query_backend",
        help="Choose where to search: cloud Weaviate, local FAISS, or both"
    )

    # If user chose FAISS but there are no FAISS indexes, use Weaviate for this run (do not mutate widget state)
    if backend_actual == "FAISS (Local Index)":
        try:
            vdb_probe = get_vector_db_provider()
            discovered_probe = vdb_probe.get_available_indexes(force_refresh=True)
            faiss_probe = [n for n in discovered_probe if vdb_probe.find_index_path(n) and n.lower() != "faiss_index"]
            if len(faiss_probe) == 0:
                st.info("No local FAISS index found. Using Weaviate backend for this search.")
                backend_actual = "Weaviate (Cloud Vector DB)"
        except Exception:
            pass
    
    if backend_actual == "Weaviate (Cloud Vector DB)":
        # Top-of-page selector (no 'All Collections')
        selected_collection = render_collection_selector(
            key="query_collection",
            label="📚 Select Collection to Search",
            help_text="Choose a Weaviate collection containing your documents",
            include_all_option=False
        )
        # If nothing is selected, auto-select first available collection for functional UX
        if not selected_collection:
            try:
                from utils.weaviate_manager import get_weaviate_manager
                wm_tmp = get_weaviate_manager()
                colls_tmp = wm_tmp.list_collections()
                if colls_tmp:
                    selected_collection = colls_tmp[0]
            except Exception:
                pass
        
        # Final autopopulate if kb_name not set yet
        try:
            if (selected_backend == "weaviate") and (not kb_name or not str(kb_name).strip()):
                from utils.weaviate_manager import get_weaviate_manager
                _wm_auto = get_weaviate_manager()
                _cols_auto = _wm_auto.list_collections() or []
                if _cols_auto:
                    kb_name = _cols_auto[0]
            elif (selected_backend == "faiss") and (not kb_name or not str(kb_name).strip()):
                _vdb_auto = get_vector_db_provider()
                _disc_auto = _vdb_auto.get_available_indexes(force_refresh=True)
                _faiss_auto = [n for n in _disc_auto if _vdb_auto.find_index_path(n) and n.lower() != "faiss_index"]
                if _faiss_auto:
                    kb_name = _faiss_auto[0]
        except Exception:
            pass
        index_name = selected_collection or ""
        # Query vectorization options for Weaviate
        with st.expander("🧮 Vectorization (Query)", expanded=False):
            use_local_q = st.checkbox(
                "Use local query embeddings (HuggingFace)",
                value=True,
                key="use_local_q",
                help="If your collection was ingested with client-side vectors (no server vectorizer), enable this to embed the query locally and use near_vector."
            )
            default_q_model = os.getenv("WEAVIATE_QUERY_MODEL_NAME") or os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
            q_model = st.text_input(
                "Query embedding model", value=default_q_model,
                key="weaviate_query_model",
                help="SentenceTransformers model name or local path (e.g., all-MiniLM-L6-v2)"
            )
            try:
                os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = "true" if use_local_q else "false"
                os.environ["WEAVIATE_QUERY_MODEL_NAME"] = q_model
                logger.info(f"Query vectorization: client_vectors={os.environ['WEAVIATE_USE_CLIENT_VECTORS']} model={q_model}")
            except Exception as _e:
                logger.warning(f"Failed to set query vectorization env vars: {_e}")
    elif backend_actual == "Both":
        # Allow selecting both Weaviate collections and FAISS indexes
        try:
            from utils.weaviate_manager import get_weaviate_manager
            wm_tmp = get_weaviate_manager()
            weaviate_cols = wm_tmp.list_collections() or []
        except Exception:
            weaviate_cols = []

        try:
            vdb = get_vector_db_provider()
            discovered = vdb.get_available_indexes(force_refresh=True)
            faiss_options = [n for n in discovered if vdb.find_index_path(n) and n.lower() != "faiss_index"]
        except Exception:
            faiss_options = []

        st.markdown("**Select Sources**")
        st.caption("Choose one or more Weaviate collections and/or FAISS indexes to search")
        st.multiselect(
            "Weaviate collections:",
            options=weaviate_cols,
            default=st.session_state.get("qa_both_weaviate_cols", []),
            key="qa_both_weaviate_cols"
        )
        st.multiselect(
            "Local FAISS indexes:",
            options=faiss_options,
            default=st.session_state.get("qa_both_faiss_indexes", []),
            key="qa_both_faiss_indexes"
        )
        index_name = ""  # Not used in Both mode
    else:
        # FAISS index selection (fallback) - show main-section selector
        try:
            vdb = get_vector_db_provider()
            discovered = vdb.get_available_indexes(force_refresh=True)
            faiss_options = [n for n in discovered if vdb.find_index_path(n) and n.lower() != "faiss_index"]
        except Exception:
            faiss_options = []
        # Only list real discovered FAISS indexes; if none, guide the user
        if not faiss_options:
            st.warning("No local FAISS indexes found. Use the Debug tab to Quick Build from extracted_text.txt, or switch to Weaviate backend.")
            index_name = ""
        else:
            # Remember last chosen FAISS index in session state
            default_choice = st.session_state.get("qa_faiss_index", faiss_options[0])
            try:
                default_idx = faiss_options.index(default_choice)
            except ValueError:
                default_idx = 0
            sel_top = st.selectbox("📦 Select Index to Search:", faiss_options, index=default_idx, key="qa_faiss_index_top")
            st.session_state["qa_faiss_index"] = sel_top
            index_name = sel_top
    
    # Custom CSS for better result display
    st.markdown("""
    <style>
    .query-result {
        background-color: #1e2a38;
        border-left: 3px solid #4da6ff;
        padding: 15px;
        border-radius: 5px;
        color: #ffffff;
        margin-bottom: 15px;
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
    }
    .web-result {
        background-color: #1e2a38;
        border: 1px solid #4da6ff;
        padding: 12px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: #ffffff;
    }
    .web-result h4 {
        margin-top: 0;
        color: #4da6ff;
    }
    .web-result .url {
        color: #4ade80;
        font-size: 0.9em;
        margin-bottom: 8px;
    }
    .result-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #4da6ff;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Get available indexes
    if not available_indexes:
        # Add default indexes if list is empty for demo purposes
        available_indexes = sample_indexes
        # Show a notification about using demo indexes, but don't block functionality
        st.warning("⚠️ No custom indexes found. Using demo indexes for now. You can ingest your own documents from the 'Ingest Document' tab.")
    
    # Create tabs for different search modes (Quick Search first for simplicity)
    quick_tab, search_tab, report_tab, web_tab, debug_tab = st.tabs(["🔎 Quick Search", "📚 Index Search", "📤 Report", "🌐 Web Search", "🛠️ Debug"])
    
    # Quick Search: Auto-detect backend and knowledge base, provide AI answer + sources
    with quick_tab:
        st.subheader("Ask your question")
        q_query = st.text_input("Your question", placeholder="e.g. What are the board meeting requirements?", key="qa_quick_query", label_visibility="collapsed")
        q_topk = st.slider("Results", 3, 20, 5, key="qa_quick_topk")
        
        # Auto-detect best backend and knowledge base (seed from top selection first)
        selected_backend = None
        kb_options = []
        kb_name = ""
        try:
            if backend_actual == "Weaviate (Cloud Vector DB)" and index_name:
                selected_backend = "weaviate"
                kb_name = index_name
            elif backend_actual == "FAISS (Local Index)" and index_name:
                selected_backend = "faiss"
                kb_name = index_name
        except Exception:
            pass
        
        # Prefer Weaviate if available (if not already seeded)
        if not selected_backend:
            try:
                from utils.weaviate_manager import get_weaviate_manager
                wm_quick = get_weaviate_manager()
                weaviate_cols_quick = wm_quick.list_collections() or []
                if weaviate_cols_quick:
                    selected_backend = "weaviate"
                    kb_options = weaviate_cols_quick
                    kb_name = index_name or st.session_state.get("qa_quick_kb", weaviate_cols_quick[0])
            except Exception:
                pass
        
        # Fallback to FAISS if no Weaviate
        if not selected_backend:
            try:
                vdb_quick = get_vector_db_provider()
                discovered_quick = vdb_quick.get_available_indexes(force_refresh=True)
                faiss_opts_quick = [n for n in discovered_quick if vdb_quick.find_index_path(n) and n.lower() != "faiss_index"]
                if faiss_opts_quick:
                    selected_backend = "faiss"
                    kb_options = faiss_opts_quick
                    kb_name = st.session_state.get("qa_quick_kb", faiss_opts_quick[0])
            except Exception:
                pass
        
        if not selected_backend:
            st.error("No knowledge base available. Ingest documents or connect Weaviate in Settings.")
        else:
            st.caption(f"Using backend: {'Weaviate' if selected_backend=='weaviate' else 'Local FAISS'} · Knowledge base: {kb_name}")
            with st.expander("Advanced options", expanded=False):
                b_sel = st.radio("Backend", ["Weaviate", "Local FAISS"], index=0 if selected_backend=="weaviate" else 1, key="qa_quick_backend")
                if b_sel == "Weaviate":
                    try:
                        cols = wm_quick.list_collections() if 'wm_quick' in locals() else []
                    except Exception:
                        cols = []
                    kb_name = st.selectbox("Knowledge base (Weaviate collection)", options=cols or [kb_name], index=0, key="qa_quick_kb_weaviate") or kb_name
                    # Local query embeddings toggle for robust retrieval on client-vector collections
                    quick_localq = st.checkbox("Use local query embeddings (near_vector)", value=True, key="qa_quick_localq")
                    default_qm = os.getenv("WEAVIATE_QUERY_MODEL_NAME") or os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
                    quick_model = st.text_input("Query model (SentenceTransformers)", value=default_qm, key="qa_quick_model")
                    selected_backend = "weaviate"
                else:
                    try:
                        vdb_sel = get_vector_db_provider()
                        disc2 = vdb_sel.get_available_indexes(force_refresh=True)
                        faiss2 = [n for n in disc2 if vdb_sel.find_index_path(n) and n.lower() != "faiss_index"]
                    except Exception:
                        faiss2 = []
                    kb_name = st.selectbox("Knowledge base (Local index)", options=faiss2 or [kb_name], index=0, key="qa_quick_kb_faiss") or kb_name
                    selected_backend = "faiss"
                # Enterprise hybrid re-ranking toggle (applies when local data available)
                st.checkbox("Use enterprise hybrid re-ranking (local merge)", value=True, key="qa_quick_enterprise")
                st.markdown("---")
                # Toggle: Merge page-based retrieval
                st.checkbox("Merge page-based retrieval (page-aware)", value=True, key="qa_quick_page_merge")
                colc1, colc2 = st.columns([1,1])
                with colc1:
                    st.checkbox("Force refresh (ignore cache)", value=False, key="qa_quick_force")
                with colc2:
                    if st.button("Clear query cache", key="qa_quick_clear_cache"):
                        try:
                            invalidate_query_cache()
                            st.success("Cache cleared.")
                        except Exception as e:
                            st.warning(f"Could not clear cache: {e}")
            
            go_btn = st.button("Get Answer", use_container_width=True, key="qa_quick_search")
            if go_btn:
                # P0 Security: Input Validation
                valid_query, error_msg, sanitized_query = validate_search_query(q_query)
                if not valid_query:
                    st.error(f"❌ Invalid query: {error_msg}")
                    return

                # P0 Security: Rate Limiting
                user_id = username or "anonymous"
                allowed, rate_error, rate_info = check_rate_limit(user_id, tier="premium", operation="query")
                if not allowed:
                    st.error(f"⚠️ {rate_error}")
                    st.info(f"Rate limit info: {rate_info.get('minute_remaining', 0)} queries remaining this minute")
                    return

                if not kb_name or not str(kb_name).strip():
                    st.warning("Please select a knowledge base (collection/index) first")
                else:
                    # NEW: ML Intent Classification
                    try:
                        from utils.ml_models.query_intent_classifier import get_query_intent_classifier
                        classifier = get_query_intent_classifier()
                        intent_result = classifier.classify_intent(q_query)
                        
                        # Show intent to user
                        col_intent1, col_intent2 = st.columns([3, 1])
                        with col_intent1:
                            st.info(f"🎯 **Query Intent**: {intent_result['intent'].title()}")
                        with col_intent2:
                            st.metric("Confidence", f"{intent_result['confidence']:.0%}")
                        
                        # Show strategy (expandable)
                        with st.expander("📊 Retrieval Strategy", expanded=False):
                            strategy = classifier.get_retrieval_strategy(intent_result['intent'])
                            st.json(strategy)
                            st.caption(f"Using {strategy['search_type']} search with {strategy['response_style']} response style")
                        
                        # Adjust top_k based on intent
                        q_topk = strategy.get('top_k', q_topk)
                        
                    except Exception as e:
                        logger.warning(f"Intent classification unavailable: {e}")
                        # Continue with default parameters
                    
                    with st.spinner("Searching knowledge base and generating answer..."):
                        try:
                            # Check cache first for Quick Search
                            cache_key = f"{q_query}|{kb_name}|{selected_backend}|{q_topk}|{username or 'anonymous'}"
                            force_refresh = st.session_state.get("qa_quick_force", False)
                            cached_result = None if force_refresh else get_cached_result(q_query, kb_name, selected_backend, q_topk, username or "anonymous")

                            if cached_result:
                                st.info("⚡ Using cached results for faster response")
                                results_quick = cached_result.get("results", [])
                                summary_text = cached_result.get("summary", "")
                            else:
                                results_quick = []
                                if selected_backend == "weaviate":
                                    # Ensure query vectorization settings are applied if needed
                                    try:
                                        quick_localq = st.session_state.get("qa_quick_localq", True)
                                        quick_model = st.session_state.get("qa_quick_model", os.getenv("WEAVIATE_QUERY_MODEL_NAME") or os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"))
                                        os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = "true" if quick_localq else "false"
                                        os.environ["WEAVIATE_QUERY_MODEL_NAME"] = quick_model
                                    except Exception:
                                        pass
                                    wm_inst = wm_quick if 'wm_quick' in locals() else __import__('utils.weaviate_manager', fromlist=['get_weaviate_manager']).get_weaviate_manager()
                                    # Primary retrieval
                                    results_quick = wm_inst.get_documents_for_tab(
                                        collection_name=kb_name,
                                        tab_name="query_assistant",
                                        query=q_query,
                                        limit=q_topk
                                    )
                                    # Unified robust fallback: variations + normalization + dedupe
                                    if not results_quick:
                                        results_quick = _quick_weaviate_search(wm_inst, kb_name, q_query, q_topk)
                                    # Automatic near_vector toggle attempt if still empty
                                    if not results_quick:
                                        try:
                                            orig_localq_env = os.getenv("WEAVIATE_USE_CLIENT_VECTORS")
                                            # Flip local query vectorization once and retry
                                            flipped = not quick_localq
                                            os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = "true" if flipped else "false"
                                            results_quick = _quick_weaviate_search(wm_inst, kb_name, q_query, q_topk)
                                            # Restore original env setting
                                            if orig_localq_env is not None:
                                                os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = orig_localq_env
                                        except Exception:
                                            pass
                                else:
                                    # Ensure local FAISS provider is available in this scope
                                    try:
                                        vdb_inst = vdb_quick if 'vdb_quick' in locals() else get_vector_db_provider()
                                    except Exception:
                                        vdb_inst = get_vector_db_provider()
                                    results_quick = vdb_inst.search_index(query=q_query, index_name=kb_name, top_k=q_topk)

                                # Normalize and filter results prior to LLM summarization
                                try:
                                    results_quick = [_normalize_content_from_result(r, kb_name) for r in (results_quick or [])]
                                    results_quick = [r for r in results_quick if r.get('content') and len(r.get('content').strip()) > 0]
                                except Exception:
                                    pass

                                # Enterprise hybrid search re-ranking/merge (before AI Answer)
                                try:
                                    if st.session_state.get("qa_quick_enterprise", True):
                                        from utils.enterprise_hybrid_search import get_enterprise_hybrid_search
                                        eh = get_enterprise_hybrid_search()
                                        eh_res = eh.search(q_query, kb_name, max_results=q_topk) or []
                                        if eh_res:
                                            eh_norm = [_normalize_content_from_result(r, kb_name) for r in eh_res]
                                            results_quick = _dedupe_results((results_quick or []) + eh_norm)[:q_topk]
                                except Exception:
                                    pass

                                # Page-based retrieval merge (before AI Answer)
                                try:
                                    if st.session_state.get("qa_quick_page_merge", False):
                                        from utils.enhanced_page_chunking import EnhancedPageChunkingRetrieval
                                        pbr = EnhancedPageChunkingRetrieval()
                                        pbr_res = pbr.retrieve_with_page_chunks(q_query, kb_name, max_results=q_topk) or []
                                        if pbr_res:
                                            pbr_norm = [_normalize_content_from_result(r, kb_name) for r in pbr_res]
                                            results_quick = _dedupe_results((results_quick or []) + pbr_norm)[:q_topk]
                                except Exception:
                                    pass
                            
                            # NEW: ML Intent Classification - Show before AI Answer
                            try:
                                # Try TensorFlow model first, fall back to simple classifier
                                try:
                                    from utils.ml_models.query_intent_classifier import get_query_intent_classifier
                                    classifier = get_query_intent_classifier()
                                except:
                                    # Use simple rule-based classifier (no TensorFlow required)
                                    from utils.ml_models.simple_intent_classifier import get_simple_intent_classifier
                                    classifier = get_simple_intent_classifier()
                                
                                intent_result = classifier.classify_intent(q_query)
                                
                                # Show intent badge
                                col_intent1, col_intent2 = st.columns([3, 1])
                                with col_intent1:
                                    st.info(f"🎯 **Query Intent**: {intent_result['intent'].title()}")
                                with col_intent2:
                                    st.metric("Confidence", f"{intent_result['confidence']:.0%}")
                                
                                # Show strategy (expandable)
                                with st.expander("📊 Retrieval Strategy", expanded=False):
                                    strategy = classifier.get_retrieval_strategy(intent_result['intent'])
                                    st.json(strategy)
                                    st.caption(f"Using {strategy['search_type']} search with {strategy['response_style']} response style")
                                
                            except Exception as e:
                                logger.debug(f"Intent classification unavailable: {e}")
                                intent_result = {'intent': 'exploratory', 'confidence': 0.7}
                            
                            # Generate enterprise-style summary using an enhanced LLM call
                            st.markdown("## 🧠 AI Answer")
                            
                            # Debug: Check LLM availability across supported providers (BYO keys)
                            openai_key = os.getenv("OPENAI_API_KEY")
                            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
                            mistral_key = os.getenv("MISTRAL_API_KEY")
                            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
                            groq_key = os.getenv("GROQ_API_KEY")
                            ollama_url = os.getenv("OLLAMA_BASE_URL")
                            if not any([openai_key, anthropic_key, mistral_key, deepseek_key, groq_key, ollama_url]):
                                st.error("⚠️ **LLM API Key Not Configured!**")
                                st.warning("Provide at least one provider key (OpenAI, Anthropic, Mistral, DeepSeek, Groq) or set Ollama base URL in the sidebar.")
                                st.info("Currently showing raw retrieval results as fallback.")
                            
                            try:
                                # Use EnhancedLLMProcessor for proper LLM integration
                                from utils.enhanced_llm_integration import EnhancedLLMProcessor
                                llm_processor = EnhancedLLMProcessor()
                                
                                # Check if LLM is available
                                if not llm_processor.available:
                                    st.warning("⚠️ LLM not available - check API keys in .env file")
                                    raise ValueError("LLM not available")
                                
                                # Determine effective model (must be configured)
                                selected_model_name = st.session_state.get("global_model")
                                effective_model = selected_model_name
                                try:
                                    from utils.llm_config import validate_llm_setup as _v, get_default_llm_model as _gdef, get_available_llm_models as _gavail
                                    ok, _msg = _v(selected_model_name) if selected_model_name else (False, "")
                                    if not ok:
                                        avail_names = _gavail() or []
                                        # Filter out sentinel messages
                                        avail_names = [n for n in avail_names if n and not n.lower().startswith("no llm models available")]
                                        effective_model = _gdef() if avail_names else None
                                except Exception:
                                    pass

                                # Show processing indicator
                                with st.spinner("🤖 Generating AI answer with LLM..."):
                                    # Process with LLM, pass effective model when available
                                    summary = llm_processor.process_retrieval_results(
                                        query=q_query,
                                        retrieval_results=results_quick,
                                        index_name=kb_name,
                                        model_name=effective_model
                                    )
                                
                                summary_text = summary.get("result", "")
                                processing_method = summary.get("processing_method", "unknown")
                                
                                # Show LLM model info (prefer effective model; note if selection was adjusted)
                                try:
                                    session_model = st.session_state.get("global_model")
                                    display_model = effective_model or session_model
                                    if not display_model:
                                        from utils.llm_config import get_default_llm_model
                                        display_model = get_default_llm_model()
                                    # If selection was adjusted, inform user non-intrusively
                                    if session_model and effective_model and session_model != effective_model:
                                        st.caption(f"🤖 **Model**: {display_model} (auto-selected) | **Method**: {processing_method}")
                                    else:
                                        st.caption(f"🤖 **Model**: {display_model} | **Method**: {processing_method}")
                                except Exception:
                                    st.caption(f"**Processing Method**: {processing_method}")
                                
                                # Debug info
                                if processing_method == "fallback_enhanced":
                                    st.warning("⚠️ Using fallback mode - LLM call failed")
                                
                                # Sanitize AI markdown to remove TOC/heading-only noise
                                summary_text = _sanitize_ai_markdown(summary_text)
                                
                                # Check if we got a valid response
                                if summary_text and len(summary_text.strip()) > 100:
                                    st.markdown(summary_text)
                                    
                                    # Display sources from the summary if available
                                    if summary.get("sources"):
                                        with st.expander("📚 Sources Used by AI"):
                                            for source in summary.get("sources", []):
                                                src = source.get('source', 'Unknown')
                                                page = source.get('page')
                                                page_seg = f", Page: {page}" if (isinstance(page, int) or (isinstance(page, str) and page.isdigit())) else ""
                                                st.info(f"{src}{page_seg}")
                                else:
                                    # Response was empty or too short - use enhanced fallback
                                    logger.warning(f"LLM response too short ({len(summary_text)} chars), using fallback")
                                    st.warning(f"⚠️ LLM response too short ({len(summary_text)} chars)")
                                    raise ValueError("LLM response was empty or insufficient")

                            except Exception as e:
                                logger.error(f"Enhanced LLM integration failed: {e}. Using enterprise fallback formatting.")
                                # Enhanced fallback with proper enterprise structure
                                fallback_parts = []
                                # Verb regex for sentence validity
                                verb_re = re.compile(r"\b(is|are|shall|must|may|will|has|have|does|do|provide|provides|include|includes|appoint|appoints|elect|elects|vote|votes|conduct|conducts|comply|complies|adopt|adopts|keep|keeps|record|records|preside|presides|delegate|delegates|authorize|authorizes|determine|determines|manage|manages)\b", re.IGNORECASE)
                                
                                # Executive Summary
                                fallback_parts.append("### Executive Summary")
                                if results_quick:
                                    top_content = clean_document_text(results_quick[0].get('content', '') or '')
                                    # Robust sentence splitting and filtering to avoid truncated fragments
                                    candidates = [s.strip() for s in re.split(r'(?<=[.!?])\s+', top_content) if s.strip()]
                                    sentences = []
                                    for s in candidates:
                                        sl = s.lower()
                                        if len(s) < 25:
                                            continue
                                        if re.match(r'^(must|shall|should|may|will|has|have|does|do|is|are|and|or)\b', sl):
                                            continue
                                        if s.endswith(':'):
                                            continue
                                        if is_noise_text(s):
                                            continue
                                        if not s[:1].isupper():
                                            continue
                                        if not verb_re.search(s):
                                            continue
                                        sentences.append(s)
                                    summary_text = '. '.join(sentences[:2]) + ('.' if sentences[:2] else '')
                                    if not summary_text:
                                        summary_text = "Information found in documents."
                                    fallback_parts.append(summary_text)
                                else:
                                    fallback_parts.append("No relevant information found.")
                                fallback_parts.append("")
                                
                                # Detailed Answer
                                fallback_parts.append("### Detailed Answer")
                                for i, result in enumerate(results_quick[:3], 1):
                                    content = clean_document_text(result.get('content', '') or '')
                                    if not content or is_noise_text(content):
                                        continue
                                    source = result.get('source', 'Unknown')
                                    page = result.get('page')
                                    page_seg = f" (Page {page})" if (isinstance(page, int) or (isinstance(page, str) and page.isdigit())) else ""
                                    
                                    # Robust sentence splitting and filtering
                                    cand = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if s.strip()]
                                    sentences = []
                                    for s in cand:
                                        sl = s.lower()
                                        if len(s) < 25:
                                            continue
                                        if re.match(r'^(must|shall|should|may|will|has|have|does|do|is|are|and|or)\b', sl):
                                            continue
                                        if s.endswith(':'):
                                            continue
                                        if is_noise_text(s):
                                            continue
                                        if not s[:1].isupper():
                                            continue
                                        if not verb_re.search(s):
                                            continue
                                        sentences.append(s)
                                    if sentences:
                                        excerpt = ' '.join(sentences[:3])
                                        if sentences[:3] and not sentences[:3][-1].endswith(('.', '!', '?')):
                                            excerpt += '.'
                                        fallback_parts.append(f"**From {source}{page_seg}:** {excerpt}")
                                        fallback_parts.append("")
                                
                                # Key Points - Using QueryResultFormatter for complete sentences
                                fallback_parts.append("### Key Points")
                                for i, result in enumerate(results_quick[:5], 1):
                                    content = result.get('content', '')
                                    source = result.get('source', 'Unknown')
                                    page = result.get('page')
                                    section = result.get('section')
                                    
                                    # Use QueryResultFormatter to get complete sentences with proper formatting
                                    formatted_point = QueryResultFormatter.format_key_point(
                                        content=content,
                                        source=source,
                                        page=page,
                                        section=section,
                                        index=i
                                    )
                                    # Drop if the formatter returned a fragment (starts with modal/aux or ends with ':')
                                    if formatted_point:
                                        fp = formatted_point.strip()
                                        if re.match(r'^\-\s*(must|shall|should|may|will|has|have|does|do|is|are)\b', fp, flags=re.IGNORECASE):
                                            formatted_point = ''
                                        if fp.endswith(':'):
                                            formatted_point = ''
                                    if formatted_point:
                                        fallback_parts.append(formatted_point)
                                
                                summary_text = "\n".join(fallback_parts)
                                # Final sanitization pass
                                summary_text = _sanitize_ai_markdown(summary_text)
                                st.markdown(summary_text)
                            
                            # Sources - Clean and professional display
                            if results_quick:
                                st.markdown("### 📚 Sources")
                                for idx, r in enumerate(results_quick, 1):
                                    if isinstance(r, dict):
                                        src = r.get('source') or r.get('file_path') or kb_name
                                        page = r.get('page')
                                        raw_content = r.get('content') or ""
                                        
                                        # Clean and extract meaningful snippet
                                        cleaned_content = clean_document_text(raw_content)
                                        if not cleaned_content or is_noise_text(cleaned_content):
                                            continue
                                        # Robust sentence splitting and filtering
                                        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_content) if s.strip()]
                                        sentences = [s for s in sentences if not s.endswith(':')]
                                        sentences = [s for s in sentences if len(s) > 20 and not is_noise_text(s)]
                                        # Additional validity: start with uppercase and has a verb
                                        v_re = re.compile(r"\b(is|are|shall|must|may|will|has|have|does|do|provide|provides|include|includes|appoint|appoints|elect|elects|vote|votes|conduct|conducts|comply|complies|adopt|adopts|keep|keeps|record|records|preside|presides|delegate|delegates|authorize|authorizes|determine|determines|manage|manages)\b", re.IGNORECASE)
                                        sentences = [s for s in sentences if (s[:1].isupper() and v_re.search(s))]
                                        sentences = [s for s in sentences if not is_noise_text(s)]
                                        
                                        if not sentences:
                                            # Skip entries without any valid sentences (likely headings/TOC)
                                            continue
                                        # Take first 2 sentences for snippet with proper punctuation
                                        snippet = ' '.join(sentences[:2])
                                        if sentences[:2]:
                                            last = sentences[:2][-1]
                                            if not last.endswith(('.', '!', '?')):
                                                snippet += '.'
                                        if len(snippet) > 250:
                                            snippet = snippet[:247] + "..."
                                        
                                        # Avoid duplicate page label if already in source string
                                        meta = ""
                                        if (isinstance(page, int) or (isinstance(page, str) and str(page).isdigit())):
                                            if not re.search(rf"\bpage\s*[:#]?\s*{str(page)}\b", str(src), flags=re.IGNORECASE):
                                                meta = f" (Page {page})"
                                        # Normalize score for percent display
                                        raw_score = r.get('score') if r.get('score') is not None else r.get('relevance_score', 0.0)
                                        try:
                                            s = float(raw_score)
                                            if s > 1.0:
                                                s = s / 100.0 if s <= 100.0 else min(1.0, s / 100.0)
                                            if s < 0.0:
                                                s = 0.0
                                        except Exception:
                                            s = 0.0
                                        score_display = f" • Relevance: {s:.2%}" if s > 0 else ""
                                        
                                        st.markdown(f"**{idx}. {src}**{meta}{score_display}")
                                        st.markdown(f"> {snippet}")
                                        st.markdown("")  # Add spacing
                                    else:
                                        st.markdown(f"- {str(r)[:200]}")
                            else:
                                st.info("No sources returned for this query.")

                            # Feedback buttons for Quick Search
                            try:
                                if summary_text and results_quick:
                                    source_docs = []
                                    for r in results_quick:
                                        if isinstance(r, dict):
                                            content_val = r.get('content', str(r))
                                            src_val = r.get('source', kb_name)
                                            source_docs.append({'content': content_val, 'source': src_val})
                                    
                                    render_feedback_buttons(
                                        query=q_query,
                                        response=summary_text[:800],
                                        source_docs=source_docs,
                                        confidence_score=sum(r.get('relevance_score', 0.5) if isinstance(r, dict) else 0.5 for r in results_quick) / len(results_quick) if results_quick else 0.0,
                                        retrieval_method="quick_search_hybrid",
                                        session_key=f"quick_search_{kb_name}"
                                    )
                                    
                                    render_query_insights(q_query)
                            except Exception as feedback_error:
                                logger.warning(f"Failed to render feedback buttons: {feedback_error}")

                            # Full Answer - Always Visible, Collapsible
                            if summary_text and results_quick:
                                st.markdown("---")
                                
                                # Create clean, well-structured report
                                full_report_lines = []
                                full_report_lines.append("# QUERY RESPONSE REPORT")
                                full_report_lines.append("")
                                full_report_lines.append(f"**Query:** {q_query}")
                                full_report_lines.append(f"**Knowledge Base:** {kb_name}")
                                full_report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                full_report_lines.append("")
                                full_report_lines.append("---")
                                full_report_lines.append("")
                                
                                # Add sanitized AI answer
                                full_report_lines.append(summary_text)
                                full_report_lines.append("")
                                full_report_lines.append("---")
                                full_report_lines.append("")
                                
                                # Add detailed sources with complete content
                                full_report_lines.append("## 📚 DETAILED SOURCES")
                                full_report_lines.append("")
                                
                                for idx, r in enumerate(results_quick[:5], 1):
                                    if isinstance(r, dict):
                                        src = r.get('source') or r.get('file_path') or kb_name
                                        page = r.get('page')
                                        section = r.get('section')
                                        raw_content = r.get('content') or ""
                                        
                                        # Clean content
                                        content_clean = clean_document_text(raw_content)
                                        if not content_clean or is_noise_text(content_clean):
                                            continue
                                        
                                        # Extract complete sentences (no truncation)
                                        complete_text = QueryResultFormatter.extract_complete_sentences(content_clean, max_length=800)
                                        if not complete_text:
                                            complete_text = content_clean[:800]
                                        
                                        # Build citation
                                        citation = f"**Source {idx}: {src}**"
                                        if isinstance(page, int) or (isinstance(page, str) and page.isdigit()):
                                            citation += f" (Page {page})"
                                        if section:
                                            citation += f" - {section}"
                                        
                                        full_report_lines.append(citation)
                                        full_report_lines.append("")
                                        full_report_lines.append(complete_text)
                                        full_report_lines.append("")
                                        full_report_lines.append("---")
                                        full_report_lines.append("")
                                
                                # Add confidence score
                                avg_conf = sum(r.get('relevance_score', 0.5) if isinstance(r, dict) else 0.5 for r in results_quick) / len(results_quick) if results_quick else 0.0
                                full_report_lines.append(f"**Average Confidence Score:** {avg_conf:.2%}")
                                full_report_lines.append("")
                                
                                full_report = "\n".join(full_report_lines)
                                
                                # Display in collapsible expander (always visible, can expand/collapse)
                                with st.expander("📄 FULL ANSWER - CLEAN FORMAT (Click to Expand)", expanded=False):
                                    st.markdown(full_report)
                                    
                                    # Download button
                                    st.download_button(
                                        label="💾 Download Full Answer (Markdown)",
                                        data=full_report,
                                        file_name=f"full_answer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                        mime="text/markdown",
                                        key="qa_quick_download_full"
                                    )

                            # Enterprise combined markdown block (copy + download)
                            try:
                                lines = []
                                lines.append(f"Backend: {'Weaviate' if selected_backend=='weaviate' else 'Local FAISS'} | Knowledge Base: {kb_name}")
                                lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                if q_query:
                                    lines.append("")
                                    lines.append(f"Query: {q_query}")
                                if summary_text:
                                    lines.append("")
                                    lines.append("## Summary")
                                    lines.append(summary_text.strip())
                                if results_quick:
                                    lines.append("")
                                    lines.append("## Sources")
                                    for rr in results_quick:
                                        if isinstance(rr, dict):
                                            ssrc = rr.get('source') or rr.get('file_path') or kb_name
                                            ppg = rr.get('page')
                                            raw_s = (rr.get('content') or '').replace('\n',' ').strip()
                                            raw_s = clean_document_text(raw_s)
                                            if not raw_s or is_noise_text(raw_s):
                                                continue
                                            # Try to cut on sentence boundary
                                            ssnip = QueryResultFormatter.extract_complete_sentences(raw_s, 300)
                                            if not ssnip:
                                                ssnip = (raw_s[:300] + '...') if len(raw_s) > 300 else raw_s
                                            mmeta = f" (page {ppg})" if (isinstance(ppg, int) or (isinstance(ppg, str) and ppg.isdigit())) else ""
                                            lines.append(f"- {ssrc}{mmeta}: {ssnip}")
                                        else:
                                            ttxt = str(rr).replace('\n',' ').strip()
                                            lines.append(f"- {ttxt[:200]}")
                                quick_combined_md = "\n".join(lines)
                                st.markdown("### Combined Markdown")
                                escaped_q = quick_combined_md.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                                st.markdown(f"""
<textarea id=\"qa_quick_report_text\" style=\"width:100%; height:220px;\">{escaped_q}</textarea>
<button id=\"qa_quick_copy_btn\">Copy to Clipboard</button>
<script>
const btn2=document.getElementById('qa_quick_copy_btn');
const ta2=document.getElementById('qa_quick_report_text');
if (btn2 && ta2) {{
  btn2.addEventListener('click', async ()=>{{
    try {{ await navigator.clipboard.writeText(ta2.value); btn2.innerText='Copied!'; setTimeout(()=>btn2.innerText='Copy to Clipboard',1500); }}
    catch(e) {{ btn2.innerText='Copy failed'; }}
  }});
}}
</script>
                                """, unsafe_allow_html=True)
                                st.download_button(
                                    label="📥 Download .md",
                                    data=quick_combined_md,
                                    file_name=f"quick_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                    mime="text/markdown",
                                    key="qa_quick_download_md"
                                )
                            except Exception:
                                pass

                            # Cache successful results for future queries
                            try:
                                if results_quick and summary_text and not st.session_state.get("qa_quick_force", False):
                                    cache_query_result(
                                        query=q_query,
                                        index_name=kb_name,
                                        backend=selected_backend,
                                        top_k=q_topk,
                                        user_id=username or "anonymous",
                                        results=results_quick,
                                        summary=summary_text
                                    )
                            except Exception as cache_error:
                                logger.warning(f"Failed to cache query results: {cache_error}")
                            # Store report data in session for the Report tab
                            try:
                                st.session_state['qa_report_query'] = q_query
                                st.session_state['qa_report_index'] = kb_name
                                st.session_state['qa_report_backend'] = 'Weaviate' if selected_backend == 'weaviate' else 'Local FAISS'
                                st.session_state['qa_report_ai_answer'] = summary_text
                                st.session_state['qa_report_sources'] = results_quick
                                conf = (sum(r.get('relevance_score', 0.5) if isinstance(r, dict) else 0.5 for r in (results_quick or [])) / len(results_quick)) if results_quick else 0.0
                                st.session_state['qa_report_confidence'] = round(conf, 3)
                            except Exception:
                                pass
                        except Exception as e:
                            st.error(f"Error generating answer: {str(e)[:200]}")
    
    # Debug tab for troubleshooting
    with debug_tab:
        st.subheader("Troubleshooting Information")
        st.write("Use this tab to diagnose issues with the Query Assistant.")
        
        # Directory information
        st.subheader("Directory Status")
        # Use module-level imports to avoid shadowing names (UnboundLocalError)
        
        # Check important directories
        data_dir = Path("data")
        faiss_dir = data_dir / "faiss_index"
        aws_dir = faiss_dir / "AWS_index"
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("data/ directory exists", "Yes" if data_dir.exists() else "No")
            st.metric("faiss_index/ directory exists", "Yes" if faiss_dir.exists() else "No")
            st.metric("AWS_index/ directory exists", "Yes" if aws_dir.exists() else "No")
            
        with col2:
            if aws_dir.exists():
                files = list(aws_dir.glob("*.*"))
                st.metric("Files in AWS_index/", str(len(files)))
                st.write("Files:")
                for file in files:
                    st.code(f"{file.name} - {file.stat().st_size} bytes")
            else:
                st.warning("AWS_index directory not found")
        
        # Vector DB status and index debugging
        vdb = get_vector_db_provider()
        status, message = vdb.get_vector_db_status()
        st.subheader("Vector DB Status")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric("Status", status)
        with col_s2:
            st.caption(message)

        # Weaviate Diagnostics
        st.subheader("Weaviate Diagnostics")
        weav_url = os.getenv("WEAVIATE_URL", "")
        weav_key_present = bool(os.getenv("WEAVIATE_API_KEY"))
        colw1, colw2 = st.columns(2)
        with colw1:
            st.code(f"URL: {weav_url or '(not set)'}")
        with colw2:
            st.code(f"API key present: {'Yes' if weav_key_present else 'No'}")
        # Cluster compatibility note and v2-skip toggle
        try:
            env_skip_v2 = str(os.getenv("WEAVIATE_SKIP_V2", "false")).lower() == "true"
        except Exception:
            env_skip_v2 = False
        if env_skip_v2:
            st.success("Compatibility: v2 listing attempts are skipped (WEAVIATE_SKIP_V2=true). This suits clusters that only expose v1 endpoints.")
        else:
            st.info("Compatibility: If your logs show 404s at /v2/collections paths, enable WEAVIATE_SKIP_V2 to reduce noise and prefer v1 schema.")
        try:
            toggle = st.checkbox("Skip v2 collections listing attempts (set WEAVIATE_SKIP_V2=true for this session)", value=env_skip_v2, key="qa_weav_skip_v2")
            if toggle != env_skip_v2:
                os.environ["WEAVIATE_SKIP_V2"] = "true" if toggle else "false"
                st.success(f"WEAVIATE_SKIP_V2 set to {'true' if toggle else 'false'} for this session")
        except Exception:
            pass
        if st.button("🔎 Ping Weaviate readiness", key="qa_weaviate_ping"):
            try:
                from utils.weaviate_manager import get_weaviate_manager
                wm_dbg = get_weaviate_manager()
                base = str(getattr(wm_dbg, 'url', '')).rstrip('/')
                if not base:
                    st.warning("Weaviate URL not configured. Set WEAVIATE_URL in config/storage.env")
                else:
                    st.info(f"Pinging Weaviate at base URL: {base}")
                    st.info(f"Using PATH_PREFIX from env: {os.getenv('WEAVIATE_PATH_PREFIX')}")
                    # Discover prefix and probe readiness + schema
                    try:
                        prefix = wm_dbg._discover_rest_prefix(force=True) or ''
                        st.info(f"Discovered prefix: '{prefix}'")
                    except Exception as e:
                        prefix = ''
                        st.warning(f"Prefix discovery failed: {e}")

                    probes = []
                    tried = set()
                    def add_probe(url):
                        if url not in tried:
                            probes.append(url)
                            tried.add(url)

                    # Add probes based on discovered prefix and fallbacks
                    if prefix:
                        add_probe(f"{base}{prefix}/v1/.well-known/ready")
                        add_probe(f"{base}{prefix}/v1/schema")
                        add_probe(f"{base}{prefix}/v2/collections")
                    
                    for p in ['', '/api', '/weaviate', '/rest']:
                        add_probe(f"{base}{p}/v1/.well-known/ready")
                        add_probe(f"{base}{p}/v1/schema")
                        add_probe(f"{base}{p}/v2/collections")

                    results = []
                    any_ok = False
                    with st.spinner("Probing endpoints..."):
                        for u in probes:
                            try:
                                r = wm_dbg._http_request("GET", u, timeout=8)
                                result = {"url": u, "status": r.status_code}
                                results.append(result)
                                if r.status_code in (200, 201, 204, 401, 403, 405):
                                    any_ok = True
                            except Exception as e:
                                results.append({"url": u, "error": str(e)[:120]})
                    
                    st.write(results)

                    if any_ok:
                        st.success("Weaviate responded on at least one readiness/schema endpoint. The connection is likely OK. Please refresh the page and try your query again.")
                    else:
                        st.error("All readiness/schema probes failed. This tab cannot connect to Weaviate. Please ensure the settings in Storage Settings are correct and have been applied.")
            except Exception as e:
                st.error(f"Weaviate diagnostics error: {e}")

        # Allow manual refresh of index discovery
        colrf1, colrf2 = st.columns([3,1])
        with colrf1:
            st.subheader("Available Indexes")
        with colrf2:
            if st.button("🔄 Refresh", key="refresh_indexes"):
                try:
                    vdb.clear_cache()
                    st.success("Index list refreshed")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to refresh: {e}")
        if available_indexes:
            st.write(f"Found {len(available_indexes)} indexes:")
            st.json(available_indexes)
        else:
            st.warning("No indexes found")

        # Local Index Maintenance: Delete FAISS indexes and folders
        st.markdown("---")
        st.subheader("Local Index Maintenance")
        st.caption("Delete local FAISS index folders to clear stale caches or broken indexes. This action cannot be undone.")

        # Delete by logical index name (uses IndexManager to find all paths)
        try:
            from utils.index_manager import IndexManager
            faiss_names = IndexManager.list_available_indexes(force_refresh=True)
        except Exception as e:
            faiss_names = []
            st.warning(f"IndexManager unavailable: {e}")

        if faiss_names:
            del_col1, del_col2 = st.columns([3, 2])
            with del_col1:
                idx_to_delete = st.selectbox("Select FAISS index to delete:", faiss_names, key="qa_del_faiss_name")
            with del_col2:
                confirm_phrase = st.text_input("Type the index name to confirm:", key="qa_del_faiss_confirm", placeholder=idx_to_delete)
            if st.button("🗑️ Delete selected FAISS index", key="qa_del_faiss_btn"):
                if confirm_phrase.strip() != idx_to_delete:
                    st.error("Confirmation text does not match the index name.")
                else:
                    try:
                        result = IndexManager.delete_index(idx_to_delete)
                        if result.get("success"):
                            st.success(result.get("message", "Deleted"))
                            st.json({"deleted_paths": result.get("deleted_paths", [])})
                            st.rerun()
                        else:
                            st.error(result.get("message", "Delete failed"))
                            errs = result.get("errors")
                            if errs:
                                st.json(errs)
                    except Exception as e:
                        st.error(f"Error deleting index: {e}")
        else:
            st.info("No FAISS indexes discovered under data/faiss_index or legacy locations.")

        # Delete an arbitrary folder under allowed bases (safeguarded)
        st.markdown("#### Danger Zone: Delete Folder in data/faiss_index or data/indexes")
        base_dirs = [Path("data") / "faiss_index", Path("data") / "indexes"]
        folder_options = []
        for b in base_dirs:
            try:
                if b.exists():
                    for p in b.glob("**/*"):
                        if p.is_dir():
                            # Show relative path from base 'data'
                            try:
                                rel = p.relative_to(Path("data"))
                                folder_options.append(str(Path("data") / rel))
                            except Exception:
                                folder_options.append(str(p))
            except Exception:
                pass

        folder_to_delete = st.selectbox(
            "Select a folder to delete:", folder_options or ["(no folders found)"] , key="qa_del_folder_select"
        )
        confirm_folder = st.text_input(
            "Type DELETE to confirm folder removal:", key="qa_del_folder_confirm", placeholder="DELETE"
        )
        if st.button("🗑️ Delete selected folder", key="qa_del_folder_btn"):
            try:
                if not folder_options or folder_to_delete not in folder_options:
                    st.error("Please select a valid folder.")
                elif confirm_folder.strip().upper() != "DELETE":
                    st.error("Type DELETE to confirm this destructive action.")
                else:
                    # Safety: ensure target is under allowed bases
                    target = Path(folder_to_delete).resolve()
                    allowed = any(str(target).startswith(str(b.resolve())) for b in base_dirs if b.exists())
                    if not allowed:
                        st.error("Refusing to delete outside allowed directories.")
                    elif not target.exists() or not target.is_dir():
                        st.error("Target folder does not exist or is not a directory.")
                    else:
                        shutil.rmtree(str(target))
                        st.success(f"Deleted folder: {target}")
                        st.rerun()
            except Exception as e:
                st.error(f"Failed to delete folder: {e}")

        # Selected index diagnostics (only for FAISS/local backend)
        if backend_actual == "FAISS (Local Index)":
            st.subheader("Selected Index Diagnostics")
            st.write(f"Selected index: `{index_name}`")
            idx_path = vdb.find_index_path(index_name)
            if idx_path:
                st.write(f"Resolved path: `{idx_path}`")
                faiss_file = idx_path / "index.faiss"
                meta_files = [p for p in [idx_path/"index.pkl", idx_path/"documents.pkl", idx_path/"metadata.pkl"] if p.exists()]
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.metric("index.faiss present", "Yes" if faiss_file.exists() else "No")
                with col_d2:
                    st.metric("metadata present", "Yes" if len(meta_files) > 0 else "No")
                try:
                    if faiss_file.exists():
                        fi = faiss.read_index(str(faiss_file))
                        st.info(f"Index vectors: {getattr(fi, 'ntotal', 0)} | Dim: {getattr(fi, 'd', 'unknown')}")
                except Exception as e:
                    st.warning(f"Failed to read FAISS index: {e}")
            else:
                st.warning("Could not resolve a valid path for the selected index. Ensure it contains index.faiss and a metadata .pkl file.")

            st.markdown("---")
            st.subheader("Quick Build: Create FAISS Index from extracted_text.txt")
            st.caption("Use this if your folder (e.g., data/indexes/Bylaws_index/) has text but no FAISS index yet.")
            col_b1, col_b2 = st.columns([3, 1])
            with col_b1:
                default_text_path = os.path.join("data", "indexes", index_name, "extracted_text.txt")
                text_path = st.text_input("Path to extracted_text.txt:", value=default_text_path)
            with col_b2:
                default_target = os.path.join("data", "faiss_index", index_name)
                target_dir = st.text_input("Target FAISS folder:", value=default_target)

            build_cols = st.columns(3)
            with build_cols[0]:
                chunk_size = st.number_input("Chunk size (chars)", min_value=256, max_value=2000, value=600, step=44)
            with build_cols[1]:
                overlap = st.number_input("Overlap", min_value=0, max_value=300, value=80, step=10)
            with build_cols[2]:
                model_name = st.text_input("Embedding model", value="all-MiniLM-L6-v2")
            use_page_chunking = st.checkbox("Use page-based chunking (detect '--- Page X ---' markers)", value=True, key="qa_use_page_chunking")

            if st.button("Build FAISS Index", key="build_faiss_index"):
                try:
                    if not os.path.exists(text_path):
                        st.error(f"Text file not found: {text_path}")
                    else:
                        # Read text and chunk
                        with open(text_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        if not content.strip():
                            st.error("The text file is empty.")
                        else:
                            chunks = []
                            if use_page_chunking and re.search(r"---\s*Page\s+\d+\s*---", content):
                                parts = re.split(r"---\s*Page\s+(\d+)\s*---", content)
                                # parts format: [pre, pageNum1, pageText1, pageNum2, pageText2, ...]
                                for i in range(1, len(parts), 2):
                                    if i + 1 >= len(parts):
                                        break
                                    try:
                                        page_num = int(parts[i])
                                    except Exception:
                                        page_num = None
                                    page_text = (parts[i+1] or "").strip()
                                    if not page_text:
                                        continue
                                    # Optional header: first non-empty line
                                    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
                                    header = lines[0] if lines else None
                                    # Use whole page or paragraph splits if very long
                                    if len(page_text) <= max(600, chunk_size):
                                        chunk_txt = (f"[Page {page_num}] " if page_num else "") + (f"{header}\n" if header else "") + page_text
                                        chunks.append(chunk_txt)
                                    else:
                                        paras = [p.strip() for p in page_text.split("\n\n") if p.strip()]
                                        for para in paras:
                                            if len(para) < 80:
                                                continue
                                            chunk_txt = (f"[Page {page_num}] " if page_num else "") + para
                                            chunks.append(chunk_txt)
                            else:
                                # Simple character-based chunking with overlap
                                start = 0
                                L = len(content)
                                while start < L:
                                    end = min(L, start + chunk_size)
                                    chunks.append(content[start:end])
                                    start = end - overlap if overlap > 0 else end
                                    if start < 0 or start >= L:
                                        break
                            # Encode
                            model = SentenceTransformer(model_name)
                            embeddings = model.encode(chunks, show_progress_bar=True)
                            embeddings = np.asarray(embeddings, dtype=np.float32)
                            # Build FAISS index
                            dim = embeddings.shape[1]
                            index = faiss.IndexFlatL2(dim)
                            index.add(embeddings)
                            # Save
                            os.makedirs(target_dir, exist_ok=True)
                            faiss.write_index(index, os.path.join(target_dir, "index.faiss"))
                            # Documents metadata
                            import pickle
                            docs = []
                            for c in chunks:
                                # Extract page number tag if present
                                m = re.match(r"\[Page\s+(\d+)\]\s+(.*)", c, re.IGNORECASE)
                                if m:
                                    pg = m.group(1)
                                    body = m.group(2)
                                    docs.append({
                                        "content": body,
                                        "source": os.path.basename(text_path),
                                        "page": int(pg)
                                    })
                                else:
                                    docs.append({"content": c, "source": os.path.basename(text_path)})
                            with open(os.path.join(target_dir, "documents.pkl"), "wb") as pf:
                                pickle.dump({
                                    "documents": docs,
                                    "texts": [c for c in chunks],
                                    "metadatas": [
                                        ({"source": os.path.basename(text_path), "page": d.get("page")} if isinstance(d, dict) else {"source": os.path.basename(text_path)})
                                        for d in docs
                                    ]
                                }, pf)
                            # Refresh provider cache and session state options
                            try:
                                vdb.clear_cache()
                            except Exception:
                                pass
                            st.success(f"FAISS index built with {len(chunks)} chunks at {target_dir}")
                            st.session_state["qa_faiss_index"] = os.path.basename(target_dir)
                            st.rerun()
                except Exception as e:
                    st.error(f"Failed to build FAISS index: {e}")
            
        # Removed obsolete AWS_index debug button to avoid confusion

        st.markdown("---")
        st.subheader("Weaviate Diagnostics")
        try:
            from utils.weaviate_manager import get_weaviate_manager
            wm_dbg = get_weaviate_manager()
            base_url = getattr(wm_dbg, 'url', os.getenv('WEAVIATE_URL', '(unknown)'))
            st.write(f"Base URL: `{base_url}`")
            cols_dbg = wm_dbg.list_collections() or []
            st.write(f"Collections ({len(cols_dbg)}):")
            st.write(", ".join(cols_dbg) if cols_dbg else "(none)")

            # Pick a collection to inspect
            target_coll = st.selectbox("Select Weaviate collection for diagnostics:", options=cols_dbg or [""], index=0 if cols_dbg else 0, key="qa_dbg_wv_coll")
            if target_coll:
                try:
                    count_val = wm_dbg.get_collection_count(target_coll)
                    st.metric(f"Objects in {target_coll}", count_val)
                except Exception as e:
                    st.warning(f"Count failed: {e}")

                st.caption("Run a quick search test against this collection.")
                qcol1, qcol2 = st.columns([3,2])
                with qcol1:
                    qtext = st.text_input("Test query text", value="Summarize this document", key="qa_dbg_wv_query")
                with qcol2:
                    topk_dbg = st.number_input("Top K", min_value=1, max_value=20, value=3, step=1, key="qa_dbg_wv_topk")

                # Toggle client-side query vectors and model
                use_local_q_dbg = st.checkbox("Use local query embeddings (near_vector)", value=True, key="qa_dbg_wv_localq")
                default_qm = os.getenv("WEAVIATE_QUERY_MODEL_NAME") or os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
                q_model_dbg = st.text_input("Query model (SentenceTransformers)", value=default_qm, key="qa_dbg_wv_model")

                dbga, dbgb, dbgc = st.columns(3)
                with dbga:
                    if st.button("Test search", key="qa_dbg_wv_search"):
                        try:
                            os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = "true" if use_local_q_dbg else "false"
                            os.environ["WEAVIATE_QUERY_MODEL_NAME"] = q_model_dbg
                            res = wm_dbg.search(collection_name=target_coll, query=qtext, limit=int(topk_dbg))
                            st.write("Search results:")
                            st.json(res or [])
                        except Exception as e:
                            st.error(f"Search error: {e}")
                with dbgb:
                    if st.button("Test hybrid", key="qa_dbg_wv_hybrid"):
                        try:
                            os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = "true" if use_local_q_dbg else "false"
                            os.environ["WEAVIATE_QUERY_MODEL_NAME"] = q_model_dbg
                            res2 = wm_dbg.hybrid_search(collection_name=target_coll, query=qtext, limit=int(topk_dbg))
                            st.write("Hybrid results:")
                            st.json(res2 or [])
                        except Exception as e:
                            st.error(f"Hybrid error: {e}")
                with dbgc:
                    if st.button("near_text (server-side)", key="qa_dbg_wv_neartext"):
                        try:
                            os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = "false"
                            res3 = wm_dbg.search(collection_name=target_coll, query=qtext, limit=int(topk_dbg))
                            st.write("near_text results:")
                            st.json(res3 or [])
                        except Exception as e:
                            st.error(f"near_text error: {e}")
        except Exception as e:
            st.warning(f"Weaviate diagnostics unavailable: {e}")
    
    with search_tab:
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Index selection with delete option
            col_select, col_delete = st.columns([4, 1])
            
            with col_select:
                if backend_actual == "Weaviate (Cloud Vector DB)":
                    # Interactive inline Weaviate collection selector without 'All Collections'
                    selected_collection_inline = render_collection_selector(
                        key="query_collection_inline",
                        label="Selected collection:",
                        help_text="Choose a Weaviate collection to search",
                        include_all_option=False
                    )
                    if selected_collection_inline:
                        index_name = selected_collection_inline
                    # Fallback inline selectbox if shared component returns None
                    if not index_name:
                        try:
                            from utils.weaviate_manager import get_weaviate_manager
                            wm_fb = get_weaviate_manager()
                            collections_fb = wm_fb.list_collections()
                            if collections_fb:
                                default_idx_fb = 0
                                sel_fb = st.selectbox("Select collection:", collections_fb, index=default_idx_fb, key="qa_weaviate_coll_fallback")
                                if sel_fb:
                                    index_name = sel_fb
                        except Exception:
                            pass
                    # If still nothing selected, auto-pick first
                    if not index_name:
                        try:
                            from utils.weaviate_manager import get_weaviate_manager
                            wm2 = get_weaviate_manager()
                            colls2 = wm2.list_collections()
                            if colls2:
                                index_name = colls2[0]
                        except Exception:
                            pass
                elif backend_actual == "Both":
                    # Show summary of selections from top section (avoid duplicate widgets/keys)
                    both_w = st.session_state.get("qa_both_weaviate_cols", [])
                    both_f = st.session_state.get("qa_both_faiss_indexes", [])
                    st.text_input("Weaviate collections selected:", ", ".join(both_w) if both_w else "(none)", disabled=True)
                    st.text_input("FAISS indexes selected:", ", ".join(both_f) if both_f else "(none)", disabled=True)
                else:
                    # Interactive inline FAISS selector when indexes exist
                    try:
                        vdb = get_vector_db_provider()
                        discovered2 = vdb.get_available_indexes(force_refresh=True)
                        faiss_options2 = [n for n in discovered2 if vdb.find_index_path(n) and n.lower() != "faiss_index"]
                    except Exception:
                        faiss_options2 = []
                    if faiss_options2:
                        default_choice2 = st.session_state.get("qa_faiss_index", faiss_options2[0])
                        try:
                            default_idx2 = faiss_options2.index(default_choice2)
                        except ValueError:
                            default_idx2 = 0
                        sel_main = st.selectbox("Select knowledge base:", faiss_options2, index=default_idx2, key="qa_faiss_index_main")
                        st.session_state["qa_faiss_index"] = sel_main
                        index_name = sel_main
                    else:
                        st.text_input("Selected knowledge base:", "(none)", disabled=True)
                        st.caption("No local FAISS index found. Use Debug → Quick Build, or switch to Weaviate backend.")
            
            with col_delete:
                st.write("")
                if backend_actual != "Weaviate (Cloud Vector DB)" and index_name and st.button("🗑️", key="delete_index", help="Delete selected index"):
                    st.session_state[f"confirm_delete_{index_name}"] = True
            
            # Show delete confirmation if needed
            if st.session_state.get(f"confirm_delete_{index_name}", False):
                st.warning(f"⚠️ Delete '{index_name}' index? This cannot be undone!")
                col_yes, col_no = st.columns(2)
                
                with col_yes:
                    if st.button("✅ Yes, Delete", key=f"confirm_yes_{index_name}"):
                        try:
                            from utils.index_manager import IndexManager
                            result = IndexManager.delete_index(index_name)
                            
                            if result['success']:
                                st.success(f"Successfully deleted '{index_name}'!")
                                st.session_state[f"confirm_delete_{index_name}"] = False
                                # Mark that an index was deleted to force refresh
                                st.session_state['index_deleted'] = True
                                # Clear all cached index lists
                                if 'cached_index_list' in st.session_state:
                                    del st.session_state['cached_index_list']
                                if 'available_indexes' in st.session_state:
                                    del st.session_state['available_indexes']
                                st.rerun()
                            else:
                                st.error(f"Failed to delete: {result['message']}")
                        except Exception as e:
                            st.error(f"Error deleting index: {str(e)}")
                
                with col_no:
                    if st.button("❌ Cancel", key=f"confirm_no_{index_name}"):
                        st.session_state[f"confirm_delete_{index_name}"] = False
                        st.rerun()
            
            query = st.text_area(
                "Your question:",
                placeholder="e.g. What security measures does AWS provide for enterprise deployments?",
                height=100
            )
            
        with col2:
            top_k = st.slider("Number of results", 1, 20, 5)
        
        # Enterprise hybrid re-ranking option for Index Search
        st.checkbox("Use enterprise hybrid re-ranking (local merge)", value=True, key="qa_index_enterprise")
        search_button = st.button("🔍 Search Knowledge Base", use_container_width=True, key="qa_index_search_btn")
        
        if search_button:
            # P0 Security: Input Validation
            valid_query, error_msg, sanitized_query = validate_search_query(query)
            if not valid_query:
                st.error(f"❌ Invalid query: {error_msg}")
                return

            # P0 Security: Rate Limiting
            user_id = username or "anonymous"
            allowed, rate_error, rate_info = check_rate_limit(user_id, tier="premium", operation="query")
            if not allowed:
                st.error(f"⚠️ {rate_error}")
                st.info(f"Rate limit info: {rate_info.get('minute_remaining', 0)} queries remaining this minute")
                return

            # Validate query length (additional check)
            if not query or len(query.strip()) < 3:
                st.warning("Please enter a query with at least 3 characters")
                return
            if len(query) > 1000:
                st.warning("Query too long (max 1000 characters)")
                return
            
            # Log user action
            st.session_state['user_action'] = "QUERY_EXECUTION"
            st.session_state['query_text'] = query[:50]
        
        # Show delete confirmation if needed
        if st.session_state.get(f"confirm_delete_{index_name}", False):
            st.warning(f"⚠️ Delete '{index_name}' index? This cannot be undone!")
            col_yes, col_no = st.columns(2)
            
            with col_yes:
                if st.button("✅ Yes, Delete", key=f"confirm_yes_{index_name}"):
                    try:
                        from utils.index_manager import IndexManager
                        result = IndexManager.delete_index(index_name)
                        
                        if result['success']:
                            st.success(f"Successfully deleted '{index_name}'!")
                            st.session_state[f"confirm_delete_{index_name}"] = False
                            # Mark that an index was deleted to force refresh
                            st.session_state['index_deleted'] = True
                            # Clear all cached index lists
                            if 'cached_index_list' in st.session_state:
                                del st.session_state['cached_index_list']
                            if 'available_indexes' in st.session_state:
                                del st.session_state['available_indexes']
                            st.rerun()
                        else:
                            st.error(f"Failed to delete: {result['message']}")
                    except Exception as e:
                        st.error(f"Error deleting index: {str(e)}")
            
            with col_no:
                if st.button("❌ Cancel", key=f"confirm_no_{index_name}"):
                    st.session_state[f"confirm_delete_{index_name}"] = False
                    st.rerun()
        
        query = st.text_area(
            "Your question:",
            placeholder="e.g. What security measures does AWS provide for enterprise deployments?",
            height=100,
            key="qa_index_question"
        )
    
    with col2:
        top_k = st.slider("Number of results", 1, 20, 5, key="qa_index_topk")
    
    search_button = st.button("🔍 Search Knowledge Base", use_container_width=True)
    
    if search_button:
        # Validate query
        if not query or len(query.strip()) < 3:
            st.warning("Please enter a query with at least 3 characters")
            return
        if len(query) > 1000:
            st.warning("Query too long (max 1000 characters)")
            return
        if backend_actual != "Both" and (not index_name or not str(index_name).strip()):
            st.warning("Please select a knowledge base (collection/index) first")
            return

        # Log user action
        st.session_state['user_action'] = "QUERY_EXECUTION"
        st.session_state['query_text'] = query[:50]

        progress_bar = st.progress(0)
        status_text = st.empty()
        combined_content = ""
        
        try:
            status_text.text("Initializing search...")
            progress_bar.progress(10)
            
            results = []
            
            if backend_actual == "FAISS (Local Index)":
                status_text.text(f"Searching local index '{index_name}'...")
                progress_bar.progress(30)
                try:
                    vdb_local = get_vector_db_provider()
                    results = vdb_local.search_index(query=query, index_name=index_name, top_k=top_k) or []
                except Exception as e:
                    status_text.text(f"Local search error: {str(e)[:100]}...")
                    results = []
            elif backend_actual == "Weaviate (Cloud Vector DB)":
                status_text.text(f"Searching collection '{index_name}'...")
                progress_bar.progress(30)
                try:
                    from utils.weaviate_manager import get_weaviate_manager
                    wm_idx = get_weaviate_manager()
                    results = wm_idx.get_documents_for_tab(
                        collection_name=index_name,
                        tab_name="query_assistant",
                        query=query,
                        limit=top_k
                    ) or []
                    if not results:
                        results = _quick_weaviate_search(wm_idx, index_name, query, top_k)
                except Exception as e:
                    status_text.text(f"Weaviate search error: {str(e)[:100]}...")
                    results = []
            else:
                status_text.text("Searching both backends...")
                progress_bar.progress(30)
                res_w, res_f = [], []
                try:
                    from utils.weaviate_manager import get_weaviate_manager
                    wm_b = get_weaviate_manager()
                    res_w = wm_b.get_documents_for_tab(
                        collection_name=index_name,
                        tab_name="query_assistant",
                        query=query,
                        limit=top_k
                    ) or []
                    if not res_w:
                        res_w = _quick_weaviate_search(wm_b, index_name, query, top_k) or []
                except Exception:
                    res_w = []
                try:
                    vdb_b = get_vector_db_provider()
                    res_f = vdb_b.search_index(query=query, index_name=index_name, top_k=top_k) or []
                except Exception:
                    res_f = []
                merged = res_w + res_f
                try:
                    merged_n = [_normalize_content_from_result(r, index_name) for r in merged]
                    results = _dedupe_results(merged_n)[:top_k]
                except Exception:
                    results = merged[:top_k]
            
            # Optional enterprise hybrid re-ranking merge
            try:
                if st.session_state.get("qa_index_enterprise", True):
                    from utils.enterprise_hybrid_search import get_enterprise_hybrid_search
                    eh2 = get_enterprise_hybrid_search()
                    eh_res2 = eh2.search(query, index_name, max_results=top_k) or []
                    if eh_res2:
                        eh_norm2 = [{
                            'content': r.content,
                            'source': r.source,
                            'page': r.page,
                            'section': r.section,
                            'relevance_score': getattr(r, 'final_score', 0.0),
                            'backend': 'EnterpriseHybrid',
                            'index_source': index_name,
                        } for r in eh_res2]
                        base_norm2 = [_normalize_content_from_result(r, index_name) for r in (results or [])]
                        results = _dedupe_results(base_norm2 + eh_norm2)[:top_k]
            except Exception:
                pass
            
            progress_bar.progress(90)
            status_text.text("Formatting results...")
            
            # Render
            if results and isinstance(results[0], dict) and results[0].get('markdown_content'):
                st.markdown("## 📄 Document Content")
                with st.container():
                    st.markdown(results[0]['markdown_content'])
            
            if not results:
                st.warning("No results found. Try different query parameters.")
                combined_content = "No results found. Try different query parameters."
            else:
                # Enterprise-ready combined summary
                try:
                    from utils.enhanced_llm_integration import process_query_with_enhanced_llm
                    summary = process_query_with_enhanced_llm(query, results, index_name)
                    summary_text = summary.get("result", "")
                except Exception:
                    try:
                        summary_text = "\n\n".join(
                            (r.get('content', str(r)) if isinstance(r, dict) else str(r))
                            for r in results
                        )[:2000]
                    except Exception:
                        summary_text = ""

                st.markdown("## 🧠 Enterprise Summary")
                st.markdown(summary_text or "(No summary available)")
                st.markdown(f"**Found {len(results)} relevant results**")
                
                # Key sources list
                st.markdown("### 📚 Key Sources")
                for r in results:
                    if isinstance(r, dict):
                        src = r.get('source') or r.get('file_path') or index_name
                        page = r.get('page')
                        snippet = (r.get('content') or "").replace('\n', ' ').strip()
                        snippet = (snippet[:300] + '...') if len(snippet) > 300 else snippet
                        meta = f" (page {page})" if page else ""
                        st.markdown(f"- **{src}**{meta}: {snippet}")
                    else:
                        txt = str(r).replace('\n', ' ').strip()
                        st.markdown(f"- {txt[:200]}")

                # Use the enterprise summary for feedback/report
                combined_content = summary_text

                # Combined Markdown block for Index Search (copy + download)
                try:
                    _lines = []
                    _lines.append(f"Backend: {backend_actual} | Knowledge Base: {index_name}")
                    _lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    if query:
                        _lines.append("")
                        _lines.append(f"Query: {query}")
                    if summary_text:
                        _lines.append("")
                        _lines.append("## Summary")
                        _lines.append(summary_text.strip())
                    if results:
                        _lines.append("")
                        _lines.append("## Sources")
                        for rr in results:
                            if isinstance(rr, dict):
                                ssrc = rr.get('source') or rr.get('file_path') or index_name
                                ppg = rr.get('page')
                                ssnip = (rr.get('content') or '').replace('\n',' ').strip()
                                ssnip = (ssnip[:300] + '...') if len(ssnip) > 300 else ssnip
                                mmeta = f" (page {ppg})" if ppg else ""
                                _lines.append(f"- {ssrc}{mmeta}: {ssnip}")
                            else:
                                ttxt = str(rr).replace('\n',' ').strip()
                                _lines.append(f"- {ttxt[:200]}")
                    idx_combined_md = "\n".join(_lines)
                    st.markdown("### Combined Markdown")
                    _escaped = idx_combined_md.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                    st.markdown(f"""
<textarea id=\"qa_index_report_text\" style=\"width:100%; height:220px;\">{_escaped}</textarea>
<button id=\"qa_index_copy_btn\">Copy to Clipboard</button>
<script>
const btn3=document.getElementById('qa_index_copy_btn');
const ta3=document.getElementById('qa_index_report_text');
if (btn3 && ta3) {{
  btn3.addEventListener('click', async ()=>{{
    try {{ await navigator.clipboard.writeText(ta3.value); btn3.innerText='Copied!'; setTimeout(()=>btn3.innerText='Copy to Clipboard',1500); }}
    catch(e) {{ btn3.innerText='Copy failed'; }}
  }});
}}
</script>
                    """, unsafe_allow_html=True)
                    st.download_button(
                        label="📥 Download .md",
                        data=idx_combined_md,
                        file_name=f"index_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown",
                        key="qa_index_download_md"
                    )
                except Exception:
                    pass

                # Detailed results moved into an expander
                with st.expander("Detailed results", expanded=False):
                    combined_results = "# Query Results\n\n"
                    combined_results += f"Query: {query}\n"
                    combined_results += f"Index: {index_name}\n"
                    combined_results += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    for idx, res in enumerate(results, 1):
                        combined_results += f"## Result {idx}\n{res}\n\n---\n\n"
                    col1, col2 = st.columns([4, 1])
                    with col2:
                        st.download_button(
                            label="📥 Download Results",
                            data=combined_results,
                            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown",
                        )
                    
                    for i, result in enumerate(results, 1):
                        st.markdown(f"### **Result {i}**")
                        if isinstance(result, dict):
                            source = result.get('source', f'Result {i}')
                            content = result.get('content', str(result))
                            relevance_score = result.get('relevance_score', 0)
                            with st.container():
                                display_content = content[:1500] if len(content) > 1500 else content
                                st.markdown(f"""
<div class=\"query-result\">\n<div class=\"result-header\">📄 {source}</div>\n\n{display_content}\n\n{'**[Content Truncated - Full content available in source]**' if len(content) > 1500 else ''}\n</div>
                                """, unsafe_allow_html=True)
                                col_a, col_b, col_c = st.columns(3)
                                with col_a:
                                    st.caption(f"Length: {len(content)} chars")
                                with col_b:
                                    st.caption(f"Relevance Score: {relevance_score}")
                                with col_c:
                                    st.caption(f"Source: {source}")
                            if i < len(results):
                                st.divider()
                        else:
                            content = str(result)
                            display_content = content[:1500] if len(content) > 1500 else content
                            st.markdown(f"""
<div class=\"query-result\">\n<div class=\"result-header\">📊 Content Preview:</div>\n\n{display_content}\n\n{'**[Content Truncated - Full content available in source]**' if len(content) > 1500 else ''}\n</div>
                            """, unsafe_allow_html=True)
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.caption(f"Length: {len(content)} chars")
                            with col_b:
                                st.caption(f"Relevance: Rank #{i}")
                            with col_c:
                                st.caption(f"Source: {index_name}")
                    
                    # Add user feedback buttons after displaying results
                    # Compose source docs with backend/index labels when available
                    source_docs = []
                    for r in results:
                        if isinstance(r, dict):
                            content_val = r.get('content', str(r))
                            src_base = r.get('source', index_name)
                            idx_src = r.get('index_source')
                            bkd = r.get('backend')
                            if idx_src and bkd:
                                src_val = f"{idx_src} · {bkd}"
                            elif idx_src:
                                src_val = idx_src
                            else:
                                src_val = src_base or index_name
                        else:
                            content_val = str(r)
                            src_val = index_name
                        source_docs.append({'content': content_val, 'source': src_val})
                    
                    render_feedback_buttons(
                        query=query,
                        response=combined_content[:800],
                        source_docs=source_docs,
                        confidence_score=sum(r.get('relevance_score', 0.5) if isinstance(r, dict) else 0.5 for r in results) / len(results) if results else 0.0,
                        retrieval_method="enhanced_hybrid_retrieval",
                        session_key=f"query_assistant_{index_name}"
                    )
                    
                    render_query_insights(query)

                # Store report data in session for the Report tab (Index Search)
                try:
                    st.session_state['qa_report_query'] = query
                    st.session_state['qa_report_index'] = index_name
                    st.session_state['qa_report_backend'] = backend_actual
                    st.session_state['qa_report_ai_answer'] = combined_content
                    st.session_state['qa_report_sources'] = results
                    conf2 = (sum(r.get('relevance_score', 0.5) if isinstance(r, dict) else 0.5 for r in (results or [])) / len(results)) if results else 0.0
                    st.session_state['qa_report_confidence'] = round(conf2, 3)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            combined_content = f"Error processing query: {str(e)[:200]}"
        finally:
            progress_bar.progress(100)
            status_text.text("Search completed")
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()
    
    with report_tab:
        st.subheader("Build an email-ready report")
        rq = st.session_state.get('qa_report_query', '')
        rk = st.session_state.get('qa_report_index', '')
        rb = st.session_state.get('qa_report_backend', '')
        ra = st.session_state.get('qa_report_ai_answer', '')
        rs = st.session_state.get('qa_report_sources', [])
        rc = st.session_state.get('qa_report_confidence', 0.0)

        if not ra and not rs:
            st.info("Run a search in Quick Search or Index Search to populate the report.")
        else:
            subj_default = f"[Report] {rq[:60] or 'Document Summary'} — {rk}"
            email_subject = st.text_input("Email subject", value=subj_default, key="qa_report_subject")
            include_sources = st.checkbox("Include sources with page references", value=True, key="qa_report_include_sources")
            include_conf = st.checkbox("Include confidence score", value=True, key="qa_report_include_conf")
            include_backend = st.checkbox("Include backend/index line", value=True, key="qa_report_include_backend")

            lines = []
            if include_backend:
                lines.append(f"Backend: {rb} | Knowledge Base: {rk}")
            if include_conf:
                lines.append(f"Confidence: {rc}")
            if rq:
                lines.append("")
                lines.append(f"Subject: {rq}")
            if ra:
                lines.append("")
                lines.append("## Summary")
                lines.append(ra.strip())
            if include_sources and rs:
                lines.append("")
                lines.append("## Sources")
                for r in rs[:30]:
                    if isinstance(r, dict):
                        src = r.get('source') or r.get('file_path') or rk
                        page = r.get('page')
                        snippet = (r.get('content') or '')
                        snippet = snippet.replace('\n', ' ').strip()
                        snippet = (snippet[:300] + '...') if len(snippet) > 300 else snippet
                        meta = f" (page {page})" if page else ""
                        lines.append(f"- {src}{meta}: {snippet}")
                    else:
                        txt = str(r).replace('\n', ' ').strip()
                        lines.append(f"- {txt[:200]}")
            lines.append("")
            lines.append(f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_body = "\n".join(lines)

            st.markdown("### Email Body")
            escaped = report_body.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            st.markdown(f"""
<textarea id=\"qa_report_text\" style=\"width:100%; height:300px;\">{escaped}</textarea>
<button id=\"qa_copy_btn\">Copy to Clipboard</button>
<script>
const btn=document.getElementById('qa_copy_btn');
const ta=document.getElementById('qa_report_text');
if (btn && ta) {{
  btn.addEventListener('click', async ()=>{{
    try {{ await navigator.clipboard.writeText(ta.value); btn.innerText='Copied!'; setTimeout(()=>btn.innerText='Copy to Clipboard',1500); }}
    catch(e) {{ btn.innerText='Copy failed'; }}
  }});
}}
</script>
            """, unsafe_allow_html=True)

            st.download_button(
                label="📥 Download .md",
                data=report_body,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                key="qa_report_download_md"
            )

    with web_tab:
        st.subheader("🌐 Web Search with AI Summary")
        web_query = st.text_input(
            "Web search query:", 
            placeholder="e.g. latest cloud security threats",
            key="qa_web_query"
        )
        max_results = st.slider("Number of web results", 1, 10, 5, key="qa_web_topk")
        
        web_button = st.button("🔍 Search Web", use_container_width=True, key="qa_web_search_btn")
        
        if web_button and web_query:
            # P0 Security: Input Validation
            valid_query, error_msg, sanitized_query = validate_search_query(web_query)
            if not valid_query:
                st.error(f"❌ Invalid query: {error_msg}")
            else:
                # P0 Security: Rate Limiting
                user_id = username or "anonymous"
                allowed, rate_error, rate_info = check_rate_limit(user_id, tier="premium", operation="web_search")
                if not allowed:
                    st.error(f"⚠️ {rate_error}")
                    st.info(f"Rate limit info: {rate_info.get('minute_remaining', 0)} searches remaining this minute")
                else:
                    # Log user action
                    st.session_state['user_action'] = "WEB_SEARCH"
                    st.session_state['query_text'] = web_query[:50]
                    
                    with st.spinner("Searching the web..."):
                        try:
                            # Get web search results
                            web_results = run_web_search(web_query, max_results)
                            
                            if not web_results:
                                st.warning("No web results found. Try different query parameters.")
                            else:
                                # Convert web results to retrieval format for LLM processing
                                web_docs = []
                                for r in web_results:
                                    web_docs.append({
                                        'content': f"{r.get('title', '')}. {r.get('snippet', '')}",
                                        'source': r.get('url', 'Web'),
                                        'page': None,
                                        'section': r.get('title', ''),
                                        'relevance_score': 0.8,
                                        'url': r.get('url', '')
                                    })
                                
                                # Generate AI summary using LLM
                                st.markdown("## 🧠 AI Summary")
                                try:
                                    from utils.enhanced_llm_integration import EnhancedLLMProcessor
                                    llm_processor = EnhancedLLMProcessor()
                                    web_summary = llm_processor.process_retrieval_results(
                                        query=web_query,
                                        retrieval_results=web_docs,
                                        index_name="Web Search"
                                    )
                                    summary_text = web_summary.get("result", "")
                                    # Sanitize AI markdown
                                    summary_text = _sanitize_ai_markdown(summary_text)
                                    
                                    if summary_text and len(summary_text.strip()) > 50:
                                        st.markdown(summary_text)
                                    else:
                                        # Fallback summary
                                        st.info(f"Found {len(web_results)} web results for: {web_query}")
                                        fallback_summary = f"### Executive Summary\n\nWeb search found {len(web_results)} relevant results about {web_query}.\n\n### Key Findings\n"
                                        for i, r in enumerate(web_results[:3], 1):
                                            fallback_summary += f"{i}. **{r.get('title', 'Untitled')}**: {r.get('snippet', 'No description')[:150]}...\n"
                                        st.markdown(fallback_summary)
                                except Exception as llm_error:
                                    logger.warning(f"LLM summary failed for web search: {llm_error}")
                                    # Simple fallback
                                    st.info(f"Found {len(web_results)} web results for: {web_query}")
                                
                                # Display web sources
                                st.markdown("### 📚 Web Sources")
                                for i, result in enumerate(web_results, 1):
                                    title = result.get('title', 'Untitled')
                                    url = result.get('url', '')
                                    snippet = result.get('snippet', 'No description available')
                                    
                                    st.markdown(f"**{i}. [{title}]({url})**")
                                    if snippet:
                                        st.markdown(f"> {snippet}")
                                    st.markdown("")
                                
                                # Feedback buttons for Web Search
                                try:
                                    if web_results:
                                        # Get the summary text (either from LLM or fallback)
                                        web_summary_text = summary_text if 'summary_text' in locals() else f"Found {len(web_results)} web results"
                                        
                                        render_feedback_buttons(
                                            query=web_query,
                                            response=web_summary_text[:800],
                                            source_docs=web_docs,
                                            confidence_score=0.75,  # Default confidence for web results
                                            retrieval_method="web_search_hybrid",
                                            session_key=f"web_search_{hash(web_query)}"
                                        )
                                        
                                        render_query_insights(web_query)
                                except Exception as feedback_error:
                                    logger.warning(f"Failed to render web search feedback buttons: {feedback_error}")
                            
                        except Exception as e:
                            st.error(f"❌ Web search failed: {type(e).__name__} — {str(e)[:200]}")
                            logger.error(f"Web search failed for user {username}: {str(e)}")
    
    # Add a help section at the bottom
    with st.expander("ℹ️ Help & Tips"):
        st.markdown("""
        ### How to use the Query Assistant
        
        **Index Search Mode:**
        1. Select a knowledge base from the dropdown
        2. Enter your question in natural language
        3. Adjust the number of results to retrieve
        4. Click "Search Knowledge Base"
        
        **Web Search Mode:**
        1. Enter your search query
        2. Adjust the number of web results to display
        3. Click "Search Web"
        
        **Tips for better results:**
        - Be specific in your questions
        - Try different knowledge bases for different types of information
        - Use the AI summary to get a quick overview of results
        - For detailed information, review all the individual results
        """)

    # Include version and last updated info
    st.caption(f"Query Assistant v2.0 | Last updated: {datetime.now().strftime('%Y-%m-%d')}")

# Ensure the render function is available for import
def render_query_assistant_tab(*args, **kwargs):
    """Alias for render_query_assistant"""
    return render_query_assistant(*args, **kwargs)

__all__ = ['render_query_assistant', 'render_query_assistant_tab']
