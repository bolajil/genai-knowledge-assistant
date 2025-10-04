"""
FAISS to Weaviate Migration Tool
===============================
Migrates existing FAISS indexes to Weaviate collections for cloud-native vector search.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    
from utils.weaviate_manager import get_weaviate_manager
from utils.embeddings import get_embeddings_model

logger = logging.getLogger(__name__)

class FAISSToWeaviateMigrator:
    """Migrates FAISS indexes to Weaviate collections"""
    
    def __init__(self):
        self.weaviate_manager = get_weaviate_manager()
        self.embeddings_model = get_embeddings_model()
        
    def discover_faiss_indexes(self, base_path: str = "data") -> List[Dict]:
        """Discover all FAISS indexes in the project"""
        indexes = []
        base_path = Path(base_path)
        
        # Common FAISS index locations
        search_paths = [
            base_path / "faiss_index",
            base_path / "indexes",
            base_path / "vector_store",
            base_path / "vectorstores"
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                for item in search_path.iterdir():
                    if item.is_dir():
                        index_info = self._analyze_index_directory(item)
                        if index_info:
                            indexes.append(index_info)
        
        return indexes
    
    def _analyze_index_directory(self, index_dir: Path) -> Optional[Dict]:
        """Analyze a directory to determine if it contains a FAISS index"""
        faiss_file = None
        pkl_file = None
        meta_file = None
        
        # Look for FAISS files
        for file in index_dir.iterdir():
            if file.suffix == '.faiss':
                faiss_file = file
            elif file.suffix == '.pkl':
                pkl_file = file
            elif file.name == 'index.meta':
                meta_file = file
        
        # Determine index type and structure
        if faiss_file and pkl_file:
            return {
                'name': index_dir.name,
                'path': str(index_dir),
                'type': 'standard_faiss',
                'faiss_file': str(faiss_file),
                'metadata_file': str(pkl_file),
                'estimated_size': self._get_directory_size(index_dir)
            }
        elif meta_file:
            return {
                'name': index_dir.name,
                'path': str(index_dir),
                'type': 'meta_based',
                'meta_file': str(meta_file),
                'estimated_size': self._get_directory_size(index_dir)
            }
        
        return None
    
    def _get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes"""
        total_size = 0
        try:
            for file in directory.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size
        except Exception as e:
            logger.warning(f"Could not calculate size for {directory}: {e}")
        return total_size
    
    def migrate_index(self, index_info: Dict, collection_name: Optional[str] = None) -> Dict:
        """Migrate a single FAISS index to Weaviate"""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")
        
        collection_name = collection_name or f"migrated_{index_info['name']}"
        
        try:
            # Load FAISS index data
            documents, embeddings = self._load_faiss_data(index_info)
            
            if not documents:
                return {
                    'success': False,
                    'error': 'No documents found in FAISS index',
                    'collection_name': collection_name
                }
            
            # Create Weaviate collection
            collection_created = self.weaviate_manager.create_collection(
                collection_name=collection_name,
                description=f"Migrated from FAISS index: {index_info['name']}"
            )
            
            if not collection_created:
                return {
                    'success': False,
                    'error': 'Failed to create Weaviate collection',
                    'collection_name': collection_name
                }
            
            # Migrate documents in batches
            batch_size = 100
            total_docs = len(documents)
            migrated_count = 0
            
            for i in range(0, total_docs, batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size] if embeddings else None
                
                success = self._migrate_batch(
                    collection_name, 
                    batch_docs, 
                    batch_embeddings,
                    batch_start_idx=i
                )
                
                if success:
                    migrated_count += len(batch_docs)
                else:
                    logger.warning(f"Failed to migrate batch {i//batch_size + 1}")
            
            return {
                'success': True,
                'collection_name': collection_name,
                'total_documents': total_docs,
                'migrated_documents': migrated_count,
                'migration_rate': migrated_count / total_docs if total_docs > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Migration failed for {index_info['name']}: {e}")
            return {
                'success': False,
                'error': str(e),
                'collection_name': collection_name
            }
    
    def _load_faiss_data(self, index_info: Dict) -> Tuple[List[Dict], Optional[np.ndarray]]:
        """Load documents and embeddings from FAISS index"""
        documents = []
        embeddings = None
        
        if index_info['type'] == 'standard_faiss':
            # Load standard FAISS index
            documents, embeddings = self._load_standard_faiss(index_info)
        elif index_info['type'] == 'meta_based':
            # Load meta-based index
            documents = self._load_meta_based_index(index_info)
        
        return documents, embeddings
    
    def _load_standard_faiss(self, index_info: Dict) -> Tuple[List[Dict], Optional[np.ndarray]]:
        """Load standard FAISS index with .faiss and .pkl files"""
        documents = []
        embeddings = None
        
        try:
            # Load FAISS index
            faiss_index = faiss.read_index(index_info['faiss_file'])
            embeddings = faiss_index.reconstruct_n(0, faiss_index.ntotal)
            
            # Load metadata
            with open(index_info['metadata_file'], 'rb') as f:
                metadata = pickle.load(f)
            
            # Convert metadata to documents
            if isinstance(metadata, list):
                for i, item in enumerate(metadata):
                    if isinstance(item, dict):
                        documents.append({
                            'content': item.get('content', item.get('text', '')),
                            'metadata': {
                                'source': item.get('source', f"faiss_doc_{i}"),
                                'migrated_from': index_info['name'],
                                'migration_date': datetime.now().isoformat(),
                                **{k: v for k, v in item.items() if k not in ['content', 'text']}
                            }
                        })
                    else:
                        documents.append({
                            'content': str(item),
                            'metadata': {
                                'source': f"faiss_doc_{i}",
                                'migrated_from': index_info['name'],
                                'migration_date': datetime.now().isoformat()
                            }
                        })
            
        except Exception as e:
            logger.error(f"Failed to load standard FAISS index: {e}")
        
        return documents, embeddings
    
    def _load_meta_based_index(self, index_info: Dict) -> List[Dict]:
        """Load meta-based index structure"""
        documents = []
        
        try:
            index_dir = Path(index_info['path'])
            
            # Look for text files or extracted content
            for file in index_dir.rglob('*'):
                if file.is_file() and file.suffix in ['.txt', '.json']:
                    try:
                        content = file.read_text(encoding='utf-8')
                        
                        if file.suffix == '.json':
                            # Try to parse as JSON
                            try:
                                json_data = json.loads(content)
                                if isinstance(json_data, list):
                                    for item in json_data:
                                        documents.append(self._format_document(item, index_info, file))
                                else:
                                    documents.append(self._format_document(json_data, index_info, file))
                            except json.JSONDecodeError:
                                # Treat as plain text
                                documents.append(self._format_document(content, index_info, file))
                        else:
                            # Plain text file
                            documents.append(self._format_document(content, index_info, file))
                            
                    except Exception as e:
                        logger.warning(f"Could not read file {file}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load meta-based index: {e}")
        
        return documents
    
    def _format_document(self, content, index_info: Dict, source_file: Path) -> Dict:
        """Format content as a document for Weaviate"""
        if isinstance(content, dict):
            return {
                'content': content.get('content', content.get('text', str(content))),
                'metadata': {
                    'source': content.get('source', str(source_file.name)),
                    'migrated_from': index_info['name'],
                    'migration_date': datetime.now().isoformat(),
                    **{k: v for k, v in content.items() if k not in ['content', 'text']}
                }
            }
        else:
            return {
                'content': str(content),
                'metadata': {
                    'source': str(source_file.name),
                    'migrated_from': index_info['name'],
                    'migration_date': datetime.now().isoformat()
                }
            }
    
    def _migrate_batch(self, collection_name: str, documents: List[Dict], 
                      embeddings: Optional[np.ndarray], batch_start_idx: int = 0) -> bool:
        """Migrate a batch of documents to Weaviate"""
        try:
            for i, doc in enumerate(documents):
                # Use pre-computed embedding if available, otherwise let Weaviate compute it
                vector = embeddings[batch_start_idx + i].tolist() if embeddings is not None else None
                
                success = self.weaviate_manager.add_document(
                    collection_name=collection_name,
                    content=doc['content'],
                    metadata=doc['metadata'],
                    vector=vector
                )
                
                if not success:
                    logger.warning(f"Failed to add document {batch_start_idx + i}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Batch migration failed: {e}")
            return False
    
    def migrate_all_indexes(self, base_path: str = "data") -> Dict:
        """Migrate all discovered FAISS indexes"""
        indexes = self.discover_faiss_indexes(base_path)
        results = {
            'total_indexes': len(indexes),
            'successful_migrations': 0,
            'failed_migrations': 0,
            'migration_details': []
        }
        
        for index_info in indexes:
            logger.info(f"Migrating index: {index_info['name']}")
            result = self.migrate_index(index_info)
            results['migration_details'].append(result)
            
            if result['success']:
                results['successful_migrations'] += 1
            else:
                results['failed_migrations'] += 1
        
        return results
    
    def get_migration_status(self) -> Dict:
        """Get status of available indexes and collections"""
        faiss_indexes = self.discover_faiss_indexes()
        
        try:
            weaviate_collections = self.weaviate_manager.list_collections()
        except Exception as e:
            logger.error(f"Failed to get Weaviate collections: {e}")
            weaviate_collections = []
        
        return {
            'faiss_indexes_found': len(faiss_indexes),
            'faiss_indexes': [idx['name'] for idx in faiss_indexes],
            'weaviate_collections_found': len(weaviate_collections),
            'weaviate_collections': weaviate_collections,
            'migration_candidates': [
                idx['name'] for idx in faiss_indexes 
                if f"migrated_{idx['name']}" not in weaviate_collections
            ]
        }

def get_migrator() -> FAISSToWeaviateMigrator:
    """Get a configured FAISS to Weaviate migrator instance"""
    return FAISSToWeaviateMigrator()
