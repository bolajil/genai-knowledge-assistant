"""
Enhanced Vector DB Initialization

Improved vector database initialization with better error handling,
index discovery, and fallback mechanisms.
"""

import logging
import os
from pathlib import Path
from typing import Tuple, Any, List, Dict
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def discover_existing_indexes() -> Dict[str, List[Path]]:
    """
    Discover all existing vector indexes in the project
    
    Returns:
        Dictionary mapping index types to their paths
    """
    project_root = Path(__file__).resolve().parent.parent
    discovered_indexes = {
        'faiss': [],
        'text': [],
        'other': []
    }
    
    # Standard search paths
    search_paths = [
        project_root / "data" / "faiss_index",
        project_root / "data" / "indexes", 
        project_root / "vector_store",
        project_root / "vectorstores"
    ]
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
            
        logger.info(f"Searching for indexes in: {search_path}")
        
        # Look for FAISS indexes
        faiss_files = list(search_path.glob("**/*.faiss"))
        pkl_files = list(search_path.glob("**/*.pkl"))
        
        # Group FAISS files by directory
        faiss_dirs = set()
        for faiss_file in faiss_files:
            faiss_dirs.add(faiss_file.parent)
        
        for faiss_dir in faiss_dirs:
            # Check if it has both .faiss and .pkl files
            has_faiss = any(f.suffix == '.faiss' for f in faiss_dir.glob('*'))
            has_pkl = any(f.suffix == '.pkl' for f in faiss_dir.glob('*'))
            
            if has_faiss and has_pkl:
                discovered_indexes['faiss'].append(faiss_dir)
                logger.info(f"Found FAISS index: {faiss_dir}")
        
        # Look for text-based indexes
        text_files = list(search_path.glob("**/extracted_text.txt"))
        for text_file in text_files:
            discovered_indexes['text'].append(text_file.parent)
            logger.info(f"Found text index: {text_file.parent}")
    
    return discovered_indexes

def init_enhanced_vector_db_provider() -> Tuple[bool, Any]:
    """
    Enhanced vector database provider initialization
    
    Returns:
        Tuple of (success, provider)
    """
    try:
        # First, discover what indexes we actually have
        discovered_indexes = discover_existing_indexes()
        
        total_indexes = sum(len(paths) for paths in discovered_indexes.values())
        logger.info(f"Discovered {total_indexes} total indexes: "
                   f"FAISS: {len(discovered_indexes['faiss'])}, "
                   f"Text: {len(discovered_indexes['text'])}")
        
        if total_indexes == 0:
            logger.warning("No vector indexes found in the system")
            return init_fallback_provider()
        
        # Try to initialize the real vector database provider
        try:
            from utils.vector_db_provider import get_vector_db_provider
            
            provider = get_vector_db_provider()
            
            # Test the provider with discovered indexes
            status, message = provider.get_vector_db_status()
            logger.info(f"Vector DB Provider Status: {status} - {message}")
            
            if status in ["Ready", "Warning"]:
                # Provider is working, even if with warnings
                return True, provider
            else:
                logger.warning(f"Vector DB provider not ready: {message}")
                return init_fallback_provider()
                
        except Exception as e:
            logger.error(f"Failed to initialize vector DB provider: {e}")
            logger.debug(traceback.format_exc())
            return init_fallback_provider()
            
    except Exception as e:
        logger.error(f"Enhanced initialization failed: {e}")
        return init_fallback_provider()

def init_fallback_provider() -> Tuple[bool, Any]:
    """
    Initialize fallback mock provider
    
    Returns:
        Tuple of (success, provider)
    """
    try:
        from utils.mock_vector_db_provider import get_mock_vector_db_provider
        
        mock_provider = get_mock_vector_db_provider()
        logger.info("Initialized mock vector database provider")
        
        # Test the mock provider
        status, message = mock_provider.get_vector_db_status()
        logger.info(f"Mock Vector DB Status: {status} - {message}")
        
        return True, mock_provider
        
    except Exception as e:
        logger.error(f"Failed to initialize mock provider: {e}")
        return False, None

def validate_provider_functionality(provider) -> Dict[str, Any]:
    """
    Validate that the provider is working correctly
    
    Args:
        provider: Vector database provider instance
        
    Returns:
        Validation results
    """
    validation_results = {
        'status_check': False,
        'index_discovery': False,
        'embedding_model': False,
        'search_capability': False,
        'issues': [],
        'recommendations': []
    }
    
    try:
        # Test 1: Status check
        status, message = provider.get_vector_db_status()
        validation_results['status_check'] = status in ["Ready", "Warning"]
        if not validation_results['status_check']:
            validation_results['issues'].append(f"Status check failed: {message}")
        
        # Test 2: Index discovery
        if hasattr(provider, 'get_available_indexes'):
            indexes = provider.get_available_indexes()
            validation_results['index_discovery'] = len(indexes) > 0
            if not validation_results['index_discovery']:
                validation_results['issues'].append("No indexes discovered")
                validation_results['recommendations'].append("Check if vector indexes exist in data directories")
        
        # Test 3: Embedding model
        if hasattr(provider, 'embedding_model'):
            validation_results['embedding_model'] = provider.embedding_model is not None
            if not validation_results['embedding_model']:
                validation_results['issues'].append("Embedding model not loaded")
                validation_results['recommendations'].append("Check sentence-transformers installation")
        
        # Test 4: Search capability (if indexes available)
        if validation_results['index_discovery'] and hasattr(provider, 'search_index'):
            try:
                # Try a simple search on the first available index
                indexes = provider.get_available_indexes()
                if indexes:
                    test_results = provider.search_index("test query", indexes[0], top_k=1)
                    validation_results['search_capability'] = isinstance(test_results, list)
            except Exception as e:
                validation_results['issues'].append(f"Search test failed: {str(e)}")
        
    except Exception as e:
        validation_results['issues'].append(f"Validation failed: {str(e)}")
    
    return validation_results

# Singleton provider instance
_enhanced_provider_instance = None
ENHANCED_VECTOR_DB_AVAILABLE = False

def get_enhanced_vector_db_provider():
    """
    Get the enhanced singleton vector database provider instance
    
    Returns:
        Enhanced vector database provider instance or None if not available
    """
    global _enhanced_provider_instance, ENHANCED_VECTOR_DB_AVAILABLE
    
    if _enhanced_provider_instance is None:
        success, provider = init_enhanced_vector_db_provider()
        if success:
            _enhanced_provider_instance = provider
            ENHANCED_VECTOR_DB_AVAILABLE = True
            
            # Validate the provider
            validation = validate_provider_functionality(provider)
            if validation['issues']:
                logger.warning(f"Provider validation issues: {validation['issues']}")
            if validation['recommendations']:
                logger.info(f"Recommendations: {validation['recommendations']}")
        else:
            ENHANCED_VECTOR_DB_AVAILABLE = False
            logger.error("Failed to initialize any vector database provider")
    
    return _enhanced_provider_instance

def get_vector_db_status_report() -> Dict[str, Any]:
    """
    Get a comprehensive status report of the vector database system
    
    Returns:
        Detailed status report
    """
    report = {
        'timestamp': str(Path(__file__).stat().st_mtime),
        'provider_available': ENHANCED_VECTOR_DB_AVAILABLE,
        'discovered_indexes': {},
        'provider_status': {},
        'validation_results': {},
        'recommendations': []
    }
    
    try:
        # Discover indexes
        report['discovered_indexes'] = discover_existing_indexes()
        
        # Get provider status
        provider = get_enhanced_vector_db_provider()
        if provider:
            status, message = provider.get_vector_db_status()
            report['provider_status'] = {'status': status, 'message': message}
            
            # Get validation results
            report['validation_results'] = validate_provider_functionality(provider)
        
        # Generate recommendations
        total_indexes = sum(len(paths) for paths in report['discovered_indexes'].values())
        if total_indexes == 0:
            report['recommendations'].append("No vector indexes found. Create indexes using the ingestion system.")
        elif not ENHANCED_VECTOR_DB_AVAILABLE:
            report['recommendations'].append("Vector DB provider not available. Check dependencies and configuration.")
        elif report['provider_status'].get('status') == 'Warning':
            report['recommendations'].append("Vector DB has warnings. Check the status message for details.")
        
    except Exception as e:
        report['error'] = str(e)
        report['recommendations'].append("System error occurred. Check logs for details.")
    
    return report
