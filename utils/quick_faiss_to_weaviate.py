"""
Quick FAISS to Weaviate Migration
Migrates documents from FAISS indexes to Weaviate collections
"""

import os
import logging
from typing import List, Dict
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


def migrate_faiss_to_weaviate(faiss_index_name: str, weaviate_collection_name: str):
    """
    Migrate documents from FAISS to Weaviate
    
    Args:
        faiss_index_name: Name of FAISS index (e.g., 'Bylaws_index')
        weaviate_collection_name: Name of Weaviate collection (e.g., 'Bylaw2025')
    """
    print(f"\n🔄 Migrating {faiss_index_name} → {weaviate_collection_name}")
    print("=" * 60)
    
    # Step 1: Load FAISS data
    print("\n📂 Step 1: Loading FAISS data...")
    faiss_data = load_faiss_data(faiss_index_name)
    
    if not faiss_data:
        print(f"❌ No data found in FAISS index: {faiss_index_name}")
        return False
    
    print(f"✅ Loaded {len(faiss_data)} documents from FAISS")
    
    # Step 2: Connect to Weaviate
    print("\n🌐 Step 2: Connecting to Weaviate...")
    try:
        import sys
        from pathlib import Path
        # Add parent directory to path
        parent_dir = str(Path(__file__).parent.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        from utils.weaviate_manager import get_weaviate_manager
        wm = get_weaviate_manager()
        print("✅ Connected to Weaviate")
    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Create collection if needed
    print(f"\n📦 Step 3: Preparing collection '{weaviate_collection_name}'...")
    try:
        # Check if collection exists
        collections = wm.list_collections()
        if weaviate_collection_name not in collections:
            print(f"Creating new collection: {weaviate_collection_name}")
            wm.create_collection(weaviate_collection_name)
        else:
            print(f"Collection already exists: {weaviate_collection_name}")
    except Exception as e:
        print(f"⚠️ Collection check/create: {e}")
    
    # Step 4: Upload documents
    print(f"\n⬆️ Step 4: Uploading {len(faiss_data)} documents to Weaviate...")
    
    success_count = 0
    error_count = 0
    
    for i, doc in enumerate(faiss_data, 1):
        try:
            # Handle different document formats
            if isinstance(doc, str):
                # Document is just a string
                weaviate_doc = {
                    'content': doc,
                    'source': faiss_index_name,
                    'page': None,
                    'metadata': {'index': i},
                }
            elif isinstance(doc, dict):
                # Document is a dictionary
                weaviate_doc = {
                    'content': doc.get('content', doc.get('text', str(doc))),
                    'source': doc.get('source', faiss_index_name),
                    'page': doc.get('page'),
                    'metadata': doc.get('metadata', {}),
                }
            else:
                # Unknown format, convert to string
                weaviate_doc = {
                    'content': str(doc),
                    'source': faiss_index_name,
                    'page': None,
                    'metadata': {'index': i},
                }
            
            # Upload to Weaviate
            wm.add_documents(
                collection_name=weaviate_collection_name,
                documents=[weaviate_doc]
            )
            
            success_count += 1
            
            # Progress indicator
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(faiss_data)} documents uploaded...")
                
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to upload document {i}: {e}")
    
    # Step 5: Summary
    print("\n" + "=" * 60)
    print("📊 Migration Summary:")
    print(f"  ✅ Successfully migrated: {success_count} documents")
    if error_count > 0:
        print(f"  ❌ Failed: {error_count} documents")
    print(f"  📍 Source: {faiss_index_name} (FAISS)")
    print(f"  📍 Destination: {weaviate_collection_name} (Weaviate)")
    print("=" * 60)
    
    return success_count > 0


def load_faiss_data(index_name: str) -> List[Dict]:
    """Load documents from FAISS index"""
    documents = []
    
    # Try different FAISS storage formats
    faiss_dir = Path("data/faiss_index")
    
    # Format 1: Standard .pkl file
    pkl_path = faiss_dir / f"{index_name}.pkl"
    if pkl_path.exists():
        try:
            with open(pkl_path, 'rb') as f:
                data = pickle.load(f)
                if isinstance(data, dict) and 'documents' in data:
                    documents = data['documents']
                elif isinstance(data, list):
                    documents = data
            print(f"  Loaded from: {pkl_path}")
        except Exception as e:
            logger.error(f"Failed to load {pkl_path}: {e}")
    
    # Format 2: Metadata file
    meta_path = faiss_dir / f"{index_name}_meta.pkl"
    if meta_path.exists() and not documents:
        try:
            with open(meta_path, 'rb') as f:
                metadata = pickle.load(f)
                if isinstance(metadata, list):
                    documents = [{'content': m.get('text', ''), 'metadata': m} for m in metadata]
            print(f"  Loaded from: {meta_path}")
        except Exception as e:
            logger.error(f"Failed to load {meta_path}: {e}")
    
    # Format 3: Index directory
    index_dir = faiss_dir / index_name
    if index_dir.exists() and not documents:
        pkl_file = index_dir / "documents.pkl"
        if pkl_file.exists():
            try:
                with open(pkl_file, 'rb') as f:
                    documents = pickle.load(f)
                print(f"  Loaded from: {pkl_file}")
            except Exception as e:
                logger.error(f"Failed to load {pkl_file}: {e}")
    
    return documents


def list_faiss_indexes() -> List[str]:
    """List available FAISS indexes"""
    faiss_dir = Path("data/faiss_index")
    if not faiss_dir.exists():
        return []
    
    indexes = set()
    
    # Find .faiss files
    for faiss_file in faiss_dir.glob("*.faiss"):
        indexes.add(faiss_file.stem)
    
    # Find .pkl files
    for pkl_file in faiss_dir.glob("*_meta.pkl"):
        indexes.add(pkl_file.stem.replace('_meta', ''))
    
    # Find directories
    for item in faiss_dir.iterdir():
        if item.is_dir():
            indexes.add(item.name)
    
    return sorted(list(indexes))


def main():
    """Interactive migration tool"""
    print("\n" + "=" * 60)
    print("🔄 FAISS to Weaviate Migration Tool")
    print("=" * 60)
    
    # List available FAISS indexes
    print("\n📂 Available FAISS Indexes:")
    indexes = list_faiss_indexes()
    
    if not indexes:
        print("❌ No FAISS indexes found in data/faiss_index/")
        return
    
    for i, idx in enumerate(indexes, 1):
        print(f"  {i}. {idx}")
    
    # Get user selection
    print("\n" + "=" * 60)
    print("\n💡 Migration Options:")
    print("\n1. Migrate Bylaws_index → Bylaw2025 (Recommended)")
    print("2. Migrate Demo1_index → Demo2025")
    print("3. Migrate AWS_index → AWS2025")
    print("4. Custom migration")
    print("5. Migrate all indexes")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        migrate_faiss_to_weaviate("Bylaws_index", "Bylaw2025")
    elif choice == "2":
        migrate_faiss_to_weaviate("Demo1_index", "Demo2025")
    elif choice == "3":
        migrate_faiss_to_weaviate("AWS_index", "AWS2025")
    elif choice == "4":
        faiss_name = input("Enter FAISS index name: ").strip()
        weaviate_name = input("Enter Weaviate collection name: ").strip()
        migrate_faiss_to_weaviate(faiss_name, weaviate_name)
    elif choice == "5":
        for idx in indexes:
            weaviate_name = f"{idx.replace('_index', '')}2025"
            migrate_faiss_to_weaviate(idx, weaviate_name)
    else:
        print("❌ Invalid choice")
    
    print("\n✅ Migration complete!")
    print("\n💡 Next steps:")
    print("1. Go to Query Assistant")
    print("2. Select 'Weaviate (Cloud Vector DB)' backend")
    print("3. Select your migrated collection")
    print("4. Query and get results from cloud!")


if __name__ == "__main__":
    main()
