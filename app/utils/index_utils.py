from pathlib import Path
from langchain_community.vectorstores import FAISS
from app.utils.embeddings import EMBEDDINGS
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

# Define the default index root
INDEX_ROOT = Path("data/faiss_index")

def list_indexes(index_root: Path = INDEX_ROOT) -> List[str]:
    """List available FAISS indexes"""
    if not index_root.exists():
        return []
    return [f.name for f in index_root.iterdir() if f.is_dir()]

def load_index(index_name: str, index_root: Path = INDEX_ROOT):
    """
    Load a FAISS index from disk with proper error handling and security settings
    """
    try:
        # Define all possible locations where the index might be stored
        possible_paths = [
            index_root / index_name,
            Path("vectorstores") / index_name,
            Path("vectorstores/compliance_demo"),  # Your specific path
            Path("compliance_demo"),  # Index name as directory
            Path("data") / index_name,
            Path(index_name)
        ]

        # Add any other custom paths that might be specific to your project
        custom_paths = [
            Path("vectorstores/compliance_demo"),  # Your specific path
            Path("compliance_demo")  # Another possible location
        ]
        possible_paths.extend(custom_paths)

        # Try to find the first existing path that contains index files
        index_path = None
        for path in possible_paths:
            if path.exists():
                # Check if it has the required index files
                if (path / "index.faiss").exists() and (path / "index.pkl").exists():
                    index_path = path
                    logger.info(f"✅ Found valid index at: {path}")
                    break
                else:
                    logger.warning(f"Path exists but missing index files: {path}")

        if not index_path:
            available = "\n".join([str(p) for p in possible_paths])
            raise FileNotFoundError(
                f"Index '{index_name}' not found. Checked locations:\n{available}"
            )

        logger.info(f"🔍 Loading FAISS index from: {index_path}")

        # Load with security override
        return FAISS.load_local(
            folder_path=str(index_path),
            embeddings=EMBEDDINGS,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        logger.error(f"❌ Failed to load index {index_name}: {str(e)}")
        raise
