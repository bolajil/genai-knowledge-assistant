"""
Simple Pinecone Ingestion Tab
Add this to your main Streamlit app as a working Pinecone solution
"""

import streamlit as st
import os
import io
from pathlib import Path
from datetime import datetime
from typing import List
import logging

# Load environment
from dotenv import load_dotenv
for env_file in [".env", "config/weaviate.env", "config/storage.env"]:
    if Path(env_file).exists():
        load_dotenv(env_file, override=True)

def extract_text_from_uploaded_file(uploaded_file) -> str:
    """Extract text from uploaded file"""
    try:
        if uploaded_file.type == "application/pdf":
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except Exception:
                return "Could not extract PDF text"
        else:
            return uploaded_file.read().decode('utf-8')
    except Exception as e:
        return f"Error reading file: {e}"

def simple_chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple text chunking"""
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
        start = end - overlap
        
        if start >= len(text):
            break
    
    return [chunk for chunk in chunks if chunk.strip()]

def generate_simple_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using sentence-transformers"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(texts)
        return [emb.tolist() for emb in embeddings]
    except Exception as e:
        st.error(f"Failed to generate embeddings: {e}")
        return []

def render_simple_pinecone_tab():
    """Render the simple Pinecone ingestion tab"""
    
    st.title("🚀 Simple Pinecone Ingestion")
    st.markdown("**Direct Pinecone ingestion that actually works!**")
    
    # Check API key
    api_key = os.getenv('PINECONE_API_KEY')
    if not api_key:
        st.error("❌ PINECONE_API_KEY not found in environment")
        st.info("Add your Pinecone API key to config/storage.env")
        return
    
    st.success(f"✅ Pinecone API key found: {api_key[:8]}...")
    
    # Connection test
    with st.expander("🔍 Connection Test", expanded=False):
        if st.button("Test Connection"):
            try:
                import pinecone
                from pinecone import Pinecone, ServerlessSpec
                
                client = Pinecone(api_key=api_key)
                indexes = client.list_indexes()
                
                st.success(f"✅ Connected: {len(indexes)} indexes found")
                
                if indexes:
                    st.write("**Existing indexes:**")
                    for idx in indexes:
                        if hasattr(idx, 'name'):
                            st.write(f"- {idx.name}")
                        elif isinstance(idx, dict):
                            st.write(f"- {idx.get('name', 'Unknown')}")
                
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
                return
    
    # File upload
    st.subheader("📄 Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['txt', 'pdf'],
        help="Upload a text or PDF file"
    )
    
    if not uploaded_file:
        st.info("👆 Upload a file to continue")
        return
    
    # Configuration
    st.subheader("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        index_name = st.text_input(
            "Index Name",
            value="simple-docs",
            help="Name for the Pinecone index"
        )
        
        # Sanitize name
        import re
        sanitized = re.sub(r'[^a-z0-9-]', '-', index_name.lower())
        sanitized = re.sub(r'^-+|-+$', '', sanitized)
        sanitized = re.sub(r'-+', '-', sanitized)
        if len(sanitized) > 45:
            sanitized = sanitized[:45].rstrip('-')
        if not sanitized:
            sanitized = "simple-docs"
        
        if sanitized != index_name:
            st.info(f"Sanitized to: `{sanitized}`")
            index_name = sanitized
    
    with col2:
        chunk_size = st.slider("Chunk Size", 500, 2000, 1000, 100)
        chunk_overlap = st.slider("Overlap", 0, 500, 200, 50)
    
    # Ingestion
    if st.button("🚀 Start Simple Ingestion", type="primary"):
        
        progress = st.progress(0)
        status = st.empty()
        
        try:
            # Extract text
            status.text("📖 Extracting text...")
            text = extract_text_from_uploaded_file(uploaded_file)
            
            if len(text.strip()) < 10:
                st.error("❌ Could not extract meaningful text")
                return
            
            st.success(f"✅ Extracted {len(text)} characters")
            progress.progress(0.2)
            
            # Chunk text
            status.text("✂️ Chunking text...")
            chunks = simple_chunk_text(text, chunk_size, chunk_overlap)
            
            st.success(f"✅ Created {len(chunks)} chunks")
            progress.progress(0.4)
            
            # Generate embeddings
            status.text("🧠 Generating embeddings...")
            embeddings = generate_simple_embeddings(chunks)
            
            if not embeddings:
                st.error("❌ Failed to generate embeddings")
                return
            
            st.success(f"✅ Generated {len(embeddings)} embeddings")
            progress.progress(0.6)
            
            # Connect to Pinecone
            status.text("🔌 Connecting to Pinecone...")
            import pinecone
            from pinecone import Pinecone, ServerlessSpec
            
            client = Pinecone(api_key=api_key)
            progress.progress(0.7)
            
            # Create/get index
            status.text(f"📊 Setting up index: {index_name}")
            
            existing_indexes = client.list_indexes()
            existing_names = []
            for idx in existing_indexes:
                if hasattr(idx, 'name'):
                    existing_names.append(idx.name)
                elif isinstance(idx, dict):
                    existing_names.append(idx.get('name', ''))
            
            if index_name not in existing_names:
                client.create_index(
                    name=index_name,
                    dimension=384,
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
                st.success(f"✅ Created index: {index_name}")
            else:
                st.info(f"ℹ️ Using existing index: {index_name}")
            
            progress.progress(0.8)
            
            # Upload vectors
            status.text("📤 Uploading to Pinecone...")
            
            index = client.Index(index_name)
            
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
            status.text("✅ Ingestion completed!")
            
            # Success
            st.success("🎉 **SIMPLE INGESTION SUCCESSFUL!**")
            st.balloons()
            
            # Results
            with st.expander("📊 Results", expanded=True):
                st.write(f"**File:** {uploaded_file.name}")
                st.write(f"**Index:** {index_name}")
                st.write(f"**Chunks:** {len(chunks)}")
                st.write(f"**Vectors:** {len(vectors)}")
            
            # Search test
            st.subheader("🔍 Test Search")
            query = st.text_input("Enter search query:")
            
            if query and st.button("Search"):
                try:
                    query_embedding = generate_simple_embeddings([query])[0]
                    results = index.query(
                        vector=query_embedding,
                        top_k=3,
                        include_metadata=True
                    )
                    
                    st.write("**Results:**")
                    for i, match in enumerate(results.matches, 1):
                        with st.expander(f"Result {i} (Score: {match.score:.3f})"):
                            st.write(match.metadata.get('content', 'No content'))
                            
                except Exception as e:
                    st.error(f"Search failed: {e}")
            
        except Exception as e:
            st.error(f"❌ Ingestion failed: {e}")
            import traceback
            st.code(traceback.format_exc())

# For standalone testing
if __name__ == "__main__":
    render_simple_pinecone_tab()
