# Vector Database Connection Testing

This document explains how to verify the connection status for Vector databases in the Storage Settings tab and ensure all connection parameters are correctly configured.

## Overview

The Storage Settings tab now includes comprehensive connection testing capabilities for vector databases. These tests help verify that:

1. All connection parameters are correctly configured
2. The system can successfully connect to the configured vector databases
3. The vector database indexes are accessible and operational

## Testing Vector Database Connections

### Using the Storage Settings Tab

1. Navigate to the Storage Settings tab in the application
2. Configure your vector database connection parameters in the appropriate sections
3. Scroll down to the "Vector Database Connection Tests" section
4. Use the provided test buttons to verify connections:
   - **Test Vector DB Provider**: Tests the connection using the VectorDBProvider class
   - **Test Multi-Vector Stores**: Tests connections to all configured vector stores using the multi-vector storage interface

### Test Results

The test results will display:

- Connection status for each configured vector database
- Available indexes/collections in each database
- Any errors or warnings encountered during connection attempts
- Overall test status (PASS/FAIL)

## Troubleshooting Connection Issues

If the connection tests fail, check the following:

1. **Configuration Parameters**:
   - Verify that all required connection parameters are provided
   - Check for typos in URLs, API keys, or other credentials
   - Ensure that the specified endpoints are accessible from your network

2. **Authentication**:
   - Verify that API keys and credentials are valid and have not expired
   - Check that the credentials have appropriate permissions to access the vector databases

3. **Network Connectivity**:
   - Ensure that your network allows connections to the vector database endpoints
   - Check if any firewalls or proxies might be blocking the connections

4. **Database Status**:
   - Verify that the vector database service is running and accessible
   - Check if the required indexes or collections exist in the database

## Manual Testing

You can also run the connection tests manually from the command line:

```bash
# Test vector database provider connections
python scripts/test_vector_db_connections.py --verbose

# Test multi-vector store connections
python scripts/test_multi_vector_connections.py --verbose
```

## Connection Status Codes

The connection tests use the following status codes:

- **Ready**: The connection is established and the vector database is operational
- **Error**: The connection failed or the vector database is not accessible
- **Warning**: The connection is partially successful, but there are issues that need attention
- **Initializing**: The connection is in the process of being established

## Adding Support for New Vector Database Types

To add connection testing support for a new vector database type:

1. Implement the `health_check` method in the corresponding adapter class
2. The method should return a tuple of (bool, str) indicating success/failure and a message
3. Register the adapter with the VectorStoreFactory

Example implementation:

```python
async def health_check(self) -> Tuple[bool, str]:
    """Check if the vector store is healthy"""
    try:
        # Perform connection test specific to this vector database type
        # For example, list collections or perform a simple query
        collections = await self.list_collections()
        return True, f"Connection healthy: {len(collections)} collections available"
    except Exception as e:
        return False, f"Health check failed: {e}"
```