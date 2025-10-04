# ui/ingest_code_ui.py

import streamlit as st
from pathlib import Path
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.loader_helpers import save_faiss_index

DATA_PATH = Path("data")
INDEX_ROOT = Path("data/faiss_index")
EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"

st.set_page_config(page_title="💻 Code/Text Ingestion Assistant", page_icon="🧾", layout="centered")
st.title("💻 Code/Text Ingestion Assistant")
st.caption("Upload or select code/text files to embed for semantic search.")

# === Drag-and-Drop Upload
uploaded_file = st.file_uploader("📎 Upload a code or text file", type=["py", "java", "md", "txt"])

# === Static File Picker
code_files = sorted([f for f in DATA_PATH.glob("*") if f.suffix in [".py", ".java", ".md", ".txt"]])
selected_file = st.selectbox("📂 Or choose from /data folder", code_files)

chunk_size = st.slider("📏 Chunk size", min_value=100, max_value=1000, value=500, step=100)
chunk_overlap = st.slider("↔️ Chunk overlap", min_value=0, max_value=100, value=50, step=10)

if st.button("🔍 Start Ingestion"):
    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        file_name = uploaded_file.name
    elif selected_file:
        content = selected_file.read_text(encoding="utf-8")
        file_name = selected_file.name
    else:
        st.warning("⚠️ Please upload or select a file.")
        st.stop()

    st.info("🧾 Preparing document...")
    doc = Document(page_content=content)

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.split_documents([doc])

    st.write(f"📦 Estimated {len(docs)} semantic chunks")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.from_documents(docs, embeddings)

    index_name = f"{Path(file_name).stem}_index"
    save_faiss_index(db, INDEX_ROOT / index_name)

    st.success(f"✅ Embedded {len(docs)} chunks → `{index_name}`")
