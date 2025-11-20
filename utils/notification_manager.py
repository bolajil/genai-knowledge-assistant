"""
VaultMind Push Notification Manager
Supports: Mobile push, Email, SMS, Desktop notifications
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import requests

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    QUERY_COMPLETE = "query_complete"
    DOCUMENT_PROCESSED = "document_processed"
    SYSTEM_ALERT = "system_alert"
    USER_MENTION = "user_mention"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationManager:
    """
    Unified notification manager supporting multiple channels:
    - Mobile push (Firebase, OneSignal, Pushover)
    - Email notifications
    - SMS (Twilio)
    - Desktop notifications
    - In-app notifications
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.enabled_channels = self._get_enabled_channels()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load notification configuration from environment"""
        return {
            # Firebase Cloud Messaging (FCM)
            'fcm': {
                'enabled': os.getenv('FCM_ENABLED', 'false').lower() == 'true',
                'server_key': os.getenv('FCM_SERVER_KEY', ''),
                'api_url': 'https://fcm.googleapis.com/fcm/send'
            },
            
            # OneSignal
            'onesignal': {
                'enabled': os.getenv('ONESIGNAL_ENABLED', 'false').lower() == 'true',
                'app_id': os.getenv('ONESIGNAL_APP_ID', ''),
                'api_key': os.getenv('ONESIGNAL_API_KEY', ''),
                'api_url': 'https://onesignal.com/api/v1/notifications'
            },
            
            # Pushover (Simple mobile push)
            'pushover': {
                'enabled': os.getenv('PUSHOVER_ENABLED', 'false').lower() == 'true',
                'user_key': os.getenv('PUSHOVER_USER_KEY', ''),
                'api_token': os.getenv('PUSHOVER_API_TOKEN', ''),
                'api_url': 'https://api.pushover.net/1/messages.json'
            },
            
            # Twilio SMS
            'twilio': {
                'enabled': os.getenv('TWILIO_ENABLED', 'false').lower() == 'true',
                'account_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
                'auth_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
                'from_number': os.getenv('TWILIO_FROM_NUMBER', '')
            },
            
            # Email
            'email': {
                'enabled': os.getenv('EMAIL_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
                'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'username': os.getenv('SMTP_USERNAME', ''),
                'password': os.getenv('SMTP_PASSWORD', ''),
                'from_email': os.getenv('FROM_EMAIL', '')
            },
            
            # Telegram Bot
            'telegram': {
                'enabled': os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true',
                'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
                'api_url': 'https://api.telegram.org/bot'
            },
            
            # Slack
            'slack': {
                'enabled': os.getenv('SLACK_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.getenv('SLACK_WEBHOOK_URL', '')
            },
            
            # Microsoft Teams
            'teams': {
                'enabled': os.getenv('TEAMS_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.getenv('TEAMS_WEBHOOK_URL', '')
            }
        }
    
    def _get_enabled_channels(self) -> List[str]:
        """Get list of enabled notification channels"""
        return [
            channel for channel, config in self.config.items()
            if config.get('enabled', False)
        ]
    
    def send_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        user_id: Optional[str] = None,
        device_tokens: Optional[List[str]] = None,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send notification through specified channels
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            user_id: User identifier
            device_tokens: List of device tokens for mobile push
            phone_number: Phone number for SMS
            email: Email address
            telegram_chat_id: Telegram chat ID
            data: Additional data to include
            channels: Specific channels to use (if None, uses all enabled)
        
        Returns:
            Dict with success status for each channel
        """
        results = {}
        
        # Determine which channels to use
        target_channels = channels if channels else self.enabled_channels
        
        # Send to each channel
        for channel in target_channels:
            try:
                if channel == 'fcm' and device_tokens:
                    results['fcm'] = self._send_fcm(
                        title, message, device_tokens, notification_type, priority, data
                    )
                
                elif channel == 'onesignal' and device_tokens:
                    results['onesignal'] = self._send_onesignal(
                        title, message, device_tokens, notification_type, priority, data
                    )
                
                elif channel == 'pushover':
                    results['pushover'] = self._send_pushover(
                        title, message, notification_type, priority, data
                    )
                
                elif channel == 'twilio' and phone_number:
                    results['twilio'] = self._send_sms(
                        phone_number, f"{title}: {message}"
                    )
                
                elif channel == 'email' and email:
                    results['email'] = self._send_email(
                        email, title, message, notification_type
                    )
                
                elif channel == 'telegram' and telegram_chat_id:
                    results['telegram'] = self._send_telegram(
                        telegram_chat_id, title, message, notification_type
                    )
                
                elif channel == 'slack':
                    results['slack'] = self._send_slack(
                        title, message, notification_type
                    )
                
                elif channel == 'teams':
                    results['teams'] = self._send_teams(
                        title, message, notification_type
                    )
                    
            except Exception as e:
                logger.error(f"Error sending notification via {channel}: {str(e)}")
                results[channel] = False
        
        return results
    
    def _send_fcm(
        self,
        title: str,
        message: str,
        device_tokens: List[str],
        notification_type: NotificationType,
        priority: NotificationPriority,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification via Firebase Cloud Messaging"""
        if not self.config['fcm']['enabled']:
            return False
        
        try:
            headers = {
                'Authorization': f"key={self.config['fcm']['server_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'registration_ids': device_tokens,
                'notification': {
                    'title': title,
                    'body': message,
                    'sound': 'default',
                    'badge': '1',
                    'priority': 'high' if priority == NotificationPriority.URGENT else 'normal'
                },
                'data': data or {},
                'priority': 'high' if priority == NotificationPriority.URGENT else 'normal'
            }
            
            response = requests.post(
                self.config['fcm']['api_url'],
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"FCM error: {str(e)}")
            return False
    
    def _send_onesignal(
        self,
        title: str,
        message: str,
        device_tokens: List[str],
        notification_type: NotificationType,
        priority: NotificationPriority,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification via OneSignal"""
        if not self.config['onesignal']['enabled']:
            return False
        
        try:
            headers = {
                'Authorization': f"Basic {self.config['onesignal']['api_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'app_id': self.config['onesignal']['app_id'],
                'include_player_ids': device_tokens,
                'headings': {'en': title},
                'contents': {'en': message},
                'data': data or {},
                'priority': 10 if priority == NotificationPriority.URGENT else 5
            }
            
            response = requests.post(
                self.config['onesignal']['api_url'],
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"OneSignal error: {str(e)}")
            return False
    
    def _send_pushover(
        self,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification via Pushover (simple mobile push)"""
        if not self.config['pushover']['enabled']:
            return False
        
        try:
            # Map priority to Pushover priority (-2 to 2)
            priority_map = {
                NotificationPriority.LOW: -1,
                NotificationPriority.NORMAL: 0,
                NotificationPriority.HIGH: 1,
                NotificationPriority.URGENT: 2
            }
            
            payload = {
                'token': self.config['pushover']['api_token'],
                'user': self.config['pushover']['user_key'],
                'title': title,
                'message': message,
                'priority': priority_map.get(priority, 0),
                'sound': 'pushover'
            }
            
            # Add retry for urgent notifications
            if priority == NotificationPriority.URGENT:
                payload['retry'] = 30
                payload['expire'] = 3600
            
            response = requests.post(
                self.config['pushover']['api_url'],
                data=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Pushover error: {str(e)}")
            return False
    
    def _send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS via Twilio"""
        if not self.config['twilio']['enabled']:
            return False
        
        try:
            from twilio.rest import Client
            
            client = Client(
                self.config['twilio']['account_sid'],
                self.config['twilio']['auth_token']
            )
            
            message = client.messages.create(
                body=message,
                from_=self.config['twilio']['from_number'],
                to=phone_number
            )
            
            return message.sid is not None
            
        except Exception as e:
            logger.error(f"Twilio SMS error: {str(e)}")
            return False
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        notification_type: NotificationType
    ) -> bool:
        """Send email notification"""
        if not self.config['email']['enabled']:
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[VaultMind] {subject}"
            msg['From'] = self.config['email']['from_email']
            msg['To'] = to_email
            
            # Create HTML email
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #1f77b4;">🧠 VaultMind Notification</h2>
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0;">{subject}</h3>
                            <p>{message}</p>
                        </div>
                        <p style="color: #666; font-size: 12px;">
                            This is an automated notification from VaultMind GenAI Knowledge Assistant.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            # Send email
            with smtplib.SMTP(
                self.config['email']['smtp_server'],
                self.config['email']['smtp_port']
            ) as server:
                server.starttls()
                server.login(
                    self.config['email']['username'],
                    self.config['email']['password']
                )
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Email error: {str(e)}")
            return False
    
    def _send_telegram(
        self,
        chat_id: str,
        title: str,
        message: str,
        notification_type: NotificationType
    ) -> bool:
        """Send notification via Telegram Bot"""
        if not self.config['telegram']['enabled']:
            return False
        
        try:
            # Map notification type to emoji
            emoji_map = {
                NotificationType.INFO: 'ℹ️',
                NotificationType.SUCCESS: '✅',
                NotificationType.WARNING: '⚠️',
                NotificationType.ERROR: '❌',
                NotificationType.QUERY_COMPLETE: '🔍',
                NotificationType.DOCUMENT_PROCESSED: '📄',
                NotificationType.SYSTEM_ALERT: '🔔',
                NotificationType.USER_MENTION: '👤'
            }
            
            emoji = emoji_map.get(notification_type, 'ℹ️')
            formatted_message = f"{emoji} *{title}*\n\n{message}"
            
            url = f"{self.config['telegram']['api_url']}{self.config['telegram']['bot_token']}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': formatted_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Telegram error: {str(e)}")
            return False
    
    def _send_slack(
        self,
        title: str,
        message: str,
        notification_type: NotificationType
    ) -> bool:
        """Send notification to Slack"""
        if not self.config['slack']['enabled']:
            return False
        
        try:
            # Map notification type to color
            color_map = {
                NotificationType.INFO: '#36a64f',
                NotificationType.SUCCESS: '#2eb886',
                NotificationType.WARNING: '#ff9900',
                NotificationType.ERROR: '#ff0000',
                NotificationType.QUERY_COMPLETE: '#1f77b4',
                NotificationType.DOCUMENT_PROCESSED: '#9467bd',
                NotificationType.SYSTEM_ALERT: '#ff7f0e',
                NotificationType.USER_MENTION: '#17becf'
            }
            
            payload = {
                'attachments': [{
                    'color': color_map.get(notification_type, '#36a64f'),
                    'title': title,
                    'text': message,
                    'footer': 'VaultMind GenAI Knowledge Assistant',
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(
                self.config['slack']['webhook_url'],
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Slack error: {str(e)}")
            return False
    
    def _send_teams(
        self,
        title: str,
        message: str,
        notification_type: NotificationType
    ) -> bool:
        """Send notification to Microsoft Teams"""
        if not self.config['teams']['enabled']:
            return False
        
        try:
            # Map notification type to theme color
            color_map = {
                NotificationType.INFO: '0078D4',
                NotificationType.SUCCESS: '28A745',
                NotificationType.WARNING: 'FFC107',
                NotificationType.ERROR: 'DC3545',
                NotificationType.QUERY_COMPLETE: '1F77B4',
                NotificationType.DOCUMENT_PROCESSED: '9467BD',
                NotificationType.SYSTEM_ALERT: 'FF7F0E',
                NotificationType.USER_MENTION: '17BECF'
            }
            
            payload = {
                '@type': 'MessageCard',
                '@context': 'https://schema.org/extensions',
                'summary': title,
                'themeColor': color_map.get(notification_type, '0078D4'),
                'title': f'🧠 VaultMind: {title}',
                'text': message,
                'sections': [{
                    'activityTitle': 'VaultMind GenAI Knowledge Assistant',
                    'activitySubtitle': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }]
            }
            
            response = requests.post(
                self.config['teams']['webhook_url'],
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Teams error: {str(e)}")
            return False
    
    # Convenience methods for common notifications
    
    def notify_query_complete(
        self,
        user_id: str,
        query: str,
        results_count: int,
        **kwargs
    ) -> Dict[str, bool]:
        """Notify user when query is complete"""
        return self.send_notification(
            title="Query Complete",
            message=f"Your query '{query[:50]}...' returned {results_count} results.",
            notification_type=NotificationType.QUERY_COMPLETE,
            priority=NotificationPriority.NORMAL,
            user_id=user_id,
            **kwargs
        )
    
    def notify_document_processed(
        self,
        user_id: str,
        document_name: str,
        chunks_count: int,
        **kwargs
    ) -> Dict[str, bool]:
        """Notify user when document processing is complete"""
        return self.send_notification(
            title="Document Processed",
            message=f"'{document_name}' has been processed into {chunks_count} chunks and is ready for search.",
            notification_type=NotificationType.DOCUMENT_PROCESSED,
            priority=NotificationPriority.NORMAL,
            user_id=user_id,
            **kwargs
        )
    
    def notify_system_alert(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.HIGH,
        **kwargs
    ) -> Dict[str, bool]:
        """Send system alert notification"""
        return self.send_notification(
            title=title,
            message=message,
            notification_type=NotificationType.SYSTEM_ALERT,
            priority=priority,
            **kwargs
        )
    
    def notify_user_mention(
        self,
        mentioned_user_id: str,
        mentioning_user: str,
        context: str,
        **kwargs
    ) -> Dict[str, bool]:
        """Notify user when they are mentioned"""
        return self.send_notification(
            title="You were mentioned",
            message=f"{mentioning_user} mentioned you: {context[:100]}...",
            notification_type=NotificationType.USER_MENTION,
            priority=NotificationPriority.NORMAL,
            user_id=mentioned_user_id,
            **kwargs
        )


# Global notification manager instance
notification_manager = NotificationManager()


# Helper functions for easy access
def send_push_notification(
    title: str,
    message: str,
    device_tokens: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, bool]:
    """Send push notification to mobile devices"""
    return notification_manager.send_notification(
        title=title,
        message=message,
        device_tokens=device_tokens,
        channels=['fcm', 'onesignal', 'pushover'],
        **kwargs
    )


def send_sms_notification(
    phone_number: str,
    message: str,
    **kwargs
) -> Dict[str, bool]:
    """Send SMS notification"""
    return notification_manager.send_notification(
        title="VaultMind",
        message=message,
        phone_number=phone_number,
        channels=['twilio'],
        **kwargs
    )


def send_email_notification(
    email: str,
    title: str,
    message: str,
    **kwargs
) -> Dict[str, bool]:
    """Send email notification"""
    return notification_manager.send_notification(
        title=title,
        message=message,
        email=email,
        channels=['email'],
        **kwargs
    )
