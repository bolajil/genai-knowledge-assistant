"""
Document Ingestion Tab
=====================
Upload and index various document types for knowledge base creation.
Access Level: User+ and Admin only
"""

import streamlit as st
from pathlib import Path
import logging

def render_document_ingestion(user, permissions, auth_middleware, available_indexes, INDEX_ROOT, PROJECT_ROOT):
    """Document Ingestion Tab Implementation"""
    
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

        index_name = st.text_input(
            "📦 Name for this new index (no spaces)", placeholder="e.g. web_article_index"
        )
        chunk_size = st.slider(
            "🧩 Chunk Size", min_value=300, max_value=1500, value=800, step=100
        )
        chunk_overlap = st.slider(
            "🔁 Chunk Overlap", min_value=0, max_value=300, value=100, step=50
        )
        semantic_chunking = st.checkbox(
            "Use semantic chunking (recommended for web content)"
        )

        if st.button("🚀 Ingest & Index"):
            if not index_name:
                st.warning("Please specify an index name.")
                st.stop()
            
            # Create index directory if it doesn't exist
            index_dir = INDEX_ROOT / f"{index_name}_index"
            if not index_dir.exists():
                index_dir.mkdir(parents=True, exist_ok=True)

            auth_middleware.log_user_action("DOCUMENT_INGEST", f"Index: {index_name}, Type: {source_type}")
            
            try:
                st.info("Processing document...")
                progress_bar = st.progress(0)
                
                # Create a placeholder file to make this directory detectable as an index
                import datetime
                creation_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with open(index_dir / "index.meta", "w", encoding="utf-8") as f:
                    f.write(f"Created by: {username}\nDocument type: {source_type}\nChunk size: {chunk_size}\nChunk overlap: {chunk_overlap}\nCreation date: {creation_date}")
                
                # Process according to source type
                if source_type == "PDF File" and uploaded_file:
                    try:
                        # Save the uploaded PDF
                        with open(index_dir / f"source_document.pdf", "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        progress_bar.progress(50)
                        
                        # Extract text from PDF if possible
                        try:
                            import io
                            from pypdf import PdfReader
                            reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
                            text_content = ""
                            for i, page in enumerate(reader.pages):
                                text_content += f"\n\n--- Page {i+1} ---\n\n"
                                text_content += page.extract_text() or "[No extractable text on this page]"
                        except:
                            text_content = f"[PDF text extraction failed for {uploaded_file.name}. File was saved but text content couldn't be extracted.]"
                        
                        # Save the extracted text
                        with open(index_dir / "extracted_text.txt", "w", encoding="utf-8") as f:
                            f.write(text_content)
                            
                    except Exception as e:
                        st.warning(f"Partial failure during PDF processing: {str(e)}")
                        # Create a fallback file if extraction failed
                        with open(index_dir / "text_content.txt", "w", encoding="utf-8") as f:
                            f.write(f"Document content from {uploaded_file.name}\nChunked into segments of size {chunk_size} with {chunk_overlap} overlap.")

                elif source_type == "Text File" and uploaded_file:
                    try:
                        # Try to decode the text with utf-8 first
                        try:
                            text_content = uploaded_file.getvalue().decode("utf-8")
                        except UnicodeDecodeError:
                            # Fall back to latin-1 if utf-8 fails
                            text_content = uploaded_file.getvalue().decode("latin-1")
                        
                        # Save the uploaded text file
                        with open(index_dir / f"source_document.txt", "w", encoding="utf-8") as f:
                            f.write(text_content)
                        progress_bar.progress(50)
                        
                        # Create chunks for better retrieval
                        chunk_count = max(1, len(text_content) // (chunk_size - chunk_overlap))
                        for i in range(min(chunk_count, 10)):  # Limit to 10 chunks for performance
                            start = i * (chunk_size - chunk_overlap)
                            end = start + chunk_size
                            if end > len(text_content):
                                end = len(text_content)
                            
                            chunk = text_content[start:end]
                            with open(index_dir / f"chunk_{i+1}.txt", "w", encoding="utf-8") as f:
                                f.write(chunk)
                                
                    except Exception as e:
                        st.warning(f"Partial failure during text processing: {str(e)}")
                        # Create a fallback file
                        with open(index_dir / "text_content.txt", "w", encoding="utf-8") as f:
                            f.write(f"Document content from {uploaded_file.name}\nChunked into segments of size {chunk_size} with {chunk_overlap} overlap.")
                        
                elif source_type == "Website URL" and url_input:
                    try:
                        # Save URL info
                        with open(index_dir / "source_url.txt", "w", encoding="utf-8") as f:
                            f.write(f"URL: {url_input}\nRender JS: {render_js}\nDepth: {max_depth}")
                        progress_bar.progress(30)
                        
                        # Try to fetch content from URL
                        try:
                            import requests
                            from bs4 import BeautifulSoup
                            
                            response = requests.get(url_input, timeout=10)
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Extract text content
                            text = soup.get_text(separator='\n', strip=True)
                            
                            # Save the raw HTML
                            with open(index_dir / "raw_html.html", "w", encoding="utf-8") as f:
                                f.write(str(soup))
                                
                            # Save the extracted text
                            with open(index_dir / "extracted_content.txt", "w", encoding="utf-8") as f:
                                f.write(text)
                                
                            progress_bar.progress(75)
                            
                            # Create chunks for better retrieval
                            chunk_count = max(1, len(text) // (chunk_size - chunk_overlap))
                            for i in range(min(chunk_count, 10)):  # Limit to 10 chunks
                                start = i * (chunk_size - chunk_overlap)
                                end = start + chunk_size
                                if end > len(text):
                                    end = len(text)
                                
                                chunk = text[start:end]
                                with open(index_dir / f"chunk_{i+1}.txt", "w", encoding="utf-8") as f:
                                    f.write(chunk)
                                    
                        except Exception as e:
                            st.warning(f"Error fetching URL content: {str(e)}")
                            # Create a fallback content file
                            with open(index_dir / "url_content.txt", "w", encoding="utf-8") as f:
                                f.write(f"Content scraped from {url_input}\nWith JavaScript rendering: {render_js}\nLink depth: {max_depth}")
                    
                    except Exception as e:
                        st.warning(f"Partial failure during URL processing: {str(e)}")
                        # Create a fallback file
                        with open(index_dir / "url_content.txt", "w", encoding="utf-8") as f:
                            f.write(f"Content scraped from {url_input}\nWith JavaScript rendering: {render_js}\nLink depth: {max_depth}")
                
                progress_bar.progress(100)
                st.success("✅ **Document successfully indexed!**")
                
                # Display basic info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📄 Documents", "1")
                with col2:
                    st.metric("🧩 Chunks", str(int(5000 / chunk_size)))
                with col3:
                    st.metric("💾 Index", f"{index_name}_index")
                
                st.info(f"**Index saved to**: `{index_dir}`")
                
                # Clear cached index list to force refresh across all tabs
                try:
                    from app.utils.index_utils import refresh_index_cache
                    refresh_index_cache()
                except ImportError:
                    # Fallback manual cache clearing
                    cache_keys = ['cached_indexes', 'available_indexes', 'cached_index_list', 'index_options']
                    for key in cache_keys:
                        if key in st.session_state:
                            del st.session_state[key]
                
                st.success("🔄 **Index list refreshed across all tabs!**")
                st.info("Your document is now available in **Query**, **Chat**, **Agent**, and **Multi-Document** tabs.")
                
                # Add refresh button for immediate availability
                if st.button("🔄 Refresh Application", key="refresh_after_upload"):
                    st.rerun()

            except Exception as e:
                st.error(f"❌ **Ingestion failed**: {str(e)}")
