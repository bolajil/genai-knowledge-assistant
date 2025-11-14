"""
Health Check System for VaultMind
Monitors system components and provides health status
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status constants"""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'
    UNKNOWN = 'unknown'


class HealthChecker:
    """System health monitoring and checks"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, Dict] = {}
        self.check_interval = 60  # seconds
        
        # Register default checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.register_check('weaviate', self.check_weaviate)
        self.register_check('faiss', self.check_faiss)
        self.register_check('redis', self.check_redis)
        self.register_check('celery', self.check_celery)
        self.register_check('disk_space', self.check_disk_space)
        self.register_check('memory', self.check_memory)
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    def run_all_checks(self) -> Dict[str, Dict]:
        """Run all registered health checks"""
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = check_func()
                duration = time.time() - start_time
                
                results[name] = {
                    'status': result.get('status', HealthStatus.UNKNOWN),
                    'message': result.get('message', ''),
                    'details': result.get('details', {}),
                    'duration_ms': int(duration * 1000),
                    'timestamp': datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = {
                    'status': HealthStatus.UNHEALTHY,
                    'message': f'Check failed: {str(e)}',
                    'details': {},
                    'duration_ms': 0,
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        self.last_check_results = results
        return results
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self.last_check_results:
            self.run_all_checks()
        
        statuses = [r['status'] for r in self.last_check_results.values()]
        
        # Determine overall status
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        return {
            'status': overall_status,
            'components': self.last_check_results,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    # ========================================================================
    # COMPONENT-SPECIFIC HEALTH CHECKS
    # ========================================================================
    
    def check_weaviate(self) -> Dict[str, Any]:
        """Check Weaviate health"""
        try:
            from utils.weaviate_manager import WeaviateManager
            
            manager = WeaviateManager()
            
            # Try to get client and list collections
            try:
                client = manager.client
                if client:
                    collections = manager.list_collections()
                    return {
                        'status': HealthStatus.HEALTHY,
                        'message': 'Weaviate is operational',
                        'details': {
                            'url': manager.url,
                            'collections': len(collections) if collections else 0,
                            'collection_names': collections[:5] if collections else []
                        }
                    }
                else:
                    return {
                        'status': HealthStatus.UNHEALTHY,
                        'message': 'Weaviate client not initialized',
                        'details': {}
                    }
            except Exception as conn_err:
                return {
                    'status': HealthStatus.UNHEALTHY,
                    'message': f'Weaviate connection failed: {str(conn_err)}',
                    'details': {'url': manager.url if hasattr(manager, 'url') else 'unknown'}
                }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Weaviate check error: {str(e)}',
                'details': {}
            }
    
    def check_faiss(self) -> Dict[str, Any]:
        """Check FAISS indexes health"""
        try:
            from pathlib import Path
            
            faiss_dir = Path('data/faiss_index')
            if not faiss_dir.exists():
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'FAISS directory not found',
                    'details': {}
                }
            
            # Count indexes
            indexes = list(faiss_dir.glob('**/index.faiss'))
            
            if len(indexes) > 0:
                return {
                    'status': HealthStatus.HEALTHY,
                    'message': 'FAISS indexes available',
                    'details': {
                        'index_count': len(indexes),
                        'indexes': [idx.parent.name for idx in indexes[:5]]
                    }
                }
            else:
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'No FAISS indexes found',
                    'details': {}
                }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'FAISS check error: {str(e)}',
                'details': {}
            }
    
    def check_redis(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            import redis
            import os
            
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            client = redis.from_url(redis_url, socket_connect_timeout=2)
            
            # Ping Redis
            response = client.ping()
            
            if response:
                # Get additional info
                info = client.info()
                return {
                    'status': HealthStatus.HEALTHY,
                    'message': 'Redis is operational',
                    'details': {
                        'url': redis_url,
                        'connected_clients': info.get('connected_clients', 0),
                        'used_memory_human': info.get('used_memory_human', 'unknown'),
                        'uptime_days': info.get('uptime_in_days', 0)
                    }
                }
            else:
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'Redis ping failed',
                    'details': {}
                }
        except Exception as e:
            # Redis is optional for basic functionality
            return {
                'status': HealthStatus.DEGRADED,
                'message': f'Redis not available (optional): {str(e)[:100]}',
                'details': {
                    'note': 'Redis is optional. Install and start Redis for background tasks and caching.'
                }
            }
    
    def check_celery(self) -> Dict[str, Any]:
        """Check Celery worker health"""
        try:
            from celery import Celery
            import os
            
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            app = Celery(broker=redis_url, backend=redis_url)
            
            # Check active workers
            inspect = app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                worker_count = len(active_workers)
                return {
                    'status': HealthStatus.HEALTHY,
                    'message': f'{worker_count} Celery worker(s) active',
                    'details': {
                        'worker_count': worker_count,
                        'workers': list(active_workers.keys())
                    }
                }
            else:
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'No active Celery workers (optional)',
                    'details': {
                        'note': 'Celery workers are optional. Start with: python celery_worker.py'
                    }
                }
        except Exception as e:
            return {
                'status': HealthStatus.DEGRADED,
                'message': f'Celery not available (optional): {str(e)[:100]}',
                'details': {
                    'note': 'Celery is optional for background tasks. Requires Redis.'
                }
            }
    
    def check_disk_space(self) -> Dict[str, Any]:
        """Check disk space"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage('.')
            free_percent = (free / total) * 100
            
            if free_percent < 10:
                status = HealthStatus.UNHEALTHY
                message = f'Critical: Only {free_percent:.1f}% disk space remaining'
            elif free_percent < 20:
                status = HealthStatus.DEGRADED
                message = f'Warning: Only {free_percent:.1f}% disk space remaining'
            else:
                status = HealthStatus.HEALTHY
                message = f'Disk space OK: {free_percent:.1f}% free'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total_gb': round(total / (1024**3), 2),
                    'used_gb': round(used / (1024**3), 2),
                    'free_gb': round(free / (1024**3), 2),
                    'free_percent': round(free_percent, 2)
                }
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'message': f'Disk check error: {str(e)}',
                'details': {}
            }
    
    def check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            available_percent = memory.available / memory.total * 100
            
            if available_percent < 10:
                status = HealthStatus.UNHEALTHY
                message = f'Critical: Only {available_percent:.1f}% memory available'
            elif available_percent < 20:
                status = HealthStatus.DEGRADED
                message = f'Warning: Only {available_percent:.1f}% memory available'
            else:
                status = HealthStatus.HEALTHY
                message = f'Memory OK: {available_percent:.1f}% available'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_percent': memory.percent,
                    'available_percent': round(available_percent, 2)
                }
            }
        except ImportError:
            return {
                'status': HealthStatus.UNKNOWN,
                'message': 'psutil not installed',
                'details': {}
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'message': f'Memory check error: {str(e)}',
                'details': {}
            }


# Global health checker instance
health_checker = HealthChecker()
