# template/query_ui_cli.py

from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DATA_PATH = Path("data/faiss_index")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def list_indexes():
    return [d for d in DATA_PATH.iterdir() if d.is_dir()]

def main():
    indexes = list_indexes()
    print("Available indexes:")
    for i, idx in enumerate(indexes):
        print(f"[{i}] {idx.name}")

    choice = input("Select index by number: ").strip()
    if not choice.isdigit() or int(choice) >= len(indexes):
        print("Invalid selection.")
        return

    selected_index = indexes[int(choice)]
    query = input("Enter your semantic query: ").strip()
    top_k = input("Number of chunks to retrieve (default 3): ").strip()
    top_k = int(top_k) if top_k.isdigit() else 3

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.load_local(selected_index, embeddings, allow_dangerous_deserialization=True)
    results = db.similarity_search(query, k=top_k)

    print(f"\nRetrieved {len(results)} chunks:")
    for i, doc in enumerate(results):
        print(f"\n--- Chunk {i+1} ---\n{doc.page_content}\n")

if __name__ == "__main__":
    main()
