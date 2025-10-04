"""
Migration Tools for FAISS to Weaviate
Utilities to migrate existing FAISS indexes to Weaviate collections
"""
import os
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class FAISSToWeaviateMigrator:
    """Tool to migrate FAISS indexes to Weaviate collections"""
    
    def __init__(self, weaviate_manager=None):
        """
        Initialize migrator
        
        Args:
            weaviate_manager: WeaviateManager instance
        """
        if weaviate_manager is None:
            try:
                from utils.weaviate_manager import get_weaviate_manager
                self.weaviate_manager = get_weaviate_manager()
            except ImportError:
                logger.error("Weaviate manager not available")
                self.weaviate_manager = None
        else:
            self.weaviate_manager = weaviate_manager
    
    def discover_faiss_indexes(self, base_paths: List[str] = None) -> List[Dict[str, Any]]:
        """
        Discover all FAISS indexes in the system
        
        Args:
            base_paths: List of base paths to search
            
        Returns:
            List of index information dictionaries
        """
        if base_paths is None:
            base_paths = [
                os.path.join("data", "faiss_index"),
                os.path.join("data", "indexes"),
                os.path.join("vector_store"),
                os.path.join("vectorstores")
            ]
        
        discovered_indexes = []
        
        for base_path in base_paths:
            if not os.path.exists(base_path):
                continue
                
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path):
                    faiss_file = os.path.join(item_path, "index.faiss")
                    pickle_file = os.path.join(item_path, "index.pkl")
                    
                    if os.path.exists(faiss_file) and os.path.exists(pickle_file):
                        # Get index info
                        index_info = {
                            "name": item.replace("_index", ""),
                            "path": item_path,
                            "faiss_file": faiss_file,
                            "pickle_file": pickle_file,
                            "size": self._get_directory_size(item_path),
                            "document_count": self._count_documents(pickle_file)
                        }
                        discovered_indexes.append(index_info)
        
        logger.info(f"Discovered {len(discovered_indexes)} FAISS indexes")
        return discovered_indexes
    
    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    def _count_documents(self, pickle_file: str) -> int:
        """Count documents in pickle file"""
        try:
            with open(pickle_file, "rb") as f:
                documents = pickle.load(f)
            return len(documents) if isinstance(documents, list) else 0
        except Exception as e:
            logger.warning(f"Could not count documents in {pickle_file}: {str(e)}")
            return 0
    
    def load_faiss_documents(self, pickle_file: str) -> List[Dict[str, Any]]:
        """
        Load documents from FAISS pickle file
        
        Args:
            pickle_file: Path to pickle file
            
        Returns:
            List of document dictionaries
        """
        try:
            with open(pickle_file, "rb") as f:
                documents = pickle.load(f)
            
            # Convert to standard format
            standardized_docs = []
            for doc in documents:
                if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                    # LangChain Document format
                    standardized_doc = {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "source": doc.metadata.get("source", "unknown"),
                        "source_type": "document"
                    }
                elif isinstance(doc, dict):
                    # Dictionary format
                    standardized_doc = {
                        "content": doc.get("content", doc.get("text", "")),
                        "metadata": doc.get("metadata", {}),
                        "source": doc.get("source", "unknown"),
                        "source_type": doc.get("source_type", "document")
                    }
                else:
                    # String format
                    standardized_doc = {
                        "content": str(doc),
                        "metadata": {},
                        "source": "unknown",
                        "source_type": "document"
                    }
                
                standardized_docs.append(standardized_doc)
            
            logger.info(f"Loaded {len(standardized_docs)} documents from {pickle_file}")
            return standardized_docs
            
        except Exception as e:
            logger.error(f"Error loading documents from {pickle_file}: {str(e)}")
            return []
    
    def migrate_index(self, index_info: Dict[str, Any], target_collection: str = None) -> bool:
        """
        Migrate a single FAISS index to Weaviate
        
        Args:
            index_info: Index information dictionary
            target_collection: Target Weaviate collection name
            
        Returns:
            True if migration successful
        """
        if not self.weaviate_manager:
            logger.error("Weaviate manager not available")
            return False
        
        try:
            # Determine target collection name
            if target_collection is None:
                target_collection = index_info["name"].lower().replace(" ", "_")
            
            # Load documents from FAISS
            documents = self.load_faiss_documents(index_info["pickle_file"])
            if not documents:
                logger.warning(f"No documents found in {index_info['name']}")
                return False
            
            # Create collection in Weaviate if it doesn't exist
            existing_collections = self.weaviate_manager.list_collections()
            if target_collection not in existing_collections:
                success = self.weaviate_manager.create_collection(
                    collection_name=target_collection,
                    description=f"Migrated from FAISS index: {index_info['name']}"
                )
                if not success:
                    logger.error(f"Failed to create collection {target_collection}")
                    return False
            
            # Migrate documents in batches
            batch_size = 100
            total_docs = len(documents)
            migrated_count = 0
            
            for i in range(0, total_docs, batch_size):
                batch = documents[i:i + batch_size]
                
                success = self.weaviate_manager.add_documents(target_collection, batch)
                if success:
                    migrated_count += len(batch)
                    logger.info(f"Migrated {migrated_count}/{total_docs} documents to {target_collection}")
                else:
                    logger.error(f"Failed to migrate batch {i//batch_size + 1}")
            
            if migrated_count == total_docs:
                logger.info(f"Successfully migrated {index_info['name']} to {target_collection}")
                return True
            else:
                logger.warning(f"Partial migration: {migrated_count}/{total_docs} documents migrated")
                return False
                
        except Exception as e:
            logger.error(f"Error migrating index {index_info['name']}: {str(e)}")
            return False
    
    def migrate_all_indexes(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Migrate all discovered FAISS indexes to Weaviate
        
        Args:
            dry_run: If True, only simulate migration without actual changes
            
        Returns:
            Migration report dictionary
        """
        # Discover all indexes
        indexes = self.discover_faiss_indexes()
        
        migration_report = {
            "total_indexes": len(indexes),
            "successful_migrations": 0,
            "failed_migrations": 0,
            "migrated_collections": [],
            "failed_collections": [],
            "dry_run": dry_run
        }
        
        if dry_run:
            logger.info("DRY RUN: Simulating migration of all FAISS indexes")
            for index_info in indexes:
                collection_name = index_info["name"].lower().replace(" ", "_")
                migration_report["migrated_collections"].append({
                    "source": index_info["name"],
                    "target": collection_name,
                    "document_count": index_info["document_count"],
                    "size": index_info["size"]
                })
            migration_report["successful_migrations"] = len(indexes)
        else:
            logger.info(f"Starting migration of {len(indexes)} FAISS indexes to Weaviate")
            
            for index_info in indexes:
                collection_name = index_info["name"].lower().replace(" ", "_")
                
                success = self.migrate_index(index_info, collection_name)
                
                if success:
                    migration_report["successful_migrations"] += 1
                    migration_report["migrated_collections"].append({
                        "source": index_info["name"],
                        "target": collection_name,
                        "document_count": index_info["document_count"],
                        "size": index_info["size"]
                    })
                else:
                    migration_report["failed_migrations"] += 1
                    migration_report["failed_collections"].append({
                        "source": index_info["name"],
                        "error": "Migration failed"
                    })
        
        return migration_report
    
    def generate_migration_report(self, report_path: str = None) -> str:
        """
        Generate a detailed migration report
        
        Args:
            report_path: Path to save the report file
            
        Returns:
            Report content as string
        """
        # Discover indexes
        indexes = self.discover_faiss_indexes()
        
        # Get Weaviate collections
        weaviate_collections = []
        if self.weaviate_manager:
            weaviate_collections = self.weaviate_manager.list_collections()
        
        # Generate report
        report_lines = [
            "# FAISS to Weaviate Migration Report",
            f"Generated at: {os.path.basename(__file__)}",
            "",
            "## Current FAISS Indexes",
            f"Total indexes found: {len(indexes)}",
            ""
        ]
        
        for index in indexes:
            report_lines.extend([
                f"### {index['name']}",
                f"- Path: {index['path']}",
                f"- Documents: {index['document_count']:,}",
                f"- Size: {index['size'] / (1024*1024):.2f} MB",
                ""
            ])
        
        report_lines.extend([
            "## Current Weaviate Collections",
            f"Total collections: {len(weaviate_collections)}",
            ""
        ])
        
        for collection in weaviate_collections:
            report_lines.append(f"- {collection}")
        
        report_lines.extend([
            "",
            "## Migration Recommendations",
            ""
        ])
        
        for index in indexes:
            target_name = index['name'].lower().replace(" ", "_")
            if target_name in weaviate_collections:
                report_lines.append(f"- {index['name']} → {target_name} (⚠️  Collection exists)")
            else:
                report_lines.append(f"- {index['name']} → {target_name} (✅ Ready to migrate)")
        
        report_content = "\n".join(report_lines)
        
        # Save to file if path provided
        if report_path:
            try:
                with open(report_path, 'w') as f:
                    f.write(report_content)
                logger.info(f"Migration report saved to {report_path}")
            except Exception as e:
                logger.error(f"Error saving report: {str(e)}")
        
        return report_content

def run_migration_analysis():
    """Run migration analysis and generate report"""
    migrator = FAISSToWeaviateMigrator()
    
    # Generate and display report
    report = migrator.generate_migration_report()
    print(report)
    
    return migrator

if __name__ == "__main__":
    run_migration_analysis()
