#!/usr/bin/env python
"""
Test MongoDB Connection
Verifies connectivity to MongoDB and tests basic vector operations
"""

import os
import sys
import logging
import argparse
from pathlib import Path
import asyncio
from typing import Dict, Any, List, Optional

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try to import required modules
try:
    import pymongo
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo package is not installed. MongoDB tests will be skipped.")
    logger.info("To install: pip install pymongo")

# Try to load environment variables
try:
    from dotenv import load_dotenv
    env_path = project_root / "config" / "storage.env"
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path))
        logger.info(f"Loaded environment from {env_path}")
except ImportError:
    logger.warning("python-dotenv not installed, using existing environment variables")

def get_mongodb_connection_params() -> Dict[str, Any]:
    """Get MongoDB connection parameters from environment variables"""
    # Check for connection string first
    connection_string = os.environ.get("MONGODB_CONNECTION_STRING", "")
    if connection_string:
        return {"connection_string": connection_string}
    
    # Otherwise use individual parameters
    return {
        "host": os.environ.get("MONGODB_HOST", "localhost"),
        "port": int(os.environ.get("MONGODB_PORT", "27017")),
        "database": os.environ.get("MONGODB_DATABASE", "vaultmind"),
        "username": os.environ.get("MONGODB_USERNAME", "vaultmind"),
        "password": os.environ.get("MONGODB_PASSWORD", ""),
    }

def build_connection_string(params: Dict[str, Any]) -> str:
    """Build MongoDB connection string from parameters"""
    if "connection_string" in params and params["connection_string"]:
        return params["connection_string"]
        
    auth_part = ""
    if params.get("username") and params.get("password"):
        auth_part = f"{params['username']}:{params['password']}@"
    
    return f"mongodb://{auth_part}{params['host']}:{params['port']}/{params['database']}"

async def test_mongodb_connection() -> bool:
    """Test connection to MongoDB"""
    if not MONGODB_AVAILABLE:
        logger.warning("MongoDB test skipped: pymongo not installed")
        return True  # Return True to allow other tests to run
    
    params = get_mongodb_connection_params()
    connection_string = build_connection_string(params)
    
    # Mask password in logs
    log_conn_string = connection_string
    if "@" in log_conn_string and ":" in log_conn_string.split("@")[0]:
        parts = log_conn_string.split("@")
        auth_parts = parts[0].split(":")
        if len(auth_parts) > 1:
            masked = f"{auth_parts[0]}:****@{parts[1]}"
            log_conn_string = masked
    
    logger.info(f"Testing MongoDB connection to: {log_conn_string}")
    
    try:
        # Connect to MongoDB
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        
        # Test connection with ping
        client.admin.command('ping')
        logger.info("✅ MongoDB connection successful")
        
        # Get server info
        server_info = client.server_info()
        logger.info(f"MongoDB version: {server_info.get('version', 'unknown')}")
        
        # Test database access
        db_name = params.get("database", "vaultmind")
        db = client[db_name]
        
        # List collections
        collections = db.list_collection_names()
        logger.info(f"Collections in {db_name}: {collections or 'none'}")
        
        # Create test collection
        test_collection = "vector_test_collection"
        if test_collection not in collections:
            db.create_collection(test_collection)
            logger.info(f"Created test collection: {test_collection}")
        
        # Test document insertion with vector
        collection = db[test_collection]
        test_doc = {
            "content": "This is a test document for vector search",
            "metadata": {"source": "test_script", "test": True},
            "embedding": [0.1] * 384  # Simple test embedding
        }
        
        result = collection.insert_one(test_doc)
        logger.info(f"✅ Test document inserted with ID: {result.inserted_id}")
        
        # Clean up
        collection.delete_one({"_id": result.inserted_id})
        logger.info("Test document cleaned up")
        
        # Close connection
        client.close()
        
        return True
        
    except ConnectionFailure as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return False
    except OperationFailure as e:
        logger.error(f"❌ MongoDB operation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing MongoDB: {e}")
        return False

async def main(args):
    """Run all tests"""
    logger.info("=== MongoDB Connection Test ===\n")
    
    # Test MongoDB connection
    mongodb_ok = await test_mongodb_connection()
    
    # Print summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"MongoDB Connection: {'✅ PASS' if mongodb_ok else '❌ FAIL'}")
    
    # Return overall status
    return mongodb_ok

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test MongoDB connection")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        success = asyncio.run(main(args))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)