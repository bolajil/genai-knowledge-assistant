"""
VaultMIND Knowledge Assistant - Enhanced Streamlit UI

This module provides a Streamlit user interface for the enhanced document processing and querying.
"""

import streamlit as st
import pandas as pd
import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime
import requests
import base64
from typing import Dict, List, Any, Optional, Union
import io
from utils.demo_mode import ensure_demo_index
from utils.vector_search_with_embeddings import search_with_embeddings, get_vector_search_engine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_URL = os.environ.get("API_URL", "http://localhost:8000")
MAX_FILE_SIZE_MB = 50
# Demo Mode flags
DEMO_MODE = os.environ.get("DEMO_MODE", "false").strip().lower() in ("1", "true", "yes", "on")
DEMO_INDEX_NAME = os.environ.get("DEMO_INDEX_NAME", "demo_index")
DEMO_INDEX_PATH = None

if DEMO_MODE:
    created, msg, _index_dir = ensure_demo_index(DEMO_INDEX_NAME)
    DEMO_INDEX_PATH = _index_dir
    logger.info(f"Demo Mode: {msg}")

# Page configuration
st.set_page_config(
    page_title="VaultMIND Knowledge Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Function to load CSS
def load_css():
    css = """
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #4A90E2;
            margin-bottom: 1rem;
        }
        .sub-header {
            font-size: 1.5rem;
            color: #333;
            margin-bottom: 0.5rem;
        }
        .info-box {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .success-box {
            background-color: #d4edda;
            color: #155724;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .warning-box {
            background-color: #fff3cd;
            color: #856404;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .error-box {
            background-color: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .result-box {
            background-color: #e9ecef;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid #4A90E2;
        }
        .document-card {
            border: 1px solid #ddd;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .tag {
            background-color: #4A90E2;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 0.25rem;
            margin-right: 0.25rem;
            font-size: 0.8rem;
        }
        .metadata-table {
            font-size: 0.9rem;
        }
        .search-highlight {
            background-color: #fff3cd;
            padding: 0 0.2rem;
            border-radius: 0.25rem;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Header and subheader components
def header(text):
    st.markdown(f'<h1 class="main-header">{text}</h1>', unsafe_allow_html=True)

def subheader(text):
    st.markdown(f'<h2 class="sub-header">{text}</h2>', unsafe_allow_html=True)

def info_box(text):
    st.markdown(f'<div class="info-box">{text}</div>', unsafe_allow_html=True)

def success_box(text):
    st.markdown(f'<div class="success-box">{text}</div>', unsafe_allow_html=True)

def warning_box(text):
    st.markdown(f'<div class="warning-box">{text}</div>', unsafe_allow_html=True)

def error_box(text):
    st.markdown(f'<div class="error-box">{text}</div>', unsafe_allow_html=True)

# Function to get system status
def get_system_status():
    if DEMO_MODE:
        return {
            "status": "healthy",
            "message": "Demo Mode",
            "components": {
                "vector_database": {"status": "ready", "available": True, "details": f"FAISS demo index: {DEMO_INDEX_NAME}"},
                "llm_service": {"status": "disabled", "available": False}
            }
        }
    try:
        response = requests.get(f"{API_URL}/status")
        return response.json()
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {"status": "error", "message": str(e)}

# Function to list documents
def list_documents(tag=None, file_type=None):
    if DEMO_MODE:
        docs = []
        try:
            if DEMO_INDEX_PATH and (DEMO_INDEX_PATH / "index.faiss").exists():
                engine = get_vector_search_engine()
                try:
                    engine.load_index(DEMO_INDEX_PATH)
                except Exception:
                    pass
                info = engine.get_index_info(DEMO_INDEX_NAME)
                docs.append({
                    "doc_id": f"{DEMO_INDEX_NAME}_0",
                    "filename": (DEMO_INDEX_PATH / "demo_source.txt").name if DEMO_INDEX_PATH else "demo_source.txt",
                    "file_type": "txt",
                    "index_name": DEMO_INDEX_NAME,
                    "chunk_count": info.get("total_chunks", 0),
                    "ingestion_date": info.get("created_at", ""),
                    "tags": ["demo"],
                    "custom_metadata": {},
                    "file_path": str((DEMO_INDEX_PATH / "demo_source.txt") if DEMO_INDEX_PATH else "demo_source.txt")
                })
        except Exception as e:
            logger.error(f"Demo Mode list_documents failed: {e}")
        return {"status": "success", "documents": docs}
    try:
        params = {}
        if tag:
            params["tag"] = tag
        if file_type:
            params["file_type"] = file_type
            
        response = requests.get(f"{API_URL}/enhanced/documents", params=params)
        return response.json()
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {"status": "error", "message": str(e)}

# Function to ingest a file
def ingest_file(file_data, file_name, index_name=None, chunk_size=500, chunk_overlap=50, tags=None):
    if DEMO_MODE:
        return {"status": "error", "message": "In Demo Mode, ingestion is disabled. Use the prebuilt demo index."}
    try:
        # Prepare the file upload
        files = {"file": (file_name, file_data)}
        
        # Prepare form data
        form_data = {}
        if index_name:
            form_data["index_name"] = index_name
        form_data["chunk_size"] = str(chunk_size)
        form_data["chunk_overlap"] = str(chunk_overlap)
        if tags:
            form_data["tags"] = ",".join(tags)
        
        response = requests.post(f"{API_URL}/ingest/file", files=files, data=form_data)
        return response.json()
    except Exception as e:
        logger.error(f"Error ingesting file: {e}")
        return {"status": "error", "message": str(e)}

# Function to ingest text
def ingest_text(content, title=None, index_name=None, chunk_size=500, chunk_overlap=50, tags=None):
    if DEMO_MODE:
        return {"status": "error", "message": "In Demo Mode, ingestion is disabled. Use the prebuilt demo index."}
    try:
        # Prepare the request payload
        payload = {
            "content": content,
            "index_name": index_name,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "tags": tags or [],
            "title": title
        }
        
        response = requests.post(f"{API_URL}/enhanced/ingest", json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Error ingesting text: {e}")
        return {"status": "error", "message": str(e)}

# Function to query the knowledge base
def query_knowledge_base(query, index_name=None, top_k=5, relevance_threshold=0.6, filters=None, provider="openai"):
    if DEMO_MODE:
        idx = index_name or DEMO_INDEX_NAME
        results = search_with_embeddings(query, idx, top_k)
        formatted = []
        for r in results:
            score = float(r.get("confidence_score", 0.0))
            rel = max(0.0, min(1.0, (score + 1.0) / 2.0))  # map cosine [-1,1] to [0,1]
            if rel < float(relevance_threshold):
                continue
            formatted.append({
                "content": r.get("content", ""),
                "source": r.get("source", "Unknown"),
                "relevance": rel,
                "metadata": r.get("metadata", {}),
            })
        return {"status": "success", "result_count": len(formatted), "results": formatted}
    try:
        # Prepare the request payload
        payload = {
            "query": query,
            "index_name": index_name,
            "top_k": top_k,
            "relevance_threshold": relevance_threshold,
            "filters": filters,
            "provider": provider
        }
        
        response = requests.post(f"{API_URL}/enhanced/query", json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return {"status": "error", "message": str(e)}

# Function to submit feedback
def submit_feedback(query, result_ids, helpful, comments=None):
    try:
        # Prepare the request payload
        payload = {
            "query": query,
            "result_ids": result_ids,
            "helpful": helpful,
            "comments": comments
        }
        
        response = requests.post(f"{API_URL}/query/feedback", json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return {"status": "error", "message": str(e)}

# Initialize session state
def init_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "query_history" not in st.session_state:
        st.session_state.query_history = []
    if "last_query" not in st.session_state:
        st.session_state.last_query = None
    if "last_results" not in st.session_state:
        st.session_state.last_results = None
    if "system_status" not in st.session_state:
        st.session_state.system_status = get_system_status()
    if "documents" not in st.session_state:
        st.session_state.documents = None
    if "selected_document" not in st.session_state:
        st.session_state.selected_document = None

# Navigation functions
def navigate_to(page):
    st.session_state.page = page

# Page rendering functions
def render_home_page():
    header("VaultMIND Knowledge Assistant")
    
    # Show system status
    system_status = get_system_status()
    st.session_state.system_status = system_status
    
    col1, col2 = st.columns(2)
    
    with col1:
        subheader("System Status")
        
        if system_status["status"] == "healthy":
            st.success("System is healthy")
        else:
            st.error(f"System is unhealthy: {system_status.get('message', 'Unknown error')}")
        
        # Display component status
        components = system_status.get("components", {})
        for component, status in components.items():
            if status.get("status") == "ready":
                st.info(f"{component.replace('_', ' ').title()}: Ready")
            else:
                st.warning(f"{component.replace('_', ' ').title()}: {status.get('status', 'Unavailable')}")
    
    with col2:
        subheader("Quick Actions")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("📝 New Document", use_container_width=True):
                navigate_to("ingest")
        
        with col_b:
            if st.button("🔍 Search Documents", use_container_width=True):
                navigate_to("search")
        
        st.markdown("---")
        
        with col_a:
            if st.button("📚 View Documents", use_container_width=True):
                navigate_to("documents")
        
        with col_b:
            if st.button("📊 View Analytics", use_container_width=True):
                navigate_to("analytics")
    
    st.markdown("---")
    
    # Show recent activity if available
    subheader("Recent Activity")
    
    if st.session_state.query_history:
        # Show recent queries
        recent_queries = st.session_state.query_history[-5:]
        for i, query in enumerate(reversed(recent_queries)):
            with st.expander(f"Query: {query['query'][:50]}...", expanded=(i == 0)):
                st.write(f"**Query:** {query['query']}")
                st.write(f"**Timestamp:** {query['timestamp']}")
                st.write(f"**Results:** {query['result_count']} documents")
                if st.button("View Details", key=f"view_details_{i}"):
                    st.session_state.last_query = query['query']
                    st.session_state.last_results = query['results']
                    navigate_to("search_results")
    else:
        st.info("No recent activity. Start by ingesting documents or searching the knowledge base.")

def render_ingest_page():
    header("Ingest Documents")
    if DEMO_MODE:
        st.warning("Demo Mode: Ingestion is disabled. Use the bundled demo index for exploration.")
    
    # Tabs for different ingestion methods
    tab1, tab2, tab3 = st.tabs(["Upload Files", "Paste Text", "Import from URL"])
    
    with tab1:
        st.markdown("### Upload Files")
        
        # File uploader
        uploaded_files = st.file_uploader("Choose files to upload", accept_multiple_files=True)
        
        # Ingestion settings
        with st.expander("Ingestion Settings", expanded=False):
            index_name = st.text_input("Index Name (optional)", help="Leave blank to use file name")
            chunk_size = st.slider("Chunk Size", min_value=100, max_value=2000, value=500, step=50)
            chunk_overlap = st.slider("Chunk Overlap", min_value=0, max_value=500, value=50, step=10)
            tags = st.text_input("Tags (comma separated)", "")
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
        
        if uploaded_files and st.button("Process Files"):
            progress_bar = st.progress(0)
            results = []
            
            for i, file in enumerate(uploaded_files):
                # Check file size
                if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    st.error(f"File {file.name} is too large. Maximum size is {MAX_FILE_SIZE_MB}MB.")
                    continue
                
                st.info(f"Processing {file.name}...")
                
                # Read file data
                file_data = file.read()
                
                # Ingest the file
                result = ingest_file(file_data, file.name, index_name, chunk_size, chunk_overlap, tag_list)
                results.append(result)
                
                # Update progress
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            # Show results
            success_count = sum(1 for r in results if r.get("status") == "success")
            if success_count == len(results):
                st.success(f"Successfully processed {success_count} files")
            elif success_count > 0:
                st.warning(f"Processed {success_count} out of {len(results)} files successfully")
            else:
                st.error("Failed to process any files")
            
            # Show details for each file
            for i, result in enumerate(results):
                with st.expander(f"File {i+1}: {uploaded_files[i].name}"):
                    st.write(result)
    
    with tab2:
        st.markdown("### Paste Text")
        
        # Text input
        title = st.text_input("Document Title", "")
        content = st.text_area("Content", "", height=300)
        
        # Ingestion settings
        with st.expander("Ingestion Settings", expanded=False):
            index_name = st.text_input("Index Name (optional)", key="paste_index_name")
            chunk_size = st.slider("Chunk Size", min_value=100, max_value=2000, value=500, step=50, key="paste_chunk_size")
            chunk_overlap = st.slider("Chunk Overlap", min_value=0, max_value=500, value=50, step=10, key="paste_chunk_overlap")
            tags = st.text_input("Tags (comma separated)", "", key="paste_tags")
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
        
        if content and st.button("Process Text"):
            st.info("Processing text...")
            
            # Ingest the text
            result = ingest_text(content, title, index_name, chunk_size, chunk_overlap, tag_list)
            
            # Show result
            if result.get("status") == "success":
                st.success("Successfully processed text")
                st.write(result)
            else:
                st.error(f"Failed to process text: {result.get('message', 'Unknown error')}")
                st.write(result)
    
    with tab3:
        st.markdown("### Import from URL")
        
        # URL input
        url = st.text_input("URL", "")
        
        # Ingestion settings
        with st.expander("Ingestion Settings", expanded=False):
            index_name = st.text_input("Index Name (optional)", key="url_index_name")
            chunk_size = st.slider("Chunk Size", min_value=100, max_value=2000, value=500, step=50, key="url_chunk_size")
            chunk_overlap = st.slider("Chunk Overlap", min_value=0, max_value=500, value=50, step=10, key="url_chunk_overlap")
            tags = st.text_input("Tags (comma separated)", "", key="url_tags")
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
        
        if url and st.button("Process URL"):
            st.info(f"Processing URL: {url}")
            
            try:
                # Prepare the request payload
                payload = {
                    "url": url,
                    "index_name": index_name,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "tags": tag_list
                }
                
                response = requests.post(f"{API_URL}/ingest/url", json=payload)
                result = response.json()
                
                # Show result
                if result.get("status") == "success":
                    st.success(f"Successfully processed URL: {url}")
                    st.write(result)
                else:
                    st.error(f"Failed to process URL: {result.get('message', 'Unknown error')}")
                    st.write(result)
            
            except Exception as e:
                st.error(f"Error processing URL: {str(e)}")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Home", use_container_width=True):
            navigate_to("home")
    
    with col2:
        if st.button("View Documents →", use_container_width=True):
            navigate_to("documents")

def render_search_page():
    header("Search Knowledge Base")
    
    # Search input
    query = st.text_input("Enter your query", "")
    
    # Search settings
    with st.expander("Search Settings", expanded=False):
        index_name = st.text_input("Index Name (optional)", help="Leave blank to search all indexes")
        top_k = st.slider("Maximum Results", min_value=1, max_value=20, value=5, step=1)
        relevance_threshold = st.slider("Relevance Threshold", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
        provider = st.selectbox("LLM Provider", ["openai", "claude", "deepseek"])
    
    # Submit search
    if query and st.button("Search"):
        st.info(f"Searching for: {query}")
        
        # Query the knowledge base
        result = query_knowledge_base(query, index_name, top_k, relevance_threshold, None, provider)
        
        if result.get("status") == "success":
            # Store the query and results in session state
            st.session_state.last_query = query
            st.session_state.last_results = result
            
            # Add to query history
            st.session_state.query_history.append({
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "result_count": result.get("result_count", 0),
                "results": result
            })
            
            # Navigate to results page
            navigate_to("search_results")
        else:
            st.error(f"Search failed: {result.get('message', 'Unknown error')}")
    
    # Show recent queries if available
    if st.session_state.query_history:
        st.markdown("---")
        subheader("Recent Queries")
        
        # Show recent queries
        recent_queries = st.session_state.query_history[-5:]
        for i, query_data in enumerate(reversed(recent_queries)):
            with st.expander(f"Query: {query_data['query'][:50]}...", expanded=False):
                st.write(f"**Query:** {query_data['query']}")
                st.write(f"**Timestamp:** {query_data['timestamp']}")
                st.write(f"**Results:** {query_data['result_count']} documents")
                if st.button("View Results", key=f"view_results_{i}"):
                    st.session_state.last_query = query_data['query']
                    st.session_state.last_results = query_data['results']
                    navigate_to("search_results")
    
    # Navigation buttons
    if st.button("← Back to Home", use_container_width=True):
        navigate_to("home")

def render_search_results_page():
    header("Search Results")
    
    # Check if we have results to display
    if not st.session_state.last_query or not st.session_state.last_results:
        st.error("No search results to display")
        
        if st.button("Go to Search", use_container_width=True):
            navigate_to("search")
        
        return
    
    # Display query and answer
    st.markdown(f"**Query:** {st.session_state.last_query}")
    
    result_data = st.session_state.last_results
    
    # Display the synthesized answer if available
    if "answer" in result_data:
        st.markdown("### Answer")
        
        with st.expander("View Answer", expanded=True):
            st.markdown(result_data["answer"])
    
    # Display individual results
    st.markdown("### Source Documents")
    
    result_count = result_data.get("result_count", 0)
    if result_count > 0:
        st.info(f"Found {result_count} relevant documents")
        
        # Show the individual results
        results = result_data.get("results", [])
        for i, result in enumerate(results):
            relevance = result.get("relevance", 0.0)
            relevance_percentage = int(relevance * 100)
            
            with st.expander(f"Document {i+1}: {result.get('source', 'Unknown')} (Relevance: {relevance_percentage}%)", expanded=(i == 0)):
                st.markdown(f"**Source:** {result.get('source', 'Unknown')}")
                st.markdown(f"**Relevance:** {relevance_percentage}%")
                
                # Display metadata if available
                metadata = result.get("metadata", {})
                if metadata:
                    with st.expander("Metadata"):
                        for key, value in metadata.items():
                            st.markdown(f"**{key}:** {value}")
                
                # Display content
                st.markdown("**Content:**")
                st.markdown(result.get("content", "No content available"))
    else:
        st.warning("No relevant documents found")
    
    # Feedback section
    st.markdown("---")
    st.markdown("### Feedback")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👍 This was helpful", use_container_width=True):
            feedback_result = submit_feedback(
                st.session_state.last_query,
                [result.get("doc_id", f"result_{i}") for i, result in enumerate(result_data.get("results", []))],
                True
            )
            
            if feedback_result.get("status") == "success":
                st.success("Thank you for your feedback!")
            else:
                st.error(f"Failed to submit feedback: {feedback_result.get('message', 'Unknown error')}")
    
    with col2:
        if st.button("👎 This wasn't helpful", use_container_width=True):
            comments = st.text_area("What could be improved?", "")
            
            if st.button("Submit Feedback"):
                feedback_result = submit_feedback(
                    st.session_state.last_query,
                    [result.get("doc_id", f"result_{i}") for i, result in enumerate(result_data.get("results", []))],
                    False,
                    comments
                )
                
                if feedback_result.get("status") == "success":
                    st.success("Thank you for your feedback!")
                else:
                    st.error(f"Failed to submit feedback: {feedback_result.get('message', 'Unknown error')}")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Search", use_container_width=True):
            navigate_to("search")
    
    with col2:
        if st.button("New Search", use_container_width=True):
            st.session_state.last_query = None
            st.session_state.last_results = None
            navigate_to("search")

def render_documents_page():
    header("Document Library")
    
    # Load documents
    documents_result = list_documents()
    
    if documents_result.get("status") == "success":
        documents = documents_result.get("documents", [])
        st.session_state.documents = documents
        
        # Display document count
        document_count = len(documents)
        if document_count > 0:
            st.info(f"Found {document_count} documents in the knowledge base")
        else:
            st.warning("No documents found in the knowledge base")
            
            if st.button("Ingest Documents", use_container_width=True):
                navigate_to("ingest")
            
            return
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            # Get all unique tags
            all_tags = set()
            for doc in documents:
                all_tags.update(doc.get("tags", []))
            
            # Create filter by tag
            selected_tag = st.selectbox("Filter by Tag", ["All Tags"] + sorted(list(all_tags)))
            
        with col2:
            # Get all unique file types
            all_file_types = set(doc.get("file_type", "unknown") for doc in documents)
            
            # Create filter by file type
            selected_file_type = st.selectbox("Filter by File Type", ["All Types"] + sorted(list(all_file_types)))
        
        # Apply filters
        filtered_documents = documents
        if selected_tag != "All Tags":
            filtered_documents = [doc for doc in filtered_documents if selected_tag in doc.get("tags", [])]
        if selected_file_type != "All Types":
            filtered_documents = [doc for doc in filtered_documents if doc.get("file_type") == selected_file_type]
        
        # Display filtered document count
        if len(filtered_documents) != document_count:
            st.info(f"Showing {len(filtered_documents)} filtered documents")
        
        # Display documents
        for i, doc in enumerate(filtered_documents):
            with st.expander(f"{doc.get('filename', 'Unnamed Document')}", expanded=False):
                # Display metadata
                st.markdown(f"**Document ID:** {doc.get('doc_id', 'Unknown')}")
                st.markdown(f"**File Type:** {doc.get('file_type', 'Unknown')}")
                st.markdown(f"**Index Name:** {doc.get('index_name', 'Unknown')}")
                st.markdown(f"**Chunk Count:** {doc.get('chunk_count', 0)}")
                st.markdown(f"**Ingestion Date:** {doc.get('ingestion_date', 'Unknown')}")
                
                # Display tags
                tags = doc.get("tags", [])
                if tags:
                    st.markdown("**Tags:**")
                    tag_html = " ".join([f'<span class="tag">{tag}</span>' for tag in tags])
                    st.markdown(tag_html, unsafe_allow_html=True)
                
                # Display custom metadata
                custom_metadata = doc.get("custom_metadata", {})
                if custom_metadata:
                    st.markdown("**Custom Metadata:**")
                    for key, value in custom_metadata.items():
                        st.markdown(f"- **{key}:** {value}")
                
                # Display file path
                st.markdown(f"**File Path:** {doc.get('file_path', 'Unknown')}")
                
                # Action buttons
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if st.button("Search in this Document", key=f"search_doc_{i}", use_container_width=True):
                        st.session_state.selected_document = doc
                        navigate_to("search_document")
                
                with col_b:
                    if st.button("Delete Document", key=f"delete_doc_{i}", use_container_width=True):
                        # Delete confirmation
                        st.markdown("Are you sure you want to delete this document?")
                        
                        confirm_col1, confirm_col2 = st.columns(2)
                        
                        with confirm_col1:
                            if st.button("Yes, Delete", key=f"confirm_delete_{i}", use_container_width=True):
                                try:
                                    response = requests.delete(f"{API_URL}/documents/{doc.get('doc_id')}")
                                    result = response.json()
                                    
                                    if result.get("status") == "success":
                                        st.success(f"Document deleted successfully")
                                        # Refresh the documents
                                        documents_result = list_documents()
                                        if documents_result.get("status") == "success":
                                            st.session_state.documents = documents_result.get("documents", [])
                                            st.rerun()
                                    else:
                                        st.error(f"Failed to delete document: {result.get('message', 'Unknown error')}")
                                
                                except Exception as e:
                                    st.error(f"Error deleting document: {str(e)}")
                        
                        with confirm_col2:
                            if st.button("Cancel", key=f"cancel_delete_{i}", use_container_width=True):
                                pass
    else:
        st.error(f"Failed to load documents: {documents_result.get('message', 'Unknown error')}")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Home", use_container_width=True):
            navigate_to("home")
    
    with col2:
        if st.button("Ingest New Documents", use_container_width=True):
            navigate_to("ingest")

def render_search_document_page():
    header("Search in Document")
    
    # Check if we have a document selected
    if not st.session_state.selected_document:
        st.error("No document selected")
        
        if st.button("Go to Documents", use_container_width=True):
            navigate_to("documents")
        
        return
    
    # Display document info
    doc = st.session_state.selected_document
    st.markdown(f"**Document:** {doc.get('filename', 'Unnamed Document')}")
    st.markdown(f"**Index Name:** {doc.get('index_name', 'Unknown')}")
    
    # Search input
    query = st.text_input("Enter your query", "")
    
    # Search settings
    with st.expander("Search Settings", expanded=False):
        top_k = st.slider("Maximum Results", min_value=1, max_value=20, value=5, step=1)
        relevance_threshold = st.slider("Relevance Threshold", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
        provider = st.selectbox("LLM Provider", ["openai", "claude", "deepseek"])
    
    # Submit search
    if query and st.button("Search"):
        st.info(f"Searching for: {query}")
        
        # Query the knowledge base with document's index name
        result = query_knowledge_base(query, doc.get('index_name'), top_k, relevance_threshold, None, provider)
        
        if result.get("status") == "success":
            # Store the query and results in session state
            st.session_state.last_query = query
            st.session_state.last_results = result
            
            # Add to query history
            st.session_state.query_history.append({
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "result_count": result.get("result_count", 0),
                "results": result
            })
            
            # Navigate to results page
            navigate_to("search_results")
        else:
            st.error(f"Search failed: {result.get('message', 'Unknown error')}")
    
    # Navigation buttons
    if st.button("← Back to Documents", use_container_width=True):
        navigate_to("documents")

def render_analytics_page():
    header("Analytics Dashboard")
    
    # Placeholder for future analytics implementation
    st.info("Analytics dashboard is under development")
    
    # Navigation buttons
    if st.button("← Back to Home", use_container_width=True):
        navigate_to("home")

# Main application
def main():
    # Load CSS
    load_css()
    
    # Initialize session state
    init_session_state()
    
    # Demo Mode notice
    if DEMO_MODE:
        st.info(f"Demo Mode is ON. Using local FAISS demo index '{DEMO_INDEX_NAME}'. Ingestion and outbound calls are disabled.")
    
    # Sidebar navigation
    with st.sidebar:
        st.title("VaultMIND")
        
        # Navigation menu
        st.subheader("Navigation")
        
        if st.button("🏠 Home", use_container_width=True):
            navigate_to("home")
        
        if st.button("📝 Ingest Documents", use_container_width=True):
            navigate_to("ingest")
        
        if st.button("🔍 Search", use_container_width=True):
            navigate_to("search")
        
        if st.button("📚 Documents", use_container_width=True):
            navigate_to("documents")
        
        if st.button("📊 Analytics", use_container_width=True):
            navigate_to("analytics")
        
        # System status
        st.markdown("---")
        st.subheader("System Status")
        
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.session_state.system_status = get_system_status()
        
        system_status = st.session_state.system_status
        
        if system_status:
            if system_status.get("status") == "healthy":
                st.success("System: Healthy")
            else:
                st.error(f"System: Unhealthy")
            
            # Display vector database status
            vector_db = system_status.get("components", {}).get("vector_database", {})
            if vector_db.get("available"):
                if vector_db.get("status") == "Ready":
                    st.info(f"Vector DB: {vector_db.get('message', 'Ready')}")
                else:
                    st.warning(f"Vector DB: {vector_db.get('message', 'Not Ready')}")
            else:
                st.warning("Vector DB: Unavailable")
    
    # Render the appropriate page based on session state
    if st.session_state.page == "home":
        render_home_page()
    elif st.session_state.page == "ingest":
        render_ingest_page()
    elif st.session_state.page == "search":
        render_search_page()
    elif st.session_state.page == "search_results":
        render_search_results_page()
    elif st.session_state.page == "documents":
        render_documents_page()
    elif st.session_state.page == "search_document":
        render_search_document_page()
    elif st.session_state.page == "analytics":
        render_analytics_page()
    else:
        render_home_page()

if __name__ == "__main__":
    main()
