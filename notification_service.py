import requests
import os
import re
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        # Configuration - Set these in your environment variables
        self.flowise_url = os.getenv("FLOWISE_URL", "http://localhost:3000/api/v1/flow")
        self.flowise_api_key = os.getenv("FLOWISE_API_KEY")
        self.n8n_url = os.getenv("N8N_URL", "http://localhost:5678/webhook")
        self.n8n_api_key = os.getenv("N8N_API_KEY")
        
    def validate_email(self, email: str) -> bool:
        """Simple email validation"""
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))
    
    def send_via_flowise(self, content: str, recipients: List[str], channels: List[str]) -> str:
        """Send notification using Flowise"""
        try:
            payload = {
                "question": f"Send this to {', '.join(channels)}: {content}",
                "overrideConfig": {
                    "sessionId": "streamlit-notification",
                    "recipients": recipients,
                    "channels": channels
                }
            }
            
            headers = {"Authorization": f"Bearer {self.flowise_api_key}"}
            response = requests.post(
                f"{self.flowise_url}/your-flow-id/run",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return "Flowise notification processed"
            return f"Flowise error: {response.text}"
        
        except Exception as e:
            logger.error(f"Flowise error: {str(e)}")
            return f"Flowise error: {str(e)}"
    
    def send_via_n8n(self, content: str, recipients: List[str], channels: List[str]) -> str:
        """Send notification using n8n"""
        try:
            # Validate and filter recipients
            valid_recipients = [r.strip() for r in recipients if self.validate_email(r.strip())]
            
            if not valid_recipients:
                return "No valid recipients provided"
                
            payload = {
                "content": content,
                "recipients": valid_recipients,
                "channels": channels,
                "source": "GenAI Assistant"
            }
            
            headers = {"X-API-KEY": self.n8n_api_key}
            response = requests.post(
                self.n8n_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return "n8n notification sent"
            return f"n8n error: {response.text}"
        
        except Exception as e:
            logger.error(f"n8n error: {str(e)}")
            return f"n8n error: {str(e)}"
    
    def send_notification(self, content: str, recipients: List[str], channels: List[str], service: str) -> str:
        """Send notification using selected service"""
        if service == "flowise":
            return self.send_via_flowise(content, recipients, channels)
        elif service == "n8n":
            return self.send_via_n8n(content, recipients, channels)
        return "No notification service selected"
