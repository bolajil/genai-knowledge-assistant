"""
Demo Mode utilities: build a small FAISS index automatically for a zero-config demo.
- Uses the local sentence-transformers model if available (models/all-minLM-L6-v2/)
- Creates an index at data/indexes/<index_name>/ if missing
- Writes a small demo text source to build from (demo_source.txt)
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Tuple

from .embedding_generator import create_vector_index_from_text

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_ROOTS = [
    PROJECT_ROOT / "data" / "indexes",
    PROJECT_ROOT / "data" / "faiss_index",
]

DEMO_TEXT = (
    "VaultMind Demo Knowledge Base\n\n"
    "This demo showcases an enterprise GenAI knowledge assistant capable of hybrid search,\n"
    "Weaviate/FAISS vector retrieval, and structured LLM outputs with citations.\n\n"
    "Key concepts:\n"
    "- Hybrid search combines BM25 keyword matching and vector similarity with re-ranking.\n"
    "- Role-based permissions (RBAC) ensure secure access to sensitive documents.\n"
    "- Structured outputs include citations and section references for traceability.\n\n"
    "Sample policy content:\n"
    "Article 1 — Access Control: Users must authenticate and will be granted access based on role.\n"
    "Article 2 — Document Sources: Policies may reside in SharePoint, Confluence, PDFs, Excel, and BI dashboards.\n"
    "Article 3 — Retrieval Quality: Responses should include citations to the originating section or page.\n"
)


def ensure_demo_index(index_name: str = "demo_index") -> Tuple[bool, str, Path | None]:
    """
    Ensure a demo FAISS index exists. Returns (created_or_exists, message, index_dir).
    """
    # Choose an output root that exists or can be created
    index_root = None
    for root in DEFAULT_INDEX_ROOTS:
        try:
            root.mkdir(parents=True, exist_ok=True)
            index_root = root
            break
        except Exception as e:
            logger.debug(f"Could not create index root {root}: {e}")
            continue

    if index_root is None:
        return False, "No writable index root available under data/indexes or data/faiss_index.", None

    index_dir = index_root / index_name
    faiss_file = index_dir / "index.faiss"
    meta_file = index_dir / "index.pkl"

    if faiss_file.exists() and meta_file.exists():
        return True, f"Demo index already present at {index_dir}", index_dir

    try:
        index_dir.mkdir(parents=True, exist_ok=True)
        # Write a small demo source file
        source_path = index_dir / "demo_source.txt"
        if not source_path.exists():
            source_path.write_text(DEMO_TEXT, encoding="utf-8")
        # Build the FAISS index from the source file
        result = create_vector_index_from_text(
            text_file_path=source_path,
            index_name=index_name,
            output_dir=index_dir,
            chunk_size=1500,
            chunk_overlap=500,
        )
        if result.get("success"):
            return True, f"Created demo index at {index_dir}", index_dir
        else:
            return False, f"Failed to create demo index: {result.get('error','unknown error')}", index_dir
    except Exception as e:
        logger.error(f"Demo index creation failed: {e}")
        return False, f"Demo index creation failed: {e}", index_dir
