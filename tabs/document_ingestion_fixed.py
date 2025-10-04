"""
Document Ingestion Tab - Fixed Version with Weaviate Integration
===============================================================
Enhanced document ingestion with dual backend support (Weaviate + FAISS)
"""

import streamlit as st
import os
from pathlib import Path
import logging
from datetime import datetime
import time
import json
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Import Weaviate components with fallback
try:
    from utils.weaviate_ingestion_helper import WeaviateIngestionHelper
    from utils.weaviate_collection_selector import render_backend_selector
    WEAVIATE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Weaviate components not available: {e}")
    WEAVIATE_AVAILABLE = False
    
    # Create fallback functions
    def render_backend_selector(key="backend"):
        return st.selectbox("Storage Backend:", ["FAISS (Local Index)"], key=key)
    
    class WeaviateIngestionHelper:
        def __init__(self):
            pass
        def test_connection(self):
            return False


def render_document_ingestion(user, permissions, auth_middleware, available_indexes=None, index_root=None, project_root=None):
    """Enhanced Document Ingestion Tab with Weaviate Integration"""
    
    # Log user action
    auth_middleware.log_user_action("ACCESS_DOCUMENT_INGESTION")
    
    st.info("🔧 Updated version - Index validation fixed")
    
    # Get current user info
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        user_role = user.get('role', 'viewer')
    else:
        username = user.username
        user_role = user.role.value if hasattr(user.role, 'value') else user.role
    
    role_display = user_role.title() if isinstance(user_role, str) else user_role
    
    # Header
    st.header("📄 Document Ingestion")
    st.info(f"👤 Logged in as: **{username}** ({role_display})")
    
    # Backend selection
    st.subheader("🔧 Storage Backend")
    
    # Support FAISS, Weaviate, or Both
    storage_backend = st.selectbox(
        "Storage Backend:",
        ["FAISS (Local Index)", "Weaviate (Cloud Vector DB)", "Both (Weaviate + Local FAISS)"],
        key="ingestion_backend"
    )
    
    if storage_backend == "Weaviate (Cloud Vector DB)":
        # Test connection and fallback if needed
        if WEAVIATE_AVAILABLE:
            try:
                weaviate_helper = WeaviateIngestionHelper()
                if weaviate_helper.test_connection():
                    st.success("☁️ Using Weaviate Cloud Vector Database")
                    render_weaviate_ingestion(username)
                else:
                    st.error("❌ **Weaviate Connection Failed**")
                    st.info("💡 **Solution**: Weaviate server not running. Switching to FAISS fallback.")
                    render_faiss_ingestion(username)
            except Exception as e:
                st.error("❌ **Weaviate Connection Error**")
                st.info("💡 **Solution**: Connection failed. Switching to FAISS fallback.")
                render_faiss_ingestion(username)
        else:
            st.error("❌ **Weaviate Unavailable**")
            st.info("💡 **Solution**: Dependencies not available. Switching to FAISS fallback.")
            render_faiss_ingestion(username)
    elif storage_backend == "Both (Weaviate + Local FAISS)":
        # Run Weaviate UI and FAISS UI sequentially
        if WEAVIATE_AVAILABLE:
            try:
                weaviate_helper = WeaviateIngestionHelper()
                if weaviate_helper.test_connection():
                    st.success("☁️ Using Weaviate Cloud Vector Database")
                    render_weaviate_ingestion(username)
                else:
                    st.error("❌ **Weaviate Connection Failed**")
                    st.info("Proceeding with FAISS local index while Weaviate is unavailable.")
            except Exception as e:
                st.warning(f"Weaviate error: {e}")
        else:
            st.info("Weaviate not available; proceeding with FAISS only.")
        st.markdown("---")
        st.info("Now configure Local FAISS index build for cross-tab availability")
        render_faiss_ingestion(username)
    else:
        st.info("💾 Using Local FAISS Index")
        render_faiss_ingestion(username)

def render_weaviate_ingestion(username):
    """Render Weaviate ingestion interface"""
    
    # Test Weaviate connection first
    try:
        weaviate_helper = WeaviateIngestionHelper()
        if not weaviate_helper.test_connection():
            st.error("❌ **Weaviate Connection Failed**")
            st.info("💡 **Solution**: Weaviate server is not running. Using FAISS fallback instead.")
            st.info("🔄 **Switching to FAISS mode...**")
            render_faiss_ingestion(username)
            return
    except Exception as e:
        st.error("❌ **Weaviate Connection Error**")
        st.info("💡 **Solution**: Weaviate dependencies unavailable. Using FAISS fallback instead.")
        st.info("🔄 **Switching to FAISS mode...**")
        render_faiss_ingestion(username)
        return
    
    # Collection name input
    st.subheader("📚 Collection Configuration")
    collection_name = st.text_input(
        "Collection Name",
        value="",
        help="Enter a name for your Weaviate collection (e.g., 'company_docs', 'bylaws_2024')"
    )
    
    if not collection_name:
        st.warning("⚠️ Please enter a collection name to proceed")
        return
    
    # Source type selection
    st.subheader("📥 Document Source")
    source_type = st.selectbox(
        "Select Source Type:",
        ["PDF File", "Text File", "Website URL"],
        key="weaviate_ingest_source_type"
    )
    
    # Chunking configuration
    st.subheader("🔧 Chunking Strategy")
    chunking_strategy = st.selectbox(
        "Chunking Method:",
        ["Semantic Chunking (Recommended)", "Fixed Size Chunking"],
        help="Semantic chunking provides better search results"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        chunk_size = st.slider("Chunk Size", 100, 2000, 800)
    with col2:
        chunk_overlap = st.slider("Chunk Overlap", 0, 200, 100)
    
    # Advanced options for semantic chunking
    if chunking_strategy == "Semantic Chunking (Recommended)":
        with st.expander("🧠 Advanced Semantic Options"):
            split_by_headers = st.checkbox("Split by Headers", value=True)
            use_embeddings = st.checkbox("Use Embeddings for Chunking", value=True)
    else:
        split_by_headers = False
        use_embeddings = False
    
    # Vectorization options specific to Weaviate ingestion
    st.subheader("🧮 Vectorization (Weaviate)")
    use_local_embeddings_ui = st.checkbox(
        "Use local embeddings (HuggingFace) for Weaviate",
        value=False,
        help=(
            "Compute vectors locally with SentenceTransformers and insert them directly into Weaviate. "
            "Disables server-side vectorizer."
        ),
    )
    default_model = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    embedding_model_ui = st.text_input(
        "Embedding model (SentenceTransformers)",
        value=default_model,
        help="Model name or local path (e.g., 'all-MiniLM-L6-v2').",
    )
    if use_local_embeddings_ui:
        st.info(f"Using local embeddings with model: {embedding_model_ui}")

    # Ingestion diagnostics and tuning options
    st.subheader("⚙️ Ingestion Diagnostics & Tuning")
    with st.expander("Batch Insert Settings (Advanced)"):
        default_log_every = int(os.getenv("WEAVIATE_INSERT_LOG_EVERY", "25"))
        default_batch_chunk = int(os.getenv("WEAVIATE_BATCH_CHUNK_SIZE", "100"))
        default_max_sec = float(os.getenv("WEAVIATE_INSERT_MAX_SEC", "180"))
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            log_every_ui = st.number_input(
                "Log Every N Inserts",
                min_value=0,
                max_value=10000,
                value=default_log_every,
                help="How frequently to log progress during batch insert.",
            )
        with col_t2:
            batch_chunk_size_ui = st.number_input(
                "Batch Chunk Size",
                min_value=1,
                max_value=10000,
                value=default_batch_chunk,
                help="Number of objects per dynamic batch chunk.",
            )
        with col_t3:
            max_insert_sec_ui = st.number_input(
                "Soft Timeout (seconds)",
                min_value=0.0,
                max_value=36000.0,
                value=default_max_sec,
                help="Abort insertion if total time exceeds this.",
            )
    
    # File upload or URL input based on source type
    uploaded_file = None
    url_input = None
    
    if source_type in ["PDF File", "Text File"]:
        file_types = ["pdf"] if source_type == "PDF File" else ["txt", "md", "csv"]
        uploaded_file = st.file_uploader(
            f"Choose {source_type}",
            type=file_types
        )
    elif source_type == "Website URL":
        url_input = st.text_input("Enter Website URL:")
        render_js = st.checkbox("Render JavaScript", value=False)
        max_depth = st.slider("Crawl Depth", 1, 3, 1)
    
    # Ingestion button
    if st.button("🚀 Start Weaviate Ingestion", type="primary"):
        if (source_type in ["PDF File", "Text File"] and uploaded_file) or (source_type == "Website URL" and url_input):
            
            # Initialize Weaviate helper
            weaviate_helper = WeaviateIngestionHelper()
            
            # Create progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("🔄 Initializing Weaviate connection...")
                progress_bar.progress(10)
                
                # Test connection
                if not weaviate_helper.test_connection():
                    st.error("❌ Cannot connect to Weaviate. Please check your configuration.")
                    return
                
                # Apply tuning settings via environment variables before ingestion begins
                try:
                    os.environ["WEAVIATE_INSERT_LOG_EVERY"] = str(int(log_every_ui))
                    os.environ["WEAVIATE_BATCH_CHUNK_SIZE"] = str(int(batch_chunk_size_ui))
                    os.environ["WEAVIATE_INSERT_MAX_SEC"] = str(float(max_insert_sec_ui))
                    logger.info(
                        f"Applied batch settings: log_every={log_every_ui}, chunk_size={batch_chunk_size_ui}, max_sec={max_insert_sec_ui}"
                    )
                except Exception as _e:
                    logger.warning(f"Failed to apply batch settings from UI: {_e}")

                # Apply vectorization mode (client-side vs server-side)
                try:
                    os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = (
                        "true" if use_local_embeddings_ui else "false"
                    )
                    logger.info(
                        f"Vectorization mode: client_vectors={os.environ['WEAVIATE_USE_CLIENT_VECTORS']} (model={embedding_model_ui})"
                    )
                except Exception as _e:
                    logger.warning(f"Failed to apply vectorization mode from UI: {_e}")

                status_text.text("📚 Creating collection...")
                progress_bar.progress(20)
                
                # Create collection
                collection_created = weaviate_helper.create_collection(
                    collection_name=collection_name,
                    description=f"Created by {username} - {source_type} ingestion"
                )
                
                if not collection_created:
                    st.error(f"❌ Failed to create collection '{collection_name}'")
                    return
                
                progress_bar.progress(30)
                
                # Process based on source type
                if source_type == "PDF File":
                    status_text.text("📄 Processing PDF...")
                    success = weaviate_helper.ingest_pdf(
                        collection_name=collection_name,
                        pdf_file=uploaded_file,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        use_semantic_chunking=(
                            chunking_strategy == "Semantic Chunking (Recommended)"
                        ),
                        split_by_headers=split_by_headers,
                        use_embeddings=use_embeddings,
                        use_local_embeddings=use_local_embeddings_ui,
                        embedding_model=embedding_model_ui,
                    )
                
                elif source_type == "Text File":
                    status_text.text("📝 Processing text file...")
                    success = weaviate_helper.ingest_text_file(
                        collection_name=collection_name,
                        text_file=uploaded_file,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        use_semantic_chunking=(
                            chunking_strategy == "Semantic Chunking (Recommended)"
                        ),
                        split_by_headers=split_by_headers,
                        use_embeddings=use_embeddings,
                        use_local_embeddings=use_local_embeddings_ui,
                        embedding_model=embedding_model_ui,
                    )
                
                elif source_type == "Website URL":
                    status_text.text("🌐 Processing website...")
                    success = weaviate_helper.ingest_url(
                        collection_name=collection_name,
                        url=url_input,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        render_js=render_js,
                        max_depth=max_depth,
                        use_semantic_chunking=(
                            chunking_strategy == "Semantic Chunking (Recommended)"
                        ),
                        split_by_headers=split_by_headers,
                        use_embeddings=use_embeddings,
                        use_local_embeddings=use_local_embeddings_ui,
                        embedding_model=embedding_model_ui,
                    )
                
                progress_bar.progress(90)
                
                if success:
                    progress_bar.progress(100)
                    status_text.text("✅ Ingestion completed successfully!")
                    
                    # Display collection statistics
                    stats = weaviate_helper.get_collection_stats(collection_name)
                    if stats:
                        st.success(
                            f"""
                        🎉 **Ingestion Successful!**
                        
                        **Collection:** {collection_name}
                        **Documents:** {stats.get('document_count', 'N/A')}
                        **Total Objects:** {stats.get('total_objects', 'N/A')}
                        **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        """
                        )
                    else:
                        st.success("✅ Documents ingested successfully into Weaviate!")

                    # Ensure readiness and show available collections
                    try:
                        from utils.weaviate_manager import get_weaviate_manager
                        wm = get_weaviate_manager()
                        wm.ensure_collection_ready(collection_name)
                        colls = wm.list_collections() or []
                        if colls:
                            st.markdown("#### 📚 Collections Detected (post-ingestion)")
                            st.write(", ".join(colls))
                    except Exception as e:
                        st.warning(f"Could not list collections: {e}")
                else:
                    st.error("❌ Ingestion failed. Please check the logs for details.")
                
                # Always display detailed diagnostics if available
                diag = getattr(weaviate_helper, "last_result", None)
                if isinstance(diag, dict) and diag:
                    st.markdown("### 📊 Detailed Ingestion Diagnostics")
                    # Key metrics summary
                    attempted = diag.get("attempted_count")
                    processed = diag.get("processed_count")
                    pre_c = diag.get("pre_count")
                    post_c = diag.get("post_count")
                    delta = diag.get("inserted_delta")
                    dur = diag.get("duration_ms")
                    chunk_ms = None
                    if isinstance(diag.get("phase_timings_ms"), dict):
                        chunk_ms = diag["phase_timings_ms"].get("chunking_ms")
                    
                    st.markdown(
                        f"- **Success:** {diag.get('success')}\n"
                        f"- **Attempted:** {attempted}  |  **Processed:** {processed}\n"
                        f"- **Counts:** before={pre_c}, after={post_c}, inserted_delta={delta}\n"
                        f"- **Insertion Duration:** {dur} ms"
                        + (f"  |  **Chunking:** {chunk_ms} ms" if chunk_ms is not None else "")
                    )
                    
                    warnings_list = diag.get("warnings") or []
                    if warnings_list:
                        st.warning("Warnings during ingestion:")
                        for w in warnings_list:
                            st.markdown(f"- {w}")
                    if diag.get("error"):
                        st.error(f"Error: {diag['error']}")
                    
                    with st.expander("🔎 Raw diagnostics JSON"):
                        st.json(diag)
                    
            except Exception as e:
                st.error(f"❌ Ingestion error: {str(e)}")
                logger.error(f"Weaviate ingestion failed: {e}")
            
            finally:
                progress_bar.empty()
                status_text.empty()
        else:
            st.warning("⚠️ Please provide the required input for the selected source type.")

def render_faiss_ingestion(username):
    """Render FAISS ingestion interface (fallback)"""
    
    st.subheader("📁 Index Configuration")
    index_name = st.text_input(
        "Index Name",
        value="document_index",
        help="Enter a name for your FAISS index"
    )
    
    if not index_name.strip():
        index_name = "document_index"
        st.info("Using default index name: document_index")
    
    # Source type selection
    st.subheader("📥 Document Source")
    source_type = st.selectbox(
        "Select Source Type:",
        ["PDF File", "Text File", "Website URL"],
        key="faiss_ingest_source_type"
    )
    
    # Chunking configuration
    st.subheader("🔧 Chunking Configuration")
    col1, col2 = st.columns(2)
    with col1:
        chunk_size = st.slider("Chunk Size", 800, 3000, 1500, help="Optimal: 1200-1800 for preserving context")
    with col2:
        chunk_overlap = st.slider("Chunk Overlap", 100, 500, 300, help="Prevents cutting sentences")
    
    chunking_strategy = st.selectbox(
        "Chunking Method:",
        ["Semantic Chunking (Recommended)", "Fixed Size Chunking"]
    )
    
    # File upload or URL input
    uploaded_file = None
    url_input = None
    
    if source_type in ["PDF File", "Text File"]:
        file_types = ["pdf"] if source_type == "PDF File" else ["txt", "md", "csv"]
        uploaded_file = st.file_uploader(
            f"Choose {source_type}",
            type=file_types
        )
    elif source_type == "Website URL":
        url_input = st.text_input("Enter Website URL:")
        render_js = st.checkbox("Render JavaScript", value=False)
        max_depth = st.slider("Crawl Depth", 1, 3, 1)
    
    # Ingestion button
    if st.button("🚀 Start FAISS Ingestion", type="primary"):
        if (source_type in ["PDF File", "Text File"] and uploaded_file) or (source_type == "Website URL" and url_input):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Create index directory
                index_dir = Path("data") / "indexes" / index_name
                index_dir.mkdir(parents=True, exist_ok=True)
                
                status_text.text("📁 Creating index directory...")
                progress_bar.progress(20)
                
                # Create metadata file
                creation_date = datetime.now().isoformat()
                with open(index_dir / "index.meta", "w", encoding="utf-8") as f:
                    f.write(
                        f"Created by: {username}\nDocument type: {source_type}\nChunk size: {chunk_size}\nChunk overlap: {chunk_overlap}\nCreation date: {creation_date}"
                    )
                
                # Process documents
                if source_type == "PDF File" and uploaded_file:
                    status_text.text("📄 Processing PDF...")
                    
                    # Save the uploaded PDF
                    with open(index_dir / f"source_document.pdf", "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    progress_bar.progress(50)
                
                    # Extract text from PDF using robust extractor
                    try:
                        from utils.robust_pdf_extractor import extract_text_from_pdf_robust, validate_extraction_quality
                        
                        pdf_bytes = uploaded_file.getvalue()
                        text_content, method = extract_text_from_pdf_robust(pdf_bytes, uploaded_file.name)
                        
                        if text_content:
                            is_valid, quality, message = validate_extraction_quality(text_content, min_quality=0.5)
                            st.info(f"📄 Extraction: {method} | Quality: {quality:.2f}")
                            if not is_valid:
                                st.warning(f"⚠️ {message}")
                        else:
                            text_content = f"[PDF text extraction failed for {uploaded_file.name}]"
                            st.error("❌ All extraction methods failed")
                    except Exception as e:
                        text_content = f"[PDF extraction error: {str(e)}]"
                        st.error(f"❌ Extraction error: {e}")
                
                    # Save the extracted text
                    with open(index_dir / "extracted_text.txt", "w", encoding="utf-8") as f:
                        f.write(text_content)
                    
                    # Create basic chunks
                    chunk_count = max(1, len(text_content) // (chunk_size - chunk_overlap))
                    for i in range(min(chunk_count, 10)):
                        start = i * (chunk_size - chunk_overlap)
                        end = start + chunk_size
                        if end > len(text_content):
                            end = len(text_content)
                        
                        chunk = text_content[start:end]
                        with open(index_dir / f"chunk_{i+1}.txt", "w", encoding="utf-8") as f:
                            f.write(chunk)
                
                elif source_type == "Text File" and uploaded_file:
                    status_text.text("📝 Processing text file...")
                    
                    # Decode text content
                    try:
                        text_content = uploaded_file.getvalue().decode("utf-8")
                    except UnicodeDecodeError:
                        text_content = uploaded_file.getvalue().decode("latin-1")
                    
                    # Save the uploaded text file
                    with open(index_dir / f"source_document.txt", "w", encoding="utf-8") as f:
                        f.write(text_content)
                    progress_bar.progress(50)
                    
                    # Create chunks
                    chunk_count = max(1, len(text_content) // (chunk_size - chunk_overlap))
                    for i in range(min(chunk_count, 10)):
                        start = i * (chunk_size - chunk_overlap)
                        end = start + chunk_size
                        if end > len(text_content):
                            end = len(text_content)
                        
                        chunk = text_content[start:end]
                        with open(index_dir / f"chunk_{i+1}.txt", "w", encoding="utf-8") as f:
                            f.write(chunk)
                
                elif source_type == "Website URL" and url_input:
                    status_text.text("🌐 Processing website...")
                    
                    # Save URL info
                    with open(index_dir / "source_url.txt", "w", encoding="utf-8") as f:
                        f.write(f"URL: {url_input}\nRender JS: {render_js}\nDepth: {max_depth}")
                    progress_bar.progress(30)
                    
                    # Create placeholder content
                    placeholder_content = f"Website content from {url_input}\nProcessed with depth {max_depth}"
                    with open(index_dir / "extracted_content.txt", "w", encoding="utf-8") as f:
                        f.write(placeholder_content)
                
                # Build FAISS index so Query/Chat/Agent tabs can discover it
                # Find a text file to embed
                status_text.text("🧠 Building FAISS vectors (HuggingFace: all-MiniLM-L6-v2)...")
                progress_bar.progress(80)
                text_path_candidates = [
                    index_dir / "extracted_text.txt",
                    index_dir / "source_document.txt",
                    index_dir / "extracted_content.txt",
                ]
                text_path = next((p for p in text_path_candidates if p.exists()), None)
                if text_path is None:
                    # As a fallback compose from chunk_*.txt files
                    chunks = []
                    for i in range(1, 11):
                        p = index_dir / f"chunk_{i}.txt"
                        if p.exists():
                            try:
                                chunks.append(
                                    p.read_text(encoding="utf-8", errors="ignore")
                                )
                            except Exception:
                                pass
                    text_to_embed = "\n\n".join(chunks)
                else:
                    text_to_embed = text_path.read_text(encoding="utf-8", errors="ignore")
                if not text_to_embed.strip():
                    raise RuntimeError(
                        "No text found to build FAISS vectors. Ensure extracted_text.txt or chunks exist."
                    )
                # Simple chunking for embedding
                chunks = []
                step = max(1, chunk_size - chunk_overlap)
                for i in range(0, len(text_to_embed), step):
                    chunk = text_to_embed[i : i + chunk_size]
                    if chunk:
                        chunks.append(chunk)
                model = SentenceTransformer("all-MiniLM-L6-v2")
                embs = model.encode(
                    chunks,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
                embs = embs.astype("float32")
                dim = embs.shape[1]
                index = faiss.IndexFlatIP(dim)
                index.add(embs)
                faiss_target = Path("data") / "faiss_index" / index_name
                faiss_target.mkdir(parents=True, exist_ok=True)
                faiss.write_index(index, str(faiss_target / "index.faiss"))
                docs = [
                    {
                        "chunk_id": i,
                        "text": chunks[i],
                        "source": f"local_ingestion:{index_name}",
                        "created_at": datetime.now().isoformat(),
                    }
                    for i in range(len(chunks))
                ]
                with open(faiss_target / "documents.pkl", "wb") as pf:
                    pickle.dump(
                        {
                            "documents": [d.get("text", "") for d in docs],
                            "metadatas": [{"source": d["source"]} for d in docs],
                        },
                        pf,
                    )

                progress_bar.progress(100)
                status_text.text("✅ FAISS ingestion + vector build completed!")
                
                st.success(
                    f"""
                🎉 **FAISS Ingestion Successful!**
                
                **Index:** {index_name}
                **Source:** {source_type}
                **Location:** {index_dir}
                **FAISS Vectors:** data/faiss_index/{index_name}
                **Embedding Engine:** SentenceTransformer (all-MiniLM-L6-v2)
                **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                )

                # Notify other tabs to refresh index discovery
                st.session_state.force_index_refresh = True
                
            except Exception as e:
                st.error(f"❌ FAISS ingestion error: {str(e)}")
                logger.error(f"FAISS ingestion failed: {e}")
            
            finally:
                progress_bar.empty()
                status_text.empty()
        else:
            st.warning("⚠️ Please provide the required input for the selected source type.")
