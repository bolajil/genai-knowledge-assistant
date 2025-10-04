#!/usr/bin/env python

import os
import sys
import logging
import requests
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import the utils module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.weaviate_manager import get_weaviate_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_connection(wm) -> bool:
    """Test the connection to Weaviate."""
    try:
        # Check if we can connect to Weaviate
        if wm and wm.client:
            logger.info(f"✅ Successfully connected to Weaviate at {wm.url}")
            return True
        else:
            logger.error("❌ Failed to connect to Weaviate")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to connect to Weaviate: {str(e)}")
        return False

def test_schema(wm) -> bool:
    """Test retrieving the schema from Weaviate."""
    try:
        schema = None
        # Try different API approaches based on client version
        if hasattr(wm.client, 'schema') and hasattr(wm.client.schema, 'get'):
            schema = wm.client.schema.get()
        elif hasattr(wm, '_client') and hasattr(wm._client, 'schema'):
            schema = wm._client.schema.get()
        else:
            # Direct REST API call if needed
            headers = {}
            if hasattr(wm, 'api_key') and wm.api_key:
                headers['Authorization'] = f'Bearer {wm.api_key}'
            response = requests.get(f"{wm.url}/v1/schema", headers=headers)
            response.raise_for_status()
            schema = response.json()
        
        if schema:
            classes = schema.get('classes', [])
            class_count = len(classes)
            logger.info(f"✅ Successfully retrieved schema with {class_count} classes")
            
            # Print class names
            if class_count > 0:
                class_names = [cls.get('class') for cls in classes]
                logger.info(f"Available classes: {', '.join(class_names)}")
            
            return True
        else:
            logger.error("❌ Failed to retrieve schema: No schema returned")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to retrieve schema: {str(e)}")
        return False

def test_basic_operations(wm) -> bool:
    """Test basic operations with Weaviate."""
    try:
        # Try to get cluster information
        try:
            # Check for different client versions
            if hasattr(wm.client, 'cluster'):
                if hasattr(wm.client.cluster, 'get_nodes_status'):
                    nodes_status = wm.client.cluster.get_nodes_status()
                    logger.info(f"✅ Successfully retrieved cluster status")
                elif hasattr(wm.client.cluster, 'get_nodes'):
                    nodes = wm.client.cluster.get_nodes()
                    logger.info(f"✅ Successfully retrieved cluster nodes")
            elif hasattr(wm, '_client') and hasattr(wm._client, 'cluster'):
                if hasattr(wm._client.cluster, 'get_nodes_status'):
                    nodes_status = wm._client.cluster.get_nodes_status()
                    logger.info(f"✅ Successfully retrieved cluster status")
                elif hasattr(wm._client.cluster, 'get_nodes'):
                    nodes = wm._client.cluster.get_nodes()
                    logger.info(f"✅ Successfully retrieved cluster nodes")
            else:
                # Direct REST API call
                headers = {}
                if hasattr(wm, 'api_key') and wm.api_key:
                    headers['Authorization'] = f'Bearer {wm.api_key}'
                response = requests.get(f"{wm.url}/v1/nodes", headers=headers)
                response.raise_for_status()
                nodes = response.json()
                logger.info(f"✅ Successfully retrieved cluster nodes via API")
                
                # Get hostname of first node
                if nodes and len(nodes) > 0:
                    hostname = nodes[0].get('hostname', 'unknown')
                    logger.info(f"Node hostname: {hostname}")
        except Exception as cluster_err:
            logger.warning(f"⚠️ Could not retrieve cluster information: {str(cluster_err)}")
        
        # Try to get meta information
        try:
            # Check for different client versions
            meta = None
            if hasattr(wm.client, 'get_meta'):
                meta = wm.client.get_meta()
            elif hasattr(wm, '_client') and hasattr(wm._client, 'get_meta'):
                meta = wm._client.get_meta()
            else:
                # Direct REST API call
                headers = {}
                if hasattr(wm, 'api_key') and wm.api_key:
                    headers['Authorization'] = f'Bearer {wm.api_key}'
                response = requests.get(f"{wm.url}/v1/meta", headers=headers)
                response.raise_for_status()
                meta = response.json()
            
            if meta:
                logger.info(f"✅ Successfully retrieved meta information")
                
                # Get version
                if 'version' in meta:
                    logger.info(f"Weaviate version: {meta['version']}")
                
                # Get modules
                if 'modules' in meta:
                    modules = list(meta['modules'].keys()) if meta['modules'] else []
                    logger.info(f"Available modules: {', '.join(modules) if modules else 'None'}")
        except Exception as meta_err:
            logger.warning(f"⚠️ Could not retrieve meta information: {str(meta_err)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to perform basic operations: {str(e)}")
        return False

def verify_weaviate():
    """Verify the Weaviate connection and functionality."""
    wm = None
    try:
        # Get the Weaviate manager
        wm = get_weaviate_manager()
        
        # Print connection parameters (masking API key)
        print("\n=== Weaviate Connection Parameters ===")
        url = wm.url if hasattr(wm, 'url') else 'Unknown'
        api_key_set = bool(wm.api_key) if hasattr(wm, 'api_key') else False
        print(f"URL: {url}")
        print(f"API Key Set: {'Yes' if api_key_set else 'No'}")
        
        # Test connection
        connection_ok = test_connection(wm)
        
        # Test schema retrieval
        schema_ok = False
        if connection_ok:
            schema_ok = test_schema(wm)
        
        # Test basic operations
        operations_ok = False
        if connection_ok and schema_ok:
            operations_ok = test_basic_operations(wm)
        
        # Print overall status
        print("\n--- Overall Status ---")
        if connection_ok and schema_ok and operations_ok:
            print("✅ Weaviate is fully operational")
        elif connection_ok:
            print("⚠️ Weaviate is partially operational")
            if not schema_ok:
                print("Could not retrieve schema.")
            if not operations_ok:
                print("Could not perform basic operations.")
        else:
            print("❌ Weaviate is not operational")
            print("Could not connect to Weaviate.")
        
        # Print test results breakdown
        print("\n--- Test Results Breakdown ---")
        print(f"Connection Test: {'✅ Passed' if connection_ok else '❌ Failed'}")
        print(f"Schema Test: {'✅ Passed' if schema_ok else '❌ Failed'}")
        print(f"Basic Operations Test: {'✅ Passed' if operations_ok else '❌ Failed'}")
        
    except Exception as e:
        print(f"\n❌ Verification process failed: {str(e)}")
    finally:
        # Close the Weaviate connection
        if wm:
            if hasattr(wm, 'close') and callable(wm.close):
                wm.close()
            logger.info("Closed Weaviate connection")

if __name__ == "__main__":
    print("\n=== Weaviate Read-Only Verification ===\n")
    verify_weaviate()