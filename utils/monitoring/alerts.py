"""
Alert Management System for VaultMind
Handles multi-channel alerting (Email, Slack, Teams)
"""

import smtplib
import requests
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Alert severity levels
SEVERITY_CRITICAL = 'critical'
SEVERITY_WARNING = 'warning'
SEVERITY_INFO = 'info'

# Alert rules configuration
ALERT_RULES = {
    'high_query_latency': {
        'threshold': 5.0,  # seconds
        'severity': SEVERITY_WARNING,
        'message': 'Query latency exceeded 5 seconds'
    },
    'ingestion_failure_rate': {
        'threshold': 0.1,  # 10%
        'severity': SEVERITY_CRITICAL,
        'message': 'High ingestion failure rate detected (>10%)'
    },
    'vector_store_down': {
        'severity': SEVERITY_CRITICAL,
        'message': 'Vector store connection failed'
    },
    'high_error_rate': {
        'threshold': 0.05,  # 5%
        'severity': SEVERITY_WARNING,
        'message': 'Error rate exceeded 5%'
    },
    'low_disk_space': {
        'threshold': 0.1,  # 10% remaining
        'severity': SEVERITY_WARNING,
        'message': 'Low disk space detected (<10% remaining)'
    }
}


class AlertManager:
    """Manages system alerts and notifications"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        self.alert_history: List[Dict] = []
        self.alert_channels = {
            'email': self._send_email_alert,
            'slack': self._send_slack_alert,
            'teams': self._send_teams_alert,
            'console': self._send_console_alert
        }
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration from environment"""
        return {
            'email': {
                'enabled': os.getenv('ALERT_EMAIL_ENABLED', 'false').lower() == 'true',
                'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'smtp_user': os.getenv('SMTP_USER', ''),
                'smtp_password': os.getenv('SMTP_PASSWORD', ''),
                'from_email': os.getenv('ALERT_FROM_EMAIL', 'alerts@vaultmind.ai'),
                'to_emails': os.getenv('ALERT_TO_EMAILS', '').split(',')
            },
            'slack': {
                'enabled': os.getenv('ALERT_SLACK_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.getenv('SLACK_WEBHOOK_URL', '')
            },
            'teams': {
                'enabled': os.getenv('ALERT_TEAMS_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.getenv('TEAMS_WEBHOOK_URL', '')
            },
            'console': {
                'enabled': True  # Always enabled for logging
            }
        }
    
    def send_alert(
        self,
        severity: str,
        title: str,
        message: str,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Send alert to configured channels
        
        Args:
            severity: Alert severity (critical, warning, info)
            title: Alert title
            message: Alert message
            channels: List of channels to send to (default: all enabled)
            metadata: Additional metadata
        
        Returns:
            True if alert sent successfully to at least one channel
        """
        if channels is None:
            channels = self._get_enabled_channels()
        
        alert_data = {
            'severity': severity,
            'title': title,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        # Store in history
        self.alert_history.append(alert_data)
        
        # Send to channels
        success = False
        for channel in channels:
            if channel in self.alert_channels:
                try:
                    self.alert_channels[channel](alert_data)
                    success = True
                    logger.info(f"Alert sent via {channel}: {title}")
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
        
        return success
    
    def _get_enabled_channels(self) -> List[str]:
        """Get list of enabled alert channels"""
        enabled = []
        for channel, config in self.config.items():
            if isinstance(config, dict) and config.get('enabled', False):
                enabled.append(channel)
        return enabled
    
    def _send_email_alert(self, alert_data: Dict):
        """Send email alert"""
        config = self.config.get('email', {})
        
        if not config.get('enabled'):
            return
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = config['from_email']
        msg['To'] = ', '.join(config['to_emails'])
        msg['Subject'] = f"[{alert_data['severity'].upper()}] {alert_data['title']}"
        
        # Email body
        body = f"""
VaultMind Alert

Severity: {alert_data['severity'].upper()}
Title: {alert_data['title']}
Time: {alert_data['timestamp']}

Message:
{alert_data['message']}

Metadata:
{self._format_metadata(alert_data.get('metadata', {}))}

---
This is an automated alert from VaultMind monitoring system.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        try:
            with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
                server.starttls()
                if config.get('smtp_user') and config.get('smtp_password'):
                    server.login(config['smtp_user'], config['smtp_password'])
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            raise
    
    def _send_slack_alert(self, alert_data: Dict):
        """Send Slack alert"""
        config = self.config.get('slack', {})
        
        if not config.get('enabled') or not config.get('webhook_url'):
            return
        
        # Slack color based on severity
        color_map = {
            SEVERITY_CRITICAL: '#FF0000',
            SEVERITY_WARNING: '#FFA500',
            SEVERITY_INFO: '#0000FF'
        }
        
        payload = {
            'attachments': [{
                'color': color_map.get(alert_data['severity'], '#808080'),
                'title': alert_data['title'],
                'text': alert_data['message'],
                'fields': [
                    {
                        'title': 'Severity',
                        'value': alert_data['severity'].upper(),
                        'short': True
                    },
                    {
                        'title': 'Time',
                        'value': alert_data['timestamp'],
                        'short': True
                    }
                ],
                'footer': 'VaultMind Monitoring',
                'ts': int(datetime.utcnow().timestamp())
            }]
        }
        
        # Add metadata fields
        for key, value in alert_data.get('metadata', {}).items():
            payload['attachments'][0]['fields'].append({
                'title': key,
                'value': str(value),
                'short': True
            })
        
        response = requests.post(config['webhook_url'], json=payload)
        response.raise_for_status()
    
    def _send_teams_alert(self, alert_data: Dict):
        """Send Microsoft Teams alert"""
        config = self.config.get('teams', {})
        
        if not config.get('enabled') or not config.get('webhook_url'):
            return
        
        # Teams color based on severity
        color_map = {
            SEVERITY_CRITICAL: 'FF0000',
            SEVERITY_WARNING: 'FFA500',
            SEVERITY_INFO: '0000FF'
        }
        
        payload = {
            '@type': 'MessageCard',
            '@context': 'https://schema.org/extensions',
            'summary': alert_data['title'],
            'themeColor': color_map.get(alert_data['severity'], '808080'),
            'title': f"[{alert_data['severity'].upper()}] {alert_data['title']}",
            'sections': [{
                'activityTitle': 'VaultMind Alert',
                'activitySubtitle': alert_data['timestamp'],
                'text': alert_data['message'],
                'facts': [
                    {'name': key, 'value': str(value)}
                    for key, value in alert_data.get('metadata', {}).items()
                ]
            }]
        }
        
        response = requests.post(config['webhook_url'], json=payload)
        response.raise_for_status()
    
    def _send_console_alert(self, alert_data: Dict):
        """Send console/log alert"""
        severity = alert_data['severity']
        title = alert_data['title']
        message = alert_data['message']
        
        log_message = f"ALERT [{severity.upper()}] {title}: {message}"
        
        if severity == SEVERITY_CRITICAL:
            logger.critical(log_message)
        elif severity == SEVERITY_WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _format_metadata(self, metadata: Dict) -> str:
        """Format metadata for display"""
        if not metadata:
            return "None"
        
        lines = []
        for key, value in metadata.items():
            lines.append(f"  {key}: {value}")
        return '\n'.join(lines)
    
    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """Get recent alert history"""
        return self.alert_history[-limit:]
    
    def clear_alert_history(self):
        """Clear alert history"""
        self.alert_history.clear()


# Global alert manager instance
alert_manager = AlertManager()


# Convenience functions
def send_critical_alert(title: str, message: str, **metadata):
    """Send critical alert"""
    return alert_manager.send_alert(SEVERITY_CRITICAL, title, message, metadata=metadata)


def send_warning_alert(title: str, message: str, **metadata):
    """Send warning alert"""
    return alert_manager.send_alert(SEVERITY_WARNING, title, message, metadata=metadata)


def send_info_alert(title: str, message: str, **metadata):
    """Send info alert"""
    return alert_manager.send_alert(SEVERITY_INFO, title, message, metadata=metadata)
