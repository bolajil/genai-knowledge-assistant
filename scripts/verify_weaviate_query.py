#!/usr/bin/env python

import os
import sys
import logging
import json
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

def get_class_properties(wm, class_name):
    """Get the properties of a class."""
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
            for cls in classes:
                if cls.get('class') == class_name:
                    properties = cls.get('properties', [])
                    property_names = [prop.get('name') for prop in properties]
                    return property_names
        
        return []
    except Exception as e:
        logger.error(f"❌ Failed to get class properties: {str(e)}")
        return []

def test_query(wm, class_name, limit=5) -> bool:
    """Test querying data from Weaviate."""
    try:
        # Get properties for the class
        properties = get_class_properties(wm, class_name)
        if not properties:
            logger.warning(f"⚠️ No properties found for class {class_name}")
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
        
        # Process results based on different response formats
        objects = []
        if results:
            if 'data' in results and 'Get' in results['data'] and class_name in results['data']['Get']:
                # GraphQL response format
                objects = results['data']['Get'][class_name]
            elif 'objects' in results:
                # REST API response format
                objects = results['objects']
            elif class_name in results:
                # Client library response format
                objects = results[class_name]
        
        # Display results
        if objects and len(objects) > 0:
            logger.info(f"✅ Successfully queried {len(objects)} objects from class '{class_name}'")
            
            # Print first object as sample
            logger.info("Sample object:")
            sample = objects[0]
            for prop in display_properties:
                if prop in sample:
                    value = sample[prop]
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    logger.info(f"  {prop}: {value}")
            
            return True
        else:
            logger.warning(f"⚠️ No objects found in class '{class_name}'")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to query data: {str(e)}")
        return False

def verify_weaviate_query():
    """Verify Weaviate query functionality."""
    wm = None
    try:
        # Get the Weaviate manager
        wm = get_weaviate_manager()
        
        # Test connection
        connection_ok = test_connection(wm)
        if not connection_ok:
            print("❌ Cannot proceed with query test: Connection failed")
            return
        
        # Get available classes
        schema = None
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
        except Exception as e:
            logger.error(f"❌ Failed to retrieve schema: {str(e)}")
            return
        
        if not schema or 'classes' not in schema or not schema['classes']:
            logger.error("❌ No classes found in schema")
            return
        
        classes = schema['classes']
        class_names = [cls.get('class') for cls in classes]
        
        print(f"\n=== Available Classes ({len(class_names)}) ===\n")
        for i, class_name in enumerate(class_names, 1):
            print(f"{i}. {class_name}")
        
        # Test query for each class
        print("\n=== Query Test Results ===\n")
        query_results = {}
        for class_name in class_names:
            print(f"\nTesting query for class: {class_name}")
            query_ok = test_query(wm, class_name)
            query_results[class_name] = query_ok
        
        # Print summary
        print("\n=== Query Test Summary ===\n")
        successful_queries = sum(1 for result in query_results.values() if result)
        print(f"Successfully queried {successful_queries} out of {len(class_names)} classes")
        
        if successful_queries > 0:
            print("✅ Weaviate query functionality is working")
        else:
            print("❌ Weaviate query functionality is not working")
        
    except Exception as e:
        print(f"\n❌ Verification process failed: {str(e)}")
    finally:
        # Close the Weaviate connection
        if wm:
            if hasattr(wm, 'close') and callable(wm.close):
                wm.close()
            logger.info("Closed Weaviate connection")

if __name__ == "__main__":
    print("\n=== Weaviate Query Verification ===\n")
    verify_weaviate_query()