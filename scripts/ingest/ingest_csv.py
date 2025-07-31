# scripts/ingest/ingest_csv.py

import os, sys
from pathlib import Path
import pandas as pd
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Add project root to path for utils import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from utils.loader_helpers import save_faiss_index

DATA_PATH = Path("data")
INDEX_ROOT = Path("data/faiss_index")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

def select_csv():
    csv_files = list(DATA_PATH.glob("*.csv"))
    if not csv_files:
        print("❌ No CSV files found in /data")
        return None

    print("📂 Available CSV files:")
    for i, f in enumerate(csv_files):
        print(f"[{i}] {f.name}")

    choice = input("Select file by number: ").strip()
    if not choice.isdigit() or int(choice) >= len(csv_files):
        print("⚠️ Invalid selection.")
        return None

    return csv_files[int(choice)]

def ingest_csv(file_path: Path):
    df = pd.read_csv(file_path)
    chunks = [
        Document(page_content=" | ".join(f"{col}: {row[col]}" for col in df.columns))
        for _, row in df.iterrows()
    ]

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    docs = splitter.split_documents(chunks)

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.from_documents(docs, embeddings)

    index_name = f"{file_path.stem}_index"
    save_faiss_index(db, INDEX_ROOT / index_name)
    print(f"✅ Indexed {len(docs)} chunks from {file_path.name} → {index_name}")

if __name__ == "__main__":
    file_path = select_csv()
    if file_path:
        ingest_csv(file_path)
