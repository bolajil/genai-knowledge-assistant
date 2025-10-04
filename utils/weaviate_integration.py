"""
Unified Weaviate Integration for All Tabs
Provides centralized vector database connectivity across VaultMind
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import streamlit as st

# Import Weaviate components
from config.weaviate_config import get_weaviate_config, create_default_collections
from utils.weaviate_manager import WeaviateManager

logger = logging.getLogger(__name__)

class UnifiedWeaviateIntegration:
    """
    Centralized Weaviate integration for all VaultMind tabs
    Ensures consistent vector database connectivity
    """
    
    _instance = None
    _weaviate_manager = None
    _available_collections = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config = get_weaviate_config()
            self.initialized = True
    
    @property
    def weaviate_manager(self) -> WeaviateManager:
        """Get or create Weaviate manager instance"""
        if self._weaviate_manager is None:
            self._weaviate_manager = WeaviateManager(
                url=self.config.url,
                api_key=self.config.api_key,
                openai_api_key=self.config.openai_api_key
            )
        return self._weaviate_manager
    
    def get_available_indexes(self, force_refresh: bool = False) -> List[str]:
        """
        Get all available Weaviate collections/indexes
        Returns unified list for all tabs
        
        Args:
            force_refresh: If True, bypass cache and scan directories again
        """
        try:
            # Force refresh or no cached data
            if force_refresh or not self._available_collections:
                # Get collections from Weaviate
                collections = self.weaviate_manager.list_collections()
                
                # Add legacy FAISS indexes if they exist
                legacy_indexes = self._get_legacy_faiss_indexes()
                
                # Combine and deduplicate
                all_indexes = list(set(collections + legacy_indexes))
                
                # Cache for performance
                self._available_collections = all_indexes
                
                logger.info(f"Found {len(all_indexes)} total indexes: {all_indexes}")
                return all_indexes
            else:
                # Return cached results
                return self._available_collections
            
        except Exception as e:
            logger.error(f"Error getting available indexes: {str(e)}")
            # Return cached or fallback indexes
            return self._available_collections or self._get_fallback_indexes()
    
    def _get_legacy_faiss_indexes(self) -> List[str]:
        """Get legacy FAISS indexes from data directory"""
        try:
            faiss_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'faiss_index')
            if not os.path.exists(faiss_dir):
                return []
            
            indexes = []
            for item in os.listdir(faiss_dir):
                item_path = os.path.join(faiss_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    # Remove '_index' suffix if present
                    clean_name = item.replace('_index', '')
                    indexes.append(clean_name)
            
            return indexes
            
        except Exception as e:
            logger.error(f"Error reading legacy FAISS indexes: {str(e)}")
            return []
    
    def _get_fallback_indexes(self) -> List[str]:
        """Fallback indexes for demo/testing"""
        return [
            "Bylaw",
            "AWS_SECURITY", 
            "AWS-combine",
            "enterprise_docs",
            "company_policies",
            "technical_manuals"
        ]
    
    def search_unified(self, 
                      query: str, 
                      collections: List[str] = None,
                      limit: int = 10,
                      search_type: str = "hybrid") -> List[Dict[str, Any]]:
        """
        Unified search across all specified collections
        
        Args:
            query: Search query
            collections: List of collections to search (None = all)
            limit: Maximum results per collection
            search_type: 'semantic', 'keyword', or 'hybrid'
        
        Returns:
            List of search results with metadata
        """
        try:
            if collections is None:
                collections = self.get_available_indexes()
            
            all_results = []
            
            for collection in collections:
                try:
                    # Search in Weaviate collection
                    if self._is_weaviate_collection(collection):
                        results = self.weaviate_manager.search(
                            collection_name=collection,
                            query=query,
                            limit=limit
                        )
                        
                        # Add collection metadata
                        for result in results:
                            result['source_collection'] = collection
                            result['search_type'] = 'weaviate'
                            all_results.append(result)
                    
                    # Search in legacy FAISS index
                    else:
                        legacy_results = self._search_legacy_faiss(collection, query, limit)
                        for result in legacy_results:
                            result['source_collection'] = collection
                            result['search_type'] = 'faiss'
                            all_results.append(result)
                            
                except Exception as e:
                    logger.error(f"Error searching collection {collection}: {str(e)}")
                    continue
            
            # Sort by relevance score
            all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return all_results[:limit * len(collections)]
            
        except Exception as e:
            logger.error(f"Unified search error: {str(e)}")
            return []
    
    def _is_weaviate_collection(self, collection_name: str) -> bool:
        """Check if collection exists in Weaviate"""
        try:
            weaviate_collections = self.weaviate_manager.list_collections()
            return collection_name in weaviate_collections
        except:
            return False
    
    def _search_legacy_faiss(self, index_name: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search legacy FAISS indexes"""
        try:
            # Import legacy search utilities
            from utils.direct_vector_search import search_documents
            
            results = search_documents(query, index_name, top_k=limit)
            
            # Convert to unified format
            formatted_results = []
            for i, result in enumerate(results):
                formatted_results.append({
                    'content': result.get('content', ''),
                    'score': result.get('relevance', 0.0),
                    'metadata': {
                        'source': result.get('source', ''),
                        'page': result.get('page', 0),
                        'index_type': 'faiss'
                    }
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Legacy FAISS search error for {index_name}: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        try:
            stats = {
                'total_collections': 0,
                'weaviate_collections': 0,
                'faiss_collections': 0,
                'collections': {}
            }
            
            available_indexes = self.get_available_indexes()
            stats['total_collections'] = len(available_indexes)
            
            for collection in available_indexes:
                if self._is_weaviate_collection(collection):
                    stats['weaviate_collections'] += 1
                    # Get Weaviate collection stats
                    try:
                        count = self.weaviate_manager.get_collection_count(collection)
                        stats['collections'][collection] = {
                            'type': 'weaviate',
                            'document_count': count,
                            'status': 'active'
                        }
                    except:
                        stats['collections'][collection] = {
                            'type': 'weaviate',
                            'document_count': 0,
                            'status': 'error'
                        }
                else:
                    stats['faiss_collections'] += 1
                    stats['collections'][collection] = {
                        'type': 'faiss',
                        'document_count': 'unknown',
                        'status': 'legacy'
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {'total_collections': 0, 'error': str(e)}
    
    def migrate_faiss_to_weaviate(self, faiss_index_name: str) -> bool:
        """
        Migrate a FAISS index to Weaviate
        
        Args:
            faiss_index_name: Name of FAISS index to migrate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from utils.migration_tools import migrate_faiss_to_weaviate
            
            success = migrate_faiss_to_weaviate(
                faiss_index_name=faiss_index_name,
                weaviate_collection_name=faiss_index_name,
                weaviate_manager=self.weaviate_manager
            )
            
            if success:
                logger.info(f"Successfully migrated {faiss_index_name} to Weaviate")
                # Refresh available collections
                self._available_collections = []
            
            return success
            
        except Exception as e:
            logger.error(f"Migration error for {faiss_index_name}: {str(e)}")
            return False

# Global instance
weaviate_integration = UnifiedWeaviateIntegration()

def get_unified_indexes() -> List[str]:
    """
    Get unified list of all available indexes for any tab
    This is the main function tabs should use
    """
    return weaviate_integration.get_available_indexes()

def search_all_indexes(query: str, 
                      selected_indexes: List[str] = None,
                      limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search across all or selected indexes
    Unified search function for all tabs
    """
    return weaviate_integration.search_unified(
        query=query,
        collections=selected_indexes,
        limit=limit
    )

def get_index_statistics() -> Dict[str, Any]:
    """Get comprehensive index statistics"""
    return weaviate_integration.get_collection_stats()

def display_weaviate_status():
    """Display Weaviate connection status in Streamlit"""
    try:
        stats = get_index_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🗄️ Total Indexes", 
                stats.get('total_collections', 0),
                help="Total available vector indexes"
            )
        
        with col2:
            st.metric(
                "🌊 Weaviate Collections", 
                stats.get('weaviate_collections', 0),
                help="Modern Weaviate vector collections"
            )
        
        with col3:
            st.metric(
                "📁 Legacy FAISS", 
                stats.get('faiss_collections', 0),
                help="Legacy FAISS indexes"
            )
        
        with col4:
            # Connection status
            try:
                weaviate_integration.weaviate_manager.client
                st.metric("🔗 Weaviate Status", "Connected", help="Weaviate connection status")
            except:
                st.metric("🔗 Weaviate Status", "Disconnected", help="Weaviate connection status")
        
        # Detailed collection info
        if st.expander("📊 Detailed Index Information", expanded=False):
            collections = stats.get('collections', {})
            if collections:
                for name, info in collections.items():
                    col_type = info.get('type', 'unknown')
                    doc_count = info.get('document_count', 0)
                    status = info.get('status', 'unknown')
                    
                    st.write(f"**{name}** ({col_type}) - {doc_count} docs - {status}")
            else:
                st.info("No detailed collection information available")
                
    except Exception as e:
        st.error(f"Error displaying Weaviate status: {str(e)}")
