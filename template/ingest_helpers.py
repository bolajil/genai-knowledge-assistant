# utils/ingest_helpers.py

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
#from utils.ingest_helpers import ingest_text
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from pathlib import Path

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_ROOT = Path("data/faiss_index")

def ingest_text(content: str, index_name: str, chunk_size=500, chunk_overlap=50):
    doc = Document(page_content=content)
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.split_documents([doc])

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(INDEX_ROOT / index_name)

    return len(docs)
