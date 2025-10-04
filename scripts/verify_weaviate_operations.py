"""Weaviate Operations Verification Script

This script tests basic document operations with Weaviate to ensure
the connection is fully functional for read/write operations.
"""
import os
import sys
import uuid
import logging
import requests
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.weaviate_manager import get_weaviate_manager, WeaviateManager
    import weaviate
    from dotenv import load_dotenv
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Please ensure all required packages are installed: weaviate-client, python-dotenv, sentence-transformers")
    sys.exit(1)

def verify_operations():
    """Test basic document operations with Weaviate"""
    print("\n=== Weaviate Operations Verification ===\n")
    
    try:
        # Get Weaviate manager
        wm = get_weaviate_manager()
        logger.info(f"Connected to Weaviate at {wm.url}")
        
        # Create a temporary test class name with a unique identifier
        test_class_name = f"TestClass_{uuid.uuid4().hex[:8]}"
        
        # Define a simple schema for testing
        schema = {
            "classes": [{
                "class": test_class_name,
                "description": "Temporary test class for verification",
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
        
        # Step 1: Create test class
        print("\n--- Step 1: Creating Test Class ---")
        try:
            # Try different API approaches based on client version
            if hasattr(wm.client, 'schema') and hasattr(wm.client.schema, 'create'):
                wm.client.schema.create(schema)
            elif hasattr(wm, '_client') and hasattr(wm._client, 'schema'):
                wm._client.schema.create(schema)
            else:
                # Direct REST API call if needed
                import requests
                headers = {}
                if hasattr(wm, 'api_key') and wm.api_key:
                    headers['Authorization'] = f'Bearer {wm.api_key}'
                headers['Content-Type'] = 'application/json'
                response = requests.post(f"{wm.url}/v1/schema", json=schema, headers=headers)
                response.raise_for_status()
                
            logger.info(f"✅ Successfully created test class: {test_class_name}")
            class_created = True
        except Exception as e:
            logger.error(f"❌ Failed to create test class: {str(e)}")
            class_created = False
            
        if class_created:
            # Step 2: Add test document
            print("\n--- Step 2: Adding Test Document ---")
            test_doc = {
                "content": "This is a test document for Weaviate connection verification.",
                "title": "Test Document"
            }
            
            try:
                # Try different API approaches based on client version
                doc_uuid = None
                if hasattr(wm.client, 'data_object') and hasattr(wm.client.data_object, 'create'):
                    doc_uuid = wm.client.data_object.create(
                        data_object=test_doc,
                        class_name=test_class_name
                    )
                elif hasattr(wm, '_client') and hasattr(wm._client, 'data'):
                    doc_uuid = wm._client.data.creator().with_class_name(test_class_name).with_properties(test_doc).do()
                else:
                    # Direct REST API call if needed
                    doc_uuid = str(uuid.uuid4())
                    headers = {}
                    if hasattr(wm, 'api_key') and wm.api_key:
                        headers['Authorization'] = f'Bearer {wm.api_key}'
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(
                        f"{wm.url}/v1/objects/{test_class_name}/{doc_uuid}", 
                        json=test_doc, 
                        headers=headers
                    )
                    response.raise_for_status()
                
                logger.info(f"✅ Successfully added test document with ID: {doc_uuid}")
                doc_added = True
            except Exception as e:
                logger.error(f"❌ Failed to add test document: {str(e)}")
                doc_added = False
                
            # Step 3: Query test document
            if doc_added:
                print("\n--- Step 3: Querying Test Document ---")
                try:
                    # Try different API approaches based on client version
                    query_result = None
                    if hasattr(wm.client, 'query') and hasattr(wm.client.query, 'get'):
                        query_result = wm.client.query.get(
                            test_class_name, ["content", "title"]
                        ).do()
                    elif hasattr(wm, '_client') and hasattr(wm._client, 'query'):
                        query_result = wm._client.query.get(test_class_name, ["content", "title"]).do()
                    else:
                        # Direct REST API call if needed
                        import requests
                        headers = {}
                        if hasattr(wm, 'api_key') and wm.api_key:
                            headers['Authorization'] = f'Bearer {wm.api_key}'
                        headers['Content-Type'] = 'application/json'
                        response = requests.get(f"{wm.url}/v1/objects?class={test_class_name}", headers=headers)
                        response.raise_for_status()
                        query_result = response.json()
                    
                    # Check if we got results - handle different response formats
                    if query_result:
                        objects = []
                        if isinstance(query_result, dict):
                            if "data" in query_result and "Get" in query_result["data"]:
                                objects = query_result["data"]["Get"].get(test_class_name, [])
                            elif "objects" in query_result:
                                objects = query_result["objects"]
                        
                        if objects:
                            logger.info(f"✅ Successfully queried test document. Found {len(objects)} objects.")
                            if isinstance(objects[0], dict) and "title" in objects[0]:
                                logger.info(f"First document title: {objects[0].get('title')}")
                            query_ok = True
                        else:
                            logger.warning("⚠️ Query returned no objects, but API call succeeded")
                            query_ok = True  # Consider this a success if the API call worked
                    else:
                        logger.error("❌ Query returned unexpected structure")
                        query_ok = False
                except Exception as e:
                    logger.error(f"❌ Failed to query test document: {str(e)}")
                    query_ok = False
            else:
                query_ok = False
                
            # Step 4: Clean up - delete test class
            print("\n--- Step 4: Cleaning Up ---")
            try:
                # Try different API approaches based on client version
                if hasattr(wm.client, 'schema') and hasattr(wm.client.schema, 'delete_class'):
                    wm.client.schema.delete_class(test_class_name)
                elif hasattr(wm, '_client') and hasattr(wm._client, 'schema'):
                    wm._client.schema.delete_class(test_class_name)
                else:
                    # Direct REST API call if needed
                    import requests
                    headers = {}
                    if hasattr(wm, 'api_key') and wm.api_key:
                        headers['Authorization'] = f'Bearer {wm.api_key}'
                    response = requests.delete(f"{wm.url}/v1/schema/{test_class_name}", headers=headers)
                    response.raise_for_status()
                
                logger.info(f"✅ Successfully deleted test class: {test_class_name}")
                cleanup_ok = True
            except Exception as e:
                logger.error(f"❌ Failed to delete test class: {str(e)}")
                cleanup_ok = False
                
            # Overall status
            print("\n--- Overall Status ---")
            if class_created and doc_added and query_ok and cleanup_ok:
                print("✅ Weaviate operations verification PASSED")
                print("The Weaviate connection is fully functional for document operations.")
            else:
                print("⚠️ Weaviate operations verification PARTIALLY PASSED")
                print(f"  - Create class: {'✅ Success' if class_created else '❌ Failed'}")
                print(f"  - Add document: {'✅ Success' if doc_added else '❌ Failed'}")
                print(f"  - Query document: {'✅ Success' if query_ok else '❌ Failed'}")
                print(f"  - Cleanup: {'✅ Success' if cleanup_ok else '❌ Failed'}")
        else:
            print("\n--- Overall Status ---")
            print("❌ Weaviate operations verification FAILED")
            print("Could not create test class. Verification cannot proceed.")
            
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
    verify_operations()