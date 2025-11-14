"""
Prometheus Metrics Collection for VaultMind
Tracks system performance, health, and usage metrics
"""

from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server, CollectorRegistry, REGISTRY
import time
import logging
from typing import Optional
from functools import wraps

logger = logging.getLogger(__name__)

# ============================================================================
# METRICS DEFINITIONS
# ============================================================================

# Use try-except to handle re-registration in Streamlit
try:
    # Document Ingestion Metrics
    ingestion_total = Counter(
        'vaultmind_ingestions_total',
        'Total number of document ingestions',
        ['status', 'backend', 'document_type']
    )
except Exception as e:
    logger.warning(f"Metric already registered: vaultmind_ingestions_total - {e}")
    # Get existing metric from registry
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == 'vaultmind_ingestions_total':
            ingestion_total = collector
            break

ingestion_duration = Histogram(
    'vaultmind_ingestion_duration_seconds',
    'Time spent ingesting documents',
    ['backend', 'document_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

# Query Metrics
query_total = Counter(
    'vaultmind_queries_total',
    'Total number of queries',
    ['query_type', 'status']
)

query_duration = Histogram(
    'vaultmind_query_duration_seconds',
    'Query processing time',
    ['query_type'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)

query_results = Histogram(
    'vaultmind_query_results_count',
    'Number of results returned per query',
    ['query_type'],
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

# Vector Store Health
vector_store_health = Gauge(
    'vaultmind_vector_store_health',
    'Vector store health status (0=down, 1=healthy)',
    ['store_name']
)

vector_store_documents = Gauge(
    'vaultmind_vector_store_documents_total',
    'Total documents in vector store',
    ['store_name']
)

vector_store_latency = Gauge(
    'vaultmind_vector_store_latency_ms',
    'Vector store response latency',
    ['store_name']
)

# System Health
active_users = Gauge(
    'vaultmind_active_users',
    'Number of currently active users'
)

celery_queue_length = Gauge(
    'vaultmind_celery_queue_length',
    'Number of tasks in Celery queue',
    ['queue_name']
)

error_total = Counter(
    'vaultmind_errors_total',
    'Total number of errors',
    ['error_type', 'component']
)

# LLM Metrics
llm_requests = Counter(
    'vaultmind_llm_requests_total',
    'Total LLM API requests',
    ['provider', 'model', 'status']
)

llm_tokens = Counter(
    'vaultmind_llm_tokens_total',
    'Total tokens consumed',
    ['provider', 'model', 'token_type']
)

llm_latency = Histogram(
    'vaultmind_llm_latency_seconds',
    'LLM API response time',
    ['provider', 'model'],
    buckets=[0.5, 1, 2, 5, 10, 20, 30]
)

# System Info
system_info = Info(
    'vaultmind_system',
    'VaultMind system information'
)

# ============================================================================
# METRICS COLLECTOR CLASS
# ============================================================================

class MetricsCollector:
    """Centralized metrics collection and management"""
    
    _instance: Optional['MetricsCollector'] = None
    _server_started = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            logger.info("MetricsCollector initialized")
    
    # ========================================================================
    # INGESTION METRICS
    # ========================================================================
    
    def record_ingestion(self, status: str, backend: str, document_type: str):
        """Record document ingestion event"""
        ingestion_total.labels(
            status=status,
            backend=backend,
            document_type=document_type
        ).inc()
    
    def record_ingestion_duration(self, duration: float, backend: str, document_type: str):
        """Record ingestion duration"""
        ingestion_duration.labels(
            backend=backend,
            document_type=document_type
        ).observe(duration)
    
    # ========================================================================
    # QUERY METRICS
    # ========================================================================
    
    def record_query(self, query_type: str, status: str):
        """Record query event"""
        query_total.labels(
            query_type=query_type,
            status=status
        ).inc()
    
    def record_query_duration(self, duration: float, query_type: str):
        """Record query duration"""
        query_duration.labels(query_type=query_type).observe(duration)
    
    def record_query_results(self, count: int, query_type: str):
        """Record number of query results"""
        query_results.labels(query_type=query_type).observe(count)
    
    # ========================================================================
    # VECTOR STORE METRICS
    # ========================================================================
    
    def update_vector_store_health(self, store_name: str, is_healthy: bool):
        """Update vector store health status"""
        vector_store_health.labels(store_name=store_name).set(1 if is_healthy else 0)
    
    def update_vector_store_documents(self, store_name: str, count: int):
        """Update document count in vector store"""
        vector_store_documents.labels(store_name=store_name).set(count)
    
    def update_vector_store_latency(self, store_name: str, latency_ms: float):
        """Update vector store latency"""
        vector_store_latency.labels(store_name=store_name).set(latency_ms)
    
    # ========================================================================
    # SYSTEM METRICS
    # ========================================================================
    
    def update_active_users(self, count: int):
        """Update active user count"""
        active_users.set(count)
    
    def update_celery_queue_length(self, queue_name: str, length: int):
        """Update Celery queue length"""
        celery_queue_length.labels(queue_name=queue_name).set(length)
    
    def record_error(self, error_type: str, component: str):
        """Record error occurrence"""
        error_total.labels(
            error_type=error_type,
            component=component
        ).inc()
    
    # ========================================================================
    # LLM METRICS
    # ========================================================================
    
    def record_llm_request(self, provider: str, model: str, status: str):
        """Record LLM API request"""
        llm_requests.labels(
            provider=provider,
            model=model,
            status=status
        ).inc()
    
    def record_llm_tokens(self, provider: str, model: str, token_type: str, count: int):
        """Record LLM token usage"""
        llm_tokens.labels(
            provider=provider,
            model=model,
            token_type=token_type
        ).inc(count)
    
    def record_llm_latency(self, duration: float, provider: str, model: str):
        """Record LLM API latency"""
        llm_latency.labels(
            provider=provider,
            model=model
        ).observe(duration)
    
    # ========================================================================
    # SYSTEM INFO
    # ========================================================================
    
    def set_system_info(self, version: str, environment: str, **kwargs):
        """Set system information"""
        info_dict = {
            'version': version,
            'environment': environment,
            **kwargs
        }
        system_info.info(info_dict)
    
    # ========================================================================
    # SERVER MANAGEMENT
    # ========================================================================
    
    @classmethod
    def start_metrics_server(cls, port: int = 8000):
        """Start Prometheus metrics HTTP server"""
        if not cls._server_started:
            try:
                start_http_server(port)
                cls._server_started = True
                logger.info(f"Prometheus metrics server started on port {port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
        else:
            logger.warning("Metrics server already started")


# ============================================================================
# DECORATORS FOR AUTOMATIC METRICS
# ============================================================================

def track_duration(metric_name: str, **labels):
    """Decorator to automatically track function duration"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record duration based on metric name
                if metric_name == 'query':
                    query_duration.labels(**labels).observe(duration)
                elif metric_name == 'ingestion':
                    ingestion_duration.labels(**labels).observe(duration)
                elif metric_name == 'llm':
                    llm_latency.labels(**labels).observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Function {func.__name__} failed after {duration}s: {e}")
                raise
        return wrapper
    return decorator


def track_errors(component: str):
    """Decorator to automatically track errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_type = type(e).__name__
                error_total.labels(
                    error_type=error_type,
                    component=component
                ).inc()
                raise
        return wrapper
    return decorator


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Create global metrics collector instance
metrics = MetricsCollector()

# Example usage:
# from utils.monitoring.metrics import metrics
# metrics.record_query('semantic_search', 'success')
# metrics.record_query_duration(1.5, 'semantic_search')
