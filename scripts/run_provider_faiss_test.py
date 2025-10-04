import os
import sys
from pathlib import Path
import json

# Configure environment BEFORE importing provider
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    # Ensure top-level packages (e.g., 'utils') are importable when running from scripts/
    sys.path.insert(0, str(PROJECT_ROOT))
local_model_path = PROJECT_ROOT / "models" / "all-minLM-L6-v2"
backup_index_path = PROJECT_ROOT / "data" / "backups" / "50_index_backup_20250809_132534"

# Prefer local model to avoid network calls
os.environ["DEFAULT_EMBEDDING_MODEL"] = str(local_model_path)
# Ensure Weaviate is disabled for this test
os.environ["ENABLE_WEAVIATE"] = "false"
# Prefer backup FAISS path as well if present, in addition to the primary
faiss_paths = [PROJECT_ROOT / "data" / "faiss_index"]
if backup_index_path.exists():
    faiss_paths.append(backup_index_path)
os.environ["FAISS_INDEX_PATHS"] = ",".join(str(p) for p in faiss_paths)

print(f"Using local embedding model path: {local_model_path}")
print(f"Model path exists: {local_model_path.exists()}")
print(f"FAISS_INDEX_PATHS: {os.environ['FAISS_INDEX_PATHS']}")

# Import provider
try:
    from utils.vector_db_provider import get_vector_db_provider
except Exception as e:
    print("ERROR: Failed to import VectorDBProvider:", e)
    sys.exit(1)

provider = get_vector_db_provider()

# List indexes
try:
    indexes = provider.get_available_indexes(force_refresh=True)
    print("Discovered indexes:", indexes)
except Exception as e:
    print("ERROR: get_available_indexes failed:", e)
    sys.exit(1)

# Determine target index
target_index = None
if isinstance(indexes, list) and indexes:
    # Prefer base-path FAISS index named 'faiss_index' if present
    if "faiss_index" in indexes:
        target_index = "faiss_index"
    else:
        target_index = indexes[0]

if not target_index:
    print("No indexes discovered; cannot run search test.")
    sys.exit(2)

print(f"Target index: {target_index}")

# Run a simple query
query = os.environ.get("TEST_QUERY", "security policy")
print(f"Running search for query: '{query}' ...")

try:
    results = provider.search_index(query=query, index_name=target_index, top_k=5)
    print(f"Search returned {len(results)} results")
    for i, r in enumerate(results[:3]):
        # Print a compact view
        preview = r.get("content", "") or ""
        if isinstance(preview, str) and len(preview) > 200:
            preview = preview[:200] + "..."
        print(f"Result {i+1}: score={r.get('score')}, source={r.get('source')}, preview={json.dumps(preview)})")
    # Write results to JSON for out-of-band inspection
    out_path = PROJECT_ROOT / "data" / "faiss_index" / "faiss_test_results.json"
    try:
        serializable_results = []
        for r in results:
            content = r.get("content", "")
            if isinstance(content, str) and len(content) > 4000:
                content = content[:4000] + "..."
            serializable_results.append({
                "score": r.get("score"),
                "source": r.get("source"),
                "content": content,
            })
        payload = {
            "indexes": indexes,
            "target_index": target_index,
            "query": query,
            "results_count": len(results),
            "results": serializable_results,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote results JSON to {out_path}")
    except Exception as write_err:
        print("WARNING: Failed to write results JSON:", write_err)
except Exception as e:
    print("ERROR: search_index failed:", e)
    last_err = getattr(provider, 'get_last_error', lambda: None)()
    if last_err:
        print("Provider last error:", last_err)
    # Write error payload for inspection
    try:
        out_path = PROJECT_ROOT / "data" / "faiss_index" / "faiss_test_results.json"
        payload = {
            "indexes": indexes if 'indexes' in locals() else None,
            "target_index": target_index if 'target_index' in locals() else None,
            "query": query if 'query' in locals() else None,
            "error": str(e),
            "provider_last_error": last_err if last_err else None,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote error JSON to {out_path}")
    except Exception as write_err:
        print("WARNING: Failed to write error JSON:", write_err)
    sys.exit(3)
