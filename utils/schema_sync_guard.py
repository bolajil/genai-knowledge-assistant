"""
Schema sync guard utilities for Weaviate SDK vs REST consistency.

- Refresh SDK-visible schema
- Wait for a class to become visible to the SDK
- Compute and log diff between SDK-visible classes and REST /v1/schema

Designed to be used by utils/weaviate_manager.py and ingestion scripts.
"""
from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def refresh_sdk_schema(client: Any) -> bool:
    """Attempt to refresh SDK's view of the schema/collections.

    Tries v4-style: client.collections.list_all().
    Falls back to v1-style: client.schema.get(refresh=True) if available.
    Returns True if the call succeeded without raising.
    """
    try:
        if hasattr(client, "collections") and hasattr(client.collections, "list_all"):
            _ = client.collections.list_all()
            return True
    except Exception as e:
        logger.debug(f"refresh_sdk_schema via collections.list_all() failed: {e}")
    try:
        # v1 SDK path (older clients)
        if hasattr(client, "schema") and hasattr(client.schema, "get"):
            _ = client.schema.get(refresh=True)  # type: ignore[arg-type]
            return True
    except Exception as e:
        logger.debug(f"refresh_sdk_schema via schema.get(refresh=True) failed: {e}")
    return False


def wait_for_class_in_sdk(client: Any, class_name: str, retries: int = 5, delay: float = 1.5) -> bool:
    """Wait until a class is visible to the SDK.

    Attempts a refresh then tries to get the collection by name.
    Returns True as soon as the SDK can access the class.
    """
    class_name = str(class_name)
    for attempt in range(max(1, int(retries))):
        try:
            # Refresh SDK view
            refresh_sdk_schema(client)
            # Try v4 path
            if hasattr(client, "collections") and hasattr(client.collections, "get"):
                try:
                    col = client.collections.get(class_name)
                    if col is not None:
                        return True
                except Exception:
                    pass
            # Try listing to see if name appears
            if hasattr(client, "collections") and hasattr(client.collections, "list_all"):
                try:
                    names: List[str] = []
                    for c in client.collections.list_all():
                        n = getattr(c, "name", None)
                        if n is None and isinstance(c, dict):
                            n = c.get("name")
                        if n is None and isinstance(c, str):
                            n = c
                        if n:
                            names.append(n)
                    if class_name in names:
                        return True
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(max(0.05, float(delay)))
    return False


def fetch_rest_schema(base_url: str, api_key: Optional[str], timeout: float = 20.0) -> Dict[str, Any]:
    """Fetch REST schema from /v1/schema."""
    url = base_url.rstrip("/") + "/v1/schema"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json() or {}


def diff_sdk_rest_classes(client: Any, base_url: str, api_key: Optional[str]) -> Dict[str, List[str]]:
    """Return a diff of class names between SDK-visible and REST schema.

    Returns dict with keys: sdk_classes, rest_classes, missing_in_sdk, missing_in_rest
    """
    sdk_names: List[str] = []
    try:
        if hasattr(client, "collections") and hasattr(client.collections, "list_all"):
            for c in client.collections.list_all():
                n = getattr(c, "name", None)
                if n is None and isinstance(c, dict):
                    n = c.get("name")
                if n is None and isinstance(c, str):
                    n = c
                if n:
                    sdk_names.append(n)
    except Exception as e:
        logger.debug(f"Listing SDK collections failed: {e}")

    rest_names: List[str] = []
    try:
        schema = fetch_rest_schema(base_url, api_key)
        for cls in schema.get("classes", []) or []:
            if isinstance(cls, dict):
                n = cls.get("class") or cls.get("name")
                if n:
                    rest_names.append(str(n))
    except Exception as e:
        logger.debug(f"Fetching REST schema failed: {e}")

    missing_in_sdk = sorted(list(set(rest_names) - set(sdk_names)))
    missing_in_rest = sorted(list(set(sdk_names) - set(rest_names)))
    return {
        "sdk_classes": sdk_names,
        "rest_classes": rest_names,
        "missing_in_sdk": missing_in_sdk,
        "missing_in_rest": missing_in_rest,
    }
