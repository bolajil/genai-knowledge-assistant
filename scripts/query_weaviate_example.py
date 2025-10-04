#!/usr/bin/env python3
"""
Example script for querying data from a read-only Weaviate instance.
This script demonstrates best practices for querying existing classes
with proper error handling for read-only instances.
"""

import logging
import sys
import json
import requests
from typing import Dict, List, Any, Optional

# Add the project root to the path so we can import the utils module
sys.path.append('.')
from utils.weaviate_manager import WeaviateManager, get_weaviate_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_class_properties(client, weaviate_url: str, headers: Dict[str, str], class_name: str) -> List[str]:
    """
    Get properties for a specific class with fallback to REST API.
    
    Args:
        client: Weaviate client instance
        weaviate_url: URL of the Weaviate instance
        headers: Headers for REST API requests
        class_name: Name of the class to get properties for
        
    Returns:
        List of property names
    """
    properties = []
    
    # Try using client API first
    try:
        if hasattr(client, 'schema') and hasattr(client.schema, 'get'):
            schema = client.schema.get()
            for cls in schema['classes']:
                if cls['class'] == class_name:
                    properties = [prop['name'] for prop in cls['properties']]
                    break
        else:
            # Fallback to REST API
            raise AttributeError("Client doesn't have schema.get method")
    except Exception as e:
        logger.info(f"Falling back to REST API for schema retrieval: {str(e)}")
        try:
            # Use REST API to get schema
            schema_url = f"{weaviate_url}/v1/schema"
            response = requests.get(schema_url, headers=headers)
            if response.status_code == 200:
                schema = response.json()
                for cls in schema['classes']:
                    if cls['class'] == class_name:
                        properties = [prop['name'] for prop in cls['properties']]
                        break
            else:
                logger.error(f"Failed to get schema: {response.text}")
        except Exception as e:
            logger.error(f"Error getting schema via REST API: {str(e)}")
    
    return properties


def query_class(client, weaviate_url: str, headers: Dict[str, str], 
                class_name: str, properties: List[str], 
                limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Query objects from a class with fallback to REST API.
    
    Args:
        client: Weaviate client instance
        weaviate_url: URL of the Weaviate instance
        headers: Headers for REST API requests
        class_name: Name of the class to query
        properties: List of properties to include in the query
        limit: Maximum number of objects to return
        filters: Optional filters to apply to the query
        
    Returns:
        Query results
    """
    results = {}
    
    # Format properties for GraphQL query
    props_str = " ".join(properties)
    
    # Try using client API first
    try:
        if hasattr(client, 'query') and hasattr(client.query, 'get'):
            # Build query with client API
            query = client.query.get(class_name, properties)
            
            # Add limit
            query = query.with_limit(limit)
            
            # Add filters if provided
            if filters:
                # This is a simplified example - actual filter implementation
                # would depend on the specific filter structure
                if 'where' in filters:
                    where_filter = filters['where']
                    # Apply where filter (implementation depends on client version)
                    if hasattr(query, 'with_where'):
                        query = query.with_where(where_filter)
            
            # Execute query
            results = query.do()
            logger.info(f"Successfully queried {class_name} using client API")
        else:
            # Fallback to REST API
            raise AttributeError("Client doesn't have query.get method")
    except Exception as e:
        logger.info(f"Falling back to REST API for querying: {str(e)}")
        try:
            # For simplicity, exclude metadata field which requires specific subfield knowledge
            filtered_props = [p for p in properties if p != 'metadata']
            
            # Format properties for GraphQL query
            props_str = " ".join(filtered_props)
            
            # Build GraphQL query
            graphql_query = f"{{Get{{{class_name}(limit: {limit}) {{{props_str}}}}}}}"
            
            # Add filters if provided (simplified example)
            # Actual implementation would need to convert filters to GraphQL format
            
            # Use REST API to execute query
            query_url = f"{weaviate_url}/v1/graphql"
            payload = {"query": graphql_query}
            response = requests.post(query_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                results = response.json()
                logger.info(f"Successfully queried {class_name} using REST API")
            else:
                logger.error(f"Failed to query {class_name}: {response.text}")
        except Exception as e:
            logger.error(f"Error querying via REST API: {str(e)}")
    
    return results


def format_results(results: Dict[str, Any], class_name: str) -> List[Dict[str, Any]]:
    """
    Format query results into a consistent structure.
    
    Args:
        results: Query results from either client API or REST API
        class_name: Name of the class that was queried
        
    Returns:
        List of formatted objects
    """
    formatted_objects = []
    
    try:
        # Handle client API response format
        if 'data' in results and f'Get{class_name}' in results['data']:
            objects = results['data'][f'Get{class_name}']
            formatted_objects = objects
        # Handle REST API response format
        elif 'data' in results and 'Get' in results['data'] and class_name in results['data']['Get']:
            objects = results['data']['Get'][class_name]
            formatted_objects = objects
        else:
            logger.warning(f"Unexpected result format: {results}")
    except Exception as e:
        logger.error(f"Error formatting results: {str(e)}")
    
    return formatted_objects


def main():
    """
    Main function to demonstrate querying a read-only Weaviate instance.
    """
    # Initialize Weaviate manager
    weaviate_manager = get_weaviate_manager()
    client = weaviate_manager.client
    
    if not client:
        logger.error("Failed to connect to Weaviate")
        return
    
    try:
        # Get Weaviate URL and headers for REST API calls
        weaviate_url = weaviate_manager.url
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add authorization header if available
        if hasattr(weaviate_manager, 'api_key') and weaviate_manager.api_key:
            headers["Authorization"] = f"Bearer {weaviate_manager.api_key}"
        
        # Get available classes
        schema = None
        try:
            if hasattr(client, 'schema') and hasattr(client.schema, 'get'):
                schema = client.schema.get()
            else:
                # Fallback to REST API
                schema_url = f"{weaviate_url}/v1/schema"
                response = requests.get(schema_url, headers=headers)
                if response.status_code == 200:
                    schema = response.json()
                else:
                    logger.error(f"Failed to get schema: {response.text}")
        except Exception as e:
            logger.error(f"Error getting schema: {str(e)}")
            return
        
        if not schema or 'classes' not in schema:
            logger.error("No schema or classes found")
            return
        
        # Get class names
        class_names = [cls['class'] for cls in schema['classes']]
        logger.info(f"Available classes: {', '.join(class_names)}")
        
        # Query each class
        for class_name in class_names:
            logger.info(f"\nQuerying class: {class_name}")
            
            # Get properties for the class
            properties = get_class_properties(client, weaviate_url, headers, class_name)
            if not properties:
                logger.warning(f"No properties found for class {class_name}")
                continue
            
            logger.info(f"Properties: {', '.join(properties)}")
            
            # Query the class
            results = query_class(client, weaviate_url, headers, class_name, properties, limit=5)
            
            # Format and display results
            formatted_objects = format_results(results, class_name)
            
            if formatted_objects:
                logger.info(f"Found {len(formatted_objects)} objects in class {class_name}")
                for i, obj in enumerate(formatted_objects[:3]):  # Show first 3 objects
                    logger.info(f"Object {i+1}: {json.dumps(obj, indent=2)}")
                if len(formatted_objects) > 3:
                    logger.info(f"... and {len(formatted_objects) - 3} more objects")
            else:
                logger.info(f"No objects found in class {class_name}")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    
    finally:
        # Close Weaviate connection
        weaviate_manager.close()
        logger.info("Closed Weaviate connection")


if __name__ == "__main__":
    main()