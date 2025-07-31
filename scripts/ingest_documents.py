"""
Multi-PDF ingestion pipeline:
- Loads all PDFs in `data/`
- Chunks and embeds each document
- Saves per-doc FAISS index
"""

from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DATA_DIR = Path("data/")
VECTOR_ROOT = Path("data/faiss_index/")
PDF_GLOB = "*.pdf"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def ingest_all_pdfs():
    pdf_files = list(DATA_DIR.glob(PDF_GLOB))
    if not pdf_files:
        print("⚠️  No PDF files found in ./data")
        return

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    for pdf_path in pdf_files:
        print(f"\n📄 Processing: {pdf_path.name}")
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        print(f"📚 Loaded {len(docs)} pages")

        chunks = splitter.split_documents(docs)
        print(f"✂️  Split into {len(chunks)} chunks")

        db = FAISS.from_documents(chunks, embeddings)
        index_dir = VECTOR_ROOT / f"{pdf_path.stem}_index"
        index_dir.mkdir(parents=True, exist_ok=True)
        db.save_local(str(index_dir))
        print(f"✅ Saved FAISS index → {index_dir}")

    print("\n🎉 All documents ingested and indexed.")

if __name__ == "__main__":
    ingest_all_pdfs()
