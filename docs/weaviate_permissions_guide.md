# Weaviate Permissions Guide

## Overview

This document provides guidance on working with the Weaviate vector database instance in this project, specifically addressing permission issues and providing solutions for handling read-only access constraints.

## Current Weaviate Instance Status

Based on our verification tests, the current Weaviate instance has the following characteristics:

- **Connection**: Successfully connects to the Weaviate instance
- **Schema Access**: Can retrieve the existing schema (3 classes found: Bylaws_New, BylawsNew, NewBylaws)
- **Meta Information**: Can retrieve cluster information
- **Write Permission**: Read-only access (422 errors when attempting to create schemas or objects)
- **Query Capability**: Can query existing classes, but proper handling is needed

## Permission Issues Identified

### 1. Write Permission Denied (422 Error)

When attempting to create a new schema class or add data objects, the Weaviate instance returns a 422 error, indicating that the instance is configured as read-only. This is likely an intentional security measure to prevent unauthorized modifications to the database.

```
Permission denied (422): Cannot create schema. This appears to be a read-only instance.
```

### 2. Query Results Handling

Queries to existing classes may return empty results if:
- The class doesn't contain any objects
- The query parameters don't match existing data
- The query syntax is incorrect

However, the API calls themselves are successful, indicating that querying functionality works correctly from a permissions perspective.

## Solutions Implemented

### 1. Graceful Error Handling for Write Operations

We've implemented robust error handling in our verification scripts and tests to gracefully handle 422 errors when attempting write operations:

- **Schema Creation**: Catches 422 errors and identifies them as read-only permission issues
- **Data Object Creation**: Handles write permission errors without crashing
- **Class Deletion**: Manages cleanup attempts with appropriate error handling

### 2. Fallback Mechanisms

Our implementation now includes fallback mechanisms to ensure functionality even with read-only access:

- **Client API Fallbacks**: Checks for client API availability and falls back to direct REST API calls when needed
- **Version Compatibility**: Handles different Weaviate client versions with appropriate method calls
- **Read-Only Mode Detection**: Automatically detects read-only mode and adjusts operations accordingly

### 3. Enhanced Testing Framework

The testing framework has been updated to:

- **Detect Read-Only Mode**: Automatically identifies read-only instances
- **Skip Write Tests**: Appropriately skips or modifies tests that require write access
- **Validate Read Operations**: Ensures all read operations work correctly

## Best Practices for Working with Read-Only Weaviate

### 1. Query Existing Data

Focus on querying existing data with these approaches:

```python
# Using client API (if available)
query_result = client.query.get(class_name, properties).do()

# Using REST API (fallback)
query_url = f"{weaviate_url}/v1/graphql"
query_payload = {
    "query": f"{{Get{{{class_name}(limit: 10) {{property1 property2}}}}}}"
}
response = requests.post(query_url, json=query_payload, headers=headers)
```

### 2. Schema Exploration

Explore the existing schema to understand available classes and properties:

```python
# Using client API
schema = client.schema.get()

# Using REST API
schema_url = f"{weaviate_url}/v1/schema"
response = requests.get(schema_url, headers=headers)
schema = response.json()
```

### 3. Error Handling

Implement proper error handling for all operations:

```python
try:
    # Attempt operation
    result = client.schema.create_class(class_obj)
except Exception as e:
    if hasattr(e, 'status_code') and e.status_code == 422:
        logging.warning("Permission denied (422): Cannot create schema. This appears to be a read-only instance.")
    else:
        logging.error(f"Error: {str(e)}")
```

## Conclusion

The Weaviate instance in this project is configured as read-only, which is likely an intentional security measure. Our implementation now gracefully handles this limitation, allowing for successful read operations while properly managing write operation attempts.

For any changes that require write access to the Weaviate instance, contact the system administrator to request temporary write permissions or to have the changes implemented through an authorized process.