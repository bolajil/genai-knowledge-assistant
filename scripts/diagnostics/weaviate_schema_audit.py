#!/usr/bin/env python3
"""
Weaviate Schema Audit CLI (Enhanced)

- Fetches full schema via REST v1
- Aggregates object counts via GraphQL (with optional tenant)
- Captures vectorizer, moduleConfig, and property names per class
- Exports results to JSON for traceability/diffing

Usage:
  python scripts/diagnostics/weaviate_schema_audit.py \
    --url https://<cluster>.weaviate.cloud \
    --api_key <YOUR_API_KEY> \
    --tenant <tenant_id_optional> \
    --export ./audit_logs/schema_audit.json \
    --verbose

Notes:
- Designed to be compatible with GCP WCS clusters that expose only v1 endpoints.
- Uses raw HTTP (httpx) to avoid SDK version differences.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import httpx


def setup_logger(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _base_url(url: str) -> str:
    return (url or "").rstrip("/")


def _headers(api_key: Optional[str]) -> Dict[str, str]:
    headers = {
        "User-Agent": "VaultMind-Weaviate-Audit/1.0",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def fetch_schema(url: str, api_key: Optional[str], timeout: float = 30.0) -> Dict[str, Any]:
    base = _base_url(url)
    endpoint = f"{base}/v1/schema"
    logging.debug(f"Fetching schema from {endpoint}")
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(endpoint, headers=_headers(api_key))
        logging.info(f"GET {endpoint} -> {resp.status_code}")
        resp.raise_for_status()
        return resp.json() or {}


def aggregate_count(url: str, api_key: Optional[str], class_name: str, tenant: Optional[str] = None, timeout: float = 30.0) -> Optional[int]:
    base = _base_url(url)
    endpoint = f"{base}/v1/graphql"
    # Build GraphQL aggregate with optional tenant
    tenant_arg = f'(tenant: "{tenant}")' if tenant else ""
    query = f"{{ Aggregate {{ {class_name}{tenant_arg} {{ meta {{ count }} }} }} }}"
    payload = {"query": query}
    logging.debug(f"Aggregate count for class '{class_name}' with tenant='{tenant}': {query}")
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(endpoint, headers=_headers(api_key), json=payload)
        logging.info(f"POST {endpoint} -> {resp.status_code}")
        if resp.status_code != 200:
            logging.warning(f"GraphQL count failed for '{class_name}': {resp.status_code} {resp.text[:200]}")
            return None
        data = resp.json() or {}
        try:
            agg = data.get("data", {}).get("Aggregate", {})
            nodes = agg.get(class_name)
            if isinstance(nodes, list) and nodes:
                meta = nodes[0].get("meta") if isinstance(nodes[0], dict) else None
                if isinstance(meta, dict) and "count" in meta:
                    return int(meta["count"])  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            logging.debug(f"Parsing aggregate response failed for '{class_name}': {e}; raw={data}")
        return None


def audit_schema(url: str, api_key: Optional[str], tenant: Optional[str] = None) -> List[Dict[str, Any]]:
    schema = fetch_schema(url, api_key)
    classes = schema.get("classes", []) or []
    results: List[Dict[str, Any]] = []

    logging.info(f"Discovered {len(classes)} classes in schema")

    for cls in classes:
        if not isinstance(cls, dict):
            continue
        class_name = cls.get("class") or cls.get("name")
        if not class_name:
            continue
        vectorizer = cls.get("vectorizer", "N/A")
        module_config = cls.get("moduleConfig", {}) or {}
        properties = cls.get("properties", []) or []

        try:
            count = aggregate_count(url, api_key, class_name, tenant=tenant)
        except Exception as e:  # noqa: BLE001
            logging.warning(f"Failed to aggregate count for '{class_name}': {e}")
            count = None

        logging.info(
            f"Class '{class_name}': objects={count if count is not None else 'UNKNOWN'} | Vectorizer={vectorizer}"
        )
        results.append(
            {
                "class": class_name,
                "object_count": count,
                "vectorizer": vectorizer,
                "moduleConfig": module_config,
                "properties": [p.get("name") for p in properties if isinstance(p, dict) and p.get("name")],
            }
        )

    return results


def export_results(results: List[Dict[str, Any]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logging.info(f"Exported audit results to {output_path}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Weaviate Schema Audit CLI (Enhanced)")
    parser.add_argument("--url", required=True, help="Weaviate cluster URL (root, no trailing slash)")
    parser.add_argument("--api_key", help="Weaviate API key")
    parser.add_argument("--tenant", help="Tenant ID (optional)")
    parser.add_argument("--export", help="Path to export results as JSON (optional)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args(argv)

    setup_logger(args.verbose)

    try:
        results = audit_schema(url=args.url, api_key=args.api_key, tenant=args.tenant)
        if args.export:
            export_results(results, args.export)
        else:
            # Pretty-print to console if no export path
            print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:  # noqa: BLE001
        logging.error(f"Audit failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
