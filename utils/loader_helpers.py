# utils/loader_helpers.py

from pathlib import Path

def save_faiss_index(db, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    db.save_local(str(output_dir))
