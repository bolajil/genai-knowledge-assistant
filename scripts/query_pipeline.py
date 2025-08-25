"""
Query pipeline to search FAISS index for relevant document chunks.
"""

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path

# === Config ===
VECTOR_DB_DIR = Path("data/faiss_index/")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def query_vector_store(question: str, top_k: int = 3):
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.load_local(str(VECTOR_DB_DIR), embeddings, allow_dangerous_deserialization=True)

    results = db.similarity_search(question, k=top_k)
    print(f"\n[SEARCH] Top {top_k} results for: \"{question}\"\n")
    for i, doc in enumerate(results, 1):
        print(f"{i}. {doc.page_content[:500]}...\n")

if __name__ == "__main__":
    user_query = input("Enter your question: ")
    query_vector_store(user_query)
