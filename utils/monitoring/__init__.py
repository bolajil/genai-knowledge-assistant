"""
VaultMind Monitoring Module
"""
# Import simple health checker (no Prometheus dependency)
from .simple_health_checks import simple_health_checker, SimpleHealthChecker

# Import alerts (safe)
from .alerts import AlertManager, ALERT_RULES

# Try to import Prometheus-based components (optional)
try:
    from .metrics import metrics, MetricsCollector, track_duration, track_errors
    from .health_checks import HealthChecker
    PROMETHEUS_AVAILABLE = True
except Exception:
    PROMETHEUS_AVAILABLE = False
    metrics = None
    MetricsCollector = None
    track_duration = None
    track_errors = None
    HealthChecker = None

__all__ = [
    'simple_health_checker',
    'SimpleHealthChecker',
    'AlertManager',
    'ALERT_RULES',
    'PROMETHEUS_AVAILABLE'
]

# Add Prometheus components if available
if PROMETHEUS_AVAILABLE:
    __all__.extend([
        'metrics',
        'MetricsCollector',
        'track_duration',
        'track_errors',
        'HealthChecker'
    ])
