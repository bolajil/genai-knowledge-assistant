"""
VaultMind Enterprise Resource Request Management System
Handles user requests for additional permissions and admin approval workflow
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

from .enterprise_permissions import ResourceRequest, PermissionLevel, enterprise_permissions

class ResourceRequestManager:
    """Manages user resource requests and admin approval workflow"""
    
    def __init__(self, db_path: str = "data/resource_requests.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize resource request database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resource_requests (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            feature_id TEXT NOT NULL,
            requested_level TEXT NOT NULL,
            justification TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_by TEXT,
            reviewed_at TIMESTAMP,
            admin_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_custom_permissions (
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            feature_id TEXT NOT NULL,
            permission_level TEXT NOT NULL,
            granted_by TEXT NOT NULL,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            notes TEXT,
            PRIMARY KEY (user_id, feature_id)
        )
        """)
        
        conn.commit()
        conn.close()
    
    def create_request(self, user_id: str, username: str, feature_id: str, 
                      requested_level: PermissionLevel, justification: str) -> str:
        """Create a new resource request"""
        request_id = f"req_{user_id}_{feature_id}_{int(datetime.now().timestamp())}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO resource_requests 
        (id, user_id, username, feature_id, requested_level, justification)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (request_id, user_id, username, feature_id, requested_level.value, justification))
        
        conn.commit()
        conn.close()
        
        return request_id
    
    def get_pending_requests(self) -> List[ResourceRequest]:
        """Get all pending resource requests"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, user_id, username, feature_id, requested_level, justification,
               status, requested_at, reviewed_by, reviewed_at, admin_notes
        FROM resource_requests 
        WHERE status = 'pending'
        ORDER BY requested_at ASC
        """)
        
        requests = []
        for row in cursor.fetchall():
            requests.append(ResourceRequest(
                id=row[0],
                user_id=row[1],
                username=row[2],
                feature_id=row[3],
                requested_level=PermissionLevel(row[4]),
                justification=row[5],
                status=row[6],
                requested_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                reviewed_by=row[8],
                reviewed_at=datetime.fromisoformat(row[9]) if row[9] else None,
                admin_notes=row[10]
            ))
        
        conn.close()
        return requests
    
    def get_user_requests(self, user_id: str) -> List[ResourceRequest]:
        """Get all requests for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, user_id, username, feature_id, requested_level, justification,
               status, requested_at, reviewed_by, reviewed_at, admin_notes
        FROM resource_requests 
        WHERE user_id = ?
        ORDER BY requested_at DESC
        """, (user_id,))
        
        requests = []
        for row in cursor.fetchall():
            requests.append(ResourceRequest(
                id=row[0],
                user_id=row[1],
                username=row[2],
                feature_id=row[3],
                requested_level=PermissionLevel(row[4]),
                justification=row[5],
                status=row[6],
                requested_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                reviewed_by=row[8],
                reviewed_at=datetime.fromisoformat(row[9]) if row[9] else None,
                admin_notes=row[10]
            ))
        
        conn.close()
        return requests
    
    def approve_request(self, request_id: str, admin_username: str, 
                       admin_notes: str = "", expires_at: Optional[datetime] = None) -> bool:
        """Approve a resource request and grant permissions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get request details
        cursor.execute("""
        SELECT user_id, username, feature_id, requested_level
        FROM resource_requests 
        WHERE id = ? AND status = 'pending'
        """, (request_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        user_id, username, feature_id, requested_level = result
        
        try:
            # Update request status
            cursor.execute("""
            UPDATE resource_requests 
            SET status = 'approved', reviewed_by = ?, reviewed_at = ?, admin_notes = ?
            WHERE id = ?
            """, (admin_username, datetime.now().isoformat(), admin_notes, request_id))
            
            # Grant custom permission
            cursor.execute("""
            INSERT OR REPLACE INTO user_custom_permissions
            (user_id, username, feature_id, permission_level, granted_by, expires_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, feature_id, requested_level, admin_username, 
                  expires_at.isoformat() if expires_at else None, admin_notes))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False
    
    def reject_request(self, request_id: str, admin_username: str, admin_notes: str = "") -> bool:
        """Reject a resource request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE resource_requests 
        SET status = 'rejected', reviewed_by = ?, reviewed_at = ?, admin_notes = ?
        WHERE id = ? AND status = 'pending'
        """, (admin_username, datetime.now().isoformat(), admin_notes, request_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_user_custom_permissions(self, user_id: str) -> Dict[str, str]:
        """Get custom permissions granted to a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT feature_id, permission_level
        FROM user_custom_permissions 
        WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
        """, (user_id, datetime.now().isoformat()))
        
        permissions = {}
        for row in cursor.fetchall():
            permissions[row[0]] = row[1]
        
        conn.close()
        return permissions
    
    def revoke_permission(self, user_id: str, feature_id: str, admin_username: str) -> bool:
        """Revoke a custom permission from a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        DELETE FROM user_custom_permissions 
        WHERE user_id = ? AND feature_id = ?
        """, (user_id, feature_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_request_statistics(self) -> Dict[str, Any]:
        """Get statistics about resource requests"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total requests by status
        cursor.execute("""
        SELECT status, COUNT(*) 
        FROM resource_requests 
        GROUP BY status
        """)
        stats['by_status'] = dict(cursor.fetchall())
        
        # Most requested features
        cursor.execute("""
        SELECT feature_id, COUNT(*) as count
        FROM resource_requests 
        GROUP BY feature_id 
        ORDER BY count DESC 
        LIMIT 10
        """)
        stats['most_requested'] = cursor.fetchall()
        
        # Recent activity
        cursor.execute("""
        SELECT COUNT(*) 
        FROM resource_requests 
        WHERE requested_at > datetime('now', '-7 days')
        """)
        stats['requests_last_7_days'] = cursor.fetchone()[0]
        
        conn.close()
        return stats

# Global instance
resource_request_manager = ResourceRequestManager()
