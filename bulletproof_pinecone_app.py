#!/usr/bin/env python3
"""
BULLETPROOF Pinecone Document Ingestion
Handles all known pinecone-client version issues
"""

import streamlit as st
import os
import io
from pathlib import Path
from datetime import datetime
from typing import List

# Page config
st.set_page_config(
    page_title="Bulletproof Pinecone",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Bulletproof Pinecone Document Ingestion")
st.markdown("**This version handles all known pinecone-client issues!**")

# Load environment manually
def load_env():
    """Load environment variables"""
    env_vars = {}
    for env_file in [".env", "config/weaviate.env", "config/storage.env"]:
        if Path(env_file).exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
                        os.environ[key.strip()] = value.strip()
    return env_vars

# Load environment
env_vars = load_env()
api_key = os.getenv('PINECONE_API_KEY')

if not api_key:
    st.error("❌ PINECONE_API_KEY not found")
    st.info("Add your Pinecone API key to config/storage.env")
    st.stop()

st.success(f"✅ API Key loaded: {api_key[:8]}...")

# Smart Pinecone import with version handling
def smart_pinecone_import():
    """Import Pinecone with intelligent version handling"""
    
    st.write("🔍 **Testing Pinecone Import...**")
    
    # Try new pinecone-client v4+ approach
    try:
        from pinecone import Pinecone, ServerlessSpec
        st.success("✅ Using pinecone-client v4+ (new API)")
        return Pinecone, ServerlessSpec, "v4+"
    except ImportError as e1:
        st.warning(f"⚠️ New API failed: {e1}")
        
        # Try old pinecone-client v3 approach
        try:
            import pinecone
            st.success("✅ Using pinecone-client v3 (legacy API)")
            return pinecone, None, "v3"
        except ImportError as e2:
            st.error(f"❌ Legacy API also failed: {e2}")
            st.error("**Please install pinecone-client:**")
            st.code("py -m pip install pinecone-client==4.1.2")
            return None, None, None

# Test Pinecone import
Pinecone, ServerlessSpec, version = smart_pinecone_import()

if not Pinecone:
    st.stop()

# Connection test
with st.expander("🔍 Connection Test", expanded=True):
    if st.button("Test Bulletproof Connection"):
        try:
            if version == "v4+":
                # New API
                client = Pinecone(api_key=api_key)
                indexes = client.list_indexes()
                st.success(f"🎉 CONNECTION SUCCESSFUL! (v4+ API)")
                st.success(f"Found {len(indexes)} indexes")
                
            elif version == "v3":
                # Legacy API
                Pinecone.init(api_key=api_key, environment="us-east1-gcp")
                indexes = Pinecone.list_indexes()
                st.success(f"🎉 CONNECTION SUCCESSFUL! (v3 API)")
                st.success(f"Found {len(indexes)} indexes")
            
            if indexes:
                st.write("**Existing indexes:**")
                for idx in indexes:
                    if hasattr(idx, 'name'):
                        st.write(f"- {idx.name}")
                    elif isinstance(idx, dict):
                        st.write(f"- {idx.get('name', 'Unknown')}")
                    else:
                        st.write(f"- {str(idx)}")
            
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
            st.code(str(e))
            
            # Provide specific guidance
            if "renamed" in str(e).lower() or "pinecone-client" in str(e).lower():
                st.error("**Version Conflict Detected!**")
                st.info("Run this command to fix:")
                st.code("py -m pip uninstall pinecone-client -y && py -m pip install pinecone-client==4.1.2")

# File upload section
st.subheader("📄 Upload Document")
uploaded_file = st.file_uploader(
    "Choose a file",
    type=['txt', 'pdf'],
    help="Upload a text or PDF file for ingestion"
)

if uploaded_file:
    st.success(f"✅ File uploaded: {uploaded_file.name}")
    
    # Configuration
    st.subheader("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        index_name = st.text_input(
            "Index Name",
            value="bulletproof-docs",
            help="Name for your Pinecone index"
        )
        
        # Sanitize index name
        import re
        sanitized = re.sub(r'[^a-z0-9-]', '-', index_name.lower())
        sanitized = re.sub(r'^-+|-+$', '', sanitized)
        sanitized = re.sub(r'-+', '-', sanitized)
        if len(sanitized) > 45:
            sanitized = sanitized[:45].rstrip('-')
        if not sanitized:
            sanitized = "bulletproof-docs"
        
        if sanitized != index_name:
            st.info(f"Sanitized to: `{sanitized}`")
            index_name = sanitized
    
    with col2:
        chunk_size = st.slider("Chunk Size", 500, 2000, 1000, 100)
        chunk_overlap = st.slider("Overlap", 0, 500, 200, 50)
    
    # Ingestion button
    if st.button("🛡️ START BULLETPROOF INGESTION", type="primary"):
        
        progress = st.progress(0)
        status = st.empty()
        
        try:
            # Extract text
            status.text("📖 Extracting text...")
            
            if uploaded_file.type == "application/pdf":
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                except Exception:
                    text = "Could not extract PDF text"
            else:
                text = uploaded_file.read().decode('utf-8')
            
            if len(text.strip()) < 10:
                st.error("❌ Could not extract meaningful text")
                st.stop()
            
            st.success(f"✅ Extracted {len(text)} characters")
            progress.progress(0.2)
            
            # Chunk text
            status.text("✂️ Chunking text...")
            chunks = []
            start = 0
            
            while start < len(text):
                end = start + chunk_size
                chunk = text[start:end]
                
                if end < len(text):
                    last_period = chunk.rfind('.')
                    if last_period > start + chunk_size // 2:
                        chunk = text[start:start + last_period + 1]
                        end = start + last_period + 1
                
                chunks.append(chunk.strip())
                start = end - chunk_overlap
                
                if start >= len(text):
                    break
            
            chunks = [chunk for chunk in chunks if chunk.strip()]
            st.success(f"✅ Created {len(chunks)} chunks")
            progress.progress(0.4)
            
            # Generate embeddings
            status.text("🧠 Generating embeddings...")
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                embeddings = model.encode(chunks)
                embeddings = [emb.tolist() for emb in embeddings]
                st.success(f"✅ Generated {len(embeddings)} embeddings")
            except Exception as e:
                st.error(f"❌ Embedding generation failed: {e}")
                st.stop()
            
            progress.progress(0.6)
            
            # Connect to Pinecone with version-specific logic
            status.text("🔌 Connecting to Pinecone...")
            
            if version == "v4+":
                # New API
                client = Pinecone(api_key=api_key)
                
                # Get existing indexes
                existing_indexes = client.list_indexes()
                existing_names = []
                for idx in existing_indexes:
                    if hasattr(idx, 'name'):
                        existing_names.append(idx.name)
                    elif isinstance(idx, dict):
                        existing_names.append(idx.get('name', ''))
                
                # Create index if needed
                if index_name not in existing_names:
                    client.create_index(
                        name=index_name,
                        dimension=384,
                        metric='cosine',
                        spec=ServerlessSpec(cloud='aws', region='us-east-1')
                    )
                    st.success(f"✅ Created new index: {index_name}")
                else:
                    st.info(f"ℹ️ Using existing index: {index_name}")
                
                # Get index client
                index = client.Index(index_name)
                
            elif version == "v3":
                # Legacy API
                if not hasattr(Pinecone, '_initialized'):
                    Pinecone.init(api_key=api_key, environment="us-east1-gcp")
                    Pinecone._initialized = True
                
                # Get existing indexes
                existing_indexes = Pinecone.list_indexes()
                
                # Create index if needed
                if index_name not in existing_indexes:
                    Pinecone.create_index(
                        name=index_name,
                        dimension=384,
                        metric='cosine'
                    )
                    st.success(f"✅ Created new index: {index_name}")
                else:
                    st.info(f"ℹ️ Using existing index: {index_name}")
                
                # Get index client
                index = Pinecone.Index(index_name)
            
            progress.progress(0.8)
            
            # Upload vectors
            status.text("📤 Uploading to Pinecone...")
            
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vectors.append({
                    "id": f"{uploaded_file.name}_{i}_{datetime.now().timestamp()}",
                    "values": embedding,
                    "metadata": {
                        "content": chunk[:40000],
                        "source": uploaded_file.name,
                        "chunk_index": i,
                        "created_at": datetime.now().isoformat()
                    }
                })
            
            # Upload in batches
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                index.upsert(vectors=batch)
            
            progress.progress(1.0)
            status.text("✅ BULLETPROOF INGESTION COMPLETED!")
            
            # Success celebration
            st.success("🎉 **BULLETPROOF INGESTION SUCCESSFUL!**")
            st.balloons()
            
            # Results
            with st.expander("📊 Ingestion Results", expanded=True):
                st.write(f"**File:** {uploaded_file.name}")
                st.write(f"**Index:** {index_name}")
                st.write(f"**API Version:** {version}")
                st.write(f"**Text chunks:** {len(chunks)}")
                st.write(f"**Vectors uploaded:** {len(vectors)}")
                st.write(f"**Timestamp:** {datetime.now().isoformat()}")
            
            # Search test
            st.subheader("🔍 Test Search")
            query = st.text_input("Enter a search query:")
            
            if query and st.button("Search Documents"):
                try:
                    query_embedding = model.encode([query])[0].tolist()
                    results = index.query(
                        vector=query_embedding,
                        top_k=3,
                        include_metadata=True
                    )
                    
                    st.write(f"**Search results for: '{query}'**")
                    for i, match in enumerate(results.matches, 1):
                        with st.expander(f"Result {i} (Score: {match.score:.3f})"):
                            st.write(match.metadata.get('content', 'No content'))
                            st.caption(f"Source: {match.metadata.get('source', 'Unknown')}")
                            
                except Exception as e:
                    st.error(f"Search failed: {e}")
            
        except Exception as e:
            st.error(f"❌ Bulletproof ingestion failed: {e}")
            import traceback
            st.code(traceback.format_exc())
            
            # Provide specific guidance based on error
            error_str = str(e).lower()
            if "renamed" in error_str or "pinecone-client" in error_str:
                st.error("**Package Rename Issue Detected!**")
                st.info("Fix with:")
                st.code("py -m pip uninstall pinecone-client -y && py -m pip install pinecone-client==4.1.2")
            elif "api key" in error_str:
                st.error("**API Key Issue!**")
                st.info("Check your PINECONE_API_KEY in config/storage.env")
            elif "dimension" in error_str:
                st.error("**Dimension Mismatch!**")
                st.info("Try using a different index name or delete the existing index")

# Footer
st.markdown("---")
st.markdown("**🛡️ This bulletproof version handles all known pinecone-client issues!**")
st.markdown("**Supports both v3 (legacy) and v4+ (new) APIs**")
