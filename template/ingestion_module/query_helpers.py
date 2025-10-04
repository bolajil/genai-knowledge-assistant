from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path

EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"
INDEX_ROOT = Path("data/faiss_index")

def query_index(query: str, index_name: str, top_k=5):
    index_path = INDEX_ROOT / index_name
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    docs = db.similarity_search(query, k=top_k)
    return [doc.page_content for doc in docs]
