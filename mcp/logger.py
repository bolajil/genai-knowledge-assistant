"""
MCP Logging Module
=================
This module provides functionality to log and retrieve MCP (Model Context Protocol) operations
from a SQLite database.
"""

import os
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
from statistics import mean
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class MCPLogger:
    """MCP Logger for storing and retrieving model operations data"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the MCP Logger
        
        Args:
            db_path: Path to the SQLite database. If None, uses the default path.
        """
        if db_path:
            self.db_path = db_path
        else:
            # Use the default path relative to the project root
            project_root = Path(__file__).resolve().parent.parent
            self.db_path = str(project_root / "mcp_logs.db")
        
        self._init_db()
    
    def _init_db(self):
        """Initialize the database and create tables if they don't exist"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create operations table for logging all MCP operations
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mcp_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL,
                username TEXT NOT NULL,
                user_role TEXT NOT NULL,
                status TEXT NOT NULL,
                duration REAL,
                details TEXT,
                tool_name TEXT,
                severity TEXT DEFAULT 'info',
                prompt_tokens INTEGER,
                response_tokens INTEGER,
                total_tokens INTEGER,
                cost REAL,
                error_code TEXT,
                service TEXT
            )
            ''')
            
            # Create tools table for tracking available tools and their usage
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mcp_tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                category TEXT,
                last_used TEXT,
                usage_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
            ''')
            
            # Create a table for system metrics
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mcp_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                details TEXT
            )
            ''')
            
            # Ensure legacy databases pick up new columns
            self._ensure_operation_columns(cursor)

            conn.commit()
            logger.info(f"MCP database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
        finally:
            if conn:
                conn.close()

    def _ensure_operation_columns(self, cursor: sqlite3.Cursor) -> None:
        """Ensure extended schema columns exist for operations table."""
        try:
            cursor.execute("PRAGMA table_info(mcp_operations)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            def add_column(name: str, ddl: str) -> None:
                if name not in existing_columns:
                    cursor.execute(f"ALTER TABLE mcp_operations ADD COLUMN {ddl}")

            add_column("severity", "severity TEXT DEFAULT 'info'")
            add_column("prompt_tokens", "prompt_tokens INTEGER")
            add_column("response_tokens", "response_tokens INTEGER")
            add_column("total_tokens", "total_tokens INTEGER")
            add_column("cost", "cost REAL")
            add_column("error_code", "error_code TEXT")
            add_column("service", "service TEXT")
        except sqlite3.Error as e:
            logger.error(f"Failed to extend mcp_operations schema: {e}")
    
    def log_operation(self, operation: str, username: str, user_role: str,
                      status: str = "success", duration: float = None,
                      details: Dict[str, Any] = None, tool_name: str = None,
                      severity: str = "info", prompt_tokens: Optional[int] = None,
                      response_tokens: Optional[int] = None, total_tokens: Optional[int] = None,
                      cost: Optional[float] = None, error_code: Optional[str] = None,
                      service: Optional[str] = None):
        """Log an MCP operation to the database
        
        Args:
            operation: Name of the operation performed
            username: Username of the user who performed the operation
            user_role: Role of the user who performed the operation
            status: Status of the operation (success, failed, etc.)
            duration: Duration of the operation in seconds
            details: Additional details about the operation
            tool_name: Name of the tool used (if applicable)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            details_json = json.dumps(details) if details else None
            
            if total_tokens is None and (prompt_tokens is not None or response_tokens is not None):
                total_tokens = (prompt_tokens or 0) + (response_tokens or 0)

            cursor.execute(
                '''INSERT INTO mcp_operations 
                   (timestamp, operation, username, user_role, status, duration, details, tool_name,
                    severity, prompt_tokens, response_tokens, total_tokens, cost, error_code, service) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    timestamp,
                    operation,
                    username,
                    user_role,
                    status,
                    duration,
                    details_json,
                    tool_name,
                    severity,
                    prompt_tokens,
                    response_tokens,
                    total_tokens,
                    cost,
                    error_code,
                    service,
                )
            )
            
            # If a tool was used, update the tool usage
            if tool_name:
                cursor.execute(
                    '''INSERT INTO mcp_tools (name, last_used, usage_count) 
                       VALUES (?, ?, 1) 
                       ON CONFLICT(name) 
                       DO UPDATE SET 
                         last_used = excluded.last_used,
                         usage_count = usage_count + 1''',
                    (tool_name, timestamp)
                )
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging operation: {e}")
        finally:
            if conn:
                conn.close()
    
    def log_metric(self, metric_name: str, metric_value: float, details: Dict[str, Any] = None):
        """Log a system metric to the database
        
        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            details: Additional details about the metric
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            details_json = json.dumps(details) if details else None
            
            cursor.execute(
                '''INSERT INTO mcp_metrics (timestamp, metric_name, metric_value, details) 
                   VALUES (?, ?, ?, ?)''',
                (timestamp, metric_name, metric_value, details_json)
            )
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging metric: {e}")
        finally:
            if conn:
                conn.close()
    
    def register_tool(self, name: str, description: str = None, category: str = None):
        """Register a new MCP tool
        
        Args:
            name: Name of the tool
            description: Description of the tool
            category: Category of the tool (e.g., search, analytics)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                '''INSERT INTO mcp_tools (name, description, category, last_used) 
                   VALUES (?, ?, ?, ?) 
                   ON CONFLICT(name) 
                   DO UPDATE SET 
                     description = COALESCE(excluded.description, description),
                     category = COALESCE(excluded.category, category)''',
                (name, description, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error registering tool: {e}")
        finally:
            if conn:
                conn.close()
    
    def get_recent_operations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent operations from the database
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of operations as dictionaries
        """
        conn = None
        operations = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                '''SELECT * FROM mcp_operations 
                   ORDER BY timestamp DESC LIMIT ?''',
                (limit,)
            )
            
            for row in cursor.fetchall():
                operation = dict(row)
                if operation['details']:
                    operation['details'] = json.loads(operation['details'])
                operations.append(operation)
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving operations: {e}")
            return []
        finally:
            if conn:
                conn.close()
                
        return operations

    def get_latency_stats(self, hours: int = 24) -> Dict[str, Optional[float]]:
        """Compute latency percentiles for recent operations."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT duration FROM mcp_operations 
                   WHERE duration IS NOT NULL AND timestamp >= datetime('now', ?)''',
                (f'-{hours} hours',)
            )
            durations = [row[0] for row in cursor.fetchall() if row[0] is not None]
            if not durations:
                return {"avg": None, "p95": None, "p99": None, "max": None, "count": 0}

            durations.sort()
            count = len(durations)

            def percentile(p: float) -> float:
                if count == 1:
                    return durations[0]
                k = (count - 1) * p
                f = int(k)
                c = min(f + 1, count - 1)
                if f == c:
                    return durations[int(k)]
                d0 = durations[f] * (c - k)
                d1 = durations[c] * (k - f)
                return d0 + d1

            return {
                "avg": mean(durations),
                "p95": percentile(0.95),
                "p99": percentile(0.99),
                "max": max(durations),
                "count": count,
            }
        except sqlite3.Error as e:
            logger.error(f"Error calculating latency stats: {e}")
            return {"avg": None, "p95": None, "p99": None, "max": None, "count": 0}
        finally:
            if conn:
                conn.close()

    def get_status_breakdown(self, hours: int = 24) -> Dict[str, int]:
        """Return operation counts grouped by status."""
        conn = None
        breakdown = {"success": 0, "failed": 0, "other": 0}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT status, COUNT(*) FROM mcp_operations 
                   WHERE timestamp >= datetime('now', ?) GROUP BY status''',
                (f'-{hours} hours',)
            )
            for status, count in cursor.fetchall():
                status_lower = (status or '').lower()
                if status_lower == 'success':
                    breakdown['success'] += count
                elif status_lower == 'failed':
                    breakdown['failed'] += count
                else:
                    breakdown['other'] += count
        except sqlite3.Error as e:
            logger.error(f"Error retrieving status breakdown: {e}")
        finally:
            if conn:
                conn.close()
        return breakdown

    def get_failure_trend(self, days: int = 7) -> List[Dict[str, Union[str, int]]]:
        """Return daily failure counts for trailing window."""
        conn = None
        trend: List[Dict[str, Union[str, int]]] = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT DATE(timestamp) AS day, COUNT(*) FROM mcp_operations 
                   WHERE status = 'failed' AND timestamp >= date('now', ?) 
                   GROUP BY day ORDER BY day''',
                (f'-{days - 1} day',)
            )
            existing = {row[0]: row[1] for row in cursor.fetchall()}
            for delta in range(days - 1, -1, -1):
                day = (datetime.now() - timedelta(days=delta)).strftime('%Y-%m-%d')
                trend.append({"day": day, "count": existing.get(day, 0)})
        except sqlite3.Error as e:
            logger.error(f"Error retrieving failure trend: {e}")
        finally:
            if conn:
                conn.close()
        return trend

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return most recent alerts or failures."""
        conn = None
        alerts: List[Dict[str, Any]] = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM mcp_operations 
                   WHERE status = 'failed' OR severity IN ('warning', 'critical') 
                   ORDER BY timestamp DESC LIMIT ?''',
                (limit,)
            )
            for row in cursor.fetchall():
                record = dict(row)
                if record.get('details'):
                    record['details'] = json.loads(record['details'])
                alerts.append(record)
        except sqlite3.Error as e:
            logger.error(f"Error retrieving recent alerts: {e}")
        finally:
            if conn:
                conn.close()
        return alerts

    def get_token_totals(self, days: int = 7) -> Dict[str, int]:
        """Aggregate token usage totals."""
        conn = None
        totals = {"prompt": 0, "response": 0, "total": 0}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT COALESCE(SUM(prompt_tokens), 0),
                          COALESCE(SUM(response_tokens), 0),
                          COALESCE(SUM(total_tokens), 0)
                   FROM mcp_operations WHERE timestamp >= date('now', ?)''',
                (f'-{days - 1} day',)
            )
            row = cursor.fetchone()
            if row:
                totals["prompt"], totals["response"], totals["total"] = [int(value or 0) for value in row]
        except sqlite3.Error as e:
            logger.error(f"Error aggregating token totals: {e}")
        finally:
            if conn:
                conn.close()
        return totals

    def get_cost_summary(self, days: int = 7) -> float:
        """Return total recorded cost for time window."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT COALESCE(SUM(cost), 0) FROM mcp_operations 
                   WHERE cost IS NOT NULL AND timestamp >= date('now', ?)''',
                (f'-{days - 1} day',)
            )
            value = cursor.fetchone()
            return float(value[0]) if value and value[0] is not None else 0.0
        except sqlite3.Error as e:
            logger.error(f"Error calculating cost summary: {e}")
            return 0.0
        finally:
            if conn:
                conn.close()
    
    def get_tool_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all tools
        
        Returns:
            List of tool statistics as dictionaries
        """
        conn = None
        tools = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                '''SELECT * FROM mcp_tools ORDER BY usage_count DESC'''
            )
            
            for row in cursor.fetchall():
                tool = dict(row)
                # Format last_used as "X time ago"
                if tool['last_used']:
                    try:
                        last_used_date = datetime.strptime(tool['last_used'], "%Y-%m-%d %H:%M:%S")
                        now = datetime.now()
                        delta = now - last_used_date
                        
                        if delta.days > 0:
                            tool['last_used_friendly'] = f"{delta.days} day(s) ago"
                        elif delta.seconds >= 3600:
                            tool['last_used_friendly'] = f"{delta.seconds // 3600} hour(s) ago"
                        elif delta.seconds >= 60:
                            tool['last_used_friendly'] = f"{delta.seconds // 60} min(s) ago"
                        else:
                            tool['last_used_friendly'] = f"{delta.seconds} sec(s) ago"
                    except ValueError:
                        tool['last_used_friendly'] = tool['last_used']
                        
                tools.append(tool)
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving tool statistics: {e}")
            return []
        finally:
            if conn:
                conn.close()
                
        return tools
    
    def get_operation_counts_by_hour(self, days: int = 1) -> Dict[int, int]:
        """Get operation counts grouped by hour for the past X days
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary mapping hour (0-23) to operation count
        """
        conn = None
        hour_counts = {hour: 0 for hour in range(24)}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate the timestamp for 'days' days ago
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            cursor.execute(
                '''SELECT strftime('%H', timestamp) AS hour, COUNT(*) AS count 
                   FROM mcp_operations 
                   WHERE timestamp >= ? 
                   GROUP BY hour''',
                (cutoff_date,)
            )
            
            for hour, count in cursor.fetchall():
                hour_counts[int(hour)] = count
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving operation counts: {e}")
        finally:
            if conn:
                conn.close()
                
        return hour_counts
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics for the MCP dashboard
        
        Returns:
            Dictionary containing various metrics for the dashboard
        """
        metrics = {
            "active_sessions": 0,
            "operations_today": 0,
            "tools_available": 0,
            "alerts": 0
        }
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count operations today
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                '''SELECT COUNT(*) FROM mcp_operations 
                   WHERE timestamp >= ?''',
                (today,)
            )
            metrics["operations_today"] = cursor.fetchone()[0]
            
            # Count available tools
            cursor.execute('''SELECT COUNT(*) FROM mcp_tools WHERE status = 'active' ''')
            metrics["tools_available"] = cursor.fetchone()[0]
            
            # Count distinct users with sessions today (estimate of active sessions)
            cursor.execute(
                '''SELECT COUNT(DISTINCT username) FROM mcp_operations 
                   WHERE timestamp >= ? AND timestamp >= datetime('now', '-1 hour')''',
                (today,)
            )
            metrics["active_sessions"] = cursor.fetchone()[0]
            
            # Count recent errors as alerts
            cursor.execute(
                '''SELECT COUNT(*) FROM mcp_operations 
                   WHERE status = 'failed' AND timestamp >= datetime('now', '-1 day')'''
            )
            metrics["alerts"] = cursor.fetchone()[0]
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving dashboard metrics: {e}")
        finally:
            if conn:
                conn.close()
                
        return metrics

# Singleton instance of the MCP Logger
mcp_logger = MCPLogger()
