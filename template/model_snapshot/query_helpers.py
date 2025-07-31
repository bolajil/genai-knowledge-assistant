import os
import sys
import pydantic
from langchain_huggingface import HuggingFaceEmbeddings

# Enhanced Pydantic compatibility shim
#if not hasattr(pydantic, 'v1'):
    #pydantic.v1 = pydantic
    #sys.modules['pydantic.v1'] = pydantic.v1
    # Create necessary v1 submodules
    #pydantic.v1.fields = pydantic.fields
    #sys.modules['pydantic.v1.fields'] = pydantic.fields

from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Constants
INDEX_ROOT = Path("data/faiss_index")

def load_index(index_name: str):
    """Load a FAISS index from disk"""
    index_dir = INDEX_ROOT / index_name
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return FAISS.load_local(str(index_dir), embeddings, allow_dangerous_deserialization=True)

def query_index(query: str, index_name: str, top_k: int = 3):
    """Query an index and return top matching chunks"""
    db = load_index(index_name)
    results = db.similarity_search(query, k=top_k)
    return [r.page_content for r in results]
