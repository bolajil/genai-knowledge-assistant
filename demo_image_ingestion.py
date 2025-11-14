"""
Image Ingestion Demo - OCR-based text extraction and vector embedding
Demonstrates the complete pipeline from image upload to queryable vector store
"""

import streamlit as st
import time
from pathlib import Path
import io

# Set page config
st.set_page_config(
    page_title="Image Ingestion Demo",
    page_icon="📸",
    layout="wide"
)

st.title("📸 Image Ingestion Demo - OCR to Vector Embeddings")
st.markdown("---")

# Check dependencies
st.sidebar.header("📋 System Status")

try:
    from utils.image_text_extractor import ImageTextExtractor, PIL_AVAILABLE, TESSERACT_AVAILABLE, EASYOCR_AVAILABLE
    st.sidebar.success("✅ Image extractor loaded")
    st.sidebar.write(f"- PIL/Pillow: {'✅' if PIL_AVAILABLE else '❌'}")
    st.sidebar.write(f"- Tesseract: {'✅' if TESSERACT_AVAILABLE else '❌'}")
    st.sidebar.write(f"- EasyOCR: {'✅' if EASYOCR_AVAILABLE else '❌'}")
except Exception as e:
    st.sidebar.error(f"❌ Image extractor error: {e}")
    st.error("Please install dependencies: pip install pillow pytesseract easyocr")
    st.stop()

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    st.sidebar.success("✅ Embedding & FAISS loaded")
except Exception as e:
    st.sidebar.error(f"❌ Embedding error: {e}")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configuration")

# LLM Mode Selection
st.sidebar.subheader("🤖 AI Mode")
ai_mode = st.sidebar.radio(
    "Select AI Mode:",
    ["Vector Search Only", "RAG (LLM + Search)", "Vision LLM", "Hybrid (Best)"],
    help="""
    - Vector Search: Fast, no LLM cost
    - RAG: LLM answers from OCR text
    - Vision LLM: Direct image understanding
    - Hybrid: Combines both for best results
    """
)

# LLM Provider (if using LLM modes)
if ai_mode != "Vector Search Only":
    llm_provider = st.sidebar.selectbox(
        "LLM Provider:",
        ["openai", "anthropic"],
        help="Choose your LLM provider"
    )
    
    if llm_provider == "openai":
        llm_model = st.sidebar.selectbox(
            "Model:",
            ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            index=1,
            help="gpt-4o has vision, gpt-4o-mini is cheaper"
        )
    else:  # anthropic
        llm_model = st.sidebar.selectbox(
            "Model:",
            ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            help="All Claude 3 models have vision"
        )
else:
    llm_provider = None
    llm_model = None

st.sidebar.markdown("---")

# OCR Configuration
ocr_engine = st.sidebar.selectbox(
    "OCR Engine:",
    ["tesseract", "easyocr"],
    help="Tesseract is faster, EasyOCR is more accurate"
)

embedding_model_name = st.sidebar.selectbox(
    "Embedding Model:",
    ["all-MiniLM-L6-v2", "all-mpnet-base-v2"],
    help="MiniLM is faster, MPNet is more accurate"
)

chunk_size = st.sidebar.slider("Chunk Size", 100, 1000, 500)

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Step 1: Upload Image")
    
    uploaded_files = st.file_uploader(
        "Choose image file(s)",
        type=["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"],
        accept_multiple_files=True,
        help="Upload images containing text (scanned documents, screenshots, etc.)"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} image(s) uploaded")
        
        # Show thumbnails
        st.subheader("📸 Uploaded Images")
        thumb_cols = st.columns(min(len(uploaded_files), 4))
        for idx, file in enumerate(uploaded_files):
            with thumb_cols[idx % 4]:
                st.image(file, caption=file.name, use_column_width=True)

with col2:
    st.header("🔍 Step 2: Extract Text (OCR)")
    
    if uploaded_files and st.button("🚀 Start OCR Extraction", type="primary"):
        extractor = ImageTextExtractor(preferred_engine=ocr_engine)
        
        # Store results
        if 'extraction_results' not in st.session_state:
            st.session_state.extraction_results = []
        
        st.session_state.extraction_results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, file in enumerate(uploaded_files):
            try:
                # Sanitize filename for display
                safe_filename = file.name.encode('ascii', 'ignore').decode('ascii')
                if not safe_filename:
                    safe_filename = f"image_{idx+1}"
                
                status_text.text(f"Processing {safe_filename}...")
                
                image_bytes = file.getvalue()
                
                start_time = time.time()
                text, method, metadata = extractor.extract_text_from_image(image_bytes, safe_filename)
                extraction_time = time.time() - start_time
                
                st.session_state.extraction_results.append({
                    'filename': safe_filename,
                    'original_filename': file.name,
                    'text': text,
                    'method': method,
                    'metadata': metadata,
                    'extraction_time': extraction_time
                })
                
            except Exception as e:
                st.error(f"Error processing {file.name}: {str(e)}")
                st.session_state.extraction_results.append({
                    'filename': f"image_{idx+1}",
                    'original_filename': file.name,
                    'text': f"Error: {str(e)}",
                    'method': 'error',
                    'metadata': {'error': str(e)},
                    'extraction_time': 0
                })
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.text("✅ Extraction complete!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

# Display extraction results
if 'extraction_results' in st.session_state and st.session_state.extraction_results:
    st.markdown("---")
    st.header("📊 Step 3: Extraction Results")
    
    for result in st.session_state.extraction_results:
        with st.expander(f"📄 {result['filename']} - {result['metadata'].get('word_count', 0)} words"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("OCR Method", result['method'])
            with col2:
                st.metric("Confidence", f"{result['metadata'].get('confidence', 0):.1f}%")
            with col3:
                st.metric("Words", result['metadata'].get('word_count', 0))
            with col4:
                st.metric("Time", f"{result['extraction_time']:.2f}s")
            
            st.subheader("Extracted Text:")
            st.text_area(
                "Text content",
                result['text'],
                height=200,
                key=f"text_{result['filename']}"
            )
    
    # Step 4: Create embeddings
    st.markdown("---")
    st.header("🧠 Step 4: Create Vector Embeddings")
    
    if st.button("🔮 Generate Embeddings", type="primary"):
        try:
            with st.spinner(f"Loading embedding model: {embedding_model_name}..."):
                import warnings
                warnings.filterwarnings('ignore', category=FutureWarning)
                warnings.filterwarnings('ignore', category=DeprecationWarning)
                model = SentenceTransformer(embedding_model_name)
            
            st.success(f"✅ Model loaded: {embedding_model_name}")
            
            # Prepare texts
            all_texts = []
            all_metadata = []
            
            for result in st.session_state.extraction_results:
                # Skip error results
                if result['method'] == 'error':
                    continue
                    
                text = result['text']
                
                # Skip if no text extracted
                if not text or text.startswith('[Image:') or text.startswith('Error:'):
                    st.warning(f"⚠️ Skipping {result['filename']} - no valid text extracted")
                    continue
                
                # Chunk text
                words = text.split()
                chunks = []
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size])
                    if chunk.strip() and len(chunk.strip()) > 10:  # Minimum chunk length
                        chunks.append(chunk)
                
                if not chunks:
                    st.warning(f"⚠️ Skipping {result['filename']} - text too short")
                    continue
                
                for chunk_idx, chunk in enumerate(chunks):
                    all_texts.append(chunk)
                    all_metadata.append({
                        'filename': result['filename'],
                        'chunk_id': chunk_idx,
                        'total_chunks': len(chunks),
                        'ocr_method': result['method'],
                        'ocr_confidence': result['metadata'].get('confidence', 0)
                    })
            
            if not all_texts:
                st.error("❌ No valid text found to create embeddings. Please check OCR results.")
                st.stop()
            
            st.info(f"📝 Created {len(all_texts)} chunks from {len(st.session_state.extraction_results)} images")
            
            # Generate embeddings
            with st.spinner("🔮 Generating embeddings..."):
                embeddings = model.encode(all_texts, show_progress_bar=False, convert_to_numpy=True)
            
            st.success(f"✅ Generated {len(embeddings)} embeddings ({embeddings.shape[1]}-dimensional)")
            
            # Create FAISS index
            with st.spinner("📊 Creating FAISS index..."):
                dimension = embeddings.shape[1]
                index = faiss.IndexFlatL2(dimension)
                index.add(embeddings.astype('float32'))
            
            st.success(f"✅ FAISS index created with {index.ntotal} vectors")
            
            # Store in session state
            st.session_state.faiss_index = index
            st.session_state.embeddings = embeddings
            st.session_state.chunks = all_texts
            st.session_state.metadata = all_metadata
            st.session_state.model = model
            
            # Show sample embeddings
            with st.expander("🔍 View Sample Embeddings"):
                st.write("First 3 chunks and their embeddings:")
                for i in range(min(3, len(all_texts))):
                    st.write(f"**Chunk {i+1}:** {all_texts[i][:100]}...")
                    st.write(f"**Embedding:** {embeddings[i][:10]}... (showing first 10 dimensions)")
                    st.write(f"**Metadata:** {all_metadata[i]}")
                    st.markdown("---")
        
        except Exception as e:
            st.error(f"❌ Error generating embeddings: {str(e)}")
            import traceback
            with st.expander("🐛 Error Details"):
                st.code(traceback.format_exc())

# Step 5: Query the index
if 'faiss_index' in st.session_state:
    st.markdown("---")
    st.header("🔎 Step 5: Query Your Images")
    
    query = st.text_input(
        "Enter your query:",
        placeholder="e.g., 'What is the invoice number?' or 'Find information about dates'"
    )
    
    top_k = st.slider("Number of results:", 1, 10, 3)
    
    if query and st.button("🔍 Search", type="primary"):
        model = st.session_state.model
        index = st.session_state.faiss_index
        chunks = st.session_state.chunks
        metadata = st.session_state.metadata
        
        # Generate query embedding
        with st.spinner("🔮 Encoding query..."):
            query_embedding = model.encode([query])
        
        # Search
        with st.spinner("🔍 Searching..."):
            distances, indices = index.search(query_embedding.astype('float32'), top_k * 2)  # Get more to filter
        
        # Filter and deduplicate results
        seen_chunks = set()
        valid_results = []
        
        for idx, distance in zip(indices[0], distances[0]):
            # Skip invalid results (infinite distance)
            if distance > 1e10:
                continue
            
            # Skip duplicates
            chunk_text = chunks[idx]
            if chunk_text in seen_chunks:
                continue
            
            seen_chunks.add(chunk_text)
            
            # Calculate similarity score (0-1, higher is better)
            similarity = 1 / (1 + distance)
            
            # Skip very low similarity results
            if similarity < 0.1:
                continue
            
            valid_results.append({
                'idx': idx,
                'distance': distance,
                'similarity': similarity,
                'chunk': chunk_text,
                'metadata': metadata[idx]
            })
            
            # Limit to requested number
            if len(valid_results) >= top_k:
                break
        
        # Use LLM if enabled
        llm_answer = None
        if ai_mode != "Vector Search Only" and valid_results:
            try:
                from utils.image_llm_query import create_image_query_system
                
                # Get retrieved chunks
                retrieved_chunks = [r['chunk'] for r in valid_results]
                result_metadata = [r['metadata'] for r in valid_results]
                
                # Get image bytes if needed for vision/hybrid
                image_bytes_for_llm = None
                if ai_mode in ["Vision LLM", "Hybrid (Best)"] and 'extraction_results' in st.session_state:
                    # Get the first image bytes
                    for result in st.session_state.extraction_results:
                        if result['filename'] == valid_results[0]['metadata']['filename']:
                            # Re-upload or store image bytes in session state
                            # For now, we'll skip vision mode in demo
                            pass
                
                # Determine mode
                if ai_mode == "RAG (LLM + Search)":
                    mode = "rag"
                elif ai_mode == "Vision LLM":
                    mode = "vision"
                else:  # Hybrid
                    mode = "hybrid"
                
                # Create query system
                with st.spinner(f"🤖 Generating {ai_mode} answer..."):
                    query_system = create_image_query_system(
                        mode=mode if mode != "hybrid" or image_bytes_for_llm else "rag",  # Fallback to RAG if no image
                        provider=llm_provider,
                        model=llm_model
                    )
                    
                    # Query
                    llm_result = query_system.query(
                        query=query,
                        image_bytes=image_bytes_for_llm,
                        retrieved_chunks=retrieved_chunks,
                        metadata=result_metadata
                    )
                    
                    if llm_result.get('success'):
                        llm_answer = llm_result
            
            except Exception as e:
                st.error(f"LLM Error: {str(e)}")
                import traceback
                with st.expander("🐛 Error Details"):
                    st.code(traceback.format_exc())
        
        # Display LLM Answer first if available
        if llm_answer and llm_answer.get('success'):
            st.success(f"✅ {ai_mode} Answer Generated")
            
            st.markdown("---")
            st.subheader("🤖 AI-Generated Answer")
            
            # Display answer in a nice box
            st.markdown(f"""
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #2196F3;">
                <h4 style="margin-top: 0; color: #1976D2;">💡 Answer:</h4>
                <p style="font-size: 16px; line-height: 1.6; color: #263238;">{llm_answer['answer']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"🤖 Mode: **{llm_answer.get('mode', 'N/A')}**")
            with col2:
                tokens = llm_answer.get('prompt_tokens', 0) + llm_answer.get('completion_tokens', 0)
                st.caption(f"🔢 Tokens: **{tokens}**")
            with col3:
                st.caption(f"📊 Sources: **{len(valid_results)}**")
            
            st.markdown("---")
        
        # Display results
        if not valid_results:
            st.warning("⚠️ No relevant results found. Try a different query.")
        else:
            if not llm_answer:
                st.success(f"✅ Found {len(valid_results)} relevant result(s)")
            else:
                st.info(f"📚 Source Documents ({len(valid_results)} found)")
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                avg_similarity = sum(r['similarity'] for r in valid_results) / len(valid_results)
                st.metric("Average Similarity", f"{avg_similarity:.1%}")
            with col2:
                best_similarity = max(r['similarity'] for r in valid_results)
                st.metric("Best Match", f"{best_similarity:.1%}")
            with col3:
                st.metric("Total Results", len(valid_results))
            
            st.markdown("---")
            st.subheader("📊 Search Results")
            
            for rank, result in enumerate(valid_results, 1):
                meta = result['metadata']
                similarity = result['similarity']
                
                # Color code by similarity
                if similarity > 0.7:
                    badge = "🟢 Excellent Match"
                    color = "green"
                elif similarity > 0.5:
                    badge = "🟡 Good Match"
                    color = "orange"
                else:
                    badge = "🟠 Fair Match"
                    color = "red"
                
                with st.expander(f"**Result #{rank}** - {badge} ({similarity:.1%})", expanded=(rank == 1)):
                    # Header with key info
                    st.markdown(f"**Source:** `{meta['filename']}` | **Confidence:** {meta['ocr_confidence']:.1f}%")
                    
                    # Content
                    st.markdown("### 📄 Extracted Text:")
                    
                    # Get content
                    content = result['chunk']
                    
                    # Clean up OCR artifacts
                    content_cleaned = content.replace(':..', '').replace('Ju', '').strip()
                    
                    # Escape HTML special characters
                    import html
                    content_escaped = html.escape(content_cleaned)
                    
                    # Display in a nice box with proper text color
                    st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 5px; border-left: 4px solid {color}; color: #262730;">
                        <pre style="white-space: pre-wrap; font-family: inherit; margin: 0; color: #262730;">{content_escaped}</pre>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Also show as plain text for fallback
                    if not content_cleaned:
                        st.warning("⚠️ No text content to display")
                    
                    # Metadata
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.caption(f"📊 Similarity: **{similarity:.1%}**")
                    with col2:
                        st.caption(f"📏 Distance: **{result['distance']:.2f}**")
                    with col3:
                        st.caption(f"🎯 OCR: **{meta['ocr_confidence']:.0f}%**")
                    with col4:
                        st.caption(f"📝 Method: **{meta['ocr_method']}**")

# Performance metrics
if 'extraction_results' in st.session_state and st.session_state.extraction_results:
    st.sidebar.markdown("---")
    st.sidebar.header("📈 Performance Metrics")
    
    total_images = len(st.session_state.extraction_results)
    total_words = sum(r['metadata'].get('word_count', 0) for r in st.session_state.extraction_results)
    total_time = sum(r['extraction_time'] for r in st.session_state.extraction_results)
    avg_confidence = sum(r['metadata'].get('confidence', 0) for r in st.session_state.extraction_results) / total_images if total_images > 0 else 0
    
    st.sidebar.metric("Images Processed", total_images)
    st.sidebar.metric("Total Words", total_words)
    st.sidebar.metric("Total Time", f"{total_time:.2f}s")
    st.sidebar.metric("Avg Confidence", f"{avg_confidence:.1f}%")
    
    if 'faiss_index' in st.session_state:
        st.sidebar.metric("Vectors in Index", st.session_state.faiss_index.ntotal)
        st.sidebar.metric("Vector Dimension", st.session_state.embeddings.shape[1])

# Instructions
with st.sidebar.expander("📖 How to Use"):
    st.markdown("""
    **Step-by-Step Guide:**
    
    1. **Upload Images** 📤
       - Click "Browse files"
       - Select images with text
       - Supports: JPG, PNG, GIF, etc.
    
    2. **Extract Text** 🔍
       - Click "Start OCR Extraction"
       - Wait for processing
       - Review extracted text
    
    3. **Generate Embeddings** 🧠
       - Click "Generate Embeddings"
       - Creates vector representations
       - Builds searchable index
    
    4. **Query** 🔎
       - Enter your question
       - Get relevant chunks
       - See source images
    
    **Tips:**
    - Use clear, high-resolution images
    - Tesseract is faster for simple text
    - EasyOCR works better for complex layouts
    - Adjust chunk size for better results
    """)

# Footer
st.markdown("---")
st.caption("📸 Image Ingestion Demo | OCR → Embeddings → Vector Search | VaultMind GenAI Knowledge Assistant")
