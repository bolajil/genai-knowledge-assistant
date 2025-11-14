"""
Backup Scheduler for VaultMind
Schedules automated backups using Celery Beat
"""

import logging
from celery import Celery
from celery.schedules import crontab
from .backup_manager import BackupManager
import os

logger = logging.getLogger(__name__)

# Get Celery app
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

try:
    from utils.ingestion_queue import celery_app
except ImportError:
    # Create standalone Celery app if not available
    celery_app = Celery(
        'vaultmind_backup',
        broker=REDIS_URL,
        backend=REDIS_URL
    )

# Configure backup schedule
celery_app.conf.beat_schedule = {
    # Daily vector store backup at 2 AM
    'daily-vector-backup': {
        'task': 'utils.backup.backup_scheduler.backup_vector_stores_task',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'backup'}
    },
    # Hourly database backup
    'hourly-database-backup': {
        'task': 'utils.backup.backup_scheduler.backup_database_task',
        'schedule': crontab(minute=0),
        'options': {'queue': 'backup'}
    },
    # Daily configuration backup at 3 AM
    'daily-config-backup': {
        'task': 'utils.backup.backup_scheduler.backup_configuration_task',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'backup'}
    },
    # Weekly cleanup on Sunday at 4 AM
    'weekly-cleanup': {
        'task': 'utils.backup.backup_scheduler.cleanup_old_backups_task',
        'schedule': crontab(day_of_week=0, hour=4, minute=0),
        'options': {'queue': 'backup'}
    },
}


@celery_app.task(name='utils.backup.backup_scheduler.backup_vector_stores_task')
def backup_vector_stores_task():
    """Scheduled vector store backup task"""
    logger.info("Starting scheduled vector store backup")
    
    try:
        manager = BackupManager()
        result = manager.backup_vector_stores()
        
        if result.get('success'):
            logger.info(f"Vector store backup completed: {result.get('backup_path')}")
        else:
            logger.error(f"Vector store backup failed: {result.get('error')}")
        
        return result
    except Exception as e:
        logger.error(f"Vector store backup task failed: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(name='utils.backup.backup_scheduler.backup_database_task')
def backup_database_task():
    """Scheduled database backup task"""
    logger.info("Starting scheduled database backup")
    
    try:
        manager = BackupManager()
        result = manager.backup_databases()
        
        if result.get('success'):
            logger.info(f"Database backup completed: {result.get('backup_path')}")
        else:
            logger.error(f"Database backup failed: {result.get('error')}")
        
        return result
    except Exception as e:
        logger.error(f"Database backup task failed: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(name='utils.backup.backup_scheduler.backup_configuration_task')
def backup_configuration_task():
    """Scheduled configuration backup task"""
    logger.info("Starting scheduled configuration backup")
    
    try:
        manager = BackupManager()
        result = manager.backup_configuration()
        
        if result.get('success'):
            logger.info(f"Configuration backup completed: {result.get('backup_path')}")
        else:
            logger.error(f"Configuration backup failed: {result.get('error')}")
        
        return result
    except Exception as e:
        logger.error(f"Configuration backup task failed: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(name='utils.backup.backup_scheduler.cleanup_old_backups_task')
def cleanup_old_backups_task(retention_days: int = 30):
    """Scheduled backup cleanup task"""
    logger.info(f"Starting scheduled backup cleanup (retention: {retention_days} days)")
    
    try:
        manager = BackupManager()
        removed_count = manager.cleanup_old_backups(retention_days)
        
        logger.info(f"Backup cleanup completed: {removed_count} backups removed")
        return {
            'success': True,
            'removed_count': removed_count,
            'retention_days': retention_days
        }
    except Exception as e:
        logger.error(f"Backup cleanup task failed: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(name='utils.backup.backup_scheduler.backup_all_task')
def backup_all_task():
    """Full system backup task"""
    logger.info("Starting full system backup")
    
    try:
        manager = BackupManager()
        results = manager.backup_all()
        
        success_count = sum(1 for r in results.values() if r.get('success'))
        logger.info(f"Full backup completed: {success_count}/3 successful")
        
        return results
    except Exception as e:
        logger.error(f"Full backup task failed: {e}")
        return {'success': False, 'error': str(e)}


def start_backup_scheduler():
    """
    Start the backup scheduler (for standalone use)
    
    Usage:
        python -m utils.backup.backup_scheduler
    """
    logger.info("Starting VaultMind Backup Scheduler")
    logger.info("Scheduled tasks:")
    logger.info("  - Vector stores: Daily at 2:00 AM")
    logger.info("  - Databases: Hourly")
    logger.info("  - Configuration: Daily at 3:00 AM")
    logger.info("  - Cleanup: Weekly on Sunday at 4:00 AM")
    
    # Start Celery Beat
    celery_app.start(['beat', '--loglevel=info'])


if __name__ == '__main__':
    start_backup_scheduler()
