import argparse
import pickle
from pathlib import Path
import sys

def summarize_mapping(name, m, limit=5):
    try:
        items = list(m.items())
    except Exception:
        items = []
    print(f"  - {name}: type={type(m).__name__}, size={len(m) if hasattr(m, '__len__') else 'n/a'}")
    if items:
        print(f"    sample keys: {[items[i][0] for i in range(min(limit, len(items)))]}")


def main():
    ap = argparse.ArgumentParser(description="Inspect a FAISS metadata pickle file")
    ap.add_argument('path', type=str, help='Path to pickle file (e.g., index.pkl)')
    args = ap.parse_args()
    p = Path(args.path)
    if not p.exists():
        print(f"ERROR: file not found: {p}")
        sys.exit(1)
    try:
        with open(p, 'rb') as f:
            obj = pickle.load(f)
    except Exception as e:
        print(f"ERROR: failed to load pickle: {e}")
        sys.exit(2)

    print(f"Loaded {p}")
    print(f"Top-level type: {type(obj).__name__}")

    if isinstance(obj, tuple):
        print(f"Tuple length: {len(obj)}")
        for i, el in enumerate(obj):
            print(f" element[{i}]: type={type(el).__name__}")
        if len(obj) == 2:
            docstore, idx_map = obj
            # summarize idx_map
            if hasattr(idx_map, 'items'):
                summarize_mapping('index_to_docstore_id', idx_map)
            # docstore internals
            for attr in ('_dict', 'dict', 'docs', '_docs', 'store', '_store'):
                d = getattr(docstore, attr, None)
                if isinstance(d, dict):
                    summarize_mapping(f'docstore.{attr}', d)
                    # try sample document
                    try:
                        first_key = next(iter(d.keys()))
                        doc = d[first_key]
                        print(f"    sample doc type: {type(doc).__name__}")
                        content = getattr(doc, 'page_content', None)
                        metadata = getattr(doc, 'metadata', None)
                        print(f"    sample doc has page_content? {content is not None}, metadata type: {type(metadata).__name__ if metadata is not None else None}")
                    except Exception as e:
                        print(f"    failed to sample doc: {e}")
                    break
    elif isinstance(obj, dict):
        print(f"Dict keys: {list(obj.keys())}")
        for k in ('documents', 'texts', 'metadatas', 'metadata', 'ids', 'docstore', 'index_to_docstore_id'):
            if k in obj:
                v = obj[k]
                if isinstance(v, (list, tuple)):
                    print(f"  - {k}: type={type(v).__name__}, len={len(v)}")
                    if v:
                        print(f"    sample[0]: type={type(v[0]).__name__}")
                elif isinstance(v, dict):
                    summarize_mapping(k, v)
                else:
                    print(f"  - {k}: type={type(v).__name__}")
        # inspect possible docstore internals
        ds = obj.get('docstore')
        if ds is not None:
            for attr in ('_dict', 'dict', 'docs', '_docs', 'store', '_store'):
                d = getattr(ds, attr, None)
                if isinstance(d, dict):
                    summarize_mapping(f'docstore.{attr}', d)
                    break
    else:
        print(f"Unhandled top-level type: {type(obj)}")

if __name__ == '__main__':
    main()
