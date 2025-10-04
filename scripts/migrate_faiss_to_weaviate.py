"""
FAISS to Weaviate Migration Script
=================================
Command-line tool to migrate existing FAISS indexes to Weaviate collections.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.faiss_to_weaviate_migrator import get_migrator
from utils.weaviate_manager import get_weaviate_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Migrate FAISS indexes to Weaviate collections')
    parser.add_argument('--list', action='store_true', help='List available FAISS indexes and Weaviate collections')
    parser.add_argument('--migrate-all', action='store_true', help='Migrate all discovered FAISS indexes')
    parser.add_argument('--migrate-index', type=str, help='Migrate specific FAISS index by name')
    parser.add_argument('--collection-name', type=str, help='Custom collection name for migration')
    parser.add_argument('--data-path', type=str, default='data', help='Base path to search for FAISS indexes')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without actually doing it')
    
    args = parser.parse_args()
    
    try:
        migrator = get_migrator()
        weaviate_manager = get_weaviate_manager()
        
        # Test Weaviate connection
        if not weaviate_manager.test_connection():
            logger.error("Cannot connect to Weaviate. Please check your configuration.")
            return 1
        
        if args.list:
            return list_status(migrator)
        elif args.migrate_all:
            return migrate_all_indexes(migrator, args.data_path, args.dry_run)
        elif args.migrate_index:
            return migrate_specific_index(migrator, args.migrate_index, args.collection_name, args.data_path, args.dry_run)
        else:
            parser.print_help()
            return 0
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1

def list_status(migrator):
    """List available indexes and collections"""
    logger.info("Checking migration status...")
    
    status = migrator.get_migration_status()
    
    print("\n" + "="*60)
    print("FAISS TO WEAVIATE MIGRATION STATUS")
    print("="*60)
    
    print(f"\n📁 FAISS Indexes Found: {status['faiss_indexes_found']}")
    for idx in status['faiss_indexes']:
        print(f"   • {idx}")
    
    print(f"\n☁️  Weaviate Collections Found: {status['weaviate_collections_found']}")
    for collection in status['weaviate_collections']:
        print(f"   • {collection}")
    
    print(f"\n🔄 Migration Candidates: {len(status['migration_candidates'])}")
    for candidate in status['migration_candidates']:
        print(f"   • {candidate} → migrated_{candidate}")
    
    if not status['migration_candidates']:
        print("   No new migrations needed!")
    
    return 0

def migrate_all_indexes(migrator, data_path, dry_run):
    """Migrate all discovered FAISS indexes"""
    logger.info(f"Discovering FAISS indexes in: {data_path}")
    
    indexes = migrator.discover_faiss_indexes(data_path)
    
    if not indexes:
        logger.info("No FAISS indexes found to migrate.")
        return 0
    
    print(f"\n🔍 Found {len(indexes)} FAISS indexes:")
    for idx in indexes:
        size_mb = idx['estimated_size'] / (1024 * 1024)
        print(f"   • {idx['name']} ({size_mb:.1f} MB) - {idx['type']}")
    
    if dry_run:
        print("\n🧪 DRY RUN: Would migrate all indexes above")
        return 0
    
    confirm = input(f"\n❓ Migrate all {len(indexes)} indexes? (y/N): ")
    if confirm.lower() != 'y':
        logger.info("Migration cancelled by user.")
        return 0
    
    logger.info("Starting migration of all indexes...")
    results = migrator.migrate_all_indexes(data_path)
    
    print("\n" + "="*60)
    print("MIGRATION RESULTS")
    print("="*60)
    print(f"Total Indexes: {results['total_indexes']}")
    print(f"Successful: {results['successful_migrations']}")
    print(f"Failed: {results['failed_migrations']}")
    
    print("\nDetailed Results:")
    for detail in results['migration_details']:
        status = "✅" if detail['success'] else "❌"
        collection = detail['collection_name']
        
        if detail['success']:
            migrated = detail.get('migrated_documents', 0)
            total = detail.get('total_documents', 0)
            rate = detail.get('migration_rate', 0) * 100
            print(f"   {status} {collection}: {migrated}/{total} docs ({rate:.1f}%)")
        else:
            error = detail.get('error', 'Unknown error')
            print(f"   {status} {collection}: {error}")
    
    return 0 if results['failed_migrations'] == 0 else 1

def migrate_specific_index(migrator, index_name, collection_name, data_path, dry_run):
    """Migrate a specific FAISS index"""
    logger.info(f"Looking for FAISS index: {index_name}")
    
    indexes = migrator.discover_faiss_indexes(data_path)
    target_index = None
    
    for idx in indexes:
        if idx['name'] == index_name:
            target_index = idx
            break
    
    if not target_index:
        logger.error(f"FAISS index '{index_name}' not found.")
        logger.info("Available indexes:")
        for idx in indexes:
            logger.info(f"   • {idx['name']}")
        return 1
    
    target_collection = collection_name or f"migrated_{index_name}"
    size_mb = target_index['estimated_size'] / (1024 * 1024)
    
    print(f"\n📋 Migration Plan:")
    print(f"   Source: {target_index['name']} ({size_mb:.1f} MB)")
    print(f"   Target: {target_collection}")
    print(f"   Type: {target_index['type']}")
    
    if dry_run:
        print("\n🧪 DRY RUN: Would migrate the index above")
        return 0
    
    confirm = input(f"\n❓ Proceed with migration? (y/N): ")
    if confirm.lower() != 'y':
        logger.info("Migration cancelled by user.")
        return 0
    
    logger.info(f"Starting migration: {index_name} → {target_collection}")
    result = migrator.migrate_index(target_index, target_collection)
    
    if result['success']:
        migrated = result.get('migrated_documents', 0)
        total = result.get('total_documents', 0)
        rate = result.get('migration_rate', 0) * 100
        print(f"\n✅ Migration successful!")
        print(f"   Collection: {result['collection_name']}")
        print(f"   Documents: {migrated}/{total} ({rate:.1f}%)")
        return 0
    else:
        error = result.get('error', 'Unknown error')
        print(f"\n❌ Migration failed: {error}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
