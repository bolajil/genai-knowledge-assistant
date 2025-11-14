"""
Simple Health Check System for VaultMind (No Prometheus dependency)
Lightweight health monitoring without metrics collection
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status constants"""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'
    UNKNOWN = 'unknown'


class SimpleHealthChecker:
    """Lightweight health monitoring without Prometheus"""
    
    def __init__(self):
        self.last_check_results: Dict[str, Dict] = {}
    
    def run_all_checks(self) -> Dict[str, Dict]:
        """Run all health checks"""
        results = {}
        
        # Run each check
        results['weaviate'] = self.check_weaviate()
        results['faiss'] = self.check_faiss()
        results['redis'] = self.check_redis()
        results['celery'] = self.check_celery()
        results['disk_space'] = self.check_disk_space()
        results['memory'] = self.check_memory()
        
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
    
    def check_weaviate(self) -> Dict[str, Any]:
        """Check Weaviate health"""
        try:
            from utils.weaviate_manager import WeaviateManager
            
            manager = WeaviateManager()
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
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Weaviate error: {str(e)[:100]}',
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
                    'message': 'FAISS directory not found (optional)',
                    'details': {}
                }
            
            indexes = list(faiss_dir.glob('**/index.faiss'))
            
            if len(indexes) > 0:
                return {
                    'status': HealthStatus.HEALTHY,
                    'message': f'{len(indexes)} FAISS index(es) available',
                    'details': {
                        'index_count': len(indexes),
                        'indexes': [idx.parent.name for idx in indexes[:5]]
                    }
                }
            else:
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'No FAISS indexes found (optional)',
                    'details': {}
                }
        except Exception as e:
            return {
                'status': HealthStatus.DEGRADED,
                'message': f'FAISS check error: {str(e)[:100]}',
                'details': {}
            }
    
    def check_redis(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            import redis
            import os
            
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            client = redis.from_url(redis_url, socket_connect_timeout=2)
            response = client.ping()
            
            if response:
                info = client.info()
                return {
                    'status': HealthStatus.HEALTHY,
                    'message': 'Redis is operational',
                    'details': {
                        'url': redis_url,
                        'connected_clients': info.get('connected_clients', 0),
                        'used_memory_human': info.get('used_memory_human', 'unknown')
                    }
                }
            else:
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'Redis ping failed (optional)',
                    'details': {}
                }
        except Exception as e:
            return {
                'status': HealthStatus.DEGRADED,
                'message': 'Redis not available (optional)',
                'details': {
                    'note': 'Redis is optional for caching and background tasks'
                }
            }
    
    def check_celery(self) -> Dict[str, Any]:
        """Check Celery worker health"""
        try:
            from celery import Celery
            import os
            
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            app = Celery(broker=redis_url, backend=redis_url)
            inspect = app.control.inspect(timeout=2)
            active_workers = inspect.active()
            
            if active_workers:
                return {
                    'status': HealthStatus.HEALTHY,
                    'message': f'{len(active_workers)} Celery worker(s) active',
                    'details': {
                        'worker_count': len(active_workers),
                        'workers': list(active_workers.keys())
                    }
                }
            else:
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'No Celery workers (optional)',
                    'details': {
                        'note': 'Start with: python celery_worker.py'
                    }
                }
        except Exception as e:
            return {
                'status': HealthStatus.DEGRADED,
                'message': 'Celery not available (optional)',
                'details': {
                    'note': 'Celery is optional for background tasks'
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
                'message': f'Disk check error: {str(e)[:100]}',
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
                'details': {'note': 'Install with: pip install psutil'}
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'message': f'Memory check error: {str(e)[:100]}',
                'details': {}
            }


# Global instance
simple_health_checker = SimpleHealthChecker()
