#!/usr/bin/env python3
"""
Cleanup Script for Mock/Empty Indexes
Safely removes empty index directories and provides options for full cleanup
"""

import os
import shutil
from pathlib import Path

# Define index directories
INDEX_DIRS = [
    "data/indexes",
    "data/faiss_index",
]

def get_directory_size(path):
    """Calculate total size of directory"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_directory_size(entry.path)
    except Exception:
        pass
    return total

def list_indexes():
    """List all indexes with their status"""
    print("=" * 70)
    print("Current Indexes")
    print("=" * 70)
    
    all_indexes = []
    
    for base_dir in INDEX_DIRS:
        if not os.path.exists(base_dir):
            continue
            
        print(f"\n[{base_dir}]")
        
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                size = get_directory_size(item_path)
                file_count = sum(1 for _ in Path(item_path).rglob('*') if _.is_file())
                
                status = "EMPTY" if file_count == 0 else f"{file_count} files"
                size_str = f"{size:,} bytes" if size > 0 else "0 bytes"
                
                print(f"  - {item:30s} [{status:15s}] {size_str}")
                
                all_indexes.append({
                    'name': item,
                    'path': item_path,
                    'base': base_dir,
                    'files': file_count,
                    'size': size,
                    'empty': file_count == 0
                })
    
    print("=" * 70)
    return all_indexes

def cleanup_empty_indexes(indexes, dry_run=True):
    """Remove empty index directories"""
    empty_indexes = [idx for idx in indexes if idx['empty']]
    
    if not empty_indexes:
        print("\n[INFO] No empty indexes found!")
        return
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Found {len(empty_indexes)} empty indexes:")
    
    for idx in empty_indexes:
        print(f"  - {idx['name']} ({idx['base']})")
    
    if dry_run:
        print("\n[DRY RUN] No changes made. Run with dry_run=False to delete.")
        return
    
    # Confirm deletion
    print("\n" + "!" * 70)
    print("WARNING: This will permanently delete these directories!")
    print("!" * 70)
    response = input("\nType 'DELETE' to confirm: ")
    
    if response != "DELETE":
        print("[CANCELLED] No changes made.")
        return
    
    # Delete empty indexes
    deleted = 0
    for idx in empty_indexes:
        try:
            shutil.rmtree(idx['path'])
            print(f"[DELETED] {idx['name']}")
            deleted += 1
        except Exception as e:
            print(f"[ERROR] Could not delete {idx['name']}: {e}")
    
    print(f"\n[SUCCESS] Deleted {deleted} empty indexes")

def cleanup_specific_index(index_name, indexes):
    """Delete a specific index by name"""
    matching = [idx for idx in indexes if idx['name'] == index_name]
    
    if not matching:
        print(f"[ERROR] Index '{index_name}' not found!")
        return
    
    idx = matching[0]
    
    print(f"\nIndex: {idx['name']}")
    print(f"Path: {idx['path']}")
    print(f"Files: {idx['files']}")
    print(f"Size: {idx['size']:,} bytes")
    
    print("\n" + "!" * 70)
    print("WARNING: This will permanently delete this index!")
    print("!" * 70)
    response = input("\nType 'DELETE' to confirm: ")
    
    if response != "DELETE":
        print("[CANCELLED] No changes made.")
        return
    
    try:
        shutil.rmtree(idx['path'])
        print(f"[SUCCESS] Deleted {idx['name']}")
    except Exception as e:
        print(f"[ERROR] Could not delete: {e}")

def cleanup_all_indexes():
    """Delete ALL indexes (use with caution!)"""
    print("\n" + "!" * 70)
    print("DANGER: This will delete ALL indexes in:")
    for base_dir in INDEX_DIRS:
        if os.path.exists(base_dir):
            print(f"  - {base_dir}")
    print("!" * 70)
    
    response = input("\nType 'DELETE ALL INDEXES' to confirm: ")
    
    if response != "DELETE ALL INDEXES":
        print("[CANCELLED] No changes made.")
        return
    
    deleted = 0
    for base_dir in INDEX_DIRS:
        if not os.path.exists(base_dir):
            continue
            
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                try:
                    shutil.rmtree(item_path)
                    print(f"[DELETED] {item}")
                    deleted += 1
                except Exception as e:
                    print(f"[ERROR] Could not delete {item}: {e}")
    
    print(f"\n[SUCCESS] Deleted {deleted} indexes")

def main():
    """Main menu"""
    print("\n" + "=" * 70)
    print("Index Cleanup Tool")
    print("=" * 70)
    
    # List all indexes
    indexes = list_indexes()
    
    if not indexes:
        print("\n[INFO] No indexes found!")
        return
    
    # Show menu
    print("\nOptions:")
    print("  1. Delete all EMPTY indexes (safe)")
    print("  2. Delete a specific index")
    print("  3. Delete ALL indexes (DANGER!)")
    print("  4. Exit (no changes)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        print("\n[DRY RUN] Checking what would be deleted...")
        cleanup_empty_indexes(indexes, dry_run=True)
        
        proceed = input("\nProceed with deletion? (yes/no): ").strip().lower()
        if proceed == "yes":
            cleanup_empty_indexes(indexes, dry_run=False)
    
    elif choice == "2":
        index_name = input("\nEnter index name (e.g., 'Demo1_index'): ").strip()
        cleanup_specific_index(index_name, indexes)
    
    elif choice == "3":
        cleanup_all_indexes()
    
    elif choice == "4":
        print("\n[EXIT] No changes made.")
    
    else:
        print("\n[ERROR] Invalid choice!")

if __name__ == "__main__":
    main()
