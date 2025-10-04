"""
CLI: Ingest a text file into a Weaviate collection using the unified ingestion helper.

Usage examples:
  python scripts/ingest_text_to_weaviate.py --file bylaws_basic_sample.txt --collection Bylaws20 --username tester --semantic --debug
  python scripts/ingest_text_to_weaviate.py -f path/to/doc.txt -c MyCollection -u alice -q "governance" --chunk-size 512 --chunk-overlap 100

This script relies on environment variables for Weaviate:
  WEAVIATE_URL, WEAVIATE_API_KEY, (optional) OPENAI_API_KEY
It auto-loads config/weaviate.env if present.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.weaviate_ingestion_helper import get_weaviate_ingestion_helper  # noqa: E402


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    if debug:
        try:
            fh = logging.FileHandler(PROJECT_ROOT / "weaviate_run.log", mode="a", encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
            logging.getLogger().addHandler(fh)
            logging.getLogger(__name__).debug("Debug file logging enabled -> weaviate_run.log")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not attach file logger: {e}")


def _load_env() -> None:
    # Attempt to load config/weaviate.env first (matches manager behavior)
    env_path = PROJECT_ROOT / "config" / "weaviate.env"
    if env_path.exists():
        if load_dotenv is not None:
            load_dotenv(env_path.as_posix())
        else:
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            except Exception:
                pass


def _read_text_file(file_path: Path) -> str:
    raw = file_path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="ignore")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a text file into a Weaviate collection")
    parser.add_argument("--file", "-f", required=True, help="Path to the text file to ingest")
    parser.add_argument("--collection", "-c", required=True, help="Target Weaviate collection name")
    parser.add_argument("--username", "-u", default=os.getenv("INGEST_USERNAME", "Unknown"), help="Username for metadata")
    parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size (default: 512)")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="Chunk overlap (default: 100)")
    parser.add_argument("--semantic", action="store_true", help="Use semantic chunking")
    parser.add_argument("--query", "-q", default=None, help="Optional query to run after ingestion")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging and file logs")
    args = parser.parse_args(argv)

    _setup_logging(args.debug)
    _load_env()

    logger = logging.getLogger("ingest_text_to_weaviate")
    logger.info("Env summary -> WEAVIATE_URL=%s | WEAVIATE_API_KEY set=%s | OPENAI_API_KEY set=%s",
                os.getenv("WEAVIATE_URL"), bool(os.getenv("WEAVIATE_API_KEY")), bool(os.getenv("OPENAI_API_KEY")))

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return 2

    helper = get_weaviate_ingestion_helper()

    # Ensure collection exists (helper will also create on-demand, but we do it upfront for clearer logs)
    created = helper.create_collection(
        collection_name=args.collection,
        description=f"Ingested via CLI for user {args.username}",
    )
    if not created:
        logger.warning("Collection creation reported False; proceeding as it may already exist")

    # Try a readiness wait (best-effort)
    try:
        wm = helper.weaviate_manager
        if hasattr(wm, "ensure_collection_ready"):
            wm.ensure_collection_ready(args.collection, timeout=20.0, interval=1.0)
    except Exception as e:
        logger.debug(f"ensure_collection_ready error: {e}")

    # Ingest content
    text = _read_text_file(file_path)
    result = helper.ingest_text_document(
        collection_name=args.collection,
        text_content=text,
        file_name=file_path.name,
        username=args.username,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        use_semantic_chunking=args.semantic,
    )

    if not result.get("success"):
        print(f"[ERROR] Ingestion failed: {result.get('error', 'Unknown error')}")
        return 1

    print(f"[OK] Ingested '{file_path.name}' into collection '{args.collection}' with {result.get('total_chunks', 0)} chunks")

    # Optional query
    query = args.query
    if query is None:
        # Use the first few words of the file as a trivial query
        words = text.strip().split()
        query = " ".join(words[:8]) if words else "test"

    try:
        hits = helper.search_collection(args.collection, query=query, limit=3)
        print(f"[QUERY] '{query}' -> {len(hits)} hits")
        for i, h in enumerate(hits, 1):
            preview = (h.get("content", "") or "")[:120].replace("\n", " ")
            print(f"  {i}. score={h.get('score', 0)} uuid={h.get('uuid', '')} preview={preview}")
    except Exception as e:
        logger.warning(f"Query step failed: {e}")

    # List collections for visibility
    try:
        cols = helper.list_available_collections()
        print(f"[COLLECTIONS] {cols}")
    except Exception as e:
        logger.debug(f"Listing collections failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
