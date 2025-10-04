import os
import logging
import requests
from dotenv import load_dotenv

try:
    # Optional: use manager's discovery and headers if available
    from utils.weaviate_manager import get_weaviate_manager  # type: ignore
except Exception:  # pragma: no cover - optional import
    get_weaviate_manager = None  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection(url: str, api_key: str | None = None, disable_tls_verify: bool = False) -> bool:
    """Verify connectivity to a Weaviate cluster using REST endpoints.
    
    Steps:
    1) Readiness probe (.well-known/ready) with standard and prefixed paths ('/weaviate', '/api')
    2) REST checks: /v2/collections and /v1/schema using discovered prefix if available,
       and fallbacks including '/weaviate' and '/api'.
    """
    if not url:
        logger.error("WEAVIATE_URL environment variable not set")
        return False

    logger.info(f"Testing connection to: {url}")

    base = url.rstrip('/')

    # Optional: use manager to discover a working REST prefix and headers
    discovered_prefix = None
    mgr_headers = None
    if get_weaviate_manager is not None:
        try:
            mgr = get_weaviate_manager()
            if hasattr(mgr, "_discover_rest_prefix"):
                discovered_prefix = mgr._discover_rest_prefix()  # type: ignore[attr-defined]
            if hasattr(mgr, "_get_headers"):
                mgr_headers = mgr._get_headers()  # type: ignore[attr-defined]
        except Exception:
            discovered_prefix = None
            mgr_headers = None

    # 1) Readiness probe (optionally without TLS verification for diagnostics only)
    try:
        kwargs = {"timeout": 8}
        if disable_tls_verify:
            kwargs["verify"] = False
        readiness_endpoints = []
        if discovered_prefix is not None:
            readiness_endpoints.append(f"{base}{discovered_prefix}/v1/.well-known/ready")
        for ep in [
            f"{base}/v1/.well-known/ready",
            f"{base}/weaviate/v1/.well-known/ready",
            f"{base}/api/v1/.well-known/ready",
        ]:
            if ep not in readiness_endpoints:
                readiness_endpoints.append(ep)
        for rep in readiness_endpoints:
            try:
                resp = requests.get(rep, **kwargs)
                logger.info(f"Readiness GET {rep} -> {resp.status_code}; body: {resp.text[:160]}")
                # 200/204/401/403/405 can indicate endpoint exists
                if resp.status_code in (200, 201, 204, 401, 403, 405):
                    break
            except Exception as e:
                logger.info(f"Readiness GET {rep} failed: {e}")
    except Exception as e:
        logger.warning(f"Readiness checks encountered an error: {e}")

    # 2) REST checks with auth headers if provided
    headers = mgr_headers or {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-KEY"] = api_key

    # Requests kwargs for REST checks (apply TLS disable if requested)
    rq_kwargs: dict = {"timeout": 10}
    if disable_tls_verify:
        rq_kwargs["verify"] = False

    endpoints = []
    if discovered_prefix is not None:
        endpoints.extend([
            f"{base}{discovered_prefix}/v2/collections",
            f"{base}{discovered_prefix}/v1/schema",
        ])
    for ep in [
        f"{base}/v2/collections",
        f"{base}/weaviate/v2/collections",
        f"{base}/api/v2/collections",
        f"{base}/v1/schema",
        f"{base}/weaviate/v1/schema",
        f"{base}/api/v1/schema",
    ]:
        if ep not in endpoints:
            endpoints.append(ep)
    any_ok = False
    for ep in endpoints:
        try:
            r = requests.get(ep, headers=headers, **rq_kwargs)
            logger.info(f"GET {ep} -> {r.status_code}")
            if r.status_code == 200:
                any_ok = True
        except Exception as e:
            logger.info(f"GET {ep} failed: {e}")
    if not any_ok:
        logger.error("All REST checks failed across v2/v1 and prefixed paths (standard, '/weaviate', '/api')")
    return any_ok

if __name__ == "__main__":
    # Load env from config/weaviate.env for local dev convenience
    load_dotenv(dotenv_path=os.path.join("config", "weaviate.env"))

    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")

    if not url:
        logger.error("ERROR: WEAVIATE_URL environment variable not set")
        raise SystemExit(1)

    if not api_key:
        logger.warning("WARNING: WEAVIATE_API_KEY not set (anonymous connection)")

    # Set DISABLE_TLS_VERIFY=true to bypass TLS verification for diagnostics only
    disable_tls = os.getenv("DISABLE_TLS_VERIFY", "false").lower() in ("1", "true", "yes")
    ok = test_connection(url, api_key, disable_tls_verify=disable_tls)
    raise SystemExit(0 if ok else 2)
