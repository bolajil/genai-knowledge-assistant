"""
README for the centralized search system implementation
This file explains the new search system and how to use it
"""

# Centralized Multi-Source Search System

This implementation provides a centralized, consistent approach to indexing and searching across the entire application. It addresses several issues with the previous implementation:

1. Inconsistent search implementations across tabs
2. Multiple index storage locations
3. Different search result formats
4. No centralized index management

## Key Components

### 1. IndexManager (utils/index_manager.py)

The `IndexManager` provides centralized access to all indexes:

- Standardizes index storage paths
- Handles index loading with caching
- Migrates indexes from legacy paths
- Provides consistent index naming

```python
from utils.index_manager import IndexManager

# List all available indexes
available_indexes = IndexManager.list_available_indexes()

# Load a specific index
index, documents = IndexManager.load_index("AWS_index")

# Get the standard path for an index
index_path = IndexManager.get_standard_index_path("my_new_index")

# Migrate legacy indexes to the standard location
migration_results = IndexManager.migrate_legacy_indexes()
```

### 2. SearchService (utils/search_service.py)

The `SearchService` provides a unified search interface:

- Consistent search across all tabs
- Handles both vector index and web search
- Formats results consistently
- Provides error handling and fallbacks

```python
from utils.search_service import SearchService

# Get available indexes
available_indexes = SearchService.get_available_indexes()

# Search across multiple indexes
search_results = SearchService.search(
    query="How to secure AWS S3 buckets?",
    index_names=["AWS_index", "Security_index"],
    max_results=5
)

# Search the web
web_results = SearchService.search_web(
    query="AWS security best practices",
    max_results=3,
    search_engines=["Google", "Bing"]
)

# Format results for display
formatted_results = SearchService.format_results_for_display(
    results=search_results,
    format_type="markdown"
)
```

### 3. Simple Search with Enhanced Compatibility (utils/simple_search.py)

The updated `simple_search.py` provides backward compatibility:

- Works with existing code
- Attempts to use the new centralized services when available
- Falls back to original implementation when needed

```python
from utils.simple_search import perform_multi_source_search, format_search_results_for_agent

# This will use the centralized service if available, otherwise fall back
search_results = perform_multi_source_search(
    query="AWS security",
    knowledge_sources=["AWS", "Security"],
    max_results=5
)

# Format results in a way compatible with existing code
formatted_text = format_search_results_for_agent(search_results)
```

### 4. Initialization Script (utils/init_search_system.py)

The initialization script sets up the centralized search system:

- Migrates indexes from legacy paths
- Ensures all required directories exist
- Provides stats about the setup

```python
from utils.init_search_system import init_search_system

# Initialize the search system and get stats
stats = init_search_system()
print(f"Migrated {stats['migrated_index_count']} indexes")
print(f"Final index count: {stats['final_index_count']}")
```

## Implementation in Tabs

### 1. Enhanced Multi-Content Dashboard (tabs/multi_content_dashboard_enhanced.py)

This example shows how to integrate the new search system in tabs:

- Uses the centralized search service
- Provides consistent search functionality
- Has fallbacks for backward compatibility
- Includes index management features

## Migration Guide

1. First, initialize the search system to migrate indexes:
   ```python
   from utils.init_search_system import init_search_system
   init_search_system()
   ```

2. Update imports in your tabs:
   ```python
   # Old approach
   from utils.simple_search import perform_multi_source_search
   
   # New approach
   from utils.search_service import SearchService
   ```

3. Update search calls:
   ```python
   # Old approach
   results = perform_multi_source_search(
       query=search_query,
       knowledge_sources=sources_to_search,
       max_results=max_results
   )
   
   # New approach
   results = SearchService.search(
       query=search_query,
       index_names=selected_indexes,
       max_results=max_results
   )
   ```

4. Use the enhanced formatter:
   ```python
   # Old approach
   formatted_results = format_search_results_for_agent(search_results)
   
   # New approach
   formatted_results = SearchService.format_results_for_display(
       results=search_results,
       format_type="markdown"
   )
   ```

## Benefits

1. **Consistency**: All tabs use the same search implementation
2. **Centralization**: Indexes are stored in a standard location
3. **Compatibility**: Backward compatibility with existing code
4. **Error Handling**: Better error handling and fallbacks
5. **Management**: Centralized index management
