# ui/query_ui.py

import streamlit as st
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DATA_PATH = Path("data/faiss_index")
EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"


st.set_page_config(page_title="🔍 Semantic Chunk Search", page_icon="📚", layout="centered")
st.title("🔍 Semantic Chunk Search")
st.caption("Query embedded documents using semantic similarity.")

# === Index Selection
index_dirs = [d for d in DATA_PATH.iterdir() if d.is_dir()]
selected_index = st.selectbox("📂 Choose an indexed document", index_dirs)

# === Query Input
query = st.text_input("🧠 Enter your question or search phrase")
top_k = st.slider("🔢 Number of chunks to retrieve", 1, 5, 3)

if st.button("🔍 Search"):
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.load_local(selected_index, embeddings, allow_dangerous_deserialization=True)
    results = db.similarity_search(query, k=top_k)

    st.write(f"📦 Retrieved {len(results)} chunks:")
    for i, doc in enumerate(results):
        st.markdown(f"**Chunk {i+1}:**")
        st.write(doc.page_content)
