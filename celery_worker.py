"""
Celery Worker Entry Point
=========================

Main entry point for starting Celery workers for document ingestion.

Usage:
    celery -A celery_worker worker --loglevel=info --pool=solo

For Windows:
    celery -A celery_worker worker --loglevel=info --pool=solo

For Linux/Mac:
    celery -A celery_worker worker --loglevel=info --concurrency=4
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/celery_worker.log')
    ]
)

logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
Path('logs').mkdir(exist_ok=True)

# Import Celery app
try:
    from utils.ingestion_queue import celery_app
    logger.info("Celery app imported successfully")
except ImportError as e:
    logger.error(f"Failed to import Celery app: {e}")
    logger.error("Make sure Redis is running and dependencies are installed:")
    logger.error("  pip install celery redis")
    sys.exit(1)

# Verify Redis connection
try:
    from redis import Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = Redis.from_url(redis_url)
    redis_client.ping()
    logger.info(f"✅ Redis connection successful: {redis_url}")
except Exception as e:
    logger.error(f"❌ Redis connection failed: {e}")
    logger.error("Please start Redis server before running Celery worker")
    logger.error("Windows: redis-server.exe")
    logger.error("Linux/Mac: sudo service redis-server start")
    sys.exit(1)

# Configure Celery for Windows
if sys.platform == 'win32':
    os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')
    logger.info("Running on Windows - using solo pool")

logger.info("="*70)
logger.info("VaultMIND Celery Worker Starting")
logger.info("="*70)
logger.info(f"Broker: {celery_app.conf.broker_url}")
logger.info(f"Backend: {celery_app.conf.result_backend}")
logger.info(f"Platform: {sys.platform}")
logger.info("="*70)

# Export celery app for Celery CLI
app = celery_app

if __name__ == '__main__':
    # Start worker programmatically (alternative to CLI)
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--pool=solo' if sys.platform == 'win32' else '--concurrency=4',
        '--max-tasks-per-child=50',
        '--time-limit=3600',
        '--soft-time-limit=3300'
    ])
