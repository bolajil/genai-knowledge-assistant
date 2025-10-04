import os
import sys
import json
from datetime import datetime


def main():
    print("=== Weaviate Query Diagnostics ===")
    try:
        from utils.weaviate_manager import get_weaviate_manager
    except Exception as e:
        print("Import error for weaviate_manager:", e)
        sys.exit(1)

    wm = get_weaviate_manager()

    try:
        base = wm.url
    except Exception:
        base = os.getenv("WEAVIATE_URL", "(unknown)")
    print("Weaviate base:", base)

    try:
        collections = wm.list_collections() or []
        print("Collections ({}):".format(len(collections)), collections)
    except Exception as e:
        print("Error listing collections:", e)
        collections = []

    # Resolve target collection
    target = os.getenv("TEST_COLLECTION")
    if not target:
        if "Bylaws20" in collections:
            target = "Bylaws20"
        elif collections:
            target = collections[0]
        else:
            target = ""

    if target:
        print("Target collection:", target)
    else:
        print("No collections available to test. Exiting.")
        return

    # Show counts
    try:
        cnt = wm.get_collection_count(target)
        print(f"Object count for '{target}':", cnt)
    except Exception as e:
        print("Count error:", e)

    # Choose a query
    q = os.getenv("TEST_QUERY", "Summarize this document")

    # Try client-side query vector mode first
    # Use same model as ingestion if known
    model = os.getenv("WEAVIATE_QUERY_MODEL_NAME") or os.getenv("EMBEDDING_MODEL_NAME") or "all-MiniLM-L6-v2"
    os.environ["WEAVIATE_QUERY_MODEL_NAME"] = model
    os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = os.getenv("WEAVIATE_USE_CLIENT_VECTORS", "true")

    print("\n-- Attempt 1: client-side query vectors (near_vector) --")
    print("WEAVIATE_USE_CLIENT_VECTORS=", os.environ["WEAVIATE_USE_CLIENT_VECTORS"], " model=", model)
    try:
        res = wm.search(collection_name=target, query=q, limit=3)
        print("Results:")
        if isinstance(res, list):
            for i, r in enumerate(res):
                try:
                    snippet = (r.get("content", "") or "")[:120].replace("\n", " ")
                    score = r.get("score") or r.get("relevance_score")
                except Exception:
                    snippet, score = str(r)[:120], None
                print(f"  [{i+1}] score={score} snippet={snippet}")
            if not res:
                print("  (no results)")
        else:
            print(res)
    except Exception as e:
        print("Client-side query vector search error:", e)

    # Try hybrid (will also supply query vector if client mode is enabled)
    print("\n-- Attempt 2: hybrid search --")
    try:
        res2 = wm.hybrid_search(collection_name=target, query=q, limit=3)
        print("Hybrid results:")
        if isinstance(res2, list):
            for i, r in enumerate(res2):
                try:
                    snippet = (r.get("content", "") or "")[:120].replace("\n", " ")
                    score = r.get("score") or r.get("relevance_score")
                except Exception:
                    snippet, score = str(r)[:120], None
                print(f"  [{i+1}] score={score} snippet={snippet}")
            if not res2:
                print("  (no results)")
        else:
            print(res2)
    except Exception as e:
        print("Hybrid search error:", e)

    # Try server-side vectorizer mode (near_text) explicitly
    print("\n-- Attempt 3: server-side near_text (disable client vectors) --")
    os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = "false"
    try:
        res3 = wm.search(collection_name=target, query=q, limit=3)
        print("near_text results:")
        if isinstance(res3, list):
            for i, r in enumerate(res3):
                try:
                    snippet = (r.get("content", "") or "")[:120].replace("\n", " ")
                    score = r.get("score") or r.get("relevance_score")
                except Exception:
                    snippet, score = str(r)[:120], None
                print(f"  [{i+1}] score={score} snippet={snippet}")
            if not res3:
                print("  (no results)")
        else:
            print(res3)
    except Exception as e:
        print("near_text search error:", e)

    print("\nDiagnostics complete at", datetime.now().isoformat())


if __name__ == "__main__":
    main()
