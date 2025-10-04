# ui/ingest_json_ui.py

import streamlit as st
from pathlib import Path
import json
import xml.etree.ElementTree as ET
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

st.set_page_config(page_title="🗂️ JSON/XML Ingestion Assistant", page_icon="🧾", layout="centered")
st.title("🗂️ JSON/XML Ingestion Assistant")
st.caption("Upload or select structured files to embed for semantic search.")

uploaded_file = st.file_uploader("📎 Upload a JSON or XML file", type=["json", "xml"])
structured_files = sorted([f for f in DATA_PATH.glob("*") if f.suffix in [".json", ".xml"]])
selected_file = st.selectbox("📂 Or choose from /data folder", structured_files)

chunk_size = st.slider("📏 Chunk size", min_value=100, max_value=1000, value=500, step=100)
chunk_overlap = st.slider("↔️ Chunk overlap", min_value=0, max_value=100, value=50, step=10)

def flatten_json(data, prefix=""):
    lines = []
    
    if st.checkbox("👀 Preview flattened content"):
        st.text("\n".join(lines[:50]))  # Show first 50 lines
    if isinstance(data, dict):
        for k, v in data.items():
            lines.extend(flatten_json(v, f"{prefix}{k}."))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            lines.extend(flatten_json(item, f"{prefix}{i}."))
    else:
        lines.append(f"{prefix[:-1]}: {data}")
    return lines

def flatten_xml(root):
    lines = []
    
    if st.checkbox("👀 Preview flattened content"):
        st.text("\n".join(lines[:50]))  # Show first 50 lines
    for elem in root.iter():
        text = elem.text.strip() if elem.text else ""
        if text:
            lines.append(f"{elem.tag}: {text}")
    return lines

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

    st.info("🧾 Flattening structured data...")
    if file_name.endswith(".json"):
        raw = json.loads(content)
        lines = flatten_json(raw)
    elif file_name.endswith(".xml"):
        root = ET.fromstring(content)
        lines = flatten_xml(root)
    else:
        st.warning("⚠️ Unsupported file type.")
        st.stop()

    doc = Document(page_content="\n".join(lines))
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.split_documents([doc])

    st.write(f"📦 Estimated {len(docs)} semantic chunks")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.from_documents(docs, embeddings)

    index_name = f"{Path(file_name).stem}_index"
    save_faiss_index(db, INDEX_ROOT / index_name)

    st.success(f"✅ Embedded {len(docs)} chunks → `{index_name}`")
