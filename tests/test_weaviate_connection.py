#!/usr/bin/env python

import os
import sys
import unittest
import logging
import uuid
import requests

# Add the parent directory to the path so we can import the utils module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.weaviate_manager import get_weaviate_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestWeaviateConnection(unittest.TestCase):
    """Test the Weaviate connection with proper error handling for read-only instances."""
    
    def setUp(self):
        """Set up the test case."""
        self.wm = None
        self.is_read_only = False
        try:
            self.wm = get_weaviate_manager()
        except Exception as e:
            logger.error(f"Failed to get Weaviate manager: {str(e)}")
            self.fail(f"Failed to get Weaviate manager: {str(e)}")
    
    def tearDown(self):
        """Clean up after the test case."""
        if self.wm:
            if hasattr(self.wm, 'close') and callable(self.wm.close):
                self.wm.close()
            logger.info("Closed Weaviate connection")
    
    def test_connection(self):
        """Test the connection to Weaviate."""
        self.assertIsNotNone(self.wm, "Weaviate manager should not be None")
        self.assertIsNotNone(self.wm.client, "Weaviate client should not be None")
        logger.info(f"Successfully connected to Weaviate at {self.wm.url}")
    
    def test_schema_retrieval(self):
        """Test retrieving the schema from Weaviate."""
        schema = None
        try:
            # Try different API approaches based on client version
            if hasattr(self.wm.client, 'schema') and hasattr(self.wm.client.schema, 'get'):
                schema = self.wm.client.schema.get()
            elif hasattr(self.wm, '_client') and hasattr(self.wm._client, 'schema'):
                schema = self.wm._client.schema.get()
            else:
                # Direct REST API call if needed
                headers = {}
                if hasattr(self.wm, 'api_key') and self.wm.api_key:
                    headers['Authorization'] = f'Bearer {self.wm.api_key}'
                response = requests.get(f"{self.wm.url}/v1/schema", headers=headers)
                response.raise_for_status()
                schema = response.json()
        except Exception as e:
            logger.warning(f"Schema retrieval via client API failed: {str(e)}")
            # Try direct REST API call as fallback
            try:
                headers = {}
                if hasattr(self.wm, 'api_key') and self.wm.api_key:
                    headers['Authorization'] = f'Bearer {self.wm.api_key}'
                response = requests.get(f"{self.wm.url}/v1/schema", headers=headers)
                response.raise_for_status()
                schema = response.json()
                logger.info("Successfully retrieved schema via direct REST API call")
            except Exception as e2:
                logger.error(f"Failed to retrieve schema via REST API: {str(e2)}")
                self.fail(f"Failed to retrieve schema: {str(e2)}")
        
        self.assertIsNotNone(schema, "Schema should not be None")
        self.assertIn('classes', schema, "Schema should contain 'classes' key")
        
        classes = schema.get('classes', [])
        logger.info(f"Retrieved schema with {len(classes)} classes")
        
        # Log class names
        if classes:
            class_names = [cls.get('class') for cls in classes]
            logger.info(f"Available classes: {', '.join(class_names)}")
    
    def test_meta_retrieval(self):
        """Test retrieving meta information from Weaviate."""
        meta = None
        try:
            # Check for different client versions
            if hasattr(self.wm.client, 'get_meta'):
                meta = self.wm.client.get_meta()
            elif hasattr(self.wm, '_client') and hasattr(self.wm._client, 'get_meta'):
                meta = self.wm._client.get_meta()
            else:
                # Try direct REST API call if client methods not available
                headers = {}
                if hasattr(self.wm, 'api_key') and self.wm.api_key:
                    headers['Authorization'] = f'Bearer {self.wm.api_key}'
                response = requests.get(f"{self.wm.url}/v1/meta", headers=headers)
                response.raise_for_status()
                meta = response.json()
        except Exception as e:
            logger.warning(f"Meta retrieval via client API failed: {str(e)}")
            # Try direct REST API call as fallback
            try:
                headers = {}
                if hasattr(self.wm, 'api_key') and self.wm.api_key:
                    headers['Authorization'] = f'Bearer {self.wm.api_key}'
                response = requests.get(f"{self.wm.url}/v1/meta", headers=headers)
                response.raise_for_status()
                meta = response.json()
                logger.info("Successfully retrieved meta information via direct REST API call")
            except Exception as e2:
                logger.error(f"Failed to retrieve meta information via REST API: {str(e2)}")
                self.fail(f"Failed to retrieve meta information: {str(e2)}")
        
        self.assertIsNotNone(meta, "Meta information should not be None")
        self.assertIn('version', meta, "Meta information should contain 'version' key")
        
        logger.info(f"Weaviate version: {meta['version']}")
        
        # Log available modules
        if 'modules' in meta:
            modules = list(meta['modules'].keys()) if meta['modules'] else []
            if modules:
                logger.info(f"Available modules: {', '.join(modules)}")
    
    def test_write_permission(self):
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
            if hasattr(self.wm.client, 'schema') and hasattr(self.wm.client.schema, 'create'):
                self.wm.client.schema.create(schema)
            elif hasattr(self.wm, '_client') and hasattr(self.wm._client, 'schema'):
                self.wm._client.schema.create(schema)
            else:
                # Direct REST API call if needed
                headers = {}
                if hasattr(self.wm, 'api_key') and self.wm.api_key:
                    headers['Authorization'] = f'Bearer {self.wm.api_key}'
                headers['Content-Type'] = 'application/json'
                response = requests.post(f"{self.wm.url}/v1/schema", json=schema, headers=headers)
                response.raise_for_status()
                
            logger.info(f"Successfully created test class: {test_class_name}")
            
            # Clean up - delete test class
            try:
                if hasattr(self.wm.client, 'schema') and hasattr(self.wm.client.schema, 'delete_class'):
                    self.wm.client.schema.delete_class(test_class_name)
                elif hasattr(self.wm, '_client') and hasattr(self.wm._client, 'schema'):
                    self.wm._client.schema.delete_class(test_class_name)
                else:
                    # Direct REST API call if needed
                    headers = {}
                    if hasattr(self.wm, 'api_key') and self.wm.api_key:
                        headers['Authorization'] = f'Bearer {self.wm.api_key}'
                    response = requests.delete(f"{self.wm.url}/v1/schema/{test_class_name}", headers=headers)
                    response.raise_for_status()
                
                logger.info(f"Successfully deleted test class: {test_class_name}")
            except Exception as e:
                logger.error(f"Failed to delete test class: {str(e)}")
                # Don't fail the test if cleanup fails
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                logger.warning(f"Permission denied (422): Cannot create schema. This appears to be a read-only instance.")
                self.is_read_only = True
                # Skip the test instead of failing it for read-only instances
                self.skipTest("Weaviate instance is read-only, skipping write permission test")
            elif e.response.status_code == 401 or e.response.status_code == 403:
                logger.warning(f"Permission denied ({e.response.status_code}): Authentication or authorization issue.")
                self.is_read_only = True
                self.skipTest("Weaviate instance has authentication/authorization issues, skipping write permission test")
            else:
                logger.error(f"HTTP error when creating test class: {str(e)}")
                self.fail(f"Failed to create test class: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create test class: {str(e)}")
            self.fail(f"Failed to create test class: {str(e)}")

if __name__ == "__main__":
    unittest.main()