"""
Slack Messaging Tool
- Uses Incoming Webhooks by default via SLACK_WEBHOOK_URL
- Exposes send_slack_message() registered with FunctionHandler

Env:
  SLACK_WEBHOOK_URL (default webhook if webhook_url not provided)
"""
from typing import Optional, Dict, Any
import os
import json
import requests

from app.mcp.function_calling import FunctionHandler


@FunctionHandler.register
def send_slack_message(
    message: str,
    webhook_url: Optional[str] = None,
    blocks_json: Optional[str] = None,
    username: Optional[str] = None,
    icon_emoji: Optional[str] = None,
    icon_url: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a message to Slack via Incoming Webhook.

    Note: Some webhook configurations ignore channel/username overrides.
    blocks_json: JSON string for Slack 'blocks' payload (optional)
    """
    url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return {"status": "error", "error": "Slack webhook not configured. Set SLACK_WEBHOOK_URL or pass webhook_url."}

    payload: Dict[str, Any] = {"text": message}
    if username:
        payload["username"] = username
    if icon_emoji:
        payload["icon_emoji"] = icon_emoji
    if icon_url:
        payload["icon_url"] = icon_url
    if channel:
        payload["channel"] = channel
    if blocks_json:
        try:
            payload["blocks"] = json.loads(blocks_json)
        except Exception:
            # ignore blocks parsing errors, send text only
            pass

    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code in (200, 204):
            return {"status": "sent", "provider": "slack", "http": r.status_code}
        return {"status": "error", "provider": "slack", "error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"status": "error", "provider": "slack", "error": str(e)}
