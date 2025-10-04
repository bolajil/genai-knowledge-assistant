"""Detailed Weaviate Connection Verification Script

This script performs a comprehensive verification of the Weaviate connection,
checking configuration parameters, connection status, and basic operations.
"""
import os
import sys
import json
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.weaviate_manager import get_weaviate_manager, WeaviateManager
    import weaviate
    import requests
    from dotenv import load_dotenv
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Please ensure all required packages are installed: weaviate-client, python-dotenv, sentence-transformers")
    sys.exit(1)

def load_config() -> Dict[str, Any]:
    """Load Weaviate configuration from environment variables"""
    config = {}
    
    # Load from config/weaviate.env
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'weaviate.env')
    if os.path.exists(config_path):
        load_dotenv(dotenv_path=config_path, override=True)
        logger.info(f"Loaded environment overrides from {config_path}")
    
    # Get configuration parameters
    config['url'] = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    config['api_key'] = os.getenv("WEAVIATE_API_KEY")
    config['force_api_version'] = os.getenv("WEAVIATE_FORCE_API_VERSION")
    config['skip_v2'] = os.getenv("WEAVIATE_SKIP_V2", "false").lower() in ("1", "true", "yes")
    config['primary_text_prop'] = os.getenv("WEAVIATE_PRIMARY_TEXT_PROP", "content")
    
    return config

def test_connection(wm: WeaviateManager) -> bool:
    """Test basic connection to Weaviate"""
    try:
        # Get Weaviate meta information
        meta = wm.client.get_meta()
        logger.info(f"✅ Successfully connected to Weaviate at {wm.url}")
        logger.info(f"Weaviate version: {meta.get('version', 'unknown')}")
        return True
    except Exception as e:
        logger.error(f"❌ Connection failed: {str(e)}")
        return False

def test_schema(wm: WeaviateManager) -> bool:
    """Test schema retrieval from Weaviate"""
    try:
        # Access schema through the client directly
        schema = wm.client.schema.get() if hasattr(wm.client, 'schema') else None
        
        # If schema attribute doesn't exist, try alternative approach
        if schema is None and hasattr(wm, '_client'):
            schema = wm._client.schema.get() if hasattr(wm._client, 'schema') else None
            
        # If still no schema, try direct API call
        if schema is None:
            import requests
            headers = {}
            if hasattr(wm, 'api_key') and wm.api_key:
                headers['Authorization'] = f'Bearer {wm.api_key}'
            response = requests.get(f"{wm.url}/v1/schema", headers=headers)
            if response.status_code == 200:
                schema = response.json()
        
        if schema:
            class_count = len(schema.get('classes', []))
            logger.info(f"✅ Successfully retrieved schema with {class_count} classes")
            
            # Print class names if available
            if class_count > 0:
                class_names = [cls.get('class') for cls in schema.get('classes', [])]
                logger.info(f"Available classes: {', '.join(class_names)}")
            return True
        else:
            logger.warning("⚠️ Schema retrieval returned empty result")
            return False
    except Exception as e:
        logger.error(f"❌ Schema retrieval failed: {str(e)}")
        return False

def test_basic_operations(wm: WeaviateManager) -> bool:
    """Test basic operations with Weaviate"""
    try:
        # Get node information
        if hasattr(wm.client, 'get_meta'):
            meta = wm.client.get_meta()
            if 'hostname' in meta:
                logger.info(f"Node hostname: {meta['hostname']}")
            if 'modules' in meta:
                modules = meta.get('modules', {})
                module_names = list(modules.keys())
                logger.info(f"Available modules: {', '.join(module_names) if module_names else 'None'}")
        
        # Try to get cluster information if available
        try:
            if hasattr(wm.client, 'cluster') and hasattr(wm.client.cluster, 'get_nodes_status'):
                health = wm.client.cluster.get_nodes_status()
                logger.info(f"Cluster health: {health}")
            elif hasattr(wm.client, 'cluster') and hasattr(wm.client.cluster, 'get_nodes'):
                nodes = wm.client.cluster.get_nodes()
                logger.info(f"Cluster nodes: {nodes}")
        except Exception as cluster_err:
            logger.warning(f"Cluster information not available: {str(cluster_err)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Basic operations test failed: {str(e)}")
        return False

def verify_weaviate():
    """Perform comprehensive Weaviate verification"""
    print("\n=== Weaviate Connection Verification ===\n")
    
    # Load configuration
    config = load_config()
    print("\n--- Configuration Parameters ---")
    for key, value in config.items():
        # Mask API key for security
        if key == 'api_key' and value:
            masked_key = value[:4] + '*' * (len(value) - 8) + value[-4:]
            print(f"{key}: {masked_key}")
        else:
            print(f"{key}: {value}")
    
    try:
        # Get Weaviate manager
        print("\n--- Connection Test ---")
        wm = get_weaviate_manager()
        
        # Test connection
        connection_ok = test_connection(wm)
        
        if connection_ok:
            # Test schema retrieval
            print("\n--- Schema Test ---")
            schema_ok = test_schema(wm)
            
            # Test basic operations
            print("\n--- Basic Operations Test ---")
            operations_ok = test_basic_operations(wm)
            
            # Test connection parameters
            print("\n--- Connection Parameters ---")
            print(f"URL: {wm.url}")
            print(f"API Key: {'Configured' if hasattr(wm, 'api_key') and wm.api_key else 'Not configured'}")
            
            if hasattr(wm, 'client') and hasattr(wm.client, 'timeout'):
                print(f"Timeout: {wm.client.timeout}")
            
            # Overall status
            print("\n--- Overall Status ---")
            if connection_ok and schema_ok and operations_ok:
                print("✅ Weaviate connection is fully operational")
            else:
                print("⚠️ Weaviate connection is partially operational")
                
                # Provide specific status for each test
                print(f"  - Connection: {'✅ Success' if connection_ok else '❌ Failed'}")
                print(f"  - Schema: {'✅ Success' if schema_ok else '❌ Failed'}")
                print(f"  - Operations: {'✅ Success' if operations_ok else '❌ Failed'}")
        else:
            print("\n--- Overall Status ---")
            print("❌ Weaviate connection failed")
            
    except Exception as e:
        print(f"\n❌ Verification process failed: {str(e)}")

if __name__ == "__main__":
    verify_weaviate()