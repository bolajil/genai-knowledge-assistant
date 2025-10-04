"""
Clean Index Script
Removes all documents and chunks from specified index to prepare for fresh ingestion
"""

import logging
import sys
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_index(index_name: str = "ByLawS2_index"):
    """
    Clean all documents and chunks from specified index
    
    Args:
        index_name: Name of the index to clean
    """
    
    print(f"🧹 Cleaning Index: {index_name}")
    print("=" * 50)
    
    try:
        index_path = Path(f"data/indexes/{index_name}")
        
        if not index_path.exists():
            print(f"❌ Index directory not found: {index_path}")
            return False
        
        print(f"📁 Index path: {index_path}")
        
        # List current contents
        files_to_remove = []
        dirs_to_remove = []
        
        for item in index_path.iterdir():
            if item.is_file():
                files_to_remove.append(item)
            elif item.is_dir():
                dirs_to_remove.append(item)
        
        print(f"📊 Found {len(files_to_remove)} files and {len(dirs_to_remove)} directories")
        
        if not files_to_remove and not dirs_to_remove:
            print("✅ Index is already empty")
            return True
        
        # Show what will be removed
        print("\n🗑️ Files to be removed:")
        for file in files_to_remove:
            print(f"   • {file.name}")
        
        if dirs_to_remove:
            print("\n📂 Directories to be removed:")
            for dir in dirs_to_remove:
                print(f"   • {dir.name}/")
        
        # Remove all files
        print(f"\n🧹 Removing {len(files_to_remove)} files...")
        for file in files_to_remove:
            try:
                file.unlink()
                print(f"   ✅ Removed: {file.name}")
            except Exception as e:
                print(f"   ❌ Failed to remove {file.name}: {e}")
        
        # Remove all directories
        if dirs_to_remove:
            print(f"\n🧹 Removing {len(dirs_to_remove)} directories...")
            for dir in dirs_to_remove:
                try:
                    shutil.rmtree(dir)
                    print(f"   ✅ Removed: {dir.name}/")
                except Exception as e:
                    print(f"   ❌ Failed to remove {dir.name}/: {e}")
        
        # Verify cleanup
        remaining_items = list(index_path.iterdir())
        if remaining_items:
            print(f"\n⚠️ Warning: {len(remaining_items)} items still remain:")
            for item in remaining_items:
                print(f"   • {item.name}")
        else:
            print(f"\n✅ Index {index_name} successfully cleaned!")
            print("📁 Directory is now empty and ready for fresh ingestion")
        
        return len(remaining_items) == 0
        
    except Exception as e:
        logger.error(f"Error cleaning index {index_name}: {e}")
        print(f"❌ Error: {e}")
        return False

def clean_all_indexes():
    """Clean all available indexes"""
    
    print("🧹 Cleaning All Indexes")
    print("=" * 50)
    
    indexes_path = Path("data/indexes")
    if not indexes_path.exists():
        print("❌ No indexes directory found")
        return False
    
    index_dirs = [d for d in indexes_path.iterdir() if d.is_dir()]
    
    if not index_dirs:
        print("✅ No indexes found to clean")
        return True
    
    print(f"📊 Found {len(index_dirs)} indexes:")
    for index_dir in index_dirs:
        print(f"   • {index_dir.name}")
    
    success_count = 0
    for index_dir in index_dirs:
        print(f"\n{'='*30}")
        if clean_index(index_dir.name):
            success_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Successfully cleaned {success_count}/{len(index_dirs)} indexes")
    
    return success_count == len(index_dirs)

def main():
    """Main function with user interaction"""
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            success = clean_all_indexes()
        else:
            index_name = sys.argv[1]
            success = clean_index(index_name)
    else:
        # Default: clean ByLawS2_index
        success = clean_index("ByLawS2_index")
    
    if success:
        print("\n🎉 Cleanup completed successfully!")
        print("💡 You can now ingest new documents with improved chunking")
    else:
        print("\n❌ Cleanup completed with errors")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
