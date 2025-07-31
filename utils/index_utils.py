from pathlib import Path
from langchain.vectorstores import FAISS

INDEX_ROOT = Path("data/faiss_index")

def load_index(index_name: str) -> FAISS:
    """Load FAISS index from disk."""
    index_path = INDEX_ROOT / index_name
    if not (index_path / "index.pkl").exists():
        raise FileNotFoundError(f"❌ Index not found at {index_path}")
    return FAISS.load_local(str(index_path), embeddings=None)

def list_saved_indexes() -> list:
    """Return list of valid index folders."""
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    return [
        folder.name for folder in INDEX_ROOT.iterdir()
        if folder.is_dir() and (folder / "index.pkl").exists()
    ]
