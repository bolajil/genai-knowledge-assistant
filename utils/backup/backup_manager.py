"""
Backup Manager for VaultMind
Handles automated backups of vector stores, databases, and configuration
"""

import os
import shutil
import tarfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class BackupManager:
    """Automated backup and recovery system"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_default_config()
        self.backup_dir = Path(self.config.get('backup_dir', 'backups'))
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        
        # S3 client (optional)
        self.s3_client = None
        if self.config.get('use_s3', False):
            try:
                import boto3
                self.s3_client = boto3.client('s3')
                logger.info("S3 backup enabled")
            except ImportError:
                logger.warning("boto3 not installed, S3 backups disabled")
    
    def _load_default_config(self) -> Dict:
        """Load default configuration"""
        return {
            'backup_dir': os.getenv('BACKUP_DIR', 'backups'),
            'use_s3': os.getenv('USE_S3_BACKUP', 'false').lower() == 'true',
            's3_bucket': os.getenv('S3_BACKUP_BUCKET', 'vaultmind-backups'),
            'retention_days': int(os.getenv('BACKUP_RETENTION_DAYS', '30')),
            'compress': True
        }
    
    def backup_vector_stores(self) -> Dict[str, str]:
        """
        Backup all vector stores (FAISS indexes)
        
        Returns:
            Dict with backup paths
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"vector_stores_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        logger.info(f"Starting vector store backup: {backup_name}")
        
        try:
            # Paths to backup
            paths_to_backup = [
                Path('data/faiss_index'),
                Path('data/embeddings')
            ]
            
            # Create tar archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                for path in paths_to_backup:
                    if path.exists():
                        tar.add(path, arcname=path.name)
                        logger.info(f"Added {path} to backup")
            
            # Get backup size
            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Vector store backup completed: {backup_size_mb:.2f} MB")
            
            # Upload to S3 if configured
            s3_path = None
            if self.s3_client:
                s3_path = self._upload_to_s3(backup_path)
            
            # Create metadata
            metadata = {
                'backup_type': 'vector_stores',
                'timestamp': timestamp,
                'local_path': str(backup_path),
                's3_path': s3_path,
                'size_mb': round(backup_size_mb, 2),
                'paths_backed_up': [str(p) for p in paths_to_backup if p.exists()]
            }
            
            self._save_metadata(backup_name, metadata)
            
            return {
                'success': True,
                'backup_path': str(backup_path),
                's3_path': s3_path,
                'size_mb': backup_size_mb
            }
            
        except Exception as e:
            logger.error(f"Vector store backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def backup_databases(self) -> Dict[str, str]:
        """
        Backup all SQLite databases
        
        Returns:
            Dict with backup paths
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"databases_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        logger.info(f"Starting database backup: {backup_name}")
        
        try:
            # Database files to backup
            db_files = [
                'app/auth/users.db',
                'mcp_logs.db',
                'utils/feedback.db',
                'data/cache.db'
            ]
            
            # Create tar archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                for db_file in db_files:
                    db_path = Path(db_file)
                    if db_path.exists():
                        tar.add(db_path, arcname=db_path.name)
                        logger.info(f"Added {db_file} to backup")
            
            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Database backup completed: {backup_size_mb:.2f} MB")
            
            # Upload to S3 if configured
            s3_path = None
            if self.s3_client:
                s3_path = self._upload_to_s3(backup_path)
            
            # Create metadata
            metadata = {
                'backup_type': 'databases',
                'timestamp': timestamp,
                'local_path': str(backup_path),
                's3_path': s3_path,
                'size_mb': round(backup_size_mb, 2),
                'databases_backed_up': [f for f in db_files if Path(f).exists()]
            }
            
            self._save_metadata(backup_name, metadata)
            
            return {
                'success': True,
                'backup_path': str(backup_path),
                's3_path': s3_path,
                'size_mb': backup_size_mb
            }
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def backup_configuration(self) -> Dict[str, str]:
        """
        Backup configuration files
        
        Returns:
            Dict with backup paths
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"config_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        logger.info(f"Starting configuration backup: {backup_name}")
        
        try:
            # Configuration paths to backup
            config_paths = [
                'config/',
                '.env',
                'requirements.txt',
                'requirements-*.txt'
            ]
            
            # Create tar archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                for pattern in config_paths:
                    if '*' in pattern:
                        # Handle glob patterns
                        for path in Path('.').glob(pattern):
                            if path.exists():
                                tar.add(path, arcname=path.name)
                                logger.info(f"Added {path} to backup")
                    else:
                        path = Path(pattern)
                        if path.exists():
                            tar.add(path, arcname=path.name)
                            logger.info(f"Added {path} to backup")
            
            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Configuration backup completed: {backup_size_mb:.2f} MB")
            
            # Upload to S3 if configured
            s3_path = None
            if self.s3_client:
                s3_path = self._upload_to_s3(backup_path)
            
            # Create metadata
            metadata = {
                'backup_type': 'configuration',
                'timestamp': timestamp,
                'local_path': str(backup_path),
                's3_path': s3_path,
                'size_mb': round(backup_size_mb, 2)
            }
            
            self._save_metadata(backup_name, metadata)
            
            return {
                'success': True,
                'backup_path': str(backup_path),
                's3_path': s3_path,
                'size_mb': backup_size_mb
            }
            
        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def backup_all(self) -> Dict[str, Dict]:
        """
        Backup everything (vector stores, databases, configuration)
        
        Returns:
            Dict with all backup results
        """
        logger.info("Starting full system backup")
        
        results = {
            'vector_stores': self.backup_vector_stores(),
            'databases': self.backup_databases(),
            'configuration': self.backup_configuration()
        }
        
        success_count = sum(1 for r in results.values() if r.get('success'))
        logger.info(f"Full backup completed: {success_count}/3 successful")
        
        return results
    
    def cleanup_old_backups(self, retention_days: Optional[int] = None):
        """
        Remove backups older than retention period
        
        Args:
            retention_days: Number of days to keep backups (default from config)
        """
        if retention_days is None:
            retention_days = self.config.get('retention_days', 30)
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        logger.info(f"Cleaning up backups older than {retention_days} days")
        
        removed_count = 0
        for backup_file in self.backup_dir.glob('*.tar.gz'):
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_time < cutoff_date:
                backup_file.unlink()
                logger.info(f"Removed old backup: {backup_file.name}")
                removed_count += 1
                
                # Also remove metadata
                metadata_file = self.backup_dir / f"{backup_file.stem}.json"
                if metadata_file.exists():
                    metadata_file.unlink()
        
        logger.info(f"Cleanup completed: {removed_count} backups removed")
        return removed_count
    
    def restore_from_backup(self, backup_path: str, target_dir: str = '.'):
        """
        Restore system from backup
        
        Args:
            backup_path: Path to backup file
            target_dir: Directory to restore to
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        logger.info(f"Restoring from backup: {backup_path}")
        
        try:
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(target_dir)
            
            logger.info(f"System restored successfully from {backup_path}")
            return {'success': True, 'restored_to': target_dir}
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def list_backups(self) -> List[Dict]:
        """List all available backups with metadata"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('*.tar.gz'), reverse=True):
            metadata_file = self.backup_dir / f"{backup_file.stem}.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                # Create basic metadata
                metadata = {
                    'backup_type': 'unknown',
                    'timestamp': datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y%m%d_%H%M%S'),
                    'local_path': str(backup_file),
                    'size_mb': round(backup_file.stat().st_size / (1024 * 1024), 2)
                }
            
            backups.append(metadata)
        
        return backups
    
    def _upload_to_s3(self, file_path: Path) -> Optional[str]:
        """Upload backup to S3"""
        if not self.s3_client:
            return None
        
        try:
            bucket = self.config.get('s3_bucket')
            key = f"vaultmind-backups/{file_path.name}"
            
            self.s3_client.upload_file(str(file_path), bucket, key)
            s3_path = f"s3://{bucket}/{key}"
            logger.info(f"Backup uploaded to S3: {s3_path}")
            return s3_path
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return None
    
    def _save_metadata(self, backup_name: str, metadata: Dict):
        """Save backup metadata"""
        metadata_file = self.backup_dir / f"{backup_name}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
