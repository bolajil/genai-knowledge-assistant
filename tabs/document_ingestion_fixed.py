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
import json
import pickle
import numpy as np
import io

logger = logging.getLogger(__name__)

# Optional PDF page counter
try:
    from PyPDF2 import PdfReader
    PDF_READER_AVAILABLE = True
except Exception:
    PDF_READER_AVAILABLE = False

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
    
    col1, col2 = st.columns([3, 1])
    with col1:
        collection_name = st.text_input(
            "Collection Name",
            value="",
            help="Enter a name for your Weaviate collection (e.g., 'company_docs', 'bylaws_2024')"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🗑️ Manage Collections", key="manage_weaviate_collections", help="Delete or clear existing collections"):
            st.session_state.show_collection_manager = True
    
    # Collection Management UI
    if st.session_state.get('show_collection_manager', False):
        st.markdown("---")
        st.subheader("🗑️ Collection Management")
        
        try:
            from utils.weaviate_manager import get_weaviate_manager
            wm = get_weaviate_manager()
            collections = wm.list_collections() or []
            
            if collections:
                st.info(f"📊 Found {len(collections)} collections")
                
                # Get collection details
                collection_details = []
                for coll_name in collections:
                    try:
                        stats = wm.get_collection_stats(coll_name)
                        obj_count = stats.get('total_objects', 0) if stats else 0
                        collection_details.append({
                            'name': coll_name,
                            'objects': obj_count,
                            'status': 'Empty' if obj_count == 0 else f'{obj_count} objects'
                        })
                    except:
                        collection_details.append({
                            'name': coll_name,
                            'objects': 0,
                            'status': 'Unknown'
                        })
                
                # Select collection to delete
                collection_options = [f"{coll['name']} - {coll['status']}" for coll in collection_details]
                selected_display = st.selectbox(
                    "Select collection to delete:",
                    ["-- Select a collection --"] + collection_options,
                    key="selected_collection_to_delete"
                )
                
                if selected_display != "-- Select a collection --":
                    selected_coll = collection_details[collection_options.index(selected_display)]
                    
                    st.warning(f"⚠️ You are about to delete: **{selected_coll['name']}**")
                    st.write(f"- Type: Weaviate Collection")
                    st.write(f"- Status: {selected_coll['status']}")
                    st.write(f"- Objects: {selected_coll['objects']}")
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("🗑️ Delete Collection", type="primary", key="confirm_delete_weaviate"):
                            try:
                                wm.delete_collection(selected_coll['name'])
                                st.success(f"✅ Deleted {selected_coll['name']}")
                                st.info("🔄 Refresh the page to see updated list")
                                # Clear the flag after successful deletion
                                if 'show_collection_manager' in st.session_state:
                                    del st.session_state.show_collection_manager
                            except Exception as e:
                                st.error(f"❌ Error deleting collection: {e}")
                    
                    with col2:
                        if st.button("❌ Cancel", key="cancel_delete_weaviate"):
                            st.session_state.show_collection_manager = False
                            st.rerun()
            else:
                st.info("📭 No collections found")
                if st.button("Close", key="close_empty_collection_manager"):
                    st.session_state.show_collection_manager = False
                    st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error accessing Weaviate: {e}")
            if st.button("Close", key="close_error_collection_manager"):
                st.session_state.show_collection_manager = False
                st.rerun()
        
        st.markdown("---")
    
    if not collection_name:
        st.warning("⚠️ Please enter a collection name to proceed")
        return
    
    # Source type selection
    st.subheader("📥 Document Source")
    source_type = st.radio(
        "Select Source Type:",
        ["PDF File", "Text File", "Image File", "Website URL"],
        index=0,
        horizontal=True,
        key="weaviate_ingest_source_type",
        help="Choose the content source. 'Image File' uses OCR to extract text from images."
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
    
    if source_type in ["PDF File", "Text File", "Image File"]:
        if source_type == "PDF File":
            file_types = ["pdf"]
        elif source_type == "Text File":
            file_types = ["txt", "md", "csv"]
        else:  # Image File
            file_types = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"]
        
        uploaded_file = st.file_uploader(
            f"Choose {source_type}",
            type=file_types
        )
        
        # NEW: Document Quality Check (before ingestion)
        if uploaded_file is not None:
            st.markdown("---")
            st.subheader("📊 Document Quality Check")
            st.write(f"🔍 Analyzing: {uploaded_file.name}")
            
            # Extract text for preview
            preview_text = None
            ocr_metadata = None
            try:
                if source_type == "PDF File":
                    from utils.robust_pdf_extractor import extract_text_from_pdf_robust
                    pdf_bytes = uploaded_file.getvalue()
                    preview_text, method = extract_text_from_pdf_robust(pdf_bytes, uploaded_file.name)
                    st.info(f"📄 Extraction method: {method}")
                
                elif source_type == "Image File":
                    from utils.image_text_extractor import ImageTextExtractor
                    
                    # Show image preview (collapsed, reduced size)
                    image_bytes = uploaded_file.getvalue()
                    with st.expander("🖼️ View Image Preview", expanded=False):
                        st.image(image_bytes, caption=uploaded_file.name, width=400)
                    
                    # OCR extraction button
                    if st.button("🔍 Start OCR Extraction", key="weaviate_ocr_btn", type="primary"):
                        with st.spinner("🔍 Extracting text from image using OCR..."):
                            extractor = ImageTextExtractor(preferred_engine="tesseract")
                            # Sanitize filename
                            safe_filename = uploaded_file.name.encode('ascii', 'ignore').decode('ascii')
                            if not safe_filename:
                                safe_filename = "image_file"
                            preview_text, method, ocr_metadata = extractor.extract_text_from_image(image_bytes, safe_filename)
                        
                        # Store in session state
                        st.session_state['weaviate_ocr_text'] = preview_text
                        st.session_state['weaviate_ocr_metadata'] = ocr_metadata
                        st.session_state['weaviate_ocr_method'] = method
                        
                        # Show OCR info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.info(f"📸 OCR method: {method}")
                        with col2:
                            st.info(f"🎯 Confidence: {ocr_metadata.get('confidence', 0):.1f}%")
                        with col3:
                            st.info(f"📝 Words: {ocr_metadata.get('word_count', 0)}")
                    
                    # Retrieve from session state if available
                    if 'weaviate_ocr_text' in st.session_state:
                        preview_text = st.session_state['weaviate_ocr_text']
                        ocr_metadata = st.session_state.get('weaviate_ocr_metadata', {})
                        
                        # Show stored OCR info
                        if preview_text:
                            st.success("✅ OCR extraction completed")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.caption(f"📸 Method: {st.session_state.get('weaviate_ocr_method', 'N/A')}")
                            with col2:
                                st.caption(f"🎯 Confidence: {ocr_metadata.get('confidence', 0):.1f}%")
                            with col3:
                                st.caption(f"📝 Words: {ocr_metadata.get('word_count', 0)}")
                    else:
                        preview_text = None
                        ocr_metadata = None
                
                else:  # Text File
                    try:
                        preview_text = uploaded_file.getvalue().decode("utf-8")
                    except UnicodeDecodeError:
                        preview_text = uploaded_file.getvalue().decode("latin-1")
                
                # Run quality check
                if preview_text:
                    from utils.document_quality_checker import check_document_quality, clean_document, get_quality_emoji, get_quality_label
                    
                    with st.spinner("🔍 Analyzing document quality..."):
                        quality_result = check_document_quality(preview_text)
                    
                    quality_score = quality_result['quality_score']
                    emoji = get_quality_emoji(quality_score)
                    label = get_quality_label(quality_score)
                    
                    # Display quality score
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Quality Score", f"{quality_score:.2f}", delta=label)
                    with col2:
                        st.metric("Issues Found", len(quality_result['issues']))
                    with col3:
                        st.metric("Total Words", f"{quality_result['stats']['total_words']:,}")
                    
                    # Show issues if any
                    if quality_result['issues']:
                        with st.expander(f"⚠️ View {len(quality_result['issues'])} Quality Issues"):
                            for issue in quality_result['issues']:
                                st.write(f"**{issue.description}**")
                                st.write(f"  - Severity: {issue.severity.title()}")
                                st.write(f"  - Count: {issue.count} occurrences")
                                if issue.examples:
                                    st.code(", ".join(issue.examples[:3]), language=None)
                                st.write("")
                    
                    # Store in session state for use during ingestion
                    if 'document_quality' not in st.session_state:
                        st.session_state.document_quality = {}
                    
                    # Initialize if not exists
                    if uploaded_file.name not in st.session_state.document_quality:
                        st.session_state.document_quality[uploaded_file.name] = {
                            'original_text': preview_text,
                            'quality_score': quality_score,
                            'should_clean': False,
                            'cleaned_text': None,
                            'new_score': None
                        }
                    
                    # Show cleaning options based on quality
                    if quality_score < 0.8:
                        st.warning(f"⚠️ Low quality detected ({quality_score:.2f}). Cleaning recommended before ingestion.")
                        default_choice = 0  # Default to "Clean"
                    else:
                        st.success(f"✅ Document quality is good ({quality_score:.2f})")
                        st.info("💡 You can still choose to clean the document if needed")
                        default_choice = 1  # Default to "Use Original"
                    
                    # ALWAYS show radio buttons - let user choose
                    st.subheader("Choose Version for Ingestion:")
                    choice = st.radio(
                        "Select which version to use:",
                        ["✨ Clean Document", "➡️ Use Original Document"],
                        index=default_choice,
                        key=f"quality_choice_{uploaded_file.name}",
                        help="Clean version will fix spacing, OCR errors, and repeated characters"
                    )
                    
                    # Process based on choice
                    if choice == "✨ Clean Document":
                        # Check if we already cleaned it
                        if st.session_state.document_quality[uploaded_file.name].get('cleaned_text') is None:
                            with st.spinner("🧹 Cleaning document..."):
                                cleaned_text, changes = clean_document(preview_text, aggressive=False)
                            
                            # Show changes
                            st.success("✅ Document cleaned successfully!")
                            
                            change_col1, change_col2, change_col3 = st.columns(3)
                            with change_col1:
                                st.metric("Spaces Added", changes['spaces_added'])
                            with change_col2:
                                st.metric("Repeated Removed", changes['repeated_chars_removed'])
                            with change_col3:
                                st.metric("Special Removed", changes['special_chars_removed'])
                            
                            # Re-check quality
                            new_result = check_document_quality(cleaned_text)
                            new_score = new_result['quality_score']
                            improvement = new_score - quality_score
                            
                            st.metric("New Quality Score", f"{new_score:.2f}", delta=f"+{improvement:.2f}")
                            
                            # Store cleaned version
                            st.session_state.document_quality[uploaded_file.name]['cleaned_text'] = cleaned_text
                            st.session_state.document_quality[uploaded_file.name]['new_score'] = new_score
                        else:
                            # Already cleaned, show stored results
                            st.success("✅ Using previously cleaned version")
                            new_score = st.session_state.document_quality[uploaded_file.name]['new_score']
                            improvement = new_score - quality_score
                            st.metric("Quality Score", f"{new_score:.2f}", delta=f"+{improvement:.2f}")
                        
                        st.session_state.document_quality[uploaded_file.name]['should_clean'] = True
                        st.info("✅ Cleaned version will be used for ingestion")
                    
                    else:  # Use Original
                        st.session_state.document_quality[uploaded_file.name]['should_clean'] = False
                        st.info("ℹ️ Original version will be used for ingestion")
                        
            except Exception as e:
                st.warning(f"⚠️ Quality check unavailable: {str(e)}")
                logger.warning(f"Quality check failed: {e}")
            
            st.markdown("---")
    
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
    
    col1, col2 = st.columns([3, 1])
    with col1:
        index_name = st.text_input(
            "Index Name",
            value="document_index",
            help="Enter a name for your FAISS index"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🗑️ Manage Indexes", key="manage_faiss_indexes", help="Delete or clear existing indexes"):
            st.session_state.show_index_manager = True
    
    if not index_name.strip():
        index_name = "document_index"
        st.info("Using default index name: document_index")
    
    # Index Management UI
    if st.session_state.get('show_index_manager', False):
        st.markdown("---")
        st.subheader("🗑️ Index Management")
        
        # Get list of existing indexes
        index_base_dir = "data/indexes"
        faiss_base_dir = "data/faiss_index"
        
        all_indexes = []
        
        # Scan for indexes
        for base_dir in [index_base_dir, faiss_base_dir]:
            if os.path.exists(base_dir):
                for item in os.listdir(base_dir):
                    item_path = os.path.join(base_dir, item)
                    if os.path.isdir(item_path):
                        file_count = sum(1 for _ in Path(item_path).rglob('*') if _.is_file())
                        all_indexes.append({
                            'name': item,
                            'path': item_path,
                            'type': 'FAISS' if 'faiss' in base_dir else 'Text',
                            'files': file_count,
                            'status': 'Empty' if file_count == 0 else f'{file_count} files'
                        })
        
        if all_indexes:
            st.info(f"📊 Found {len(all_indexes)} indexes")
            
            # Select index to delete
            index_options = [f"{idx['name']} ({idx['type']}) - {idx['status']}" for idx in all_indexes]
            selected_display = st.selectbox(
                "Select index to delete:",
                ["-- Select an index --"] + index_options,
                key="selected_index_to_delete"
            )
            
            if selected_display != "-- Select an index --":
                selected_idx = all_indexes[index_options.index(selected_display)]
                
                st.warning(f"⚠️ You are about to delete: **{selected_idx['name']}**")
                st.write(f"- Type: {selected_idx['type']}")
                st.write(f"- Status: {selected_idx['status']}")
                st.write(f"- Path: `{selected_idx['path']}`")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("🗑️ Delete Index", type="primary", key="confirm_delete"):
                        try:
                            import shutil
                            shutil.rmtree(selected_idx['path'])
                            st.success(f"✅ Deleted {selected_idx['name']}")
                            st.info("🔄 Refresh the page to see updated list")
                            # Clear the flag after successful deletion
                            if 'show_index_manager' in st.session_state:
                                del st.session_state.show_index_manager
                        except Exception as e:
                            st.error(f"❌ Error deleting index: {e}")
                
                with col2:
                    if st.button("❌ Cancel", key="cancel_delete"):
                        st.session_state.show_index_manager = False
                        st.rerun()
        else:
            st.info("📭 No indexes found")
            if st.button("Close", key="close_empty_manager"):
                st.session_state.show_index_manager = False
                st.rerun()
        
        st.markdown("---")
    
    # Source type selection
    st.subheader("📥 Document Source")
    source_type = st.radio(
        "Select Source Type:",
        ["PDF File", "Text File", "Image File", "Website URL"],
        index=0,
        horizontal=True,
        key="faiss_ingest_source_type",
        help="Choose the content source. 'Image File' uses OCR to extract text from images."
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
    
    if source_type in ["PDF File", "Text File", "Image File"]:
        if source_type == "PDF File":
            file_types = ["pdf"]
        elif source_type == "Text File":
            file_types = ["txt", "md", "csv"]
        else:  # Image File
            file_types = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"]
        
        uploaded_file = st.file_uploader(
            f"Choose {source_type}",
            type=file_types
        )
        
        # NEW: Document Quality Check (before ingestion) - FAISS version
        if uploaded_file is not None:
            st.markdown("---")
            st.subheader("📊 Document Quality Check")
            st.write(f"🔍 Analyzing: {uploaded_file.name}")
            
            # Extract text for preview
            preview_text = None
            ocr_metadata = None
            try:
                if source_type == "PDF File":
                    from utils.robust_pdf_extractor import extract_text_from_pdf_robust
                    pdf_bytes = uploaded_file.getvalue()
                    preview_text, method = extract_text_from_pdf_robust(pdf_bytes, uploaded_file.name)
                    st.info(f"📄 Extraction method: {method}")
                
                elif source_type == "Image File":
                    from utils.image_text_extractor import ImageTextExtractor
                    
                    # Show image preview (collapsed, reduced size)
                    image_bytes = uploaded_file.getvalue()
                    with st.expander("🖼️ View Image Preview", expanded=False):
                        st.image(image_bytes, caption=uploaded_file.name, width=400)
                    
                    # OCR extraction button
                    if st.button("🔍 Start OCR Extraction", key="faiss_ocr_btn", type="primary"):
                        with st.spinner("🔍 Extracting text from image using OCR..."):
                            extractor = ImageTextExtractor(preferred_engine="tesseract")
                            # Sanitize filename
                            safe_filename = uploaded_file.name.encode('ascii', 'ignore').decode('ascii')
                            if not safe_filename:
                                safe_filename = "image_file"
                            preview_text, method, ocr_metadata = extractor.extract_text_from_image(image_bytes, safe_filename)
                        
                        # Store in session state
                        st.session_state['faiss_ocr_text'] = preview_text
                        st.session_state['faiss_ocr_metadata'] = ocr_metadata
                        st.session_state['faiss_ocr_method'] = method
                        
                        # Show OCR info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.info(f"📸 OCR method: {method}")
                        with col2:
                            st.info(f"🎯 Confidence: {ocr_metadata.get('confidence', 0):.1f}%")
                        with col3:
                            st.info(f"📝 Words: {ocr_metadata.get('word_count', 0)}")
                    
                    # Retrieve from session state if available
                    if 'faiss_ocr_text' in st.session_state:
                        preview_text = st.session_state['faiss_ocr_text']
                        ocr_metadata = st.session_state.get('faiss_ocr_metadata', {})
                        
                        # Show stored OCR info
                        if preview_text:
                            st.success("✅ OCR extraction completed")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.caption(f"📸 Method: {st.session_state.get('faiss_ocr_method', 'N/A')}")
                            with col2:
                                st.caption(f"🎯 Confidence: {ocr_metadata.get('confidence', 0):.1f}%")
                            with col3:
                                st.caption(f"📝 Words: {ocr_metadata.get('word_count', 0)}")
                    else:
                        preview_text = None
                        ocr_metadata = None
                
                else:  # Text File
                    try:
                        preview_text = uploaded_file.getvalue().decode("utf-8")
                    except UnicodeDecodeError:
                        preview_text = uploaded_file.getvalue().decode("latin-1")
                
                # Run quality check
                if preview_text:
                    from utils.document_quality_checker import check_document_quality, clean_document, get_quality_emoji, get_quality_label
                    
                    with st.spinner("🔍 Analyzing document quality..."):
                        quality_result = check_document_quality(preview_text)
                    
                    quality_score = quality_result['quality_score']
                    emoji = get_quality_emoji(quality_score)
                    label = get_quality_label(quality_score)
                    
                    # Display quality score
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Quality Score", f"{quality_score:.2f}", delta=label)
                    with col2:
                        st.metric("Issues Found", len(quality_result['issues']))
                    with col3:
                        st.metric("Total Words", f"{quality_result['stats']['total_words']:,}")
                    
                    # Show issues if any
                    if quality_result['issues']:
                        with st.expander(f"⚠️ View {len(quality_result['issues'])} Quality Issues"):
                            for issue in quality_result['issues']:
                                st.write(f"**{issue.description}**")
                                st.write(f"  - Severity: {issue.severity.title()}")
                                st.write(f"  - Count: {issue.count} occurrences")
                                if issue.examples:
                                    st.code(", ".join(issue.examples[:3]), language=None)
                                st.write("")
                    
                    # Store in session state for use during ingestion
                    if 'document_quality_faiss' not in st.session_state:
                        st.session_state.document_quality_faiss = {}
                    
                    # Initialize if not exists
                    if uploaded_file.name not in st.session_state.document_quality_faiss:
                        st.session_state.document_quality_faiss[uploaded_file.name] = {
                            'original_text': preview_text,
                            'quality_score': quality_score,
                            'should_clean': False,
                            'cleaned_text': None,
                            'new_score': None
                        }
                    
                    # Show cleaning options based on quality
                    if quality_score < 0.8:
                        st.warning(f"⚠️ Low quality detected ({quality_score:.2f}). Cleaning recommended before ingestion.")
                        default_choice = 0  # Default to "Clean"
                    else:
                        st.success(f"✅ Document quality is good ({quality_score:.2f})")
                        st.info("💡 You can still choose to clean the document if needed")
                        default_choice = 1  # Default to "Use Original"
                    
                    # ALWAYS show radio buttons - let user choose
                    st.subheader("Choose Version for Ingestion:")
                    choice = st.radio(
                        "Select which version to use:",
                        ["✨ Clean Document", "➡️ Use Original Document"],
                        index=default_choice,
                        key=f"quality_choice_faiss_{uploaded_file.name}",
                        help="Clean version will fix spacing, OCR errors, and repeated characters"
                    )
                    
                    # Process based on choice
                    if choice == "✨ Clean Document":
                        # Check if we already cleaned it
                        if st.session_state.document_quality_faiss[uploaded_file.name].get('cleaned_text') is None:
                            with st.spinner("🧹 Cleaning document..."):
                                cleaned_text, changes = clean_document(preview_text, aggressive=False)
                            
                            # Show changes
                            st.success("✅ Document cleaned successfully!")
                            
                            change_col1, change_col2, change_col3 = st.columns(3)
                            with change_col1:
                                st.metric("Spaces Added", changes['spaces_added'])
                            with change_col2:
                                st.metric("Repeated Removed", changes['repeated_chars_removed'])
                            with change_col3:
                                st.metric("Special Removed", changes['special_chars_removed'])
                            
                            # Re-check quality
                            new_result = check_document_quality(cleaned_text)
                            new_score = new_result['quality_score']
                            improvement = new_score - quality_score
                            
                            st.metric("New Quality Score", f"{new_score:.2f}", delta=f"+{improvement:.2f}")
                            
                            # Store cleaned version
                            st.session_state.document_quality_faiss[uploaded_file.name]['cleaned_text'] = cleaned_text
                            st.session_state.document_quality_faiss[uploaded_file.name]['new_score'] = new_score
                        else:
                            # Already cleaned, show stored results
                            st.success("✅ Using previously cleaned version")
                            new_score = st.session_state.document_quality_faiss[uploaded_file.name]['new_score']
                            improvement = new_score - quality_score
                            st.metric("Quality Score", f"{new_score:.2f}", delta=f"+{improvement:.2f}")
                        
                        st.session_state.document_quality_faiss[uploaded_file.name]['should_clean'] = True
                        st.info("✅ Cleaned version will be used for ingestion")
                    
                    else:  # Use Original
                        st.session_state.document_quality_faiss[uploaded_file.name]['should_clean'] = False
                        st.info("ℹ️ Original version will be used for ingestion")
                        
            except Exception as e:
                st.warning(f"⚠️ Quality check unavailable: {str(e)}")
                logger.warning(f"Quality check failed: {e}")
            
            st.markdown("---")
    
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
                # Validate optional dependencies needed for FAISS ingestion
                if not SENTENCE_TRANSFORMERS_AVAILABLE:
                    raise RuntimeError("SentenceTransformers not installed. Install with: pip install sentence-transformers")
                if not FAISS_AVAILABLE:
                    raise RuntimeError("FAISS is not installed. Install with: pip install faiss-cpu (Windows/macOS) or use conda on some platforms")
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
                page_count = None  # will be set for PDFs if available
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
                        # Try to count PDF pages if library is available
                        if PDF_READER_AVAILABLE:
                            try:
                                reader = PdfReader(io.BytesIO(pdf_bytes))
                                page_count = len(reader.pages)
                            except Exception:
                                page_count = None
                        text_content, method = extract_text_from_pdf_robust(pdf_bytes, uploaded_file.name)
                        
                        if text_content:
                            is_valid, quality, message = validate_extraction_quality(text_content, min_quality=0.5)
                            st.info(f"📄 Extraction: {method} | Quality: {quality:.2f}")
                            if not is_valid:
                                st.warning(f"⚠️ {message}")
                            
                            # NEW: Document Quality Check and Cleaning
                            try:
                                from utils.document_quality_checker import check_document_quality, clean_document, get_quality_emoji, get_quality_label
                                
                                status_text.text("🔍 Analyzing document quality...")
                                quality_result = check_document_quality(text_content)
                                quality_score = quality_result['quality_score']
                                
                                # Display quality score
                                emoji = get_quality_emoji(quality_score)
                                label = get_quality_label(quality_score)
                                st.info(f"{emoji} Document Quality: {quality_score:.2f} ({label})")
                                
                                # Show issues if any
                                if quality_result['issues']:
                                    with st.expander(f"⚠️ {len(quality_result['issues'])} Quality Issues Detected"):
                                        for issue in quality_result['issues'][:3]:  # Show top 3
                                            st.write(f"• {issue.description} ({issue.count} occurrences)")
                                
                                # Auto-clean if quality is low
                                if quality_score < 0.8:
                                    st.warning(f"⚠️ Low quality detected ({quality_score:.2f}). Cleaning recommended.")
                                    
                                    # Show cleaning option
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("✨ Clean Document", key=f"clean_{uploaded_file.name}"):
                                            status_text.text("🧹 Cleaning document...")
                                            cleaned_text, changes = clean_document(text_content, aggressive=False)
                                            
                                            # Show changes
                                            st.success(f"✅ Cleaned! Spaces added: {changes['spaces_added']}, Repeated chars removed: {changes['repeated_chars_removed']}")
                                            
                                            # Re-check quality
                                            new_result = check_document_quality(cleaned_text)
                                            new_score = new_result['quality_score']
                                            improvement = new_score - quality_score
                                            st.metric("New Quality Score", f"{new_score:.2f}", delta=f"+{improvement:.2f}")
                                            
                                            # Use cleaned text
                                            text_content = cleaned_text
                                    
                                    with col2:
                                        if st.button("➡️ Use Original", key=f"original_{uploaded_file.name}"):
                                            st.info("Using original document")
                                
                            except Exception as e:
                                logger.warning(f"Quality check failed: {e}")
                                st.warning(f"⚠️ Quality check unavailable: {e}")
                        
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
                    
                    # NEW: Document Quality Check and Cleaning for text files
                    try:
                        from utils.document_quality_checker import check_document_quality, clean_document, get_quality_emoji, get_quality_label
                        
                        status_text.text("🔍 Analyzing document quality...")
                        quality_result = check_document_quality(text_content)
                        quality_score = quality_result['quality_score']
                        
                        # Display quality score
                        emoji = get_quality_emoji(quality_score)
                        label = get_quality_label(quality_score)
                        st.info(f"{emoji} Document Quality: {quality_score:.2f} ({label})")
                        
                        # Show issues if any
                        if quality_result['issues']:
                            with st.expander(f"⚠️ {len(quality_result['issues'])} Quality Issues Detected"):
                                for issue in quality_result['issues'][:3]:
                                    st.write(f"• {issue.description} ({issue.count} occurrences)")
                        
                        # Auto-clean if quality is low
                        if quality_score < 0.8:
                            st.warning(f"⚠️ Low quality detected ({quality_score:.2f}). Cleaning recommended.")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✨ Clean Document", key=f"clean_txt_{uploaded_file.name}"):
                                    status_text.text("🧹 Cleaning document...")
                                    cleaned_text, changes = clean_document(text_content, aggressive=False)
                                    
                                    st.success(f"✅ Cleaned! Spaces added: {changes['spaces_added']}, Repeated chars removed: {changes['repeated_chars_removed']}")
                                    
                                    # Re-check quality
                                    new_result = check_document_quality(cleaned_text)
                                    new_score = new_result['quality_score']
                                    improvement = new_score - quality_score
                                    st.metric("New Quality Score", f"{new_score:.2f}", delta=f"+{improvement:.2f}")
                                    
                                    text_content = cleaned_text
                            
                            with col2:
                                if st.button("➡️ Use Original", key=f"original_txt_{uploaded_file.name}"):
                                    st.info("Using original document")
                    
                    except Exception as e:
                        logger.warning(f"Quality check failed: {e}")
                        st.warning(f"⚠️ Quality check unavailable: {e}")
                    
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
                    
                    # Try to fetch content from URL
                    try:
                        import requests
                        from bs4 import BeautifulSoup
                        
                        resp = requests.get(url_input, timeout=15)
                        resp.raise_for_status()
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        text = soup.get_text(separator='\n', strip=True) or ""
                        
                        # Save raw HTML and extracted text
                        with open(index_dir / "raw_html.html", "w", encoding="utf-8") as f:
                            f.write(str(soup))
                        with open(index_dir / "extracted_content.txt", "w", encoding="utf-8") as f:
                            f.write(text)
                        with open(index_dir / "extracted_text.txt", "w", encoding="utf-8") as f:
                            f.write(text)
                        
                        # Create chunk files for reference (limit to 10)
                        step = max(1, chunk_size - chunk_overlap)
                        chunk_count = 0
                        for i in range(0, len(text), step):
                            if chunk_count >= 10:
                                break
                            chunk = text[i:i+chunk_size]
                            if not chunk:
                                break
                            with open(index_dir / f"chunk_{chunk_count+1}.txt", "w", encoding="utf-8") as f:
                                f.write(chunk)
                            chunk_count += 1
                    except Exception as e:
                        st.warning(f"Error fetching URL content: {e}")
                        # Fallback minimal content
                        with open(index_dir / "extracted_content.txt", "w", encoding="utf-8") as f:
                            f.write(f"Website content placeholder for {url_input}")
                
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
                # Compute ingestion metrics
                total_chunks = len(chunks)
                total_chars = len(text_to_embed)
                approx_tokens = total_chars // 4  # rough heuristic
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
                **Pages (PDF):** {page_count if page_count is not None else 'N/A'}
                **Chunks Created:** {total_chunks}
                **Characters:** {total_chars}
                **~Tokens (est.):** {approx_tokens}
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
