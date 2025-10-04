"""
Enterprise Email Tool
- Supports SMTP and Microsoft Graph sendMail
- Exposes a unified send_email() function registered with FunctionHandler

Env (SMTP):
  SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_USE_TLS (true/false), SMTP_FROM
Env (MS Graph):
  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, GRAPH_SENDER (user principal name or user id)
  GRAPH_SCOPE (optional, default: https://graph.microsoft.com/.default)

Usage via FunctionHandler.execute("send_email", {...})
"""
from typing import List, Optional, Dict, Any
import os
import base64
import json
import smtplib
from email.message import EmailMessage
import requests

from app.mcp.function_calling import FunctionHandler


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _send_email_smtp(
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    subtype: str = "plain",
) -> Dict[str, Any]:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    use_tls = _bool_env("SMTP_USE_TLS", True)
    use_ssl = _bool_env("SMTP_USE_SSL", False)
    sender = os.getenv("SMTP_FROM", username or "noreply@example.com")

    # Configuration validation:
    # - Host is required
    # - Credentials: either both username and password are provided, or neither (allow unauthenticated relay)
    if not host:
        return {"status": "error", "error": "SMTP not configured. Set SMTP_HOST (and PORT)."}
    if (username and not password) or (password and not username):
        return {"status": "error", "error": "Incomplete SMTP credentials: provide both SMTP_USERNAME and SMTP_PASSWORD, or neither for unauthenticated send."}

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        # BCC isn't part of headers exposed to recipients; we keep it separate
        pass
    msg["Subject"] = subject
    msg.set_content(body, subtype=subtype)

    if attachments:
        for att in attachments:
            # att: {filename, content (base64 or raw), mime_type}
            filename = att.get("filename", "attachment")
            mime_type = att.get("mime_type", "application/octet-stream")
            content = att.get("content")
            if isinstance(content, str):
                try:
                    # try base64 decode first
                    data = base64.b64decode(content)
                except Exception:
                    data = content.encode("utf-8")
            else:
                data = content or b""
            maintype, _, subtype_part = mime_type.partition("/")
            msg.add_attachment(data, maintype=maintype or "application", subtype=subtype_part or "octet-stream", filename=filename)

    try:
        # Primary path: SSL first if explicitly requested or port 465
        if use_ssl or port == 465:
            try:
                with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                    # EHLO for capability discovery under SSL
                    try:
                        server.ehlo()
                    except Exception:
                        pass
                    if username and password:
                        server.login(username, password)
                    server.send_message(msg, from_addr=sender, to_addrs=(to + (cc or []) + (bcc or [])))
                return {"status": "sent", "provider": "smtp"}
            except Exception as e:
                # Fall through to STARTTLS attempt if SSL path failed and TLS is allowed
                if not use_tls:
                    return {"status": "error", "provider": "smtp", "error": str(e)}

        # STARTTLS path (typical for port 587)
        with smtplib.SMTP(host, port, timeout=30) as server:
            # EHLO pre-TLS
            try:
                server.ehlo()
            except Exception:
                pass
            if use_tls:
                try:
                    server.starttls()
                    # EHLO post-TLS to refresh capabilities (AUTH often appears only after STARTTLS)
                    try:
                        server.ehlo()
                    except Exception:
                        pass
                except Exception as e:
                    return {"status": "error", "provider": "smtp", "error": f"STARTTLS failed: {e}"}

            # Attempt login if credentials provided
            if username and password:
                try:
                    # Some servers do not advertise AUTH pre-TLS; after TLS, AUTH should be present
                    server.login(username, password)
                except smtplib.SMTPNotSupportedError as e:
                    # If AUTH still not supported, try SSL fallback on 465
                    try:
                        with smtplib.SMTP_SSL(host, 465, timeout=30) as ssl_server:
                            try:
                                ssl_server.ehlo()
                            except Exception:
                                pass
                            ssl_server.login(username, password)
                            ssl_server.send_message(msg, from_addr=sender, to_addrs=(to + (cc or []) + (bcc or [])))
                        return {"status": "sent", "provider": "smtp"}
                    except Exception as e2:
                        return {"status": "error", "provider": "smtp", "error": f"AUTH not supported on {host}:{port}; SSL fallback failed: {e2}"}
                except smtplib.SMTPException as e:
                    # Other SMTP auth errors
                    return {"status": "error", "provider": "smtp", "error": str(e)}

            # Send message (for servers relaying without auth)
            server.send_message(msg, from_addr=sender, to_addrs=(to + (cc or []) + (bcc or [])))
        return {"status": "sent", "provider": "smtp"}
    except Exception as e:
        return {"status": "error", "provider": "smtp", "error": str(e)}


def _get_graph_token() -> Optional[str]:
    tenant = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    scope = os.getenv("GRAPH_SCOPE", "https://graph.microsoft.com/.default")
    if not (tenant and client_id and client_secret):
        return None
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
        "grant_type": "client_credentials",
    }
    try:
        r = requests.post(token_url, data=data, timeout=30)
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception:
        return None


def _send_email_graph(
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    subtype: str = "html",
) -> Dict[str, Any]:
    token = _get_graph_token()
    sender = os.getenv("GRAPH_SENDER")  # user id or UPN
    if not (token and sender):
        return {"status": "error", "error": "Microsoft Graph not configured. Set AZURE_* and GRAPH_SENDER."}

    url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _addr(a: List[str]):
        return [{"emailAddress": {"address": x}} for x in (a or [])]

    msg: Dict[str, Any] = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML" if subtype.lower() == "html" else "Text", "content": body},
            "toRecipients": _addr(to),
        },
        "saveToSentItems": True,
    }
    if cc:
        msg["message"]["ccRecipients"] = _addr(cc)
    if bcc:
        msg["message"]["bccRecipients"] = _addr(bcc)
    if attachments:
        atts = []
        for att in attachments:
            filename = att.get("filename", "attachment")
            mime_type = att.get("mime_type", "application/octet-stream")
            content = att.get("content", b"")
            if isinstance(content, bytes):
                content_b64 = base64.b64encode(content).decode("utf-8")
            else:
                # assume base64 string or text
                try:
                    base64.b64decode(content)
                    content_b64 = content
                except Exception:
                    content_b64 = base64.b64encode(str(content).encode("utf-8")).decode("utf-8")
            atts.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": filename,
                "contentType": mime_type,
                "contentBytes": content_b64,
            })
        msg["message"]["attachments"] = atts

    try:
        r = requests.post(url, headers=headers, data=json.dumps(msg), timeout=30)
        if r.status_code in (202, 200):
            return {"status": "sent", "provider": "ms_graph"}
        return {"status": "error", "provider": "ms_graph", "error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"status": "error", "provider": "ms_graph", "error": str(e)}


@FunctionHandler.register
def send_email(
    recipients: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    attachments_json: Optional[str] = None,
    provider: Optional[str] = None,
    subtype: str = "plain",
) -> Dict[str, Any]:
    """Send an email using SMTP or Microsoft Graph.

    recipients: comma-separated email addresses
    cc/bcc: comma-separated
    attachments_json: JSON list of {filename, mime_type, content(base64 or text)}
    provider: "smtp" | "ms_graph" | None (auto)
    subtype: "plain" or "html"
    """
    to = [x.strip() for x in (recipients or "").split(",") if x.strip()]
    cc_list = [x.strip() for x in (cc or "").split(",") if x.strip()]
    bcc_list = [x.strip() for x in (bcc or "").split(",") if x.strip()]
    attachments = None
    if attachments_json:
        try:
            attachments = json.loads(attachments_json)
        except Exception:
            attachments = None

    chosen = (provider or os.getenv("EMAIL_PROVIDER") or "").lower()
    if chosen == "smtp" or not chosen:
        smtp_res = _send_email_smtp(to, subject, body, cc_list, bcc_list, attachments, subtype)
        if smtp_res.get("status") == "sent" or chosen == "smtp":
            return smtp_res
    # Try Graph as fallback if configured
    graph_res = _send_email_graph(to, subject, body, cc_list, bcc_list, attachments, subtype)
    return graph_res
