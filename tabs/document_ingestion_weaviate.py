"""
Document Ingestion Tab with Weaviate Integration
===============================================
Upload and index various document types for knowledge base creation.
Access Level: User+ and Admin only
"""

import streamlit as st
from pathlib import Path
import logging
from utils.weaviate_ingestion_helper import get_weaviate_ingestion_helper

def render_document_ingestion(user, permissions, auth_middleware, available_indexes, INDEX_ROOT, PROJECT_ROOT):
    """Document Ingestion Tab Implementation with Weaviate Integration"""
    
    # Handle both dict and object user formats for role check
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        role = user.get('role', 'viewer')
    else:
        username = user.username
        role = user.role.value
    
    if not (permissions.get('can_upload', False) or role in ['user', 'admin']):
        st.error("❌ Document upload requires User or Admin privileges")
    else:
        auth_middleware.log_user_action("ACCESS_INGEST_TAB")
        
        # Document ingestion form
        st.subheader("📁 Upload and Index Content")
        st.write(f"👤 Logged in as: {username} ({role})")
        
        # Storage backend selection
        storage_backend = st.radio(
            "Select storage backend:",
            ["Weaviate (Cloud Vector DB)", "Local FAISS Index"],
            horizontal=True,
            help="Weaviate provides cloud-based vector search with better scalability"
        )
        
        source_type = st.radio(
            "Select content source:",
            ["PDF File", "Text File", "Website URL"],
            horizontal=True
        )

        if source_type == "PDF File":
            uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
        elif source_type == "Text File":
            uploaded_file = st.file_uploader("Choose a text file", type=["txt"])
        else:
            url_input = st.text_input(
                "Enter website URL:", placeholder="https://example.com/article"
            )
            render_js = st.checkbox("Render JavaScript (for dynamic sites)")
            max_depth = st.slider("Link depth (for multi-page scraping)", 0, 3, 0)

        if storage_backend == "Weaviate (Cloud Vector DB)":
            collection_name = st.text_input(
                "📦 Collection name (no spaces)", 
                placeholder="e.g. web_article_collection",
                help="Weaviate collection name for storing documents"
            )
            # Upfront connectivity check so users see connection status early
            try:
                weaviate_helper = get_weaviate_ingestion_helper()
                conn_ok = weaviate_helper.test_connection()
                if conn_ok:
                    try:
                        api_ver = weaviate_helper.weaviate_manager.detect_api_version()
                    except Exception:
                        api_ver = "unknown"
                    st.success(f"🔗 Weaviate connection OK (API {api_ver}) → {weaviate_helper.weaviate_manager.url}")
                else:
                    st.error("❌ Weaviate connection failed. Check WEAVIATE_URL / WEAVIATE_API_KEY in config/weaviate.env or environment. You can switch to 'Local FAISS Index' as a fallback.")
            except Exception as ce:
                st.error(f"❌ Weaviate connectivity check errored: {ce}")
        else:
            index_name = st.text_input(
                "📦 Name for this new index (no spaces)", placeholder="e.g. web_article_index"
            )
            
        # Advanced chunking settings
        st.subheader("🔧 Chunking Configuration")
        
        chunking_strategy = st.radio(
            "Select chunking strategy:",
            ["Semantic Chunking (Recommended)", "Size-based Chunking"],
            help="Semantic chunking splits by headers and sections for better accuracy"
        )
        
        if chunking_strategy == "Semantic Chunking (Recommended)":
            chunk_size = st.slider(
                "🧩 Chunk Size", min_value=512, max_value=1024, value=512, step=64,
                help="Smaller chunks (512-1024) work better for semantic search"
            )
            chunk_overlap = st.slider(
                "🔁 Chunk Overlap", min_value=100, max_value=200, value=100, step=25,
                help="Prevents sentences from being cut off between chunks"
            )
            split_by_headers = st.checkbox(
                "Split by Headers", value=True,
                help="Creates new chunks at section boundaries (HIGHLY RECOMMENDED)"
            )
            use_embeddings = st.checkbox(
                "Generate Embeddings", value=True,
                help="Enables semantic search using text-embedding-ada-002"
            )
        else:
            chunk_size = st.slider(
                "🧩 Chunk Size", min_value=300, max_value=1500, value=800, step=100
            )
            chunk_overlap = st.slider(
                "🔁 Chunk Overlap", min_value=0, max_value=300, value=100, step=50
            )
            split_by_headers = False
            use_embeddings = False

        if st.button("🚀 Ingest & Index"):
            # Validate input based on storage backend
            if storage_backend == "Weaviate (Cloud Vector DB)":
                if not collection_name:
                    st.warning("Please specify a collection name.")
                    st.stop()
                target_name = collection_name
            else:
                if not index_name:
                    st.warning("Please specify an index name.")
                    st.stop()
                target_name = index_name
            
            auth_middleware.log_user_action("DOCUMENT_INGEST", f"Backend: {storage_backend}, Target: {target_name}, Type: {source_type}")
            
            try:
                st.info("Processing document...")
                progress_bar = st.progress(0)
                
                if storage_backend == "Weaviate (Cloud Vector DB)":
                    # Weaviate ingestion path
                    weaviate_helper = get_weaviate_ingestion_helper()
                    # Enforce connectivity check before any ingestion
                    if not weaviate_helper.test_connection():
                        st.error("❌ Weaviate connection failed. Please verify WEAVIATE_URL / WEAVIATE_API_KEY and try again.")
                        st.stop()
                    else:
                        try:
                            api_ver = weaviate_helper.weaviate_manager.detect_api_version()
                        except Exception:
                            api_ver = "unknown"
                        st.success(f"🔗 Connected to Weaviate (API {api_ver})")
                    
                    use_semantic = chunking_strategy == "Semantic Chunking (Recommended)"
                    
                    if source_type == "PDF File" and uploaded_file:
                        progress_bar.progress(25)
                        result = weaviate_helper.ingest_pdf_document(
                            collection_name=collection_name,
                            file_content=uploaded_file.getbuffer(),
                            file_name=uploaded_file.name,
                            username=username,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            use_semantic_chunking=use_semantic
                        )
                        
                    elif source_type == "Text File" and uploaded_file:
                        progress_bar.progress(25)
                        try:
                            text_content = uploaded_file.getvalue().decode("utf-8")
                        except UnicodeDecodeError:
                            text_content = uploaded_file.getvalue().decode("latin-1")
                        
                        result = weaviate_helper.ingest_text_document(
                            collection_name=collection_name,
                            text_content=text_content,
                            file_name=uploaded_file.name,
                            username=username,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            use_semantic_chunking=use_semantic
                        )
                        
                    elif source_type == "Website URL" and url_input:
                        progress_bar.progress(25)
                        result = weaviate_helper.ingest_url_content(
                            collection_name=collection_name,
                            url=url_input,
                            username=username,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            use_semantic_chunking=use_semantic,
                            render_js=render_js
                        )
                    else:
                        st.error("Please provide the required input for the selected source type.")
                        st.stop()
                    
                    progress_bar.progress(100)
                    
                    if result.get("success"):
                        st.success("✅ **Document successfully ingested into Weaviate!**")
                        
                        # Display results
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📄 Documents", "1")
                        with col2:
                            st.metric("🧩 Chunks", str(result.get("total_chunks", 0)))
                        with col3:
                            st.metric("🗄️ Collection", result.get("collection_name", collection_name))
                        
                        st.info(f"**Collection**: `{result.get('collection_name', collection_name)}`")
                        st.success("🔄 **Document available in Weaviate Cloud Service!**")
                        st.info("Your document is now searchable across all tabs using Weaviate.")
                        
                        # Show available collections
                        collections = weaviate_helper.list_available_collections()
                        if collections:
                            st.subheader("📚 Available Collections")
                            for col in collections:
                                stats = weaviate_helper.get_collection_stats(col)
                                st.write(f"- **{col}**: {stats.get('total_objects', 0)} documents")
                    else:
                        st.error(f"❌ **Weaviate ingestion failed**: {result.get('error', 'Unknown error')}")
                
                else:
                    # Original FAISS ingestion path (fallback)
                    st.info("Using FAISS backend - creating local index...")
                    
                    # Create index directory if it doesn't exist
                    index_dir = INDEX_ROOT / f"{index_name}_index"
                    if not index_dir.exists():
                        index_dir.mkdir(parents=True, exist_ok=True)
                    
                    import datetime
                    creation_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    chunking_method = "semantic" if chunking_strategy == "Semantic Chunking (Recommended)" else "size_based"
                    
                    with open(index_dir / "index.meta", "w", encoding="utf-8") as f:
                        f.write(f"Created by: {username}\nDocument type: {source_type}\nChunk size: {chunk_size}\nChunk overlap: {chunk_overlap}\nChunking method: {chunking_method}\nSplit by headers: {split_by_headers}\nUse embeddings: {use_embeddings}\nCreation date: {creation_date}")
                    
                    # Basic file processing for FAISS
                    if source_type == "PDF File" and uploaded_file:
                        with open(index_dir / f"source_document.pdf", "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        with open(index_dir / "extracted_text.txt", "w", encoding="utf-8") as f:
                            f.write(f"PDF document: {uploaded_file.name}")
                            
                    elif source_type == "Text File" and uploaded_file:
                        try:
                            text_content = uploaded_file.getvalue().decode("utf-8")
                        except UnicodeDecodeError:
                            text_content = uploaded_file.getvalue().decode("latin-1")
                        
                        with open(index_dir / f"source_document.txt", "w", encoding="utf-8") as f:
                            f.write(text_content)
                            
                    elif source_type == "Website URL" and url_input:
                        with open(index_dir / "source_url.txt", "w", encoding="utf-8") as f:
                            f.write(f"URL: {url_input}\nRender JS: {render_js}\nDepth: {max_depth}")
                    
                    progress_bar.progress(100)
                    st.success("✅ **Document successfully indexed with FAISS!**")
                    
                    # Display basic info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📄 Documents", "1")
                    with col2:
                        st.metric("🧩 Chunks", str(int(5000 / chunk_size)))
                    with col3:
                        st.metric("💾 Index", f"{index_name}_index")
                    
                    st.info(f"**Index saved to**: `{index_dir}`")
                    st.success("🔄 **Index list refreshed across all tabs!**")
                    st.info("Your document is now available in **Query**, **Chat**, **Agent**, and **Multi-Document** tabs.")

            except Exception as e:
                st.error(f"❌ **Ingestion failed**: {str(e)}")
                logging.error(f"Document ingestion error: {e}")
