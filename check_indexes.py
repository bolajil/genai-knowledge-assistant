"""
Check FAISS Index Availability
Quick diagnostic to verify indexes are accessible
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("FAISS Index Diagnostic")
print("=" * 80)

# Check index root
index_root = project_root / "data" / "faiss_index"
print(f"\nIndex Root: {index_root}")
print(f"Exists: {index_root.exists()}")

if not index_root.exists():
    print("\n[ERROR] Index root directory does not exist!")
    print(f"Please create: {index_root}")
    sys.exit(1)

# List all directories
print(f"\nScanning for indexes...")
indexes = [d for d in index_root.iterdir() if d.is_dir()]

if not indexes:
    print("\n[WARNING] No index directories found!")
else:
    print(f"\nFound {len(indexes)} index directories:\n")
    
    for idx_dir in sorted(indexes):
        print(f"\n{idx_dir.name}:")
        print(f"  Path: {idx_dir}")
        
        # Check for required files
        index_faiss = idx_dir / "index.faiss"
        index_pkl = idx_dir / "index.pkl"
        
        print(f"  index.faiss: {'✓' if index_faiss.exists() else '✗ MISSING'}")
        print(f"  index.pkl: {'✓' if index_pkl.exists() else '✗ MISSING'}")
        
        if index_faiss.exists():
            size_mb = index_faiss.stat().st_size / (1024 * 1024)
            print(f"  Size: {size_mb:.2f} MB")
        
        # Try to load
        if index_faiss.exists() and index_pkl.exists():
            try:
                from langchain_community.vectorstores import FAISS
                from langchain_huggingface import HuggingFaceEmbeddings
                
                embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                
                db = FAISS.load_local(
                    str(idx_dir),
                    embeddings,
                    allow_dangerous_deserialization=True
                )
                
                # Try a test search
                docs = db.similarity_search("test", k=1)
                print(f"  Status: ✓ LOADABLE ({len(docs)} docs found in test search)")
                
            except Exception as e:
                print(f"  Status: ✗ ERROR - {str(e)[:100]}")
        else:
            print(f"  Status: ✗ INCOMPLETE (missing required files)")

print("\n" + "=" * 80)
print("\nSummary:")
print(f"  Total indexes: {len(indexes)}")

loadable = 0
for idx_dir in indexes:
    if (idx_dir / "index.faiss").exists() and (idx_dir / "index.pkl").exists():
        loadable += 1

print(f"  Loadable indexes: {loadable}")

if loadable == 0:
    print("\n[WARNING] No loadable indexes found!")
    print("You may need to:")
    print("  1. Ingest documents using the 'Ingest Document' tab")
    print("  2. Verify the embedding model is installed: pip install sentence-transformers")
    print("  3. Check that indexes were created successfully")
else:
    print(f"\n[OK] {loadable} indexes are ready to use!")

print("\n" + "=" * 80)
