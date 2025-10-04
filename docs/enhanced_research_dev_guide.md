# Enhanced Research Module - Developer Quick Reference

## Overview

This quick reference guide provides essential information for developers working with the optimized Enhanced Research module. It covers key components, API usage, best practices, and common troubleshooting tips.

## Key Components

### 1. `enhanced_research_optimized.py` (utils/)

Core optimization module containing:
- Parallel processing engine
- Enhanced caching system
- Memory management utilities
- Performance monitoring tools

### 2. Scripts

- `test_enhanced_research_performance.py`: Performance testing tool
- `integrate_optimized_research.py`: Safe integration utility

## API Reference

### Main Function

```python
from utils.enhanced_research_optimized import generate_enhanced_research_content

# Generate research content
content = generate_enhanced_research_content(
    task="Your research query here",
    operation="Research Topic",  # or "Problem Solving", "Comparative Analysis", etc.
    knowledge_sources=["Indexed Documents", "Web Search (External)"]
)
```

### Available Operations

- `"Research Topic"`: General research on a topic
- `"Problem Solving"`: Analysis focused on solving a specific problem
- `"Comparative Analysis"`: Compare different approaches or concepts
- `"Data Analysis"`: Analyze structured data sources
- `"Technical Deep Dive"`: In-depth technical exploration

### Available Knowledge Sources

- `"Indexed Documents"`: Local document database
- `"Web Search (External)"`: Internet search results
- `"Structured Data (External)"`: Databases and structured sources
- `"Code Repositories"`: Code examples and repositories
- `"Expert Knowledge"`: Synthesized expert knowledge

### Cache Control

```python
from utils.enhanced_research_optimized import clear_cache, set_cache_ttl

# Clear the entire cache
clear_cache()

# Set cache time-to-live (in seconds)
set_cache_ttl(7200)  # 2 hours
```

### Parallel Processing Control

```python
from utils.enhanced_research_optimized import configure_parallel_processing

# Configure parallel processing
configure_parallel_processing(
    max_workers=4,           # Maximum number of concurrent workers
    timeout=30,              # Timeout in seconds per source
    progressive_results=True # Return results as they complete
)
```

## Integration Examples

### Basic Integration

```python
import streamlit as st
from utils.enhanced_research_optimized import generate_enhanced_research_content

def render_research_tab():
    st.title("Enhanced Research")
    
    # User inputs
    query = st.text_input("Research Query")
    operation = st.selectbox(
        "Research Operation",
        ["Research Topic", "Problem Solving", "Comparative Analysis"]
    )
    sources = st.multiselect(
        "Knowledge Sources",
        ["Indexed Documents", "Web Search (External)", "Structured Data (External)"]
    )
    
    if st.button("Generate Research"):
        with st.spinner("Generating research content..."):
            content = generate_enhanced_research_content(
                task=query,
                operation=operation,
                knowledge_sources=sources
            )
            
            st.markdown(content)
```

### Advanced Integration with Progress Tracking

```python
import streamlit as st
import time
from utils.enhanced_research_optimized import (
    generate_enhanced_research_content_async,
    get_progress
)

def render_advanced_research_tab():
    st.title("Enhanced Research")
    
    # User inputs
    query = st.text_input("Research Query")
    operation = st.selectbox(
        "Research Operation",
        ["Research Topic", "Problem Solving", "Comparative Analysis"]
    )
    sources = st.multiselect(
        "Knowledge Sources",
        ["Indexed Documents", "Web Search (External)", "Structured Data (External)"]
    )
    
    if st.button("Generate Research"):
        # Start async research process
        task_id = generate_enhanced_research_content_async(
            task=query,
            operation=operation,
            knowledge_sources=sources
        )
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Track progress
        completed = False
        result = None
        
        while not completed:
            progress, status, result, completed = get_progress(task_id)
            progress_bar.progress(int(progress * 100))
            status_text.text(status)
            
            if completed:
                break
                
            time.sleep(0.1)
        
        # Display final result
        st.markdown(result)
```

## Best Practices

### Performance Optimization

1. **Cache Effectively**
   - Use consistent task/operation/sources for better cache hits
   - Consider user-specific factors in cache keys if personalization is needed

2. **Control Parallel Processing**
   - Limit `max_workers` on resource-constrained environments
   - Increase `timeout` for complex sources that need more time

3. **Memory Management**
   - Call `cleanup_resources()` periodically during long sessions
   - Monitor memory usage with `get_memory_stats()`

### Error Handling

```python
try:
    content = generate_enhanced_research_content(
        task=query,
        operation=operation,
        knowledge_sources=sources
    )
except SourceUnavailableError as e:
    st.error(f"One or more knowledge sources are unavailable: {str(e)}")
    # Fall back to available sources
    available_sources = get_available_sources()
    content = generate_enhanced_research_content(
        task=query,
        operation=operation,
        knowledge_sources=available_sources
    )
except ResourceExhaustedError as e:
    st.error(f"System resources exhausted: {str(e)}")
    # Fall back to less resource-intensive approach
    content = generate_enhanced_research_content(
        task=query,
        operation=operation,
        knowledge_sources=["Indexed Documents"]  # Only use local documents
    )
except Exception as e:
    st.error(f"An unexpected error occurred: {str(e)}")
    content = "Unable to generate research content at this time."
```

## Troubleshooting

### Common Issues and Solutions

1. **High Memory Usage**
   - Problem: Memory usage grows unbounded during extended sessions
   - Solution: 
     - Call `cleanup_resources()` periodically
     - Reduce `max_workers` in parallel processing
     - Lower cache TTL and size

2. **Slow Performance**
   - Problem: Research generation still takes too long
   - Solution:
     - Check if parallelization is working (monitor CPU usage)
     - Verify cache hit rates with `get_cache_stats()`
     - Limit knowledge sources for complex queries

3. **Cache Not Working**
   - Problem: Same queries repeatedly processed from scratch
   - Solution:
     - Ensure cache keys are consistent
     - Check if TTL is appropriate
     - Verify cache isn't being cleared prematurely

4. **Thread Pool Exhaustion**
   - Problem: "ThreadPoolExecutor is shutdown" errors
   - Solution:
     - Ensure executors are properly closed with context managers
     - Increase `max_workers` if appropriate
     - Add timeouts to prevent blocking threads

## Performance Monitoring

### Collecting Performance Metrics

```python
from utils.enhanced_research_optimized import get_performance_metrics

# Get detailed performance metrics
metrics = get_performance_metrics()

print(f"Average query time: {metrics['avg_query_time']:.2f}s")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.2f}%")
print(f"Thread pool utilization: {metrics['thread_pool_utilization']:.2f}%")
print(f"Peak memory usage: {metrics['peak_memory_mb']:.2f} MB")
```

### Writing Custom Performance Tests

Extend the provided test script:

```python
# Add to test_enhanced_research_performance.py

def test_concurrent_users(num_users=5, queries_per_user=3):
    """Test performance with concurrent users"""
    import threading
    import random
    
    # Sample queries
    sample_queries = [
        "Cloud computing security",
        "Machine learning applications",
        "Blockchain technology",
        "DevOps best practices",
        "Serverless architecture"
    ]
    
    # Create user threads
    threads = []
    results = []
    
    def user_session(user_id):
        user_results = []
        for i in range(queries_per_user):
            query = random.choice(sample_queries)
            start_time = time.time()
            
            content = generate_enhanced_research_content(
                task=query,
                operation="Research Topic",
                knowledge_sources=["Indexed Documents"]
            )
            
            end_time = time.time()
            user_results.append({
                "user_id": user_id,
                "query": query,
                "time": end_time - start_time,
                "content_size": len(content)
            })
        
        results.extend(user_results)
    
    # Start user threads
    for i in range(num_users):
        thread = threading.Thread(target=user_session, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Analyze results
    avg_time = sum(r["time"] for r in results) / len(results)
    max_time = max(r["time"] for r in results)
    min_time = min(r["time"] for r in results)
    
    print(f"Concurrent Users Test Results ({num_users} users, {queries_per_user} queries each):")
    print(f"  - Average query time: {avg_time:.2f}s")
    print(f"  - Maximum query time: {max_time:.2f}s")
    print(f"  - Minimum query time: {min_time:.2f}s")
```

## Further Reading

For more detailed information, refer to:

1. [Enhanced Research Optimization Documentation](../docs/enhanced_research_optimization.md)
2. [Performance Testing Guide](../docs/performance_testing.md)
3. [Thread Pool Executor Documentation](https://docs.python.org/3/library/concurrent.futures.html)
4. [Streamlit Performance Best Practices](https://docs.streamlit.io/knowledge-base/using-streamlit/performance-best-practices)
