# ui/ingest_csv_ui.py

import streamlit as st
from pathlib import Path
import pandas as pd
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.loader_helpers import save_faiss_index

DATA_PATH = Path("data")
INDEX_ROOT = Path("data/faiss_index")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

st.set_page_config(page_title="📊 CSV Ingestion Assistant", page_icon="📁", layout="centered")
st.title("📊 CSV Ingestion Assistant")
st.caption("Select and embed a CSV file for semantic search.")

# === CSV File Picker
csv_files = sorted([f for f in DATA_PATH.glob("*.csv")])
selected_file = st.selectbox("📂 Choose a CSV file", csv_files)

if selected_file:
    df = pd.read_csv(selected_file)
    total_rows = df.shape[0]
    st.write(f"📄 Detected {total_rows:,} rows in `{selected_file.name}`")

    # === Optional Row Limit for Testing
    row_limit = st.slider("🧪 Row limit (for speed testing)", 100, min(total_rows, 20000), value=1000)

    chunk_size = st.slider("📏 Chunk size", min_value=100, max_value=1000, value=500, step=100)
    chunk_overlap = st.slider("↔️ Chunk overlap", min_value=0, max_value=100, value=50, step=10)

    # === Ingestion Trigger
    if st.button("🔍 Start Ingestion"):
        st.info("⚙️ Preprocessing rows...")
        rows = df.head(row_limit)
        combined_rows = [
            Document(page_content=" | ".join(f"{col}: {row[col]}" for col in rows.columns))
            for _, row in rows.iterrows()
        ]

        st.write(f"✂️ Preparing to chunk {len(combined_rows)} rows...")

        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        docs = splitter.split_documents(combined_rows)

        st.write(f"📦 Estimated {len(docs)} semantic chunks")

        st.info("🔍 Embedding chunks into FAISS index...")
        embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
        db = FAISS.from_documents(docs, embeddings)

        index_name = f"{selected_file.stem}_index"
        save_faiss_index(db, INDEX_ROOT / index_name)
        st.success(f"✅ Embedded {len(docs)} chunks from `{selected_file.name}` → `{index_name}`")


