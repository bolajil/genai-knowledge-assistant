# app/utils/faiss_loader.py
from langchain_community.vectorstores import FAISS
from app.utils.embeddings import get_embeddings
import os

def safe_load_faiss(index_path: str):
    """Safely load FAISS index with all necessary overrides"""
    # Ensure environment variable is set
    os.environ["LANGCHAIN_ALLOW_DANGEROUS_DESERIALIZATION"] = "True"
    
    return FAISS.load_local(
        index_path,
        get_embeddings(),
        allow_dangerous_deserialization=True
    )
