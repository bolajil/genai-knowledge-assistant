#!/usr/bin/env python3
"""
Weaviate Ingestion Validator / Object Inspector (CLI)

Validates a target class by:
- Confirming schema presence and listing properties
- Aggregating total object count (GraphQL Aggregate)
- Sampling objects via GraphQL Get and checking required fields
- Optional vector presence checks via REST per-object (include=vector)
- Optional bm25 search to confirm retrievability
- Exports a detailed JSON report

Usage:
  python scripts/diagnostics/weaviate_ingestion_validator.py \
    --url https://<cluster>.weaviate.cloud \
    --api_key <YOUR_API_KEY> \
    --class Bylaws1000 \
    --tenant <tenant_id_optional> \
    --limit 50 \
    --expected content,source,metadata \
    --check_vectors 10 \
    --query "board" \
    --export ./audit_logs/ingestion_validation.json \
    --verbose

Notes:
- Targets v1 endpoints (/v1/schema, /v1/graphql, /v1/objects) to match GCP WCS behavior.
- Avoids SDK to reduce version mismatch issues; uses httpx directly.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import httpx


# ---------- Logging ----------

def setup_logger(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# ---------- HTTP helpers ----------

def _base_url(url: str) -> str:
    return (url or "").rstrip("/")


def _headers(api_key: Optional[str]) -> Dict[str, str]:
    headers = {
        "User-Agent": "VaultMind-Weaviate-Validator/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


# ---------- Weaviate calls ----------

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
    tenant_arg = f'(tenant: "{tenant}")' if tenant else ""
    query = f"{{ Aggregate {{ {class_name}{tenant_arg} {{ meta {{ count }} }} }} }}"
    payload = {"query": query}
    logging.debug(f"Aggregate count: {query}")
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


def _build_get_selection(schema_props: List[str], desired: List[str]) -> str:
    # Only request properties that exist in schema to avoid GraphQL errors
    allowed = [p for p in desired if p in schema_props]
    # Always include these when available
    base_fields = ["content", "source", "source_type", "metadata", "created_at", "title"]
    for f in base_fields:
        if f in schema_props and f not in allowed:
            allowed.append(f)
    # Build selection set
    prop_selection = " ".join(allowed)
    additional = "_additional { id uuid score certainty distance }"
    selection = (prop_selection + " " + additional).strip()
    return selection


def get_samples(url: str, api_key: Optional[str], class_name: str, schema_props: List[str], limit: int = 50, tenant: Optional[str] = None, desired_props: Optional[List[str]] = None, timeout: float = 30.0) -> List[Dict[str, Any]]:
    base = _base_url(url)
    endpoint = f"{base}/v1/graphql"
    sel = _build_get_selection(schema_props, desired_props or [])
    tenant_arg = f'(tenant: "{tenant}")' if tenant else ""
    q = (
        f"{{ Get {{ {class_name}{tenant_arg}(limit: {int(limit)}) {{ {sel} }} }} }}"
    )
    payload = {"query": q}
    logging.debug(f"Get query: {q}")
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(endpoint, headers=_headers(api_key), json=payload)
        logging.info(f"POST {endpoint} -> {resp.status_code}")
        if resp.status_code != 200:
            logging.warning(f"GraphQL Get failed for '{class_name}': {resp.status_code} {resp.text[:200]}")
            return []
        data = resp.json() or {}
        nodes = data.get("data", {}).get("Get", {}).get(class_name)
        if isinstance(nodes, list):
            return nodes
        return []


def fetch_object_vector_presence(url: str, api_key: Optional[str], object_id: str, timeout: float = 20.0) -> bool:
    """Fetch object by id and check if 'vector' present.
    Uses /v1/objects/{id}?include=vector. Returns True if vector field exists.
    """
    if not object_id:
        return False
    base = _base_url(url)
    endpoint = f"{base}/v1/objects/{object_id}?include=vector"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(endpoint, headers=_headers(api_key))
            logging.debug(f"GET {endpoint} -> {resp.status_code}")
            if resp.status_code != 200:
                return False
            data = resp.json() or {}
            return "vector" in data or ("vectors" in data and isinstance(data["vectors"], dict))
    except Exception:
        return False


# ---------- Validation ----------

def _is_iso8601(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        v = value
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        datetime.fromisoformat(v)
        return True
    except Exception:
        return False


def validate_samples(samples: List[Dict[str, Any]], expected_props: List[str], vector_check: int, url: str, api_key: Optional[str]) -> Dict[str, Any]:
    missing_counts: Dict[str, int] = {p: 0 for p in expected_props}
    empty_content = 0
    invalid_metadata = 0
    bad_created_at = 0
    checked_vectors = 0
    present_vectors = 0

    # Extract ids for optional vector checks
    ids: List[str] = []
    for s in samples:
        addl = s.get("_additional") if isinstance(s, dict) else None
        uid = ""
        if isinstance(addl, dict):
            uid = addl.get("id") or addl.get("uuid") or ""
        if uid:
            ids.append(str(uid))

    for s in samples:
        if not isinstance(s, dict):
            continue
        for p in expected_props:
            if p not in s:
                missing_counts[p] = missing_counts.get(p, 0) + 1
        content_val = s.get("content", "")
        if not isinstance(content_val, str) or len(content_val.strip()) < 3:
            empty_content += 1
        md = s.get("metadata")
        if md is not None and not isinstance(md, dict):
            invalid_metadata += 1
        created = s.get("created_at")
        if created is not None and not _is_iso8601(created):
            bad_created_at += 1

    # Vector presence check (sample up to vector_check ids)
    for oid in ids[: max(0, int(vector_check))]:
        checked_vectors += 1
        if fetch_object_vector_presence(url, api_key, oid):
            present_vectors += 1

    return {
        "total_samples": len(samples),
        "missing_property_counts": missing_counts,
        "empty_content_count": empty_content,
        "invalid_metadata_count": invalid_metadata,
        "bad_created_at_count": bad_created_at,
        "vector_checked": checked_vectors,
        "vector_present_count": present_vectors,
    }


def bm25_search(url: str, api_key: Optional[str], class_name: str, query: str, limit: int = 10, tenant: Optional[str] = None, timeout: float = 30.0) -> Tuple[int, List[str]]:
    """Run a bm25 search and return (hit_count, top_ids)."""
    base = _base_url(url)
    endpoint = f"{base}/v1/graphql"
    tenant_arg = f'(tenant: "{tenant}")' if tenant else ""
    q = (
        f"{{ Get {{ {class_name}{tenant_arg}(bm25: {{ query: {json.dumps(query)} }}, limit: {int(limit)}) "
        "{ _additional { id uuid score } } } } }"
    )
    payload = {"query": q}
    logging.debug(f"bm25 query: {q}")
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(endpoint, headers=_headers(api_key), json=payload)
        logging.info(f"POST {endpoint} -> {resp.status_code}")
        if resp.status_code != 200:
            return 0, []
        data = resp.json() or {}
        nodes = data.get("data", {}).get("Get", {}).get(class_name)
        if not isinstance(nodes, list):
            return 0, []
        ids: List[str] = []
        for n in nodes:
            if isinstance(n, dict):
                addl = n.get("_additional") if isinstance(n.get("_additional"), dict) else {}
                uid = addl.get("id") or addl.get("uuid")
                if uid:
                    ids.append(str(uid))
        return len(nodes), ids


# ---------- Main CLI ----------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Weaviate Ingestion Validator / Object Inspector")
    parser.add_argument("--url", required=True, help="Weaviate cluster URL (root, no trailing slash)")
    parser.add_argument("--api_key", help="Weaviate API key")
    parser.add_argument("--class", dest="clazz", required=True, help="Target class/collection name")
    parser.add_argument("--tenant", help="Tenant ID (optional)")
    parser.add_argument("--limit", type=int, default=50, help="Number of sample objects to fetch")
    parser.add_argument("--expected", help="Comma-separated list of expected properties")
    parser.add_argument("--check_vectors", type=int, default=0, help="Number of objects to sample for vector presence via REST")
    parser.add_argument("--query", help="Optional bm25 query to test retrievability")
    parser.add_argument("--export", help="Path to export results as JSON (optional)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args(argv)

    setup_logger(args.verbose)

    base = _base_url(args.url)
    clazz = args.clazz

    try:
        schema = fetch_schema(base, args.api_key)
        classes = schema.get("classes", []) or []
        target = None
        for c in classes:
            if isinstance(c, dict) and (c.get("class") == clazz or c.get("name") == clazz):
                target = c
                break
        if not target:
            logging.error(f"Class '{clazz}' not found in schema")
            return 2

        schema_props = [p.get("name") for p in (target.get("properties") or []) if isinstance(p, dict) and p.get("name")]
        vectorizer = target.get("vectorizer", "N/A")
        module_config = target.get("moduleConfig", {}) or {}

        total = aggregate_count(base, args.api_key, clazz, tenant=args.tenant)

        expected_props: List[str] = []
        if args.expected:
            expected_props = [p.strip() for p in args.expected.split(",") if p.strip()]

        samples = get_samples(
            base,
            args.api_key,
            clazz,
            schema_props=schema_props,
            limit=max(1, int(args.limit)),
            tenant=args.tenant,
            desired_props=expected_props,
        )

        validation = validate_samples(samples, expected_props, vector_check=max(0, int(args.check_vectors)), url=base, api_key=args.api_key)

        search_info: Optional[Dict[str, Any]] = None
        if args.query:
            hits, top_ids = bm25_search(base, args.api_key, clazz, args.query, limit=10, tenant=args.tenant)
            search_info = {"query": args.query, "bm25_hits": hits, "top_ids": top_ids}

        report: Dict[str, Any] = {
            "class": clazz,
            "tenant": args.tenant,
            "aggregate_count": total,
            "schema_properties": schema_props,
            "vectorizer": vectorizer,
            "moduleConfig": module_config,
            "sample": {
                "limit": args.limit,
                "retrieved": len(samples),
                "validation": validation,
            },
        }
        if search_info is not None:
            report["search"] = search_info

        if args.export:
            os.makedirs(os.path.dirname(args.export) or ".", exist_ok=True)
            with open(args.export, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logging.info(f"Exported validation report to {args.export}")
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:  # noqa: BLE001
        logging.error(f"Validation failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
