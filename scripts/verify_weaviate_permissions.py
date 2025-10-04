#!/usr/bin/env python

"""
Weaviate Permissions Verification Script

This script tests both read and write operations with Weaviate to determine
the permission level of the current connection and handle errors gracefully.
"""

import os
import sys
import uuid
import logging
import json
import requests
from typing import Dict, Any, Optional, Tuple

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

def test_schema_retrieval(wm) -> Tuple[bool, list]:
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
            
            # Get class names
            class_names = [cls.get('class') for cls in classes]
            if class_count > 0:
                logger.info(f"Available classes: {', '.join(class_names)}")
            
            return True, class_names
        else:
            logger.error("❌ Failed to retrieve schema: No schema returned")
            return False, []
    except Exception as e:
        logger.error(f"❌ Failed to retrieve schema: {str(e)}")
        return False, []

def test_meta_retrieval(wm) -> bool:
    """Test retrieving meta information from Weaviate."""
    try:
        meta = None
        # Check for different client versions
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
            
            # Log version information
            if 'version' in meta:
                logger.info(f"Weaviate version: {meta['version']}")
            
            # Log available modules
            if 'modules' in meta:
                modules = list(meta['modules'].keys()) if meta['modules'] else []
                if modules:
                    logger.info(f"Available modules: {', '.join(modules)}")
                else:
                    logger.info("No modules available")
            
            return True
        else:
            logger.warning("⚠️ Meta information retrieval returned empty result")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to retrieve meta information: {str(e)}")
        return False

def test_write_permission(wm) -> bool:
    """Test write permission by attempting to create a test class."""
    # Create a temporary test class name with a unique identifier
    test_class_name = f"TestClass_{uuid.uuid4().hex[:8]}"
    
    # Define a simple schema for testing
    schema = {
        "classes": [{
            "class": test_class_name,
            "description": "Temporary test class for permission verification",
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "The content of the test document"
                },
                {
                    "name": "title",
                    "dataType": ["text"],
                    "description": "The title of the test document"
                }
            ]
        }]
    }
    
    try:
        # Try different API approaches based on client version
        if hasattr(wm.client, 'schema') and hasattr(wm.client.schema, 'create'):
            wm.client.schema.create(schema)
        elif hasattr(wm, '_client') and hasattr(wm._client, 'schema'):
            wm._client.schema.create(schema)
        else:
            # Direct REST API call if needed
            headers = {}
            if hasattr(wm, 'api_key') and wm.api_key:
                headers['Authorization'] = f'Bearer {wm.api_key}'
            headers['Content-Type'] = 'application/json'
            response = requests.post(f"{wm.url}/v1/schema", json=schema, headers=headers)
            response.raise_for_status()
            
        logger.info(f"✅ Successfully created test class: {test_class_name}")
        
        # Clean up - delete test class
        try:
            if hasattr(wm.client, 'schema') and hasattr(wm.client.schema, 'delete_class'):
                wm.client.schema.delete_class(test_class_name)
            elif hasattr(wm, '_client') and hasattr(wm._client, 'schema'):
                wm._client.schema.delete_class(test_class_name)
            else:
                # Direct REST API call if needed
                headers = {}
                if hasattr(wm, 'api_key') and wm.api_key:
                    headers['Authorization'] = f'Bearer {wm.api_key}'
                response = requests.delete(f"{wm.url}/v1/schema/{test_class_name}", headers=headers)
                response.raise_for_status()
            
            logger.info(f"✅ Successfully deleted test class: {test_class_name}")
        except Exception as e:
            logger.error(f"❌ Failed to delete test class: {str(e)}")
        
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            logger.warning(f"⚠️ Permission denied (422): Cannot create schema. This appears to be a read-only instance.")
        elif e.response.status_code == 401 or e.response.status_code == 403:
            logger.warning(f"⚠️ Permission denied ({e.response.status_code}): Authentication or authorization issue.")
        else:
            logger.error(f"❌ HTTP error when creating test class: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to create test class: {str(e)}")
        return False

def test_query_existing_class(wm, class_name, limit=5) -> bool:
    """Test querying data from an existing Weaviate class."""
    try:
        # Get properties for the class
        schema = None
        properties = []
        
        # Try to get schema to find properties
        try:
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
                for cls in classes:
                    if cls.get('class') == class_name:
                        properties = [prop.get('name') for prop in cls.get('properties', [])]
        except Exception as e:
            logger.warning(f"⚠️ Could not get properties for class {class_name}: {str(e)}")
        
        if not properties:
            # Use some common properties as fallback
            properties = ["title", "content", "text", "name", "description"]
        
        # Filter to only text properties for display
        display_properties = properties[:5]  # Limit to first 5 properties
        
        logger.info(f"Querying class '{class_name}' with properties: {', '.join(display_properties)}")
        
        # Try different API approaches based on client version
        results = None
        if hasattr(wm.client, 'query') and hasattr(wm.client.query, 'get'):
            results = wm.client.query.get(
                class_name, display_properties
            ).with_limit(limit).do()
        elif hasattr(wm, '_client') and hasattr(wm._client, 'query'):
            results = wm._client.query.get(class_name, display_properties).with_limit(limit).do()
        else:
            # Direct REST API call if needed
            headers = {}
            if hasattr(wm, 'api_key') and wm.api_key:
                headers['Authorization'] = f'Bearer {wm.api_key}'
            headers['Content-Type'] = 'application/json'
            
            # Build GraphQL query
            graphql_query = {
                "query": f"""
                {{  
                    Get {{ 
                        {class_name}(limit: {limit}) {{ 
                            {' '.join(display_properties)}
                        }}
                    }}
                }}
                """
            }
            
            response = requests.post(f"{wm.url}/v1/graphql", json=graphql_query, headers=headers)
            response.raise_for_status()
            results = response.json()
        
        # Check if we got results - handle different response formats
        objects = []
        if results:
            if isinstance(results, dict):
                if "data" in results and "Get" in results["data"]:
                    objects = results["data"]["Get"].get(class_name, [])
                elif "objects" in results:
                    objects = results["objects"]
        
        if objects:
            logger.info(f"✅ Successfully queried class '{class_name}'. Found {len(objects)} objects.")
            # Display first object properties
            if len(objects) > 0 and isinstance(objects[0], dict):
                first_obj = objects[0]
                for prop in display_properties:
                    if prop in first_obj:
                        value = first_obj[prop]
                        # Truncate long values
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:50] + "..."
                        logger.info(f"  - {prop}: {value}")
            return True
        else:
            logger.warning(f"⚠️ Query to class '{class_name}' returned no objects, but API call succeeded")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to query class '{class_name}': {str(e)}")
        return False

def verify_permissions():
    """Verify Weaviate permissions by testing read and write operations."""
    print("\n=== Weaviate Permissions Verification ===\n")
    
    try:
        # Get Weaviate manager
        wm = get_weaviate_manager()
        
        # Test connection
        print("\n--- Testing Connection ---")
        connection_ok = test_connection(wm)
        if not connection_ok:
            print("\n❌ Verification failed: Could not connect to Weaviate")
            return
        
        # Test schema retrieval
        print("\n--- Testing Schema Retrieval ---")
        schema_ok, class_names = test_schema_retrieval(wm)
        
        # Test meta information retrieval
        print("\n--- Testing Meta Information Retrieval ---")
        meta_ok = test_meta_retrieval(wm)
        
        # Test write permission
        print("\n--- Testing Write Permission ---")
        write_ok = test_write_permission(wm)
        
        # Test querying existing classes
        if schema_ok and class_names:
            print("\n--- Testing Query on Existing Classes ---")
            query_results = []
            for class_name in class_names:
                print(f"\nQuerying class: {class_name}")
                query_ok = test_query_existing_class(wm, class_name)
                query_results.append((class_name, query_ok))
        
        # Overall status
        print("\n--- Overall Status ---")
        read_ok = connection_ok and schema_ok and meta_ok
        
        if read_ok and write_ok:
            print("✅ Weaviate has FULL READ-WRITE permissions")
            print("The Weaviate connection is fully functional for all operations.")
        elif read_ok and not write_ok:
            print("⚠️ Weaviate has READ-ONLY permissions")
            print("The Weaviate connection can read data but cannot modify the schema or add data.")
        else:
            print("❌ Weaviate has LIMITED permissions")
            print("Some operations are not available with the current connection.")
        
        print("\n--- Detailed Results ---")
        print(f"  - Connection: {'✅ Success' if connection_ok else '❌ Failed'}")
        print(f"  - Schema retrieval: {'✅ Success' if schema_ok else '❌ Failed'}")
        print(f"  - Meta information: {'✅ Success' if meta_ok else '❌ Failed'}")
        print(f"  - Write permission: {'✅ Success' if write_ok else '❌ Failed (Read-Only)'}")
        
        if schema_ok and class_names:
            print("\n--- Query Results ---")
            successful_queries = sum(1 for _, result in query_results if result)
            print(f"Successfully queried {successful_queries} out of {len(class_names)} classes")
            
            for class_name, result in query_results:
                print(f"  - {class_name}: {'✅ Data found' if result else '⚠️ No data found'}")
        
    except Exception as e:
        print(f"\n❌ Verification process failed: {str(e)}")
    finally:
        # Ensure we close the connection
        if 'wm' in locals():
            try:
                wm.close()
                logger.info("Closed Weaviate connection")
            except:
                pass

if __name__ == "__main__":
    verify_permissions()