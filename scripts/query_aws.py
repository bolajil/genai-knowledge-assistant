"""
Query script for AWS Rackspace cloud benefits PDF.
Searches FAISS index: data/faiss_index/Rackspace-Ebook-6-benefits-public-cloud-master-AWS-12639_index/
"""

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path

# === Paths & Config ===
#AWS_INDEX_DIR = Path("data/faiss_index/")
AWS_INDEX_DIR = Path("data/faiss_index/Rackspace-Ebook-6-benefits-public-cloud-master-AWS-12639_index/")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def query_aws_doc(question: str, top_k: int = 3):
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.load_local(str(AWS_INDEX_DIR), embeddings, allow_dangerous_deserialization=True)

    results = db.similarity_search(question, k=top_k)
    print(f"\n[SEARCH] Top {top_k} results for: \"{question}\"\n")
    for i, doc in enumerate(results, 1):
        print(f"{i}. {doc.page_content[:500].strip()}...\n")

if __name__ == "__main__":
    user_query = input("Enter your question about AWS cloud benefits: ")
    query_aws_doc(user_query)
