import os
import sys
from pathlib import Path
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
from app.utils.embeddings import get_embeddings

# Add utils directory to path
utils_path = Path(__file__).resolve().parent
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

# Constants
INDEX_ROOT = Path("data/faiss_index")

def load_index(index_name: str):
    """Load a FAISS index from disk"""
    index_dir = INDEX_ROOT / index_name
    embeddings = get_embeddings()
    return FAISS.load_local(str(index_dir), embeddings, allow_dangerous_deserialization=True)

def query_index(query: str, index_name: str, top_k: int = 3):
    """Query an index and return top matching chunks"""
    db = load_index(index_name)
    results = db.similarity_search(query, k=top_k)
    return [r.page_content for r in results]
