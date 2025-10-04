"""
Microsoft Teams Messaging Tool
- Uses Incoming Webhooks via TEAMS_WEBHOOK_URL
- Exposes send_teams_message() registered with FunctionHandler

Env:
  TEAMS_WEBHOOK_URL (default webhook if webhook_url not provided)
"""
from typing import Optional, Dict, Any
import os
import requests
import json

from app.mcp.function_calling import FunctionHandler


@FunctionHandler.register
def send_teams_message(
    message: str,
    webhook_url: Optional[str] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a message to Microsoft Teams via Incoming Webhook.

    Most Teams webhooks accept a simple payload: {"text": "..."}.
    Some may require Office 365 Connector Card format; we keep it simple by default.
    """
    url = webhook_url or os.getenv("TEAMS_WEBHOOK_URL")
    if not url:
        return {"status": "error", "error": "Teams webhook not configured. Set TEAMS_WEBHOOK_URL or pass webhook_url."}

    payload: Dict[str, Any] = {"text": message}
    if title:
        # Use a basic card-like payload where supported
        payload = {
            "title": title,
            "text": message,
        }

    try:
        r = requests.post(url, json=payload, timeout=20)
        # Teams typically returns 200 on success
        if r.status_code in (200, 204):
            return {"status": "sent", "provider": "teams", "http": r.status_code}
        return {"status": "error", "provider": "teams", "error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"status": "error", "provider": "teams", "error": str(e)}
