#!/usr/bin/env python3
"""
Standalone Pinecone Document Ingestion Tool
Bypasses all the complex multi-vector system and works directly with Pinecone
"""

import streamlit as st
import os
import io
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

# Load environment
from dotenv import load_dotenv
for env_file in [".env", "config/weaviate.env", "config/storage.env"]:
    if Path(env_file).exists():
        load_dotenv(env_file, override=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_file(uploaded_file) -> str:
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
            # Text file
            return uploaded_file.read().decode('utf-8')
    except Exception as e:
        return f"Error reading file: {e}"

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple text chunking"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
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

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using sentence-transformers"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(texts)
        return [emb.tolist() for emb in embeddings]
    except Exception as e:
        st.error(f"Failed to generate embeddings: {e}")
        return []

def standalone_pinecone_ingestion():
    """Standalone Pinecone ingestion interface"""
    
    st.title("🚀 Standalone Pinecone Document Ingestion")
    st.markdown("**Direct Pinecone ingestion - bypasses all complex systems**")
    
    # Check API key
    api_key = os.getenv('PINECONE_API_KEY')
    if not api_key:
        st.error("❌ PINECONE_API_KEY not found in environment")
        st.info("Add your Pinecone API key to config/storage.env")
        return
    
    st.success(f"✅ Pinecone API key found: {api_key[:8]}...")
    
    # Test Pinecone connection
    with st.expander("🔍 Connection Test", expanded=True):
        if st.button("Test Pinecone Connection"):
            try:
                import pinecone
                from pinecone import Pinecone, ServerlessSpec
                
                client = Pinecone(api_key=api_key)
                indexes = client.list_indexes()
                
                st.success(f"✅ Connected to Pinecone: {len(indexes)} indexes found")
                
                # Show existing indexes
                if indexes:
                    st.write("**Existing indexes:**")
                    for idx in indexes:
                        if hasattr(idx, 'name'):
                            st.write(f"- {idx.name}")
                        elif isinstance(idx, dict):
                            st.write(f"- {idx.get('name', 'Unknown')}")
                        else:
                            st.write(f"- {idx}")
                
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
                return
    
    # File upload
    st.subheader("📄 Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['txt', 'pdf'],
        help="Upload a text or PDF file for ingestion"
    )
    
    if not uploaded_file:
        st.info("👆 Upload a file to continue")
        return
    
    # Index configuration
    st.subheader("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        index_name = st.text_input(
            "Index Name",
            value="standalone-test",
            help="Name for the Pinecone index (lowercase, numbers, hyphens only)"
        )
        
        # Sanitize index name
        import re
        sanitized_name = re.sub(r'[^a-z0-9-]', '-', index_name.lower())
        sanitized_name = re.sub(r'^-+|-+$', '', sanitized_name)
        sanitized_name = re.sub(r'-+', '-', sanitized_name)
        if len(sanitized_name) > 45:
            sanitized_name = sanitized_name[:45].rstrip('-')
        if not sanitized_name:
            sanitized_name = "standalone-test"
        
        if sanitized_name != index_name:
            st.info(f"Index name sanitized to: `{sanitized_name}`")
            index_name = sanitized_name
    
    with col2:
        chunk_size = st.slider("Chunk Size", 500, 2000, 1000, 100)
        chunk_overlap = st.slider("Chunk Overlap", 0, 500, 200, 50)
    
    # Ingestion button
    if st.button("🚀 Start Standalone Ingestion", type="primary"):
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Extract text
            status_text.text("📖 Extracting text from file...")
            text = extract_text_from_file(uploaded_file)
            
            if not text or len(text.strip()) < 10:
                st.error("❌ Could not extract meaningful text from file")
                return
            
            st.success(f"✅ Extracted {len(text)} characters")
            progress_bar.progress(0.2)
            
            # Chunk text
            status_text.text("✂️ Chunking text...")
            chunks = chunk_text(text, chunk_size, chunk_overlap)
            
            if not chunks:
                st.error("❌ No text chunks created")
                return
            
            st.success(f"✅ Created {len(chunks)} text chunks")
            progress_bar.progress(0.4)
            
            # Generate embeddings
            status_text.text("🧠 Generating embeddings...")
            embeddings = generate_embeddings(chunks)
            
            if not embeddings:
                st.error("❌ Failed to generate embeddings")
                return
            
            st.success(f"✅ Generated {len(embeddings)} embeddings")
            progress_bar.progress(0.6)
            
            # Connect to Pinecone
            status_text.text("🔌 Connecting to Pinecone...")
            import pinecone
            from pinecone import Pinecone, ServerlessSpec
            
            client = Pinecone(api_key=api_key)
            progress_bar.progress(0.7)
            
            # Create or get index
            status_text.text(f"📊 Creating/getting index: {index_name}")
            
            # Check if index exists
            existing_indexes = client.list_indexes()
            existing_names = []
            for idx in existing_indexes:
                if hasattr(idx, 'name'):
                    existing_names.append(idx.name)
                elif isinstance(idx, dict):
                    existing_names.append(idx.get('name', ''))
                else:
                    existing_names.append(str(idx))
            
            if index_name not in existing_names:
                # Create new index
                client.create_index(
                    name=index_name,
                    dimension=384,  # MiniLM dimension
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                st.success(f"✅ Created new index: {index_name}")
            else:
                st.info(f"ℹ️ Using existing index: {index_name}")
            
            progress_bar.progress(0.8)
            
            # Get index client
            index = client.Index(index_name)
            
            # Prepare documents for upsert
            status_text.text("📤 Uploading documents to Pinecone...")
            
            vectors_to_upsert = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_id = f"{uploaded_file.name}_{i}_{datetime.now().timestamp()}"
                
                vectors_to_upsert.append({
                    "id": doc_id,
                    "values": embedding,
                    "metadata": {
                        "content": chunk[:40000],  # Pinecone metadata limit
                        "source": uploaded_file.name,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "created_at": datetime.now().isoformat()
                    }
                })
            
            # Upsert in batches
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                index.upsert(vectors=batch)
            
            progress_bar.progress(1.0)
            status_text.text("✅ Ingestion completed!")
            
            # Success message
            st.success("🎉 **STANDALONE INGESTION SUCCESSFUL!**")
            st.balloons()
            
            # Show results
            with st.expander("📊 Ingestion Results", expanded=True):
                st.write(f"**File:** {uploaded_file.name}")
                st.write(f"**Index:** {index_name}")
                st.write(f"**Text chunks:** {len(chunks)}")
                st.write(f"**Vectors uploaded:** {len(vectors_to_upsert)}")
                st.write(f"**Timestamp:** {datetime.now().isoformat()}")
            
            # Test search
            st.subheader("🔍 Test Search")
            test_query = st.text_input("Enter a test query:")
            
            if test_query and st.button("Search"):
                try:
                    # Generate query embedding
                    query_embedding = generate_embeddings([test_query])[0]
                    
                    # Search
                    results = index.query(
                        vector=query_embedding,
                        top_k=3,
                        include_metadata=True
                    )
                    
                    st.write("**Search Results:**")
                    for i, match in enumerate(results.matches, 1):
                        with st.expander(f"Result {i} (Score: {match.score:.3f})"):
                            st.write(match.metadata.get('content', 'No content'))
                            
                except Exception as e:
                    st.error(f"Search failed: {e}")
            
        except Exception as e:
            st.error(f"❌ Ingestion failed: {e}")
            import traceback
            st.code(traceback.format_exc())

if __name__ == "__main__":
    standalone_pinecone_ingestion()
