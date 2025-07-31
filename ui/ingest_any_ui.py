# ui/ingest_any_ui.py

import streamlit as st
from pathlib import Path
import json, xml.etree.ElementTree as ET
import pandas as pd
from bs4 import BeautifulSoup
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

st.set_page_config(page_title="🧠 Unified Ingestion Assistant", page_icon="📂", layout="centered")
st.title("🧠 Unified Ingestion Assistant")
st.caption("Upload any supported file type for semantic embedding.")

uploaded_file = st.file_uploader("📎 Upload a file", type=["csv", "html", "py", "java", "md", "txt", "json", "xml"])
chunk_size = st.slider("📏 Chunk size", 100, 1000, 500, step=100)
chunk_overlap = st.slider("↔️ Chunk overlap", 0, 100, 50, step=10)

def flatten_json(data, prefix=""):
    lines = []
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
    for elem in root.iter():
        text = elem.text.strip() if elem.text else ""
        if text:
            lines.append(f"{elem.tag}: {text}")
    return lines

if uploaded_file and st.button("🔍 Start Ingestion"):
    file_name = uploaded_file.name
    content = uploaded_file.read().decode("utf-8")
    suffix = Path(file_name).suffix

    st.info(f"🧾 Processing `{file_name}`...")

    if suffix == ".csv":
        df = pd.read_csv(uploaded_file)
        rows = [
            Document(page_content=" | ".join(f"{col}: {row[col]}" for col in df.columns))
            for _, row in df.iterrows()
        ]
        doc = Document(page_content="\n".join([r.page_content for r in rows]))
    elif suffix == ".html":
        soup = BeautifulSoup(content, "html.parser")
        doc = Document(page_content=soup.get_text(separator=" ", strip=True))
    elif suffix in [".py", ".java", ".md", ".txt"]:
        doc = Document(page_content=content)
    elif suffix == ".json":
        raw = json.loads(content)
        lines = flatten_json(raw)
        if st.checkbox("👀 Preview flattened JSON"):
            st.text("\n".join(lines[:50]))
        doc = Document(page_content="\n".join(lines))
    elif suffix == ".xml":
        root = ET.fromstring(content)
        lines = flatten_xml(root)
        if st.checkbox("👀 Preview flattened XML"):
            st.text("\n".join(lines[:50]))
        doc = Document(page_content="\n".join(lines))
    else:
        st.warning("⚠️ Unsupported file type.")
        st.stop()

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.split_documents([doc])
    st.write(f"📦 Estimated {len(docs)} semantic chunks")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.from_documents(docs, embeddings)

    index_name = f"{Path(file_name).stem}_index"
    save_faiss_index(db, INDEX_ROOT / index_name)

    st.success(f"✅ Embedded {len(docs)} chunks → `{index_name}`")
