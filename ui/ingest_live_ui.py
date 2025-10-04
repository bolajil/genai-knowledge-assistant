# ui/ingest_live_ui.py

import streamlit as st
from pathlib import Path
import time
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.loader_helpers import save_faiss_index

LIVE_PATH = Path("data/live")
INDEX_ROOT = Path("data/faiss_index")
EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"


st.set_page_config(page_title="🔁 Live Ingestion Assistant", page_icon="📡", layout="centered")
st.title("🔁 Live Ingestion Assistant")
st.caption("Watches `/data/live/` for new files and embeds them automatically.")

chunk_size = st.slider("📏 Chunk size", 100, 1000, 500, step=100)
chunk_overlap = st.slider("↔️ Chunk overlap", 0, 100, 50, step=10)
poll_interval = st.slider("⏱️ Polling interval (seconds)", 2, 30, 5)

processed = set()

st.info("🟢 Live ingestion started. Drop files into `/data/live/` to ingest.")

while True:
    live_files = [f for f in LIVE_PATH.glob("*") if f.name not in processed]
    for file in live_files:
        st.write(f"📂 New file detected: `{file.name}`")
        content = file.read_text(encoding="utf-8")
        doc = Document(page_content=content)

        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        docs = splitter.split_documents([doc])

        embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
        db = FAISS.from_documents(docs, embeddings)

        index_name = f"{file.stem}_index"
        save_faiss_index(db, INDEX_ROOT / index_name)

        st.success(f"✅ Embedded {len(docs)} chunks → `{index_name}`")
        processed.add(file.name)

    time.sleep(poll_interval)
