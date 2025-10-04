"""
Multi-Vector Document Ingestion Tab
Enhanced document ingestion with multi-vector storage support
"""

import streamlit as st
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from datetime import datetime
import re
import io
import os
import sys
import importlib
try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError as _PkgNotFound
except Exception:  # pragma: no cover
    _pkg_version = None
    class _PkgNotFound(Exception):
        pass

from utils.multi_vector_storage_manager import get_multi_vector_manager
from utils.multi_vector_storage_interface import VectorStoreType, VectorStoreFactory
from utils.multi_vector_ui_components import (
    render_vector_store_selector, render_collection_selector, 
    render_vector_store_status, render_collection_stats
)
from utils.cache_manager import full_cache_reset

# Import existing ingestion utilities
try:
    from utils.document_processor import DocumentProcessor
    from utils.embedding_generator import EmbeddingGenerator
    INGESTION_AVAILABLE = True
except ImportError:
    INGESTION_AVAILABLE = False

logger = logging.getLogger(__name__)

# Optional simple Pinecone client availability (v4 API)
try:
    from pinecone import Pinecone as _PineconeClient, ServerlessSpec as _ServerlessSpec  # type: ignore
    PINECONE_SIMPLE_AVAILABLE = True
except Exception:
    _PineconeClient = None  # type: ignore
    _ServerlessSpec = None  # type: ignore
    PINECONE_SIMPLE_AVAILABLE = False

def render_multi_vector_document_ingestion():
    """Render the multi-vector document ingestion interface"""
    
    # Ensure VectorStoreType is available in function scope
    from utils.multi_vector_storage_interface import VectorStoreType
    
    st.title("📚 Multi-Vector Document Ingestion")
    st.markdown("Ingest documents into multiple vector storage backends with unified management.")
    
    # Vector store status
    with st.expander("Vector Store Status", expanded=True):
        # Add cache reset and debug buttons
        col_status, col_reset, col_debug = st.columns([3, 1, 1])
        with col_reset:
            if st.button("🔄 Reset Cache", key="reset_cache_btn", help="Clear cache and reload configuration"):
                with st.spinner("Resetting cache..."):
                    if full_cache_reset():
                        st.success("Cache reset successful!")
                        st.rerun()
                    else:
                        st.error("Cache reset failed. Check logs.")
        
        with col_debug:
            if st.button("🔍 Debug", key="debug_btn", help="Show detailed manager state"):
                with st.expander("Manager Debug Info", expanded=True):
                    try:
                        manager = get_multi_vector_manager()
                        stores = manager.get_available_stores()
                        
                        st.write("**Raw Manager Data:**")
                        for store in stores:
                            if store['type'] == 'pinecone':
                                st.json({
                                    'type': store['type'],
                                    'connected': store['connected'],
                                    'is_fallback': store['is_fallback'],
                                    'collection_count': store['collection_count'],
                                    'error': store['error'],
                                    'key': store.get('key', 'N/A')
                                })
                                
                                # Test direct connection
                                pinecone_store = manager.get_store_by_type(VectorStoreType.PINECONE)
                                if pinecone_store:
                                    direct_test = pinecone_store.connect_sync()
                                    st.write(f"**Direct Connection Test:** {'✅ SUCCESS' if direct_test else '❌ FAILED'}")
                                    
                                    # Environment diagnostics
                                    st.markdown("**Runtime Diagnostics:**")
                                    st.write(f"- Python executable: {sys.executable}")
                                    # Pinecone import availability
                                    pinecone_spec = importlib.util.find_spec("pinecone")
                                    st.write(f"- pinecone importable: {bool(pinecone_spec)}")
                                    if pinecone_spec:
                                        try:
                                            import pinecone  # type: ignore
                                            pc_ver = getattr(pinecone, "__version__", "unknown")
                                            st.write(f"- pinecone module version: {pc_ver}")
                                        except Exception as _e:
                                            st.write(f"- pinecone import error: {_e}")
                                    # Package version via metadata
                                    if _pkg_version is not None:
                                        try:
                                            st.write(f"- pinecone-client dist version: {_pkg_version('pinecone-client')}")
                                        except _PkgNotFound:
                                            st.write("- pinecone-client dist not found")
                                    # Registered adapters
                                    try:
                                        registered = [t.value for t in VectorStoreFactory.get_available_types()]
                                        st.write(f"- Registered adapters: {registered}")
                                    except Exception as _e:
                                        st.write(f"- Could not list registered adapters: {_e}")
                                    
                                    # Test collection creation
                                    st.write("**Testing Collection Creation:**")
                                    try:
                                        test_result = manager.create_collection_sync("debug-test-collection", VectorStoreType.PINECONE)
                                        st.write(f"Create test result: {'✅ SUCCESS' if test_result else '❌ FAILED'}")
                                        if test_result:
                                            # Clean up
                                            manager.delete_collection_sync("debug-test-collection", VectorStoreType.PINECONE)
                                            st.write("✅ Cleaned up test collection")
                                    except Exception as create_e:
                                        st.error(f"Collection creation test failed: {create_e}")
                                        st.code(str(create_e))
                                break
                    except Exception as e:
                        st.error(f"Debug failed: {e}")
        
        with col_status:
            render_vector_store_status(key_prefix="ingest_status")
    
    # Index/Collection Management Section (Always visible)
    with st.expander("🗑️ Delete Collections/Indexes", expanded=False):
        st.subheader("Delete Existing Collections")
        
        # Get manager
        manager = get_multi_vector_manager()
        
        # Store selection for deletion
        delete_store = render_vector_store_selector(
            key="delete_store_selector",
            label="Select Vector Store",
            include_all_option=False
        )
        
        if delete_store:
            # Get collections for this store
            try:
                collections = manager.list_collections_sync(delete_store)
                if collections:
                    col_sel, col_btn = st.columns([3, 1])
                    with col_sel:
                        collection_to_delete = st.selectbox(
                            "Select collection to delete:",
                            options=collections,
                            key="delete_collection_selector"
                        )
                    with col_btn:
                        st.write("")  # Spacing
                        st.write("")  # Spacing
                        if st.button("🗑️ Delete", key="delete_collection_btn", type="secondary"):
                            if delete_collection_with_confirmation(collection_to_delete, delete_store):
                                st.success(f"✅ Deleted '{collection_to_delete}'")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to delete '{collection_to_delete}'")
                else:
                    st.info(f"No collections found in {delete_store.value}")
            except Exception as e:
                st.error(f"Error listing collections: {e}")
    
    # Main ingestion interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Document Upload & Processing")
        
        # File upload
        uploaded_files = st.file_uploader(
            "Choose documents to ingest",
            type=['pdf', 'txt', 'docx', 'md', 'json', 'csv'],
            accept_multiple_files=True,
            help="Upload documents in supported formats"
        )
        
        # Processing options
        st.subheader("Processing Options")
        
        chunk_size = st.slider(
            "Chunk Size",
            min_value=500,
            max_value=3000,
            value=1500,
            step=100,
            help="Size of text chunks for embedding"
        )
        
        chunk_overlap = st.slider(
            "Chunk Overlap",
            min_value=0,
            max_value=1000,
            value=500,
            step=50,
            help="Overlap between consecutive chunks"
        )
        
        preserve_structure = st.checkbox(
            "Preserve Document Structure",
            value=True,
            help="Maintain headings and section boundaries"
        )
        
        extract_tables = st.checkbox(
            "Extract Tables",
            value=True,
            help="Extract and process tabular data"
        )
    
    with col2:
        st.subheader("Vector Store Configuration")
        
        # Vector store selection
        selected_store = render_vector_store_selector(
            key="ingestion_store_selector",
            label="Target Vector Store",
            include_all_option=False
        )
        
        if selected_store:
            # Collection selection
            collection_name, is_new = render_collection_selector(
                store_type=selected_store,
                key="ingestion_collection_selector",
                label="Target Collection",
                allow_new=True
            )
            # Sanitize collection names for different stores
            if is_new and collection_name:
                if selected_store == VectorStoreType.AWS_OPENSEARCH:
                    original_name = collection_name
                    sanitized = sanitize_opensearch_index_name(original_name)
                    if sanitized != original_name:
                        st.info(f"OpenSearch index names must be lowercase and use only letters, numbers, '-' or '_'. Using sanitized name: {sanitized}")
                        collection_name = sanitized
                elif selected_store == VectorStoreType.PINECONE:
                    # Pinecone naming rules: lowercase letters, numbers, hyphens only
                    original_name = collection_name
                    import re
                    # Convert to lowercase and replace invalid chars with hyphens
                    sanitized = re.sub(r'[^a-z0-9-]', '-', original_name.lower())
                    # Remove leading/trailing hyphens and multiple consecutive hyphens
                    sanitized = re.sub(r'^-+|-+$', '', sanitized)
                    sanitized = re.sub(r'-+', '-', sanitized)
                    # Ensure length is within limits
                    if len(sanitized) > 45:
                        sanitized = sanitized[:45].rstrip('-')
                    if len(sanitized) < 1:
                        sanitized = "collection"
                    
                    if sanitized != original_name:
                        st.info(f"Pinecone index names must be lowercase letters, numbers, and hyphens only. Using sanitized name: {sanitized}")
                        collection_name = sanitized

            if collection_name and not is_new:
                # Show collection stats and delete option
                with st.expander("Collection Management"):
                    render_collection_stats(collection_name, selected_store)
                    
                    st.markdown("---")
                    st.subheader("⚠️ Danger Zone")
                    
                    col_del1, col_del2 = st.columns([2, 1])
                    with col_del1:
                        st.warning(f"Delete collection '{collection_name}' from {selected_store.value}?")
                    with col_del2:
                        if st.button("🗑️ Delete Collection", key=f"delete_{collection_name}", type="secondary"):
                            if delete_collection_with_confirmation(collection_name, selected_store):
                                st.success(f"✅ Deleted '{collection_name}'")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to delete '{collection_name}'")

            # Pinecone-specific tools integrated here
            use_direct_pinecone = False
            if selected_store == VectorStoreType.PINECONE:
                with st.expander("Pinecone Tools", expanded=False):
                    if not PINECONE_SIMPLE_AVAILABLE:
                        st.warning("Pinecone client not importable in this environment. Install pinecone-client==4.1.2 and restart.")
                    else:
                        col_a, col_b = st.columns([1, 1])
                        with col_a:
                            if st.button("Test Pinecone Connection", key="pc_test_btn"):
                                try:
                                    api_key = os.getenv("PINECONE_API_KEY")
                                    if not api_key:
                                        st.error("PINECONE_API_KEY not set in environment")
                                    else:
                                        client = _PineconeClient(api_key=api_key)
                                        indexes = client.list_indexes()
                                        st.success(f"Connected to Pinecone: {len(indexes)} index(es)")
                                        # Show names if present
                                        names = []
                                        for idx in indexes:
                                            if hasattr(idx, 'name'):
                                                names.append(idx.name)
                                            elif isinstance(idx, dict) and 'name' in idx:
                                                names.append(idx['name'])
                                            elif isinstance(idx, str):
                                                names.append(idx)
                                        if names:
                                            st.caption(", ".join(names))
                                except Exception as e:
                                    st.error(f"Connection test failed: {e}")
                        with col_b:
                            use_direct_pinecone = st.checkbox(
                                "Use Direct Pinecone mode (bypass manager)",
                                value=False,
                                help="If enabled, ingestion will use the Pinecone SDK directly from this tab."
                            )
        
        # Ingestion options
        st.subheader("Ingestion Options")
        
        parallel_ingestion = st.checkbox(
            "Parallel Ingestion",
            value=False,
            help="Ingest to multiple stores simultaneously"
        )
        
        batch_size = st.number_input(
            "Batch Size",
            min_value=1,
            max_value=100,
            value=10,
            help="Number of documents to process in each batch"
        )
        
        embedding_model = st.selectbox(
            "Embedding Model",
            ["all-MiniLM-L6-v2", "all-mpnet-base-v2", "sentence-t5-base"],
            help="Model for generating embeddings"
        )
    
    # Ingestion execution
    st.subheader("Execute Ingestion")
    
    if uploaded_files and selected_store and collection_name:
        if st.button("Start Ingestion", type="primary"):
            # Use direct Pinecone path only when explicitly selected
            if selected_store == VectorStoreType.PINECONE and 'use_direct_pinecone' in locals() and use_direct_pinecone:
                execute_pinecone_simple_ingestion(
                    uploaded_files=uploaded_files,
                    collection_name=collection_name,
                    is_new_collection=is_new,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    embedding_model=embedding_model
                )
            else:
                execute_ingestion(
                    uploaded_files=uploaded_files,
                    store_type=selected_store,
                    collection_name=collection_name,
                    is_new_collection=is_new,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    preserve_structure=preserve_structure,
                    extract_tables=extract_tables,
                    parallel_ingestion=parallel_ingestion,
                    batch_size=batch_size,
                    embedding_model=embedding_model
                )
    else:
        missing_items = []
        if not uploaded_files:
            missing_items.append("documents")
        if not selected_store:
            missing_items.append("vector store")
        if not collection_name:
            missing_items.append("collection name")
        
        st.info(f"Please provide: {', '.join(missing_items)}")
    
    # Recent ingestions
    render_recent_ingestions()

def execute_ingestion(
    uploaded_files,
    store_type: VectorStoreType,
    collection_name: str,
    is_new_collection: bool,
    chunk_size: int,
    chunk_overlap: int,
    preserve_structure: bool,
    extract_tables: bool,
    parallel_ingestion: bool,
    batch_size: int,
    embedding_model: str
):
    """Execute the document ingestion process"""
    
    try:
        manager = get_multi_vector_manager()
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create collection if new
        if is_new_collection:
            status_text.text("Creating new collection...")
            
            # Debug: Check manager and store
            st.write(f"🔍 **Debug Info:**")
            st.write(f"- Collection name: '{collection_name}'")
            st.write(f"- Store type: {store_type.value}")
            
            # Check if manager can find the store
            pinecone_store = manager.get_store_by_type(store_type)
            st.write(f"- Store found: {bool(pinecone_store)}")
            if pinecone_store:
                st.write(f"- Store type: {type(pinecone_store).__name__}")
                st.write(f"- API key present: {bool(getattr(pinecone_store, 'api_key', None))}")
            
            try:
                # Create collection with retry logic
                success = False
                for attempt in range(5):
                    success = manager.create_collection_sync(
                        collection_name=collection_name,
                        store_type=store_type,
                        description=f"VaultMind collection created on {datetime.now().isoformat()}"
                    )
                    if success:
                        st.success(f"Created collection '{collection_name}'")
                        # Wait for collection to be ready
                        status_text.text(f"Waiting for '{collection_name}' to be ready... (attempt {attempt + 1})")
                        import time
                        time.sleep(3 + attempt * 2) # Exponential backoff
                        if manager.collection_exists_sync(collection_name, store_type):
                            st.success(f"Collection '{collection_name}' is ready!")
                            break
                        else:
                            st.warning(f"Collection not yet visible, retrying...")
                            success = False # Force loop to continue
                
                if not success:
                    st.error(f"Failed to create and verify collection '{collection_name}' after multiple attempts. Please check Weaviate logs.")
                    return
            except Exception as e:
                st.error(f"Exception creating collection '{collection_name}': {str(e)}")
                st.error(f"Error type: {type(e).__name__}")
                import traceback
                st.code(traceback.format_exc())
                return
        
        # Process documents
        total_files = len(uploaded_files)
        processed_docs = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing {uploaded_file.name}...")
            progress_bar.progress((i + 1) / total_files)
            
            # Read file content
            raw_bytes = uploaded_file.read()
            filename = uploaded_file.name
            ext = Path(filename).suffix.lower()
            content = None
            if ext == '.pdf':
                # Extract text from PDF bytes with quality validation
                text = extract_text_from_pdf_bytes(raw_bytes, filename)
                if not text or not text.strip():
                    st.warning(f"Could not extract text from {filename}, skipping...")
                    continue
                content = text
            else:
                # Try robust decoding for text-like files
                if isinstance(raw_bytes, bytes):
                    for enc in ('utf-8', 'utf-16', 'latin-1', 'cp1252'):
                        try:
                            content = raw_bytes.decode(enc)
                            break
                        except UnicodeDecodeError:
                            continue
                    if not content:
                        st.warning(f"Could not decode {filename}, skipping...")
                        continue
                else:
                    content = str(raw_bytes)
            
            # Process document
            doc_chunks = process_document(
                content=content,
                filename=filename,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_structure=preserve_structure,
                extract_tables=extract_tables
            )
            
            processed_docs.extend(doc_chunks)
        
        # Generate embeddings
        status_text.text("Generating embeddings...")
        embeddings = generate_embeddings(
            texts=[doc['content'] for doc in processed_docs],
            model_name=embedding_model
        )
        
        if not embeddings:
            st.error("Failed to generate embeddings")
            return
        
        # Ingest documents
        status_text.text("Ingesting documents...")
        # Use a more direct, synchronous method for ingestion
        store = manager.get_store_by_type(store_type)
        if not store or not store.adapter:
            st.error(f"Could not get a valid adapter for store type: {store_type.value}")
            return

        try:
            status_text.text(f"Uploading {len(processed_docs)} chunks to '{collection_name}'...")
            # Use the adapter's direct method
            if hasattr(store.adapter, 'add_documents'):
                add_result = store.adapter.add_documents(
                    collection_name=collection_name,
                    documents=processed_docs,
                    embeddings=embeddings
                )
                # Check result format
                if isinstance(add_result, dict):
                    success = add_result.get('success', False)
                    st.write("Ingestion Diagnostics:", add_result)
                else:
                    success = bool(add_result)
            else:
                st.error(f"The adapter for {store_type.value} does not have an 'add_documents' method.")
                success = False
        except Exception as e:
            st.error(f"An error occurred during document upload: {e}")
            logger.error(f"Upload error for {collection_name}: {e}", exc_info=True)
            success = False
        
        progress_bar.progress(1.0)
        
        if success:
            st.success(f"Successfully ingested {len(processed_docs)} document chunks into '{collection_name}'")
            
            # Update session state for recent ingestions
            if 'recent_ingestions' not in st.session_state:
                st.session_state.recent_ingestions = []
            
            st.session_state.recent_ingestions.insert(0, {
                'timestamp': datetime.now().isoformat(),
                'collection': collection_name,
                'store_type': store_type.value,
                'document_count': len(processed_docs),
                'files': [f.name for f in uploaded_files]
            })
            
            # Keep only last 10 ingestions
            st.session_state.recent_ingestions = st.session_state.recent_ingestions[:10]
            
        else:
            st.error("Failed to ingest documents")
        
        status_text.empty()
        
    except Exception as e:
        st.error(f"Ingestion failed: {e}")
        logger.error(f"Ingestion error: {e}", exc_info=True)
        
def execute_pinecone_simple_ingestion(
    uploaded_files,
    collection_name: str,
    is_new_collection: bool,
    chunk_size: int,
    chunk_overlap: int,
    embedding_model: str
):
    """Direct Pinecone ingestion path (bypasses manager).
    Uses pinecone-client v4 API. Creates index if needed with correct dimension.
    """
    try:
        if not PINECONE_SIMPLE_AVAILABLE:
            st.error("Pinecone SDK not available. Please install pinecone-client==4.1.2 and restart.")
            return

        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            st.error("PINECONE_API_KEY not set in environment (see config/storage.env)")
            return

        # Progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Process documents
        total_files = len(uploaded_files)
        processed_docs: List[Dict[str, Any]] = []
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing {uploaded_file.name}...")
            progress_bar.progress(min(0.15, 0.05 + (i + 1) / max(total_files, 1) * 0.1))

            raw_bytes = uploaded_file.read()
            filename = uploaded_file.name
            ext = Path(filename).suffix.lower()
            content: Optional[str] = None
            if ext == '.pdf':
                text = extract_text_from_pdf_bytes(raw_bytes)
                if not text or not text.strip():
                    st.warning(f"Could not extract text from {filename}, skipping...")
                    continue
                content = text
            else:
                if isinstance(raw_bytes, bytes):
                    for enc in ('utf-8', 'utf-16', 'latin-1', 'cp1252'):
                        try:
                            content = raw_bytes.decode(enc)
                            break
                        except UnicodeDecodeError:
                            continue
                if not content:
                    content = str(raw_bytes)

            # Convert to chunks / documents
            doc_chunks = process_document(
                content=content or "",
                filename=filename,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_structure=True,
                extract_tables=True
            )
            processed_docs.extend(doc_chunks)

        if not processed_docs:
            st.error("No document content to ingest")
            return

        # Generate embeddings
        status_text.text("Generating embeddings...")
        embeddings = generate_embeddings(
            texts=[doc['content'] for doc in processed_docs],
            model_name=embedding_model
        )
        if not embeddings:
            st.error("Failed to generate embeddings")
            return

        vector_dim = len(embeddings[0])

        # Connect to Pinecone
        status_text.text("Connecting to Pinecone...")
        client = _PineconeClient(api_key=api_key)

        # Ensure index exists (create if new or missing)
        status_text.text("Ensuring index exists...")
        existing = client.list_indexes()
        existing_names: List[str] = []
        for idx in existing:
            if hasattr(idx, 'name'):
                existing_names.append(idx.name)
            elif isinstance(idx, dict) and 'name' in idx:
                existing_names.append(idx['name'])
            elif isinstance(idx, str):
                existing_names.append(idx)

        if is_new_collection or collection_name not in existing_names:
            try:
                client.create_index(
                    name=collection_name,
                    dimension=vector_dim,
                    metric='cosine',
                    spec=_ServerlessSpec(cloud='aws', region='us-east-1') if _ServerlessSpec else None
                )
                # small wait is often needed for serverless index readiness
                import time
                time.sleep(5)
                st.success(f"Created Pinecone index: {collection_name} (dim={vector_dim})")
            except Exception as ce:
                # If index exists with a different dimension, report clearly
                st.error(f"Failed to create index '{collection_name}': {ce}")
                st.info("If the index already exists with a different dimension, use a new collection name.")
                return

        index = client.Index(collection_name)

        # Prepare vectors
        status_text.text("Uploading vectors to Pinecone...")
        vectors_to_upsert = []
        for i, (doc, emb) in enumerate(zip(processed_docs, embeddings)):
            vectors_to_upsert.append({
                "id": str(doc.get('id', f"doc_{i}_{datetime.now().timestamp()}")),
                "values": emb,
                "metadata": {
                    "content": doc.get('content', '')[:40000],
                    "source": doc.get('source', ''),
                    "source_type": doc.get('source_type', 'unknown'),
                    "chunk_index": doc.get('metadata', {}).get('chunk_index', i),
                    "total_chunks": doc.get('metadata', {}).get('total_chunks', len(processed_docs)),
                    "created_at": doc.get('created_at', datetime.now().isoformat())
                }
            })

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            index.upsert(vectors=batch)

        progress_bar.progress(1.0)
        status_text.text("Ingestion completed!")

        st.success(f"Successfully ingested {len(vectors_to_upsert)} chunks into Pinecone '{collection_name}'")

        # Track recent ingestions
        if 'recent_ingestions' not in st.session_state:
            st.session_state.recent_ingestions = []
        st.session_state.recent_ingestions.insert(0, {
            'timestamp': datetime.now().isoformat(),
            'collection': collection_name,
            'store_type': 'pinecone',
            'document_count': len(vectors_to_upsert),
            'files': [f.name for f in uploaded_files]
        })
        st.session_state.recent_ingestions = st.session_state.recent_ingestions[:10]

    except Exception as e:
        st.error(f"Direct Pinecone ingestion failed: {e}")
        logger.error(f"Direct Pinecone ingestion error: {e}", exc_info=True)

def sanitize_opensearch_index_name(name: str) -> str:
    """Sanitize a proposed collection name to a valid OpenSearch index name.
    Rules: lowercase; allowed chars [a-z0-9-_]; cannot start with '-', '_', or '+'; length <= 255; cannot be '.' or '..'.
    """
    try:
        s = (name or "").strip().lower()
        # Replace invalid characters with '-'
        s = re.sub(r"[^a-z0-9-_]", "-", s)
        # Remove leading invalid starters
        while s.startswith(('-', '_', '+')):
            s = s[1:]
        # Avoid reserved names
        if s in {".", "..", ""}:
            s = "collection"
        # Trim to 255 chars
        if len(s) > 255:
            s = s[:255]
        # Ensure not empty
        if not s:
            s = "collection"
        return s
    except Exception:
        return "collection"

def extract_text_from_pdf_bytes(data: bytes, filename: str = "document.pdf") -> str:
    """Extract text from PDF using robust multi-method extraction with quality validation."""
    try:
        from utils.robust_pdf_extractor import extract_text_from_pdf_robust, validate_extraction_quality
        
        text, method = extract_text_from_pdf_robust(data, filename)
        
        if text:
            # Validate quality
            is_valid, quality, message = validate_extraction_quality(text, min_quality=0.5)
            
            if is_valid:
                st.success(f"✅ PDF extracted successfully using {method} (quality: {quality:.2f})")
                return text
            else:
                st.warning(f"⚠️ PDF extraction quality is low: {message}")
                st.info("The text may have spacing or formatting issues. Consider using a different PDF or OCR.")
                return text  # Return anyway, but warn user
        else:
            st.error(f"❌ Failed to extract text from {filename}")
            return ""
            
    except ImportError:
        # Fallback to old method if robust extractor not available
        st.warning("Using legacy PDF extraction (may have quality issues)")
        return extract_text_from_pdf_bytes_legacy(data)

def process_document(
    content: str,
    filename: str,
    chunk_size: int,
    chunk_overlap: int,
    preserve_structure: bool,
    extract_tables: bool
) -> List[Dict[str, Any]]:
    """Process a document into chunks"""
    
    try:
        if INGESTION_AVAILABLE:
            # Use existing document processor if available
            processor = DocumentProcessor()
            chunks = processor.process_text(
                text=content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_structure=preserve_structure
            )
        else:
            # Simple fallback chunking
            chunks = simple_chunk_text(content, chunk_size, chunk_overlap)
        
        # Convert to document format
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                'id': f"{filename}_{i}",
                'content': chunk,
                'source': filename,
                'source_type': Path(filename).suffix.lower().lstrip('.') or 'txt',
                'created_at': datetime.now().isoformat(),
                'metadata': {
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'filename': filename,
                    'chunk_size': len(chunk)
                }
            }
            documents.append(doc)
        
        return documents
        
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        return []

def simple_chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Simple text chunking fallback"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > start + chunk_size // 2:
                chunk = text[start:start + break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - chunk_overlap
        
        if start >= len(text):
            break
    
    return [chunk for chunk in chunks if chunk.strip()]

def generate_embeddings(texts: List[str], model_name: str) -> List[List[float]]:
    """Generate embeddings for texts"""
    
    try:
        if INGESTION_AVAILABLE:
            # Use existing embedding generator if available
            generator = EmbeddingGenerator(model_name=model_name)
            return generator.generate_embeddings(texts)
        else:
            # Use interface utility function
            from utils.multi_vector_storage_interface import batch_embeddings
            return batch_embeddings(texts, model_name)
        
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        return []

def delete_collection_with_confirmation(collection_name: str, store_type: VectorStoreType) -> bool:
    """Delete a collection from the specified vector store"""
    try:
        manager = get_multi_vector_manager()
        success = manager.delete_collection_sync(collection_name, store_type)
        
        if success:
            logger.info(f"Deleted collection '{collection_name}' from {store_type.value}")
        else:
            logger.error(f"Failed to delete collection '{collection_name}' from {store_type.value}")
        
        return success
    except Exception as e:
        logger.error(f"Error deleting collection '{collection_name}': {e}")
        st.error(f"Exception: {str(e)}")
        return False

def render_recent_ingestions():
    """Render recent ingestion history"""
    
    st.subheader("Recent Ingestions")
    
    if 'recent_ingestions' not in st.session_state or not st.session_state.recent_ingestions:
        st.info("No recent ingestions")
        return
    
    for ingestion in st.session_state.recent_ingestions:
        with st.expander(f"{ingestion['collection']} - {ingestion['timestamp'][:19]}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Collection:** {ingestion['collection']}")
                st.write(f"**Store Type:** {ingestion['store_type']}")
                st.write(f"**Documents:** {ingestion['document_count']}")
            
            with col2:
                st.write("**Files:**")
                for filename in ingestion['files']:
                    st.write(f"- {filename}")

# Main function for tab integration
def main():
    """Main function for standalone testing"""
    render_multi_vector_document_ingestion()

if __name__ == "__main__":
    main()
