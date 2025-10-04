#!/usr/bin/env python3
"""
Test AWS OpenSearch connectivity using environment variables from config/storage.env.
- Non-mutating: only GET /, GET _cluster/health
- Supports both Managed domains (*.es.amazonaws.com) and Serverless (*.aoss.amazonaws.com)

Usage:
  py -m pip install opensearch-py boto3 requests-aws4auth python-dotenv
  py scripts/test_aws_opensearch_connection.py --verbose
"""
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False


def sanitize_host(raw: Optional[str]) -> str:
    if not raw:
        return ""
    raw = str(raw).strip()
    if raw.lower().startswith("arn:"):
        raise ValueError(
            "AWS_OPENSEARCH_HOST must be the domain endpoint hostname (e.g., 'search-<domain>-<hash>.<region>.es.amazonaws.com'), not an ARN."
        )
    if "://" in raw:
        p = urlparse(raw)
        if p.hostname:
            return p.hostname
    return raw


def detect_service_name(host: str) -> str:
    h = (host or "").lower()
    if h.endswith(".aoss.amazonaws.com"):
        return "aoss"  # OpenSearch Serverless
    return "es"       # Managed OpenSearch/Elasticsearch service name


def main(verbose: bool = False) -> int:
    # Load config/storage.env if present
    storage_env = Path("config/storage.env")
    if storage_env.exists():
        load_dotenv(storage_env, override=True)
        if verbose:
            print(f"Loaded env from {storage_env}")
    else:
        # Also respect top-level .env if present (override existing)
        env_loaded = load_dotenv(override=True)
        if verbose and env_loaded:
            print("Loaded env from .env")

    host_raw = os.getenv("AWS_OPENSEARCH_HOST")
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")

    if not host_raw:
        print("[ERROR] AWS_OPENSEARCH_HOST not set. Set it in Storage Settings to your domain endpoint hostname.")
        return 2

    try:
        host = sanitize_host(host_raw)
    except Exception as e:
        print(f"[ERROR] {e}")
        return 3

    service = detect_service_name(host)

    if verbose:
        print(f"Host: {host}")
        print(f"Region: {region}")
        print(f"Service: {service}")

    # Build IAM auth (falls back to default profile if keys not set)
    try:
        try:
            import boto3
            from requests_aws4auth import AWS4Auth
        except Exception as e:
            print("[ERROR] Missing dependencies. Install with: py -m pip install boto3 requests-aws4auth")
            return 4

        if access_key and secret_key:
            auth = AWS4Auth(access_key, secret_key, region, service, session_token=session_token)
        else:
            # Use ambient credentials (profile, env, SSO, etc.)
            session = boto3.Session()
            creds = session.get_credentials()
            if not creds:
                print("[ERROR] No AWS credentials found. Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or configure AWS CLI profile.")
                return 5
            frozen = creds.get_frozen_credentials()
            auth = AWS4Auth(frozen.access_key, frozen.secret_key, region, service, session_token=frozen.token)
    except Exception as e:
        print(f"[ERROR] Failed to resolve AWS credentials: {e}")
        return 6

    # Create OpenSearch client
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
    except Exception:
        print("[ERROR] Missing dependency 'opensearch-py'. Install with: py -m pip install opensearch-py")
        return 7

    use_ssl = True
    verify_certs = True
    port = 443

    if verbose:
        print(f"Connecting: host={host}, port={port}, ssl={use_ssl}, verify={verify_certs}")

    try:
        client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=auth,
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            connection_class=RequestsHttpConnection,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
    except Exception as e:
        print(f"[ERROR] Failed to create OpenSearch client: {e}")
        return 8

    # Non-mutating checks
    try:
        info = client.info()
        print("[OK] Cluster info:")
        print(info)
    except Exception as e:
        print(f"[ERROR] GET / info failed: {e}")
        return 9

    try:
        health = client.cluster.health()
        print("[OK] Cluster health:")
        print(health)
    except Exception as e:
        print(f"[WARN] GET _cluster/health failed: {e}")

    print("[DONE] OpenSearch connectivity test completed.")
    return 0


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    sys.exit(main(verbose))
