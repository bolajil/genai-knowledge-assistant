"""
Weaviate Vector Database Manager
Unified vector storage solution replacing FAISS across all tabs
"""
import os
import logging
import json
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import time
import re
import weaviate
from weaviate.classes.config import Configure
from weaviate.classes.query import Filter
import numpy as np
import httpx
import atexit
from sentence_transformers import SentenceTransformer
from .schema_sync_guard import refresh_sdk_schema, wait_for_class_in_sdk, diff_sdk_rest_classes

logger = logging.getLogger(__name__)

class WeaviateManager:
    """
    Enhanced with:
    - Cross-tab document access
    - Performance monitoring
    - Centralized caching
    """
    
    def __init__(self, 
                 url: str = "http://localhost:8080",
                 api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None):
        """
        Initialize Weaviate client
        
        Args:
            url: Weaviate instance URL (default: localhost:8080)
            api_key: Weaviate API key (for cloud instances)
            openai_api_key: OpenAI API key for vectorization
        """
        # If a console link is provided, do NOT try to derive the runtime endpoint automatically.
        # Console URLs lack region/provider segments needed for the cluster hostname.
        if "console.weaviate.cloud" in url:
            logger.warning(
                "A console.weaviate.cloud link was provided. Please set WEAVIATE_URL to your cluster endpoint, "
                "e.g., https://<slug>.c0.<region>.<provider>.weaviate.cloud. Using the provided URL as-is."
            )
            self.url = url if url.startswith('http') else f'https://{url}'
        else:
            # If no scheme, prefer HTTPS for cloud domains
            if not url.startswith('http'):
                if ('weaviate.cloud' in url) or ('weaviate.network' in url):
                    self.url = f'https://{url}'
                else:
                    self.url = f'http://{url}'
            else:
                self.url = url
        # Enforce HTTPS for WCS/cloud endpoints if incorrectly provided as HTTP
        try:
            parsed = urlparse(self.url)
            host = parsed.hostname or ''
            if parsed.scheme == 'http' and (host.endswith('weaviate.cloud') or host.endswith('weaviate.network')):
                https_url = self.url.replace('http://', 'https://', 1)
                logger.warning(f"Upgrading scheme to HTTPS for cloud endpoint: {https_url}")
                self.url = https_url
        except Exception:
            pass
        # Prefer weaviate.cloud domain by default, but only rewrite if the hostname looks like a full cluster endpoint
        try:
            parsed = urlparse(self.url)
            host = parsed.hostname or ''
            use_network = os.getenv("WEAVIATE_USE_NETWORK_DOMAIN", "false").lower() in ("1", "true", "yes")
            disable_rewrite = os.getenv("WEAVIATE_DISABLE_DOMAIN_REWRITE", "false").lower() in ("1", "true", "yes")
            if disable_rewrite:
                logger.info("Domain rewrite is disabled via WEAVIATE_DISABLE_DOMAIN_REWRITE=true; using URL as provided: %s", self.url)
            if host.endswith('weaviate.network') and not use_network and not disable_rewrite:
                # Match: <slug>.c<number>.<region>.<provider>.weaviate.network
                cluster_pat = re.compile(r"^[a-z0-9-]+\.c\d+\.[^.]+\.[^.]+\.weaviate\.network$")
                if cluster_pat.match(host):
                    new_host = host[: -len('weaviate.network')] + 'weaviate.cloud'
                    new_netloc = new_host
                    if parsed.port:
                        new_netloc = f"{new_host}:{parsed.port}"
                    rewritten = parsed._replace(netloc=new_netloc).geturl()
                    logger.info(
                        "Rewriting endpoint from weaviate.network to weaviate.cloud by default. "
                        "Set WEAVIATE_USE_NETWORK_DOMAIN=true to retain the network domain. New URL: %s",
                        rewritten,
                    )
                    self.url = rewritten
                else:
                    logger.warning(
                        "Endpoint host '%s' does not look like a full cluster hostname (slug.cN.region.provider.weaviate.network); "
                        "skipping auto-rewrite. Please set WEAVIATE_URL to the exact cluster endpoint.", host
                    )
        except Exception:
            pass
        
        # Store gRPC endpoint if provided
        self.grpc_url = None
        self.api_key = api_key
        self.openai_api_key = openai_api_key
        self._client = None
        self._collections = {}
        self.grpc_url = os.getenv("WEAVIATE_GRPC_URL")
        self.cache = {}
        self.performance_stats = {
            'query_times': [],
            'cache_hits': 0
        }
        # Discovered REST path prefix (e.g., '', '/weaviate', '/api')
        self._rest_prefix: Optional[str] = None
        self._prefix_candidates: Optional[List[str]] = None
        # Detected REST API version: 'v1' or 'v2' (lazy-detected)
        self._api_version: Optional[str] = None
        # Shared HTTP client for all REST calls (disable HTTP/2 by default; configurable TLS)
        self._http: Optional[httpx.Client] = None
        self._http = self._build_http_client()
        # Map of user-provided names -> sanitized Weaviate class names
        self._name_aliases: Dict[str, str] = {}
        # Local query embedding cache
        self._query_embedder = None
        # Track the prefix hint used at construction (for rebuild detection)
        try:
            pref = os.getenv("WEAVIATE_PATH_PREFIX", "").strip()
            if pref and not pref.startswith('/'):
                pref = '/' + pref
            if pref.endswith('/'):
                pref = pref[:-1]
            self.prefix_hint = pref or None
        except Exception:
            self.prefix_hint = None
        try:
            self._query_model_name = os.getenv("WEAVIATE_QUERY_MODEL_NAME") or os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
        except Exception:
            self._query_model_name = "all-MiniLM-L6-v2"
        
    @property
    def client(self):
        """Lazy initialization of Weaviate client"""
        if self._client is None:
            self._connect()
        return self._client

    def _sanitize_class_name(self, name: str) -> str:
        """Return a Weaviate-compatible class name.
        Rules (v1 schema / GraphQL): must start with a letter; only letters/digits/underscore. Dashes are not allowed.
        We conservatively convert to PascalCase letters+digits only.
        """
        try:
            if not isinstance(name, str):
                name = str(name or "")
            # Split on any non-alphanumeric character
            parts = re.split(r"[^A-Za-z0-9]+", name)
            parts = [p for p in parts if p]
            if not parts:
                sanitized = "Collection"
            else:
                def cap(tok: str) -> str:
                    return tok[:1].upper() + tok[1:]
                sanitized = "".join(cap(p) for p in parts)
            # Ensure starts with a letter
            if not sanitized or not sanitized[0].isalpha():
                sanitized = f"C{sanitized}"
            # Limit length gently
            if len(sanitized) > 128:
                sanitized = sanitized[:128]
            return sanitized
        except Exception:
            return "Collection"

    def _resolve_collection_name(self, given: str) -> str:
        """Map a user-supplied collection name to the sanitized Weaviate class name.
        Stores an alias for later reference and logs when a change occurs.
        """
        actual = self._sanitize_class_name(given)
        try:
            if given != actual:
                self._name_aliases[given] = actual
                logger.info(f"Sanitized collection name '{given}' -> '{actual}' for Weaviate compatibility")
        except Exception:
            pass
        return actual
    
    def _connect(self):
        """Establish connection to Weaviate"""
        try:
            # Configure connection based on available credentials
            if self.api_key:
                # WCS / Cloud: use v4 connect helper with API key and optional OpenAI header
                headers = {"X-OpenAI-Api-Key": self.openai_api_key} if self.openai_api_key else None
                # Respect path prefix (env or discovery) so SDK's /v1/meta probes target the correct path
                cluster_base = self.url.rstrip('/')
                prefix_env = os.getenv("WEAVIATE_PATH_PREFIX", "").strip()
                if prefix_env and not prefix_env.startswith('/'):
                    prefix_env = '/' + prefix_env
                if prefix_env and prefix_env.endswith('/'):
                    prefix_env = prefix_env[:-1]
                use_prefix = prefix_env
                if not use_prefix:
                    try:
                        use_prefix = self._discover_rest_prefix(force=True) or ''
                    except Exception:
                        use_prefix = ''
                cluster_with_prefix = f"{cluster_base}{use_prefix}" if use_prefix else cluster_base
                try:
                    if headers:
                        self._client = weaviate.connect_to_weaviate_cloud(
                            cluster_url=cluster_with_prefix,
                            auth_credentials=weaviate.auth.AuthApiKey(self.api_key),
                            headers=headers,
                        )
                    else:
                        self._client = weaviate.connect_to_weaviate_cloud(
                            cluster_url=cluster_with_prefix,
                            auth_credentials=weaviate.auth.AuthApiKey(self.api_key),
                        )
                except TypeError:
                    # Older/newer SDK variant without 'headers' kw: retry without it
                    self._client = weaviate.connect_to_weaviate_cloud(
                        cluster_url=cluster_with_prefix,
                        auth_credentials=weaviate.auth.AuthApiKey(self.api_key),
                    )
            else:
                # Local instance or GCP cluster
                parsed_url = urlparse(self.url)
                host = parsed_url.hostname
                port = parsed_url.port

                if not host:
                    # Fallback for simple "localhost:8080" format
                    url_parts = self.url.split(":")
                    host = url_parts[0]
                    port = int(url_parts[1]) if len(url_parts) > 1 else 8080

                # Check if we have a gRPC URL
                if self.grpc_url:
                    # For GCP clusters with gRPC endpoint
                    grpc_host = urlparse(self.grpc_url).hostname
                    grpc_port = urlparse(self.grpc_url).port or 50051
                    logger.info(f"Attempting to connect to Weaviate GCP cluster with gRPC at host='{host}', port={port}, grpc_host='{grpc_host}', grpc_port={grpc_port}")
                    
                    self._client = weaviate.connect_to_local(
                        host=host,
                        port=port,
                        grpc_host=grpc_host,
                        grpc_port=grpc_port
                    )
                else:
                    grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
                    logger.info(f"Attempting to connect to local Weaviate instance at host='{host}', port={port}, grpc_port={grpc_port}")

                    self._client = weaviate.connect_to_local(
                        host=host,
                        port=port,
                        grpc_port=grpc_port
                    )
            
            logger.info(f"Successfully connected to Weaviate at {self.url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {str(e)}")
            raise

    def _build_http_client(self) -> httpx.Client:
        """Create a resilient shared HTTPX client.

        - Disables HTTP/2 by default to avoid TLS/ALPN issues some clusters exhibit
        - Allows disabling TLS verification via WEAVIATE_TLS_VERIFY=false (diagnostics only)
        - Allows custom CA bundle via WEAVIATE_CA_BUNDLE
        - Respects system proxies via trust_env=True
        """
        # HTTP/2 often causes EOF/connection resets on some managed clusters; default off
        # Force disable HTTP/2 to prevent SSL EOF errors with some cloud proxies
        http2_env = False
        # TLS verification controls
        verify_env = os.getenv("WEAVIATE_TLS_VERIFY", "true").lower()
        ca_bundle = os.getenv("WEAVIATE_CA_BUNDLE")
        if ca_bundle and os.path.exists(ca_bundle):
            verify: Union[bool, str] = ca_bundle
        else:
            verify = verify_env not in ("0", "false", "no")

        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)

        client = httpx.Client(
            http2=http2_env,
            timeout=timeout,
            verify=verify,
            follow_redirects=True,
            trust_env=True,
        )
        # Log diagnostics for connection behavior
        try:
            if isinstance(verify, str):
                logger.info(f"HTTP client: http2={http2_env}, verify=custom-ca({verify}), trust_env=True")
            else:
                logger.info(f"HTTP client: http2={http2_env}, verify={verify}, trust_env=True")
        except Exception:
            pass
        return client

    def _http_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """HTTP request wrapper with merged headers and simple retries for transient errors.

        Retries on common transient network/TLS issues (EOF, connection reset) with backoff.
        """
        if self._http is None:
            self._http = self._build_http_client()

        # Merge headers with auth headers
        headers = kwargs.pop("headers", {}) or {}
        try:
            auth_headers = self._get_headers()
        except Exception:
            auth_headers = {}
        # Ensure a helpful User-Agent
        headers.setdefault("User-Agent", "VaultMind-WeaviateManager/1.0 (+python-httpx)")
        merged_headers = {**auth_headers, **headers}

        # Basic retry loop
        max_attempts = int(os.getenv("WEAVIATE_HTTP_RETRIES", "3"))
        base_delay = float(os.getenv("WEAVIATE_HTTP_RETRY_BASE_DELAY", "0.5"))
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                resp = self._http.request(method.upper(), url, headers=merged_headers, **kwargs)
                return resp
            except Exception as e:  # httpx.HTTPError and others
                last_exc = e
                msg = str(e)
                # Retry only for transient signs
                transient = (
                    "UNEXPECTED_EOF_WHILE_READING" in msg
                    or "EOF occurred in violation of protocol" in msg
                    or "WinError 10054" in msg
                    or "Connection reset by peer" in msg
                    or "Read timed out" in msg
                    or "Timeout" in msg
                )
                logger.debug(f"HTTP {method} {url} failed (attempt {attempt}/{max_attempts}): {e}")
                if attempt >= max_attempts or not transient:
                    break
                # Exponential backoff
                time.sleep(base_delay * (2 ** (attempt - 1)))
        # If we reach here, attempt a one-time domain fallback from '.weaviate.network' -> '.weaviate.cloud'
        if last_exc:
            try:
                use_network = os.getenv("WEAVIATE_USE_NETWORK_DOMAIN", "false").lower() in ("1", "true", "yes")
                disable_rewrite = os.getenv("WEAVIATE_DISABLE_DOMAIN_REWRITE", "false").lower() in ("1", "true", "yes")
                parsed_u = urlparse(url)
                host = parsed_u.hostname or ""
                if (not use_network) and (not disable_rewrite) and host.endswith("weaviate.network"):
                    # Only fallback if host looks like a full cluster hostname
                    cluster_pat = re.compile(r"^[a-z0-9-]+\.c\d+\.[^.]+\.[^.]+\.weaviate\.network$")
                    if cluster_pat.match(host):
                        new_host = host[: -len("weaviate.network")] + "weaviate.cloud"
                        new_netloc = new_host
                        if parsed_u.port:
                            new_netloc = f"{new_host}:{parsed_u.port}"
                        alt_url = parsed_u._replace(netloc=new_netloc).geturl()
                        logger.warning(f"TLS/connection error to network domain; trying cloud domain fallback: {alt_url}")
                        try:
                            resp2 = self._http.request(method.upper(), alt_url, headers=merged_headers, **kwargs)
                            # If original URL used our manager base, update base to cloud variant
                            try:
                                base = self._get_base()
                                if url.startswith(base):
                                    parsed_base = urlparse(base)
                                    base_host = parsed_base.hostname or ""
                                    if cluster_pat.match(base_host):
                                        base_new_host = base_host[: -len("weaviate.network")] + "weaviate.cloud"
                                        base_new_netloc = base_new_host
                                        if parsed_base.port:
                                            base_new_netloc = f"{base_new_host}:{parsed_base.port}"
                                        self.url = parsed_base._replace(netloc=base_new_netloc).geturl()
                                        logger.info(f"Switched manager base URL to cloud domain: {self.url}")
                            except Exception:
                                pass
                            return resp2
                        except Exception as e2:
                            logger.debug(f"Cloud domain fallback failed: {e2}")
                    else:
                        logger.debug("Network-domain host does not match full cluster pattern; skipping cloud fallback")
            except Exception:
                pass
            # Raise the original exception if fallback did not succeed
            raise last_exc
        # Fallback (should not happen)
        raise RuntimeError(f"HTTP request failed for {method} {url}")

    # --- Local query embedding helpers ---
    def _get_query_model_name(self) -> str:
        try:
            return os.getenv("WEAVIATE_QUERY_MODEL_NAME") or self._query_model_name
        except Exception:
            return getattr(self, "_query_model_name", "all-MiniLM-L6-v2")

    def _get_or_load_query_embedder(self, model_name: Optional[str] = None):
        try:
            name = model_name or self._get_query_model_name()
            # Reload if name changed
            if getattr(self, "_query_embedder", None) is None or getattr(self, "_query_model_loaded", None) != name:
                logger.info(f"Loading SentenceTransformer model for queries: {name}")
                self._query_embedder = SentenceTransformer(name)
                self._query_model_loaded = name
            return self._query_embedder
        except Exception as e:
            logger.error(f"Failed to load query embedding model: {e}")
            return None

    def _get_class_schema_via_schema(self, class_name: str) -> Optional[Dict[str, Any]]:
        """Return raw class schema dict.
        Tries /v1/schema/{class} first; if unavailable, falls back to /v1/schema and selects the class.
        """
        try:
            actual = self._resolve_collection_name(class_name)
            base = self._get_base()
            # Try direct class endpoint
            try:
                url = f"{base}/v1/schema/{actual}"
                resp = self._http_request("GET", url, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict):
                        return data
            except Exception as e1:
                logger.debug(f"Direct /v1/schema/{{class}} failed for '{class_name}': {e1}")

            # Fallback to full schema listing
            url_all = f"{base}/v1/schema"
            resp_all = self._http_request("GET", url_all, timeout=20)
            if resp_all.status_code == 200:
                data_all = resp_all.json() if resp_all.content else {}
                if isinstance(data_all, dict):
                    classes = data_all.get("classes", []) or []
                    for c in classes:
                        if not isinstance(c, dict):
                            continue
                        cname = c.get("class") or c.get("name")
                        if cname == actual:
                            return c
        except Exception as e:
            logger.debug(f"_get_class_schema_via_schema failed for '{class_name}': {e}")
        return None

    def _get_known_properties_for_class(self, class_name: str) -> Optional[set]:
        """Return a set of property names defined for the class, if obtainable."""
        try:
            info = self._get_class_schema_via_schema(class_name)
            if info and isinstance(info.get("properties"), list):
                names = set()
                for p in info.get("properties", []) or []:
                    if isinstance(p, dict) and p.get("name"):
                        names.add(str(p["name"]))
                return names
        except Exception:
            pass
        return None

    def _filter_props_to_known(self, class_name: str, props: Dict[str, Any]) -> Dict[str, Any]:
        """Filter outgoing properties to those present in the class schema.
        If schema not available, return props unchanged.
        """
        try:
            known = self._get_known_properties_for_class(class_name)
            if not known:
                return props
            filtered = {k: v for k, v in props.items() if k in known}
            # If content missing but available as alternative (rare), keep original props
            return filtered if filtered else props
        except Exception:
            return props

    def _class_has_named_vector(self, class_name: str, vector_name: str) -> bool:
        """Best-effort check for a named vector definition on the class.

        - Returns False for v1-only clusters or when detection fails.
        - On v2 clusters, queries /v2/collections/{class} and looks for a vector named `vector_name`.
        """
        try:
            # Skip when v2 probing is disabled or API version is v1
            if os.getenv("WEAVIATE_SKIP_V2", "false").lower() in ("1", "true", "yes"):
                return False
            if self.detect_api_version() != "v2":
                return False
            base = self._get_base()
            actual = self._resolve_collection_name(class_name)
            url = f"{base}/v2/collections/{actual}"
            resp = self._http_request("GET", url, timeout=15)
            if resp.status_code != 200:
                return False
            data = resp.json() if resp.content else {}
            # Try a few common shapes
            # 1) { vectors: [ { name: "content", ... }, ... ] }
            try:
                vectors = data.get("vectors")
                if isinstance(vectors, list):
                    for v in vectors:
                        if isinstance(v, dict) and str(v.get("name")) == vector_name:
                            return True
                # 2) { vector_config: { content: {...}, ... } }
                vc = data.get("vector_config") or data.get("namedVectors")
                if isinstance(vc, dict) and vector_name in vc:
                    return True
            except Exception:
                pass
            return False
        except Exception:
            return False

    def _encode_query_text(self, text: str, model_name: Optional[str] = None) -> Optional[List[float]]:
        try:
            embedder = self._get_or_load_query_embedder(model_name)
            if embedder is None:
                return None
            vec = embedder.encode([text])
            # vec shape (1, d)
            try:
                return vec[0].tolist()
            except Exception:
                return list(vec[0])
        except Exception as e:
            logger.error(f"Query encoding failed: {e}")
            return None

    def _run_preflight(self) -> bool:
        """Preflight connectivity validation for the configured Weaviate URL.
        Returns True if basic endpoints respond (even if auth/method required).
        Controlled by env:
          - WEAVIATE_PREFLIGHT_TIMEOUT (seconds, default 8)
          - WEAVIATE_PREFLIGHT_ON_INIT (default true)
          - WEAVIATE_PREFLIGHT_ON_URL_CHANGE (default true)
          - WEAVIATE_PREFLIGHT_FAIL_FATAL (default false)
        """
        try:
            timeout = float(os.getenv("WEAVIATE_PREFLIGHT_TIMEOUT", "8"))
        except Exception:
            timeout = 8.0
        try:
            base = self._get_base()
        except Exception:
            base = str(getattr(self, "url", "")).rstrip("/")
        logger.info(f"Running Weaviate preflight for base={base}")
        endpoints = [
            f"{base}/v1/.well-known/ready",
            f"{base}/v1/schema",
        ]
        ok = False
        last_error: Optional[Exception] = None
        for ep in endpoints:
            try:
                resp = self._http_request("GET", ep, timeout=timeout)
                sc = resp.status_code
                if sc in (200, 201, 204, 401, 403, 405):
                    logger.info(f"Preflight OK via {ep} ({sc})")
                    ok = True
                    break
                logger.debug(f"Preflight GET {ep} -> {sc}")
            except Exception as e:
                last_error = e
                logger.debug(f"Preflight GET {ep} failed: {e}")
        if not ok:
            if last_error:
                logger.warning(f"Preflight failed for base={base}: {last_error}")
            else:
                logger.warning(f"Preflight failed for base={base}: endpoints did not respond")
        return ok

    def create_collection(self, 
                         collection_name: str, 
                         description: str = "",
                         properties: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new collection (class) in Weaviate
        
        Args:
            collection_name: Name of the collection
            description: Description of the collection
            properties: Additional properties schema
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Default properties for document storage
            default_properties = [
                weaviate.classes.config.Property(
                    name="content",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Document content"
                ),
                weaviate.classes.config.Property(
                    name="source",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Source of the document"
                ),
                weaviate.classes.config.Property(
                    name="source_type",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Type of source (file, web, api, etc.)"
                ),
                weaviate.classes.config.Property(
                    name="created_at",
                    data_type=weaviate.classes.config.DataType.DATE,
                    description="Creation timestamp"
                ),
                weaviate.classes.config.Property(
                    name="metadata",
                    data_type=weaviate.classes.config.DataType.OBJECT,
                    description="Additional metadata"
                )
            ]
            
            # Add custom properties if provided
            if properties:
                for prop_name, prop_config in properties.items():
                    default_properties.append(
                        weaviate.classes.config.Property(
                            name=prop_name,
                            data_type=self._coerce_datatype(prop_config.get("data_type", weaviate.classes.config.DataType.TEXT)),
                            description=prop_config.get("description", "")
                        )
                    )
            
            # Create collection with vectorizer configuration (SDK-first)
            try:
                actual_name = self._resolve_collection_name(collection_name)
                create_kwargs = {
                    "name": actual_name,
                    "description": description,
                    "properties": default_properties,
                }
                # Multi-strategy attempt to support different client versions/configs
                # Allow forcing client-side vectors even when an OpenAI key exists
                use_client_vecs = os.getenv("WEAVIATE_USE_CLIENT_VECTORS", "false").lower() in ("1", "true", "yes")
                if self.openai_api_key and not use_client_vecs:
                    # Prefer single-vector config only (avoid deprecated vectorizer_config warnings)
                    single_vec_api = getattr(Configure, "Vectors", None)
                    if single_vec_api and hasattr(single_vec_api, "text2vec_openai"):
                        try:
                            logger.info("SDK create attempt 1: vector_config (single)")
                            self.client.collections.create(**{**create_kwargs, "vector_config": single_vec_api.text2vec_openai()})
                            logger.info(f"Created collection '{collection_name}' (actual='{actual_name}') successfully (SDK, vector_config single)")
                            self.ensure_collection_ready(collection_name)
                            return True
                        except Exception as e2:
                            logger.debug(f"Attempt 1 (vector_config single) failed: {e2}")
                    else:
                        logger.debug("Configure.Vectors not available; skipping single-vector attempts")

                    # Then try NamedVectors variants (list) using vector_config only
                    nv_api = getattr(Configure, "NamedVectors", None) or getattr(Configure, "Vectors", None)
                    nv = None
                    if nv_api and hasattr(nv_api, "text2vec_openai"):
                        nv = nv_api.text2vec_openai(
                            name="content",
                            source_properties=["content"],
                        )
                    else:
                        logger.debug("Neither Configure.NamedVectors nor Configure.Vectors provides text2vec_openai; skipping named-vector attempts")
                    if nv is not None:
                        try:
                            logger.info("SDK create attempt 2: vector_config (NamedVectors list)")
                            self.client.collections.create(**{**create_kwargs, "vector_config": [nv]})
                            logger.info(f"Created collection '{collection_name}' (actual='{actual_name}') successfully (SDK, vector_config NamedVectors)")
                            self.ensure_collection_ready(collection_name)
                            return True
                        except Exception as e4:
                            logger.debug(f"Attempt 2 (vector_config NamedVectors) failed: {e4}")
                else:
                    # Force or default to client-side vectors: create without server vectorizer
                    try:
                        # Try to define a named vector 'content' with no vectorizer if SDK supports it
                        nv_api_none = None
                        for api_name in ("NamedVectors", "Vectors"):
                            api = getattr(Configure, api_name, None)
                            if api and hasattr(api, "none"):
                                nv_api_none = getattr(api, "none")
                                break
                        if nv_api_none is not None:
                            try:
                                logger.info("SDK create: vector_config NamedVectors.none(name='content') for client-side vectors")
                                vec_cfg = nv_api_none(name="content")
                                self.client.collections.create(**{**create_kwargs, "vector_config": [vec_cfg]})
                                logger.info(f"Created collection '{collection_name}' (actual='{actual_name}') successfully (SDK, NamedVectors.none)")
                                self.ensure_collection_ready(collection_name)
                                return True
                            except Exception as e_nv_none:
                                logger.debug(f"NamedVectors.none create attempt failed: {e_nv_none}")
                        # Fallback: create without any vectorizer config (defaults to 'none')
                        self.client.collections.create(**create_kwargs)
                        logger.info(f"Created collection '{collection_name}' (actual='{actual_name}') successfully (SDK, no vectorizer)")
                        self.ensure_collection_ready(collection_name)
                        return True
                    except Exception as e_no_vec:
                        logger.debug(f"SDK no-vectorizer creation failed: {e_no_vec}")
                # If we reach here, SDK attempts failed
                raise RuntimeError("All SDK create attempts failed")
            except Exception as sdk_err:
                logger.warning(f"SDK collection create failed for '{collection_name}' ({sdk_err}); attempting REST fallbacks")

                # First try: REST v2 collections only if API version supports it
                try:
                    ver = self.detect_api_version()
                    if ver == "v2":
                        base = self._get_base()
                        prefix = self._discover_rest_prefix() or ''
                        urls: List[str] = []
                        if prefix:
                            urls.append(f"{base}{prefix}/v2/collections")
                        urls.append(f"{base}/v2/collections")

                        v2_payload = {"name": actual_name}
                        if description:
                            v2_payload["description"] = description

                        last_status = None
                        last_text = None
                        for v2_url in urls:
                            try:
                                resp_v2 = self._http_request("POST", v2_url, headers=self._get_headers(), json=v2_payload, timeout=30)
                                last_status = resp_v2.status_code
                                last_text = resp_v2.text
                                if resp_v2.status_code in (200, 201, 409):
                                    if resp_v2.status_code == 409:
                                        logger.warning(f"Collection '{collection_name}' already exists (409) via REST v2 at {v2_url}")
                                    else:
                                        logger.info(f"Created collection '{collection_name}' (actual='{actual_name}') successfully via REST v2 at {v2_url}")
                                    self.ensure_collection_ready(collection_name)
                                    return True
                                else:
                                    logger.debug(f"Attempted v2 create at {v2_url} -> {resp_v2.status_code}: {resp_v2.text}")
                            except Exception as single_v2_err:
                                logger.debug(f"v2 create attempt error at {v2_url}: {single_v2_err}")
                        logger.warning(f"REST v2 collection create failed for '{collection_name}' at canonical endpoints; last status {last_status}: {last_text}")
                    else:
                        logger.info(f"API version detected as '{ver}'; skipping REST v2 collection creation attempts")
                except Exception as v2_err:
                    logger.warning(f"REST v2 collections create exception for '{collection_name}': {v2_err}")

                # Fallback: create class via REST v1 schema
                base = self._get_base()
                url = f"{base}/v1/schema/classes"

                # Build v1 properties
                v1_properties = [
                    {"name": "content", "description": "Main text content", "dataType": ["text"]},
                    {"name": "source", "description": "Source of the document", "dataType": ["text"]},
                    {"name": "source_type", "description": "Type of source (PDF, TXT, URL)", "dataType": ["text"]},
                    {"name": "created_at", "description": "Creation timestamp", "dataType": ["date"]},
                    {
                        "name": "metadata",
                        "description": "Additional metadata",
                        "dataType": ["object"],
                        "nestedProperties": [
                            {
                                "name": "kv",
                                "description": "Generic key/value holder",
                                "dataType": ["text"]
                            }
                        ]
                    },
                ]
                if properties:
                    for prop_name, prop_config in properties.items():
                        v1_type = self._to_v1_type(prop_config.get("data_type", "TEXT"))
                        prop_obj = {
                            "name": prop_name,
                            "description": prop_config.get("description", ""),
                            "dataType": [v1_type]
                        }
                        if v1_type == "object":
                            # Ensure at least one nested property for object/object[] types
                            prop_obj["nestedProperties"] = [
                                {
                                    "name": "kv",
                                    "description": "Generic key/value holder",
                                    "dataType": ["text"]
                                }
                            ]
                        v1_properties.append(prop_obj)

                # Ensure default properties if v1_properties is empty
                if not v1_properties:
                    v1_properties = [
                        {'name': 'content', 'dataType': ['text']},
                        {'name': 'source', 'dataType': ['string']},
                        {'name': 'page', 'dataType': ['int']},
                        {'name': 'metadata', 'dataType': ['object']}
                    ]

                schema_payload = {
                    "class": actual_name,
                    "description": description,
                    "properties": v1_properties,
                }
                # Vectorizer configuration for v1
                use_client_vecs_v1 = os.getenv("WEAVIATE_USE_CLIENT_VECTORS", "false").lower() in ("1", "true", "yes")
                schema_payload["vectorizer"] = "none" if (use_client_vecs_v1 or not self.openai_api_key) else "text2vec-openai"

                try:
                    resp = self._http_request("POST", url, headers=self._get_headers(), json=schema_payload, timeout=30)
                    if resp.status_code in (200, 201):
                        logger.info(f"Created collection '{collection_name}' successfully via REST v1 schema")
                        self.ensure_collection_ready(collection_name)
                        return True
                    elif resp.status_code == 409:
                        logger.warning(f"Collection '{collection_name}' already exists (409) via REST v1")
                        self.ensure_collection_ready(collection_name)
                        return True
                    elif resp.status_code == 405:
                        # Some clusters block POST /v1/schema/classes. Try alternatives before PUT.
                        logger.warning(f"POST /v1/schema/classes not allowed (405) for '{collection_name}'")
                        # 1) If class already exists, treat as success
                        try:
                            schema_get = self._http_request("GET", f"{base}/v1/schema", timeout=30)
                            if schema_get.status_code == 200:
                                classes = (schema_get.json() or {}).get("classes", []) or []
                                names = [c.get("class") or c.get("name") for c in classes if isinstance(c, dict)]
                                if collection_name in names:
                                    logger.info(f"Class '{collection_name}' already exists per /v1/schema; skipping creation")
                                    self.ensure_collection_ready(collection_name)
                                    return True
                        except Exception as e:
                            logger.debug(f"Schema existence check failed: {e}")
                        # 2) Try POST to /v1/schema as an alternative creation endpoint
                        alt_url = f"{base}/v1/schema"
                        try:
                            resp_alt = self._http_request("POST", alt_url, headers=self._get_headers(), json=schema_payload, timeout=30)
                            if resp_alt.status_code in (200, 201, 409):
                                logger.info(f"Created collection '{collection_name}' via REST v1 POST {alt_url}")
                                self.ensure_collection_ready(collection_name)
                                return True
                        except Exception as e:
                            logger.debug(f"Alternate POST {alt_url} failed: {e}")
                        # 3) Last resort: PUT /v1/schema/{className} (some deployments support create via PUT)
                        put_url = f"{base}/v1/schema/{actual_name}"
                        logger.warning(f"Trying PUT {put_url} for class creation/update")
                        resp_put = self._http_request("PUT", put_url, headers=self._get_headers(), json=schema_payload, timeout=30)
                        if resp_put.status_code in (200, 201):
                            logger.info(f"Created collection '{collection_name}' successfully via REST v1 PUT {put_url}")
                            self.ensure_collection_ready(collection_name)
                            return True
                        elif resp_put.status_code == 409:
                            logger.warning(f"Collection '{collection_name}' already exists (409) via REST v1 PUT")
                            self.ensure_collection_ready(collection_name)
                            return True
                        elif resp_put.status_code == 422:
                            # Retry PUT by coercing unsupported 'object' properties to 'text'
                            logger.warning(f"422 from REST v1 PUT for '{collection_name}': {resp_put.text}. Retrying with 'object' -> 'text' for properties.")
                            fallback_props = []
                            for p in schema_payload.get("properties", []):
                                p2 = dict(p)
                                dts = p2.get("dataType", []) or []
                                p2["dataType"] = ["text" if (isinstance(t, str) and t.lower() == "object") else t for t in dts]
                                fallback_props.append(p2)
                            retry_payload = dict(schema_payload)
                            retry_payload["properties"] = fallback_props
                            resp_put2 = self._http_request("PUT", put_url, headers=self._get_headers(), json=retry_payload, timeout=30)
                            if resp_put2.status_code in (200, 201):
                                logger.info(f"Created collection '{collection_name}' (actual='{actual_name}') via REST v1 PUT (fallback without object)")
                                self.ensure_collection_ready(collection_name)
                                return True
                            elif resp_put2.status_code == 409:
                                logger.warning(f"Collection '{collection_name}' already exists (409) via REST v1 PUT after fallback")
                                self.ensure_collection_ready(collection_name)
                                return True
                            else:
                                logger.error(f"REST v1 schema PUT fallback failed for '{collection_name}' with status {resp_put2.status_code}: {resp_put2.text}")
                                return False
                        else:
                            logger.error(f"REST v1 schema PUT failed for '{collection_name}' with status {resp_put.status_code}: {resp_put.text}")
                            return False
                except Exception as e:
                    logger.error(f"REST v1 schema create exception for '{collection_name}': {e}")
                    return False

        except Exception as e:
            logger.error(f"Error creating collection '{collection_name}': {str(e)}")
            return False

    def add_documents_with_stats(self,
                                 collection_name: str,
                                 documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add documents to a collection and return detailed diagnostics.

        Returns a dict with keys:
        - success: bool
        - attempted_count: int
        - processed_count: int
        - pre_count: Optional[int]
        - post_count: Optional[int]
        - inserted_delta: Optional[int]
        - duration_ms: Optional[int]
        - collection_name: str
        - warnings: List[str]
        - error: Optional[str]
        """
        result: Dict[str, Any] = {
            "success": False,
            "attempted_count": len(documents),
            "processed_count": 0,
            "pre_count": None,
            "post_count": None,
            "inserted_delta": None,
            "duration_ms": None,
            "collection_name": collection_name,
            "warnings": [],
            "error": None,
        }
        try:
            actual = self._resolve_collection_name(collection_name)
            collection = self.get_collection(actual)
            if not collection:
                logger.warning(f"Collection '{collection_name}' not found via SDK; waiting for readiness and retrying...")
                self.ensure_collection_ready(collection_name)
                collection = self.get_collection(actual)
                if not collection:
                    # Additional retries to account for SDK eventual consistency, even when REST confirms readiness
                    try:
                        sdk_get_timeout = float(os.getenv("WEAVIATE_SDK_GET_TIMEOUT_SEC", "15"))
                    except Exception:
                        sdk_get_timeout = 15.0
                    try:
                        sdk_get_interval = float(os.getenv("WEAVIATE_SDK_GET_INTERVAL_SEC", "0.5"))
                    except Exception:
                        sdk_get_interval = 0.5

                    deadline = time.time() + max(0.0, sdk_get_timeout)
                    attempts = 0
                    while time.time() < deadline and not collection:
                        attempts += 1
                        # Nudge SDK by listing all collections and clearing local cache entry
                        try:
                            _ = self.client.collections.list_all()
                        except Exception as e:
                            logger.debug(f"SDK list_all during retry failed: {e}")
                        try:
                            if collection_name in self._collections:
                                del self._collections[collection_name]
                        except Exception:
                            pass
                        try:
                            collection = self.get_collection(actual)
                            if collection:
                                logger.info(
                                    f"Collection '{collection_name}' became available via SDK after {attempts} attempts / "
                                    f"~{int((sdk_get_timeout - max(0.0, deadline - time.time())))}s"
                                )
                                break
                        except Exception as e:
                            logger.debug(f"Retry get_collection failed: {e}")
                        time.sleep(max(0.0, sdk_get_interval))

                    if not collection:
                        # As a final hint for diagnostics, verify presence via REST again
                        names_schema = self._list_collections_via_schema() or []
                        names_v2 = self._list_collections_v2() or []
                        present_via_schema = (actual in names_schema) or (collection_name in names_schema)
                        present_via_v2 = (actual in names_v2) or (collection_name in names_v2)
                        if present_via_schema:
                            # Fallback: perform insertion via REST v1 batch endpoint when SDK visibility lags
                            logger.warning(f"SDK still cannot see '{collection_name}' but REST schema does; attempting REST v1 batch insertion fallback")
                            # Prepare documents for REST insertion
                            objects_to_insert = []
                            force_named_content = os.getenv("WEAVIATE_USE_CLIENT_VECTORS", "false").lower() in ("1", "true", "yes")
                            include_meta = os.getenv("WEAVIATE_INCLUDE_METADATA", "false").lower() in ("1", "true", "yes")
                            for doc in documents:
                                props: Dict[str, Any] = {
                                    "content": doc.get("content", ""),
                                    "source": doc.get("source", "unknown"),
                                    "source_type": doc.get("source_type", "document"),
                                    "created_at": datetime.now().isoformat(),
                                }
                                if include_meta and isinstance(doc.get("metadata"), dict):
                                    props["metadata"] = doc.get("metadata", {})
                                for key, value in doc.items():
                                    if key not in ["content", "source", "source_type", "metadata", "vector", "vectors"]:
                                        props[key] = value
                                # Filter to schema-known properties to avoid validation errors
                                try:
                                    props = self._filter_props_to_known(actual, props)
                                except Exception:
                                    pass
                                vec = doc.get("vector")
                                named_vecs = doc.get("vectors")
                                if force_named_content and named_vecs is None and vec is not None:
                                    try:
                                        named_vecs = {"content": vec}
                                        vec = None
                                    except Exception:
                                        pass
                                objects_to_insert.append({"properties": props, "vector": vec, "vectors": named_vecs})
                            # Read batch/env knobs
                            log_every_n = int(os.getenv("WEAVIATE_INSERT_LOG_EVERY", "25"))
                            batch_chunk_size = int(os.getenv("WEAVIATE_BATCH_CHUNK_SIZE", "100"))
                            max_insert_sec = float(os.getenv("WEAVIATE_INSERT_MAX_SEC", "180"))
                            # Execute REST fallback insertion
                            rest_diag = self._insert_objects_via_rest_v1(
                                actual,
                                objects_to_insert,
                                log_every_n,
                                batch_chunk_size,
                                max_insert_sec,
                            )
                            # Merge diagnostics into result and return
                            result.update({
                                "processed_count": rest_diag.get("processed_count", 0),
                                "duration_ms": rest_diag.get("duration_ms"),
                                "post_count": rest_diag.get("post_count"),
                            })
                            if rest_diag.get("warnings"):
                                result["warnings"].extend(rest_diag["warnings"]) 
                            if rest_diag.get("error"):
                                result["error"] = rest_diag["error"]
                                return result
                            # Compute delta best-effort if post_count available
                            pc = result["pre_count"]
                            qc = result["post_count"]
                            if pc is not None and qc is not None:
                                try:
                                    result["inserted_delta"] = max(0, int(qc) - int(pc))
                                except Exception:
                                    result["inserted_delta"] = None
                            result["success"] = True
                            # Log line similar to SDK path
                            logger.info((
                                f"[add_documents_with_stats:REST] attempted={len(documents)} to '{collection_name}' in "
                                f"{result['duration_ms']}ms; counts: before={result['pre_count']}, after={result['post_count']}, inserted_delta={result['inserted_delta']}"
                            ))
                            return result
                        else:
                            msg = (
                                f"Collection '{collection_name}' not found via SDK after readiness wait and retries "
                                f"(REST schema={present_via_schema}, REST v2={present_via_v2})."
                            )
                            logger.error(msg)
                            result["error"] = msg
                            return result

            # Allow forcing REST v1 batch insertion (diagnostics are clearer on some clusters)
            force_rest_batch = os.getenv("WEAVIATE_FORCE_REST_BATCH", "false").lower() in ("1", "true", "yes")
            if force_rest_batch:
                logger.info("WEAVIATE_FORCE_REST_BATCH=true; using REST v1 batch insertion path")
                # Build objects for REST path (mirror SDK-prep logic)
                objects_to_insert = []
                include_meta_rest = os.getenv("WEAVIATE_INCLUDE_METADATA", "false").lower() in ("1", "true", "yes")
                for doc in documents:
                    props: Dict[str, Any] = {
                        "content": doc.get("content", ""),
                        "source": doc.get("source", "unknown"),
                        "source_type": doc.get("source_type", "document"),
                        "created_at": datetime.now().isoformat(),
                    }
                    if include_meta_rest and isinstance(doc.get("metadata"), dict):
                        props["metadata"] = doc.get("metadata", {})
                    for key, value in doc.items():
                        if key not in ["content", "source", "source_type", "metadata", "vector", "vectors"]:
                            props[key] = value
                    try:
                        props = self._filter_props_to_known(actual, props)
                    except Exception:
                        pass
                    vec = doc.get("vector")
                    named_vecs = doc.get("vectors")
                    objects_to_insert.append({"properties": props, "vector": vec, "vectors": named_vecs})

                # Read knobs and execute REST insertion
                log_every_n = int(os.getenv("WEAVIATE_INSERT_LOG_EVERY", "25"))
                batch_chunk_size = int(os.getenv("WEAVIATE_BATCH_CHUNK_SIZE", "100"))
                max_insert_sec = float(os.getenv("WEAVIATE_INSERT_MAX_SEC", "180"))
                rest_diag2 = self._insert_objects_via_rest_v1(actual, objects_to_insert, log_every_n, batch_chunk_size, max_insert_sec)

                # Merge results
                result.update({
                    "processed_count": rest_diag2.get("processed_count", 0),
                    "duration_ms": rest_diag2.get("duration_ms"),
                    "post_count": rest_diag2.get("post_count"),
                })
                if rest_diag2.get("warnings"):
                    result["warnings"].extend(rest_diag2["warnings"]) 
                if rest_diag2.get("error"):
                    result["error"] = rest_diag2["error"]
                    return result
                pc = result["pre_count"]
                qc = result["post_count"]
                if pc is not None and qc is not None:
                    try:
                        result["inserted_delta"] = max(0, int(qc) - int(pc))
                    except Exception:
                        result["inserted_delta"] = None
                result["success"] = True
                logger.info((
                    f"[add_documents_with_stats:REST(force)] attempted={len(documents)} to '{collection_name}' in "
                    f"{result['duration_ms']}ms; counts: before={result['pre_count']}, after={result['post_count']}, inserted_delta={result['inserted_delta']}"
                ))
                return result

            # Pre count (best-effort)
            try:
                agg_before = collection.aggregate.over_all(total_count=True)
                result["pre_count"] = getattr(agg_before, "total_count", None)
            except Exception as e:
                logger.debug(f"Pre-insert count failed for '{collection_name}': {e}")
                # GraphQL fallback for pre_count
                try:
                    gq_pre = self._get_class_count_via_graphql(collection_name)
                    if gq_pre is not None:
                        result["pre_count"] = gq_pre
                except Exception:
                    pass

            # Prepare documents (separate properties from vectors)
            objects_to_insert = []
            # Only use named vector 'content' when the class actually defines it
            use_named_content = self._class_has_named_vector(actual, "content")
            include_meta2 = os.getenv("WEAVIATE_INCLUDE_METADATA", "false").lower() in ("1", "true", "yes")
            for doc in documents:
                # Build properties
                props: Dict[str, Any] = {
                    "content": doc.get("content", ""),
                    "source": doc.get("source", "unknown"),
                    "source_type": doc.get("source_type", "document"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                if include_meta2 and isinstance(doc.get("metadata"), dict):
                    props["metadata"] = doc.get("metadata", {})
                for key, value in doc.items():
                    if key not in ["content", "source", "source_type", "metadata", "vector", "vectors"]:
                        props[key] = value
                # Filter to schema-known properties
                try:
                    props = self._filter_props_to_known(actual, props)
                except Exception:
                    pass
                # Extract vectors
                vec = doc.get("vector")
                named_vecs = doc.get("vectors")
                # If class supports named vectors and only default vector provided, map to 'content'
                if use_named_content and named_vecs is None and vec is not None:
                    try:
                        named_vecs = {"content": vec}
                        vec = None
                    except Exception:
                        pass
                objects_to_insert.append({"properties": props, "vector": vec, "vectors": named_vecs})

            # Insert batch with progress logging and optional timeout
            insert_start_ts = time.time()
            processed = 0
            log_every_n = int(os.getenv("WEAVIATE_INSERT_LOG_EVERY", "25"))
            batch_chunk_size = int(os.getenv("WEAVIATE_BATCH_CHUNK_SIZE", "100"))
            max_insert_sec = float(os.getenv("WEAVIATE_INSERT_MAX_SEC", "180"))
            aborted = False

            for chunk_start in range(0, len(objects_to_insert), max(1, batch_chunk_size)):
                chunk = objects_to_insert[chunk_start:chunk_start + batch_chunk_size]
                with collection.batch.dynamic() as batch:
                    for item in chunk:
                        props = item.get("properties", {})
                        vec_default = item.get("vector")
                        vec_named = item.get("vectors") if isinstance(item.get("vectors"), dict) else None
                        # Determine correct vector and name for SDK v4
                        vec_to_send = None
                        vec_name = None
                        if use_named_content:
                            # Prefer named 'content' vector when class supports it
                            if vec_named and "content" in vec_named:
                                vec_to_send = vec_named.get("content")
                                vec_name = "content"
                            elif vec_default is not None:
                                vec_to_send = vec_default
                                vec_name = "content"
                        else:
                            # If not forcing named vectors, send default if present; otherwise try named 'content'
                            if vec_default is not None:
                                vec_to_send = vec_default
                            elif vec_named and "content" in vec_named:
                                vec_to_send = vec_named.get("content")
                        # Add object; pass vector_name when using named vector
                        if vec_name:
                            batch.add_object(properties=props, vector=vec_to_send, vector_name=vec_name)
                        else:
                            batch.add_object(properties=props, vector=vec_to_send)
                        processed += 1
                        if log_every_n > 0 and (processed % log_every_n == 0 or processed == len(objects_to_insert)):
                            elapsed_ms = int((time.time() - insert_start_ts) * 1000)
                            logger.info(f"Insertion progress: {processed}/{len(objects_to_insert)} objects into '{collection_name}' ({elapsed_ms}ms)")
                        # Soft timeout check
                        if max_insert_sec > 0 and (time.time() - insert_start_ts) > max_insert_sec:
                            aborted = True
                            warn_msg = f"Insertion timeout after {int(time.time() - insert_start_ts)}s: processed {processed}/{len(objects_to_insert)}"
                            logger.warning(warn_msg)
                            result["warnings"].append(warn_msg)
                            break
                if aborted:
                    break

            result["duration_ms"] = int((time.time() - insert_start_ts) * 1000)
            result["processed_count"] = processed
            # If aborted early, mark error (still proceed to compute post_count best-effort)
            if aborted and processed < len(objects_to_insert):
                result["error"] = f"Insertion aborted due to timeout after processing {processed}/{len(objects_to_insert)} objects"

            # Post count (best-effort)
            try:
                time.sleep(0.3)
                agg_after = collection.aggregate.over_all(total_count=True)
                result["post_count"] = getattr(agg_after, "total_count", None)
            except Exception as e:
                logger.debug(f"Post-insert count failed for '{collection_name}': {e}")
                # GraphQL fallback for post_count
                try:
                    gq_post = self._get_class_count_via_graphql(collection_name)
                    if gq_post is not None:
                        result["post_count"] = gq_post
                except Exception:
                    pass

            # Compute delta
            pc = result["pre_count"]
            qc = result["post_count"]
            if pc is not None and qc is not None:
                try:
                    result["inserted_delta"] = max(0, int(qc) - int(pc))
                except Exception:
                    result["inserted_delta"] = None

            # Log diagnostic line
            logger.info(
                (
                    f"[add_documents_with_stats] attempted={len(documents)} to '{collection_name}' in {result['duration_ms']}ms; "
                    f"counts: before={result['pre_count']}, after={result['post_count']}, inserted_delta={result['inserted_delta']}"
                )
            )
            if result["inserted_delta"] is not None and result["inserted_delta"] < len(documents):
                warn = (
                    f"Inserted delta ({result['inserted_delta']}) < attempted ({len(documents)}). "
                    f"Possible partial failure or eventual consistency delay."
                )
                logger.warning(warn)
                result["warnings"].append(warn)

            result["success"] = True
            return result
        except Exception as e:
            msg = f"Error adding documents to '{collection_name}': {str(e)}"
            logger.error(msg)
            result["error"] = str(e)
            return result

    def _insert_objects_via_rest_v1(self, class_name: str, objects: List[Dict[str, Any]], log_every_n: int, batch_chunk_size: int, max_insert_sec: float) -> Dict[str, Any]:
        """Insert objects via REST v1 batch endpoint as a fallback when SDK visibility lags.
        Returns diagnostics dict: processed_count, duration_ms, warnings, error, post_count."""
        warnings: List[str] = []
        processed = 0
        start_ts = time.time()
        error: Optional[str] = None
        try:
            base = self._get_base()
            endpoint = f"{base}/v1/batch/objects"
            for i in range(0, len(objects), max(1, batch_chunk_size)):
                chunk = objects[i:i+batch_chunk_size]
                payload_objs: List[Dict[str, Any]] = []
                for item in chunk:
                    # Support both legacy 'properties-only' and structured items
                    if isinstance(item, dict) and ("properties" in item or "vector" in item or "vectors" in item):
                        props = item.get("properties", {}) if isinstance(item.get("properties"), dict) else {}
                        vec = item.get("vector")
                        named_vecs = item.get("vectors") if isinstance(item.get("vectors"), dict) else None
                    else:
                        props = item if isinstance(item, dict) else {}
                        vec = None
                        named_vecs = None
                    # For v1, map named vectors to default 'vector'; prefer 'content'
                    if vec is None and named_vecs:
                        try:
                            if "content" in named_vecs:
                                vec = named_vecs.get("content")
                            else:
                                # Take the first available named vector
                                first_key = next(iter(named_vecs.keys()))
                                vec = named_vecs.get(first_key)
                        except Exception:
                            pass
                    obj_payload: Dict[str, Any] = {"class": class_name, "properties": props}
                    if vec is not None:
                        try:
                            # Ensure JSON-serializable list of floats
                            if hasattr(vec, "tolist"):
                                vec_list = vec.tolist()
                            else:
                                vec_list = list(vec)
                            obj_payload["vector"] = vec_list
                        except Exception:
                            # If conversion fails, skip vector for this object
                            pass
                    payload_objs.append(obj_payload)
                payload = {"objects": payload_objs}
                resp = self._http_request("POST", endpoint, headers=self._get_headers(), json=payload, timeout=60)
                if resp.status_code not in (200, 201):
                    error = f"REST v1 batch insert failed with status {resp.status_code}: {resp.text[:500]}"
                    logger.error(error)
                    break
                # Check per-object errors if provided
                # Parse per-object results to refine processed count and capture errors
                try:
                    data = resp.json()
                    # Typical shape: { "results": { "objects": [ {"status": "SUCCESS"|"FAILED", ...}, ... ] }, "errors": {...}? }
                    results_obj = None
                    if isinstance(data, dict):
                        results_obj = (
                            data.get("results") or data.get("result") or {}
                        )
                    objs = []
                    if isinstance(results_obj, dict):
                        objs = results_obj.get("objects") or results_obj.get("object") or []
                    if isinstance(objs, list) and objs:
                        ok = 0
                        err_msgs: List[str] = []
                        for ro in objs:
                            status = (ro.get("status") or ro.get("result")) if isinstance(ro, dict) else None
                            s = str(status).upper() if status is not None else ""
                            if any(tok in s for tok in ("SUCCESS", "OK")):
                                ok += 1
                            else:
                                # Collect an error snippet if available
                                em = None
                                try:
                                    em = ro.get("result", {}).get("errors") or ro.get("errors")
                                except Exception:
                                    em = None
                                if em:
                                    err_msgs.append(str(em)[:300])
                        processed += ok
                        if err_msgs:
                            warnings.append(f"REST batch had {len(objs)-ok} errors: {err_msgs[:3]}")
                    else:
                        # Fallback: count the whole chunk
                        processed += len(chunk)
                    # Top-level errors block
                    if isinstance(data, dict) and data.get("errors"):
                        warnings.append(f"REST batch reported top-level errors: {str(data.get('errors'))[:500]}")
                except Exception:
                    processed += len(chunk)
                if log_every_n > 0 and (processed % log_every_n == 0 or processed == len(objects)):
                    elapsed_ms = int((time.time() - start_ts) * 1000)
                    logger.info(f"[REST] Insertion progress: {processed}/{len(objects)} into '{class_name}' ({elapsed_ms}ms)")
                if max_insert_sec > 0 and (time.time() - start_ts) > max_insert_sec:
                    warn = f"[REST] Insertion timeout after {int(time.time() - start_ts)}s: processed {processed}/{len(objects)}"
                    logger.warning(warn)
                    warnings.append(warn)
                    break
        except Exception as e:
            error = f"REST v1 insert exception: {e}"
            logger.error(error)
        duration_ms = int((time.time() - start_ts) * 1000)
        # Best-effort post-count via GraphQL
        post_count = None
        try:
            post_count = self._get_class_count_via_graphql(class_name)
        except Exception as e:
            logger.debug(f"GraphQL count after REST insert failed: {e}")
        return {"processed_count": processed, "duration_ms": duration_ms, "warnings": warnings, "error": error, "post_count": post_count}

    def _get_class_count_via_graphql(self, class_name: str) -> Optional[int]:
        """Return total object count for the class via GraphQL aggregate."""
        # Use sanitized class name for GraphQL query
        actual_class_name = self._resolve_collection_name(class_name)
        base = self._get_base()
        endpoint = f"{base}/v1/graphql"
        query = f"{{ Aggregate {{ {actual_class_name} {{ meta {{ count }} }} }} }}"
        resp = self._http_request("POST", endpoint, json={"query": query}, timeout=30)
        if resp.status_code != 200:
            logger.debug(f"GraphQL count query failed with status {resp.status_code} for class '{actual_class_name}'")
            return None
        data = resp.json()
        if not isinstance(data, dict) or "data" not in data:
            logger.debug(f"GraphQL count response missing data field for class '{actual_class_name}': {data}")
            return None
        agg = data.get("data", {}).get("Aggregate", {})
        # GraphQL returns the class name as key mapping to a list
        nodes = agg.get(actual_class_name)
        if isinstance(nodes, list) and nodes:
            meta = nodes[0].get("meta") if isinstance(nodes[0], dict) else None
            if isinstance(meta, dict) and "count" in meta:
                try:
                    count = int(meta["count"])  # type: ignore[arg-type]
                    logger.debug(f"GraphQL count for class '{actual_class_name}': {count}")
                    return count
                except Exception:
                    return None
        logger.debug(f"GraphQL count query returned no valid nodes for class '{actual_class_name}': {agg}")
        return None

    

    def _search_via_graphql(self,
                            class_name: str,
                            query: str,
                            limit: int = 10,
                            alpha: float = 0.5) -> List[Dict[str, Any]]:
        """Fallback search using REST GraphQL when SDK collection access is unavailable.

        Tries, in order:
        - bm25 (most reliable, works without vectors)
        - hybrid
        - nearText
        Returns a normalized list of dicts with keys: content, source, source_type, metadata, score, uuid
        """
        results: List[Dict[str, Any]] = []
        actual = self._resolve_collection_name(class_name)
        base = self._get_base()
        endpoint = f"{base}/v1/graphql"
        primary_prop = self._get_primary_text_property(actual) or "content"

        def _run(qpayload: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
            try:
                resp = self._http_request("POST", endpoint, json=qpayload, timeout=30)
                if resp.status_code != 200:
                    logger.debug(f"GraphQL search failed status={resp.status_code}: {resp.text[:200]}")
                    return None
                data = resp.json()
                if not isinstance(data, dict):
                    return None
                get_block = data.get("data", {}).get("Get", {}) if isinstance(data.get("data"), dict) else {}
                nodes = get_block.get(actual)
                if not isinstance(nodes, list):
                    return None
                out: List[Dict[str, Any]] = []
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    props = node
                    addl = props.get("_additional", {}) if isinstance(props.get("_additional"), dict) else {}
                    score_val = addl.get("score")
                    if score_val is None:
                        # try certainty/distance -> score heuristic
                        try:
                            cert = addl.get("certainty")
                            dist = addl.get("distance")
                            if cert is not None:
                                score_val = cert
                            elif dist is not None:
                                score_val = 1.0 - float(dist)
                        except Exception:
                            score_val = 0.0
                    uid = addl.get("id") or addl.get("uuid") or ""
                    out.append({
                        "content": props.get(primary_prop, ""),
                        "source": props.get("source", ""),
                        "source_type": props.get("source_type", ""),
                        "metadata": props.get("metadata", {}),
                        "score": float(score_val or 0.0),
                        "uuid": str(uid),
                    })
                logger.debug(f"GraphQL returned {len(out)} hits for class '{actual}' using prop '{primary_prop}'")
                return out
            except Exception as e:
                logger.debug(f"GraphQL search exception: {e}")
                return None

        # Build fields to request based on detected primary text property
        fields = f"{primary_prop} _additional {{ id uuid score certainty distance }}"

        # Try bm25 first (keyword-only, most reliable)
        try:
            bm_props = f"properties: [\"{primary_prop}\"]" if primary_prop else f""
            bm_query = {
                "query": (
                    f"{{ Get {{ {actual}(bm25: {{ query: {json.dumps(query)}{', ' + bm_props if bm_props else ''} }}, limit: {int(limit)}) "
                    f"{{ {fields} }} }} }}"
                )
            }
            res = _run(bm_query)
            if res:
                logger.debug(f"BM25 search returned {len(res)} results for '{class_name}'")
                return res
        except Exception:
            pass

        # Try hybrid (vector + keyword) as fallback
        try:
            hy_props = f", properties: [\"{primary_prop}\"]" if primary_prop else ""
            hy_query = {
                "query": (
                    f"{{ Get {{ {actual}(hybrid: {{ query: {json.dumps(query)}, alpha: {alpha}{hy_props} }}, limit: {int(limit)}) "
                    f"{{ {fields} }} }} }}"
                )
            }
            res = _run(hy_query)
            if res:
                logger.debug(f"Hybrid search returned {len(res)} results for '{class_name}'")
                return res
        except Exception:
            pass

        # Try nearText as final fallback
        try:
            nt_query = {
                "query": (
                    f"{{ Get {{ {actual}(nearText: {{ concepts: [{json.dumps(query)}] }}, limit: {int(limit)}) "
                    f"{{ {fields} }} }} }}"
                )
            }
            res = _run(nt_query)
            if res:
                logger.debug(f"NearText search returned {len(res)} results for '{class_name}'")
                return res
        except Exception:
            pass

        return results

    def get_collection(self, collection_name: str):
        """Get a collection object via SDK with simple caching."""
        try:
            actual = self._resolve_collection_name(collection_name)
            if actual not in self._collections:
                try:
                    self._collections[actual] = self.client.collections.get(actual)
                except Exception as e1:
                    logger.debug(f"Initial SDK get failed for '{actual}': {e1}; attempting schema refresh and wait")
                    try:
                        refresh_sdk_schema(self.client)
                    except Exception as re:
                        logger.debug(f"Schema refresh attempt failed: {re}")
                    # Short wait for SDK visibility
                    try:
                        if wait_for_class_in_sdk(self.client, actual, retries=5, delay=1.0):
                            self._collections[actual] = self.client.collections.get(actual)
                        else:
                            # Log SDK vs REST diff for diagnostics
                            try:
                                diff = diff_sdk_rest_classes(self.client, self._get_base(), os.getenv("WEAVIATE_API_KEY"))
                                logger.warning(f"Class '{actual}' not visible to SDK after wait; missing_in_sdk={diff.get('missing_in_sdk')}")
                            except Exception as de:
                                logger.debug(f"SDK/REST schema diff failed: {de}")
                            return None
                    except Exception as e2:
                        logger.debug(f"SDK wait/get failed for '{actual}': {e2}")
                        return None
            return self._collections.get(actual)
        except Exception as e:
            logger.error(f"Error getting collection '{collection_name}': {str(e)}")
            return None

    def ensure_collection_ready(self, collection_name: str, timeout: float = 20.0, interval: float = 1.0) -> bool:
        """Wait until the collection is available via the SDK and/or REST.

        This helps avoid race conditions where creation is immediately followed by a get.
        Returns True if collection is accessible via any method (SDK or REST).
        """
        start = time.time()
        # Clear any cached stale entry
        actual = self._resolve_collection_name(collection_name)
        for key in [collection_name, actual]:
            if key in self._collections:
                try:
                    del self._collections[key]
                except Exception:
                    pass
        
        sdk_ready = False
        rest_ready = False
        
        while time.time() - start < timeout:
            try:
                # Try SDK get first
                if not sdk_ready:
                    try:
                        col = self.get_collection(actual)
                        if col:
                            logger.info(f"Collection '{collection_name}' is ready (SDK)")
                            sdk_ready = True
                            return True
                    except Exception as e:
                        logger.debug(f"SDK get failed for '{collection_name}': {e}")
                
                # Try REST schema listing as fallback
                if not rest_ready:
                    names = self._list_collections_via_schema()
                    if (actual in names) or (collection_name in names):
                        logger.info(f"Collection '{collection_name}' is ready (REST schema)")
                        rest_ready = True
                        # Don't return immediately - give SDK one more chance
                
                # Try REST v2 listing as additional fallback
                if not rest_ready:
                    names = self._list_collections_v2()
                    if (actual in names) or (collection_name in names):
                        logger.info(f"Collection '{collection_name}' is ready (REST v2)")
                        rest_ready = True
                
                # If we found it via REST but not SDK, that's still success
                if rest_ready and not sdk_ready:
                    # Try to give SDK one more chance by forcing refresh and wait
                    try:
                        refresh_sdk_schema(self.client)
                        if wait_for_class_in_sdk(self.client, actual, retries=5, delay=1.0):
                            logger.info(f"Collection '{collection_name}' is ready (SDK after refresh)")
                            return True
                        else:
                            try:
                                diff = diff_sdk_rest_classes(self.client, self._get_base(), os.getenv("WEAVIATE_API_KEY"))
                                logger.warning(f"SDK still cannot see '{actual}'. missing_in_sdk={diff.get('missing_in_sdk')}")
                            except Exception:
                                pass
                    except Exception as wex:
                        logger.debug(f"SDK refresh/wait failed in readiness: {wex}")
                    logger.info(f"Collection '{collection_name}' accessible via REST (SDK consistency delay)")
                    return True
                    
                time.sleep(interval)
            except Exception as e:
                logger.debug(f"Readiness wait loop exception: {e}")
                time.sleep(interval)
        
        # Final check - if we can find it via any method, consider it ready
        try:
            all_names = set()
            all_names.update(self._list_collections_via_sdk())
            all_names.update(self._list_collections_v2())
            all_names.update(self._list_collections_via_schema())
            if (actual in all_names) or (collection_name in all_names):
                logger.info(f"Collection '{collection_name}' (actual='{actual}') found in final check - considering ready")
                return True
        except Exception as e:
            logger.debug(f"Final readiness check failed: {e}")
        
        logger.error(f"Collection '{collection_name}' (actual='{actual}') not found after readiness wait")
        return False

    def _coerce_datatype(self, dt_value: Any):
        """Convert provided data_type values to v4 DataType enum when given as strings.

        Supports minimal set used by this project: TEXT, DATE, INT, OBJECT.
        Defaults to TEXT if unknown.
        """
        try:
            from weaviate.classes.config import DataType
        except Exception:
            return dt_value
        if isinstance(dt_value, DataType):
            return dt_value
        if isinstance(dt_value, str):
            key = dt_value.strip().upper()
            mapping = {
                "TEXT": DataType.TEXT,
                "DATE": DataType.DATE,
                "INT": DataType.INT,
                "OBJECT": getattr(DataType, "OBJECT", DataType.TEXT),
            }
            return mapping.get(key, DataType.TEXT)
        return dt_value

    def _to_v1_type(self, dt_value: Any) -> str:
        """Map v4 DataType or string to v1 type string."""
        try:
            from weaviate.classes.config import DataType
        except Exception:
            DataType = None  # type: ignore
        if DataType and isinstance(dt_value, DataType):
            mapping = {
                getattr(DataType, 'TEXT', None): 'text',
                getattr(DataType, 'INT', None): 'int',
                getattr(DataType, 'DATE', None): 'date',
                getattr(DataType, 'OBJECT', None): 'object',
            }
            return mapping.get(dt_value, 'text')
        if isinstance(dt_value, str):
            key = dt_value.strip().upper()
            mapping = {
                'TEXT': 'text',
                'INT': 'int',
                'DATE': 'date',
                'OBJECT': 'object',
            }
            return mapping.get(key, 'text')
        return 'text'

    def _get_base(self) -> str:
        """Return base URL without trailing slash."""
        return self.url.rstrip('/')

    def _get_headers(self) -> Dict[str, str]:
        """Build HTTP headers for REST calls."""
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            # WCS commonly expects Authorization: Bearer; some setups also accept X-API-KEY
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-KEY"] = self.api_key
        if self.openai_api_key:
            headers["X-OpenAI-Api-Key"] = self.openai_api_key
        return headers

    def detect_api_version(self, force: bool = False) -> str:
        """Detect and cache the Weaviate REST API version ('v1' or 'v2').

        Detection order:
        - Honor WEAVIATE_FORCE_API_VERSION if provided ('v1' or 'v2')
        - Probe '/v2/.well-known/weaviate-version' (200 -> v2)
        - Probe '/v2/collections' (200/401/403/204/405 -> v2 path exists)
        - Default to 'v1'
        """
        try:
            forced = os.getenv("WEAVIATE_FORCE_API_VERSION")
            if forced and forced.lower() in ("v1", "v2"):
                self._api_version = forced.lower()
                logger.info(f"API version forced via WEAVIATE_FORCE_API_VERSION={self._api_version}")
                return self._api_version
        except Exception:
            pass

        if self._api_version is not None and not force:
            return self._api_version

        base = self._get_base()
        # Prefer canonical root paths for version detection
        v2_version_url = f"{base}/v2/.well-known/weaviate-version"
        v2_collections_url = f"{base}/v2/collections"
        # 1) Try the version endpoint
        try:
            resp = self._http_request("GET", v2_version_url, timeout=10)
            if resp.status_code == 200:
                try:
                    data = resp.json() if resp.content else {}
                    ver = data.get("version") or data.get("weaviateVersion") or "unknown"
                    logger.info(f"Detected Weaviate REST API v2 (version endpoint ok, version={ver})")
                except Exception:
                    logger.info("Detected Weaviate REST API v2 (version endpoint ok)")
                self._api_version = "v2"
                return self._api_version
        except Exception as e:
            logger.debug(f"v2 version endpoint probe failed: {e}")

        # 2) Try the canonical v2 collections endpoint
        try:
            resp2 = self._http_request("GET", v2_collections_url, timeout=10)
            if resp2.status_code in (200, 201, 204, 401, 403, 405):
                logger.info(f"Detected Weaviate REST API v2 (collections endpoint exists: {resp2.status_code})")
                self._api_version = "v2"
                return self._api_version
        except Exception as e2:
            logger.debug(f"v2 collections endpoint probe failed: {e2}")

        # Default to v1
        self._api_version = "v1"
        logger.info("Detected Weaviate REST API v1 (v2 endpoints unavailable)")
        return self._api_version

    def _get_prefix_candidates(self) -> List[str]:
        """Return ordered list of REST path prefix candidates.

        Sources:
        - WEAVIATE_PATH_PREFIX (single value)
        - WEAVIATE_PATH_PREFIXES (comma-separated list)
        - Defaults: '', '/weaviate', '/api', '/v1', '/v2'
        """
        if self._prefix_candidates is not None:
            return self._prefix_candidates

        candidates: List[str] = []
        env_single = os.getenv('WEAVIATE_PATH_PREFIX')
        env_multi = os.getenv('WEAVIATE_PATH_PREFIXES')

        if env_single:
            p = env_single.strip()
            if p and not p.startswith('/'):
                p = '/' + p
            if p.endswith('/'):
                p = p[:-1]
            candidates.append(p)

        if env_multi:
            for p in env_multi.split(','):
                p = p.strip()
                if not p:
                    continue
                if not p.startswith('/'):
                    p = '/' + p
                if p.endswith('/'):
                    p = p[:-1]
                if p not in candidates:
                    candidates.append(p)

        # Defaults at the end to preserve env order
        for d in ['', '/weaviate', '/api', '/rest', '/v1', '/v2']:
            if d not in candidates:
                candidates.append(d)

        self._prefix_candidates = candidates
        return candidates

    def _probe_endpoint(self, url: str) -> bool:
        """Return True if endpoint exists (even if unauthorized)."""
        try:
            resp = self._http_request("GET", url, timeout=10)
            logger.debug(f"Probe response for {url}: {resp.status_code}")
            if resp.status_code in (200, 201):
                logger.debug(f"Successful probe at {url}")
                return True
            # Consider 401/403/204/405 as existence (auth/method issues but path valid)
            if resp.status_code in (401, 403, 204, 405):
                logger.debug(f"Endpoint exists but requires auth/method at {url}")
                return True
            logger.debug(f"Endpoint not found at {url} (status: {resp.status_code})")
            return False
        except Exception as e:
            logger.debug(f"Probe failed for {url}: {e}")
            return False

    def _discover_rest_prefix(self, force: bool = False) -> Optional[str]:
        """Discover and cache a working REST path prefix.

        Tries simple prefix candidates first (combined with common endpoints),
        then tries full GCP/WCS patterns as complete paths.
        """
        if self._rest_prefix is not None and not force:
            return self._rest_prefix

        base = self._get_base()
        candidates = self._get_prefix_candidates()
        test_paths = [
            '/v2/collections',
            '/v1/schema',
            '/v1/.well-known/ready',
            '/v1/graphql',
        ]

        # 1) Try simple prefix candidates with typical endpoints
        for cand in candidates:
            for path in test_paths:
                url = f"{base}{cand}{path}"
                if self._probe_endpoint(url):
                    self._rest_prefix = cand
                    pdisp = cand or '(root)'
                    logger.info(f"Discovered Weaviate REST prefix {pdisp} via {url}")
                    return cand

        # 2) Try full GCP/WCS patterns as complete paths (not combined with test_paths)
        disable_gcp = os.getenv("WEAVIATE_DISABLE_GCP_PATTERNS", "false").lower() in ("1", "true", "yes")
        if disable_gcp:
            logger.info("GCP/WCS pattern probing is disabled via WEAVIATE_DISABLE_GCP_PATTERNS=true")
            gcp_patterns = []
        else:
            gcp_patterns = [
                '/api/rest/v2/collections',
                '/api/rest/v1/schema',
                '/rest/v2/collections',
                '/rest/v1/schema',
                '/api/v1/.well-known/ready',
                '/api/v1/graphql',
                '/api/weaviate/v2/collections',
                '/api/weaviate/v1/schema',
                '/api/weaviate/v1/.well-known/ready',
                '/api/weaviate/v1/graphql',
                '/v1/.well-known/ready',
                '/v1/graphql',
                '/v1/schema',
                '/v2/collections',
            ]

        for pattern in gcp_patterns:
            url = f"{base}{pattern}"
            if self._probe_endpoint(url):
                # Derive the prefix before the versioned segment
                idx = pattern.find('/v2/')
                if idx == -1:
                    idx = pattern.find('/v1/')
                cand = pattern[:idx] if idx != -1 else ''
                self._rest_prefix = cand
                pdisp = cand or '(root)'
                logger.info(f"Discovered GCP-specific Weaviate REST prefix {pdisp} via {url}")
                return cand

        logger.warning(f"Could not discover REST path prefix for base={base}. Tried candidates: {candidates} and GCP patterns: {gcp_patterns}")
        self._rest_prefix = None
        return None

    def _list_collections_via_schema(self) -> List[str]:
        """Fallback: list collections by querying schema endpoints.
        Tries discovered/explicit REST prefix first, then falls back to root '/v1/schema'.
        """
        base = self._get_base()
        # Build candidate URLs: base+prefix, then base
        urls: List[str] = []
        try:
            prefix = self._discover_rest_prefix() or ''
        except Exception:
            prefix = ''
        if prefix:
            urls.append(f"{base}{prefix}/v1/schema")
        urls.append(f"{base}/v1/schema")
        last_err: Optional[Exception] = None
        for url in urls:
            for attempt in range(2):  # simple retry per URL for transient issues
                try:
                    resp = self._http_request("GET", url, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        classes = data.get("classes", []) or []
                        names = [c.get("class") or c.get("name") for c in classes if isinstance(c, dict)]
                        logger.info(f"Listed collections via schema endpoint at {url}")
                        return [n for n in names if n]
                    else:
                        logger.error(f"Schema query failed: {resp.status_code} at {url}")
                        break
                except Exception as e:
                    last_err = e
                    logger.warning(f"Schema attempt {attempt+1} failed at {url}: {e}")
        if last_err:
            logger.error(f"All schema attempts failed; last error: {last_err}")
        return []
    
    def _get_primary_text_property(self, class_name: str) -> Optional[str]:
        """Inspect the schema and return the most suitable text property for the class.

        Preference order:
        - 'content' if present and type is text/string
        - first property with dataType including 'text' or 'string'
        Returns None if schema unavailable.
        """
        try:
            # Allow manual override via environment variable
            override = os.getenv("WEAVIATE_PRIMARY_TEXT_PROP")
            if override:
                logger.info(f"Using WEAVIATE_PRIMARY_TEXT_PROP override: {override}")
                return override
            base = self._get_base()
            urls: List[str] = []
            try:
                prefix = self._discover_rest_prefix() or ''
            except Exception:
                prefix = ''
            if prefix:
                urls.append(f"{base}{prefix}/v1/schema")
            urls.append(f"{base}/v1/schema")
            data = {}
            for url in urls:
                resp = self._http_request("GET", url, timeout=20)
                if resp.status_code == 200:
                    data = resp.json() if resp.content else {}
                    break
            if not isinstance(data, dict) or not data:
                return None
            classes = data.get("classes", []) or []
            for c in classes:
                cname = c.get("class") or c.get("name")
                if not cname or cname != self._resolve_collection_name(class_name):
                    continue
                props = c.get("properties", []) or []
                # normalize types to lowercase strings
                def is_text_type(dt: Any) -> bool:
                    try:
                        if isinstance(dt, str):
                            return dt.lower() in ("text", "string")
                        if isinstance(dt, list) and dt:
                            return any(isinstance(x, str) and x.lower() in ("text", "string") for x in dt)
                    except Exception:
                        return False
                    return False
                # prefer 'content'
                for p in props:
                    pname = p.get("name")
                    if pname == "content" and is_text_type(p.get("dataType")):
                        return "content"
                # otherwise first text-like property
                for p in props:
                    pname = p.get("name")
                    if pname and is_text_type(p.get("dataType")):
                        return pname
            return None
        except Exception as e:
            logger.debug(f"Primary text property detection failed for '{class_name}': {e}")
            return None
    
    def _list_collections_v2(self) -> List[str]:
        """List collections via v2 REST using the canonical endpoint only.
        Skips entirely when API version is detected as v1.
        """
        # Allow environment override to skip v2 attempts for clusters that only expose v1
        try:
            if os.getenv("WEAVIATE_SKIP_V2", "false").lower() in ("1", "true", "yes"):
                logger.info("WEAVIATE_SKIP_V2=true; skipping v2 collections listing attempts")
                return []
        except Exception:
            pass

        ver = self.detect_api_version()
        if ver != "v2":
            logger.debug(f"API version '{ver}' does not support v2 collections; skipping v2 listing")
            return []

        base = self._get_base()
        urls: List[str] = []
        prefix = self._discover_rest_prefix() or ''
        if prefix:
            urls.append(f"{base}{prefix}/v2/collections")
        urls.append(f"{base}/v2/collections")

        last_error: Optional[str] = None
        for url in urls:
            try:
                resp = self._http_request("GET", url, timeout=30)
                if resp.status_code != 200:
                    last_error = f"status={resp.status_code} body={resp.text[:200]}"
                    logger.debug(f"v2 listing {url} -> {last_error}")
                    continue
                data = resp.json() if resp.content else {}
                cols = data.get("collections", []) or []
                names = [c.get("name") for c in cols if isinstance(c, dict)]
                logger.info(f"Listed collections via v2 endpoint at {url}")
                return [n for n in names if n]
            except Exception as e:
                last_error = str(e)
                logger.debug(f"v2 collection listing attempt failed at {url}: {e}")
        if last_error:
            logger.warning(f"v2 listing failed although API version detected as v2; last error: {last_error}")
        return []
    
    def _list_collections_via_sdk(self) -> List[str]:
        """List collections using the official Python SDK (v4) if available."""
        try:
            cols = self.client.collections.list_all()
            names: List[str] = []
            for c in cols:
                n = getattr(c, "name", None)
                if n is None and isinstance(c, dict):
                    n = c.get("name")
                if n is None and isinstance(c, str):
                    n = c
                if n:
                    names.append(n)
            return names
        except Exception as e:
            logger.warning(f"SDK collection listing failed: {e}")
            return []

    def list_collections(self) -> List[str]:
        """List all available collections by merging SDK, v2 REST, and v1 schema results.

        Ensures REST-visible classes appear even if the SDK schema cache lags.
        """
        try:
            sdk_names = set(self._list_collections_via_sdk())
            v2_names = set(self._list_collections_v2())
            rest_names = set(self._list_collections_via_schema())
            union = sdk_names | v2_names | rest_names
            if not union:
                logger.warning("No collections found via SDK or REST fallbacks.")
                return []
            missing_in_sdk = sorted(list(rest_names - sdk_names))
            if missing_in_sdk:
                try:
                    diff = diff_sdk_rest_classes(self.client, self._get_base(), os.getenv("WEAVIATE_API_KEY"))
                    logger.info(
                        f"Merging REST-visible collections with SDK list; missing_in_sdk={diff.get('missing_in_sdk') or missing_in_sdk}"
                    )
                except Exception:
                    logger.info(f"Merging REST-visible collections with SDK list; missing_in_sdk={missing_in_sdk}")
            return sorted(union)
        except Exception as e:
            logger.error(f"list_collections failed: {e}")
            try:
                return sorted(self._list_collections_via_schema())
            except Exception:
                return []

    def add_documents(self, 
                      collection_name: str, 
                      documents: List[Dict[str, Any]]) -> bool:
        """
        Add documents to a collection
        
        Args:
            collection_name: Name of the collection
            documents: List of document dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            actual = self._resolve_collection_name(collection_name)
            collection = self.get_collection(actual)
            if not collection:
                # Attempt to wait for readiness in case of eventual consistency
                logger.warning(f"Collection '{collection_name}' not found via SDK; waiting for readiness and retrying...")
                self.ensure_collection_ready(collection_name)
                collection = self.get_collection(actual)
                if not collection:
                    logger.error(f"Collection '{collection_name}' not found after readiness wait")
                    return False

            # Measure pre-insert object count (best-effort)
            pre_count = None
            try:
                agg_before = collection.aggregate.over_all(total_count=True)
                pre_count = getattr(agg_before, "total_count", None)
            except Exception as e:
                logger.debug(f"Pre-insert count failed for '{collection_name}': {e}")
            # Prepare objects to insert
            include_meta = os.getenv("WEAVIATE_INCLUDE_METADATA", "false").lower() in ("1", "true", "yes")
            objects_to_insert: List[Dict[str, Any]] = []
            for doc in documents:
                try:
                    obj: Dict[str, Any] = {
                        "content": doc.get("content", ""),
                        "source": doc.get("source", "unknown"),
                        "source_type": doc.get("source_type", "document"),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if include_meta and isinstance(doc.get("metadata"), dict):
                        obj["metadata"] = doc["metadata"]
                    # Filter to known schema properties (best-effort)
                    obj = self._filter_props_to_known(actual, obj)
                    objects_to_insert.append(obj)
                except Exception as be:
                    logger.warning(f"Skipping document due to build error: {be}")

            # Batch insert
            start_ts = time.time()
            with collection.batch.dynamic() as batch:
                for obj in objects_to_insert:
                    batch.add_object(properties=obj)
            duration_ms = int((time.time() - start_ts) * 1000)

            # Measure post-insert object count (best-effort) with small retries; allow brief delay for consistency.
            post_count = None
            attempts = int(os.getenv("WEAVIATE_COUNT_RETRIES", "3"))
            delay = float(os.getenv("WEAVIATE_COUNT_RETRY_DELAY", "0.5"))
            for _try in range(max(1, attempts)):
                if _try > 0:
                    time.sleep(delay)
                try:
                    agg_after = collection.aggregate.over_all(total_count=True)
                    post_count = getattr(agg_after, "total_count", None)
                except Exception as e:
                    logger.debug(f"Post-insert count attempt via SDK failed for '{collection_name}': {e}")
                if post_count is None:
                    try:
                        gq_post = self._get_class_count_via_graphql(collection_name)
                        if gq_post is not None:
                            post_count = gq_post
                    except Exception:
                        pass
                if post_count is not None:
                    break

            inserted = None
            if pre_count is not None and post_count is not None:
                try:
                    inserted = max(0, int(post_count) - int(pre_count))
                except Exception:
                    inserted = None

            # Detailed diagnostics
            logger.info(
                (
                    f"Added {len(documents)} documents to collection '{collection_name}' in {duration_ms}ms. "
                    f"Counts -> before: {pre_count}, after: {post_count}, inserted_delta: {inserted}"
                )
            )
            if inserted is not None and inserted < len(documents):
                logger.warning(
                    f"Inserted delta ({inserted}) is less than attempted ({len(documents)}). "
                    f"This may indicate partial failures or eventual consistency delays."
                )

            return True

        except Exception as e:
            logger.error(f"Error adding documents to '{collection_name}': {e}")
            return False

    def search(self, 
               collection_name: str, 
               query: str, 
               limit: int = 10,
               where_filter: Optional[Dict] = None,
               return_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Search documents in a collection
        
        Args:
            collection_name: Name of the collection to search
            query: Search query
            limit: Maximum number of results
            where_filter: Additional filters
            return_metadata: Whether to return metadata
            
        Returns:
            List of search results
        """
        try:
            actual = self._resolve_collection_name(collection_name)
            collection = self.get_collection(actual)
            if not collection:
                logger.error(f"Collection '{collection_name}' not found")
                return []

            metadata = weaviate.classes.query.MetadataQuery(score=True) if return_metadata else None

            use_client_vecs = os.getenv("WEAVIATE_USE_CLIENT_VECTORS", "false").lower() in ("1", "true", "yes")
            objects: List[Any] = []

            # If client-side vectors are enabled, prefer near_vector with a locally-encoded query
            if use_client_vecs:
                qvec = self._encode_query_text(query)
                if qvec is not None:
                    try:
                        nv_resp = collection.query.near_vector(
                            vector=qvec,
                            limit=limit,
                            return_metadata=metadata,
                        )
                        if nv_resp and hasattr(nv_resp, "objects") and nv_resp.objects:
                            objects = nv_resp.objects
                    except TypeError:
                        # Try named vector 'content' if supported
                        try:
                            nv_resp2 = collection.query.near_vector(
                                vector=qvec,
                                limit=limit,
                                return_metadata=metadata,
                                target_vector="content",
                            )
                            if nv_resp2 and hasattr(nv_resp2, "objects") and nv_resp2.objects:
                                objects = nv_resp2.objects
                        except Exception as nve2:
                            logger.debug(f"near_vector with target_vector failed: {nve2}")
                if not objects:
                    logger.info("Client-side query vector produced no results; falling back to near_text for keyword-only match")

            # If we still have no objects, try near_text (server-side vectorizer collections)
            if not objects:
                response = None
                try:
                    response = collection.query.near_text(
                        query=query,
                        limit=limit,
                        return_metadata=metadata,
                    )
                except Exception as qe:
                    logger.warning(f"near_text default attempt failed for '{collection_name}': {qe}")
                    response = None
                if response and hasattr(response, "objects") and response.objects:
                    objects = response.objects
                else:
                    # Fallback: try named vector commonly used in this project
                    try:
                        response2 = collection.query.near_text(
                            query=query,
                            limit=limit,
                            return_metadata=metadata,
                            target_vector="content",
                        )
                        if response2 and hasattr(response2, "objects") and response2.objects:
                            logger.info(
                                f"near_text fallback with target_vector='content' returned {len(response2.objects)} results in '{collection_name}'"
                            )
                            objects = response2.objects
                    except TypeError as te:
                        # Older/newer SDK without target_vector support
                        logger.debug(f"near_text does not support target_vector on this SDK: {te}")
                    except Exception as qe2:
                        logger.debug(f"near_text target_vector fallback failed: {qe2}")

            # Final fallback: if no results and client vectors enabled, retry near_vector named 'content'
            if not objects and use_client_vecs:
                qvec = self._encode_query_text(query)
                if qvec is not None:
                    try:
                        nv_resp3 = collection.query.near_vector(
                            vector=qvec,
                            limit=limit,
                            return_metadata=metadata,
                            target_vector="content",
                        )
                        if nv_resp3 and hasattr(nv_resp3, "objects") and nv_resp3.objects:
                            objects = nv_resp3.objects
                    except Exception as nve3:
                        logger.debug(f"Final near_vector fallback failed: {nve3}")

            # Keyword-only fallback (BM25 via hybrid with alpha=1.0)
            if not objects:
                try:
                    logger.info(f"Vector path returned no results; trying keyword-only hybrid (alpha=1.0) for '{collection_name}'")
                    hy_kw = collection.query.hybrid(
                        query=query,
                        alpha=1.0,
                        limit=limit,
                        return_metadata=metadata,
                    )
                    if hy_kw and hasattr(hy_kw, "objects") and hy_kw.objects:
                        objects = hy_kw.objects
                except Exception as khe:
                    logger.debug(f"Keyword-only hybrid fallback failed: {khe}")

            # Optional filter support: apply client-side to avoid SDK incompatibilities
            if where_filter and objects:
                st_val = where_filter.get("source_type")
                if st_val is not None:
                    try:
                        objects = [
                            o for o in objects
                            if isinstance(getattr(o, "properties", {}), dict)
                            and o.properties.get("source_type") == st_val
                        ]
                    except Exception:
                        pass

            # Format results
            results: List[Dict[str, Any]] = []
            for obj in objects:
                result = {
                    "content": obj.properties.get("content", ""),
                    "source": obj.properties.get("source", ""),
                    "source_type": obj.properties.get("source_type", ""),
                    "metadata": obj.properties.get("metadata", {}),
                    "uuid": str(obj.uuid),
                }
                if return_metadata and hasattr(obj, "metadata"):
                    try:
                        result["score"] = getattr(obj.metadata, "score", 0.0) or 0.0
                    except Exception:
                        result["score"] = 0.0
                results.append(result)

            logger.info(f"Found {len(results)} results for query '{query}' in '{collection_name}' (actual='{actual}')")
            if not results:
                try:
                    agg = collection.aggregate.over_all(total_count=True)
                    tc = getattr(agg, "total_count", None)
                    logger.debug(f"Empty results; collection '{collection_name}' total_count={tc}")
                except Exception as e:
                    logger.debug(f"Aggregate check after empty results failed: {e}")
            return results

        except Exception as e:
            logger.error(f"Error searching collection '{collection_name}': {str(e)}")
            return []

    def hybrid_search(self,
                     collection_name: str,
                     query: str,
                     alpha: float = 0.5,
                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + keyword)
        
        Args:
            collection_name: Name of the collection
            query: Search query
            alpha: Balance between vector (0) and keyword (1) search
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        try:
            actual = self._resolve_collection_name(collection_name)
            collection = self.get_collection(actual)
            if not collection:
                return []

            metadata = weaviate.classes.query.MetadataQuery(score=True)

            use_client_vecs = os.getenv("WEAVIATE_USE_CLIENT_VECTORS", "false").lower() in ("1", "true", "yes")

            # Primary attempt: hybrid; if client vectors enabled, supply query vector
            response = None
            try:
                if use_client_vecs:
                    qvec = self._encode_query_text(query)
                    response = collection.query.hybrid(
                        query=query,
                        alpha=alpha,
                        limit=limit,
                        return_metadata=metadata,
                        vector=qvec,
                    )
                else:
                    response = collection.query.hybrid(
                        query=query,
                        alpha=alpha,
                        limit=limit,
                        return_metadata=metadata,
                    )
                
                objects = response.objects if response and hasattr(response, "objects") else []
                
            except Exception as he:
                logger.debug(f"Hybrid search failed: {he}")
                objects = []
                
                # Fallback to near_text search
                try:
                    logger.info(f"Hybrid failed; trying near_text for '{collection_name}'")
                    if use_client_vecs:
                        qvec = self._encode_query_text(query)
                        nt_resp = collection.query.near_vector(
                            near_vector=qvec,
                            limit=limit,
                            return_metadata=metadata,
                        )
                    else:
                        nt_resp = collection.query.near_text(
                            query=query,
                            limit=limit,
                            return_metadata=metadata,
                        )
                    if nt_resp and hasattr(nt_resp, "objects") and nt_resp.objects:
                        logger.debug(
                            f"near_text fallback returned {len(nt_resp.objects)} results in '{collection_name}'"
                        )
                        objects = nt_resp.objects
                    else:
                        # Try with target_vector if available
                        try:
                            nt_resp2 = collection.query.near_text(
                                query=query,
                                limit=limit,
                                return_metadata=metadata,
                                target_vector="content",
                            )
                            if nt_resp2 and hasattr(nt_resp2, "objects") and nt_resp2.objects:
                                logger.debug(
                                    f"near_text fallback with target_vector='content' returned {len(nt_resp2.objects)} results in '{collection_name}'"
                                )
                                objects = nt_resp2.objects
                        except TypeError as te:
                            logger.debug(f"near_text target_vector unsupported in hybrid fallback: {te}")
                except Exception as ne:
                    logger.debug(f"near_text fallback after hybrid failed: {ne}")

                # Final keyword-only fallback
                if not objects:
                    try:
                        logger.info(f"All vector attempts empty; trying keyword-only hybrid (alpha=1.0) for '{collection_name}'")
                        hy_kw2 = collection.query.hybrid(
                            query=query,
                            alpha=1.0,
                            limit=limit,
                            return_metadata=metadata,
                        )
                        if hy_kw2 and hasattr(hy_kw2, "objects") and hy_kw2.objects:
                            objects = hy_kw2.objects
                    except Exception as khe2:
                        logger.debug(f"Keyword-only hybrid fallback (final) failed: {khe2}")

            results: List[Dict[str, Any]] = []
            for obj in objects:
                result = {
                    "content": obj.properties.get("content", ""),
                    "source": obj.properties.get("source", ""),
                    "source_type": obj.properties.get("source_type", ""),
                    "metadata": obj.properties.get("metadata", {}),
                    "score": obj.metadata.score if hasattr(obj, 'metadata') and getattr(obj.metadata, "score", None) else 0.0,
                    "uuid": str(obj.uuid),
                }
                results.append(result)

            if not results:
                try:
                    agg = collection.aggregate.over_all(total_count=True)
                    tc = getattr(agg, "total_count", None)
                    logger.debug(f"Hybrid/near_text resulted in 0 hits; collection '{collection_name}' total_count={tc}")
                except Exception as e:
                    logger.debug(f"Aggregate check after hybrid empty results failed: {e}")
            return results

        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return []

    def _get_tab_accessible_collection(self, 
                                     collection_name: str,
                                     tab_name: str) -> Optional[Any]:
        """
        Verify tab has access to collection
        """
        actual = self._resolve_collection_name(collection_name)
        collection = self.get_collection(actual)
        if not collection:
            return None
            
        # Add tab-specific access logic here
        return collection

    def get_documents_for_tab(self,
                              collection_name: str,
                              tab_name: str,
                              query: str,
                              limit: int = 5,
                              where_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Unified retrieval helper used by UI tabs.

        - Sanitizes collection name and verifies access
        - Tries hybrid search first, then falls back to near_text search
        - Returns a list of normalized dicts with content, source, metadata, score, uuid
        """
        try:
            # Ensure access and resolve sanitized class name
            actual = self._resolve_collection_name(collection_name)
            collection = self._get_tab_accessible_collection(actual, tab_name)
            if not collection:
                # Attempt a short readiness wait then retry
                self.ensure_collection_ready(collection_name)
                collection = self._get_tab_accessible_collection(actual, tab_name)
                if not collection:
                    logger.warning(
                        f"Tab '{tab_name}' cannot access collection '{collection_name}' (actual='{actual}') via SDK; using GraphQL fallback"
                    )
                    # REST GraphQL fallback path
                    gql_results = self._search_via_graphql(actual, query, limit=limit)
                    out: List[Dict[str, Any]] = []
                    for r in gql_results:
                        try:
                            out.append({
                                "content": r.get("content", ""),
                                "source": r.get("source", "Weaviate"),
                                "metadata": r.get("metadata", {}),
                                "relevance_score": float(r.get("score") or 0.0),
                                "uuid": r.get("uuid") or "",
                            })
                        except Exception:
                            pass
                    return out

            # Prefer hybrid to mix vector + keyword signals
            results = self.hybrid_search(collection_name=actual, query=query, limit=limit)
            if not results:
                # Fallback to near_text and allow optional where_filter
                results = self.search(collection_name=actual, query=query, limit=limit, where_filter=where_filter)

            # Ensure normalized structure
            out: List[Dict[str, Any]] = []
            for r in results or []:
                if isinstance(r, dict):
                    out.append({
                        "content": r.get("content", ""),
                        "source": r.get("source", "Weaviate"),
                        "metadata": r.get("metadata", {}),
                        "relevance_score": float(r.get("score") or r.get("relevance_score") or 0.0),
                        "uuid": r.get("uuid") or r.get("id") or "",
                    })
                else:
                    out.append({
                        "content": str(r),
                        "source": "Weaviate",
                        "metadata": {},
                        "relevance_score": 0.0,
                        "uuid": "",
                    })
            return out
        except Exception as e:
            logger.error(f"get_documents_for_tab failed for '{collection_name}' (tab='{tab_name}'): {e}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection"""
        try:
            self.client.collections.delete(collection_name)
            if collection_name in self._collections:
                del self._collections[collection_name]
            logger.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection '{collection_name}': {str(e)}")
            return False
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection"""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return {}
            
            # Get object count
            response = collection.aggregate.over_all(total_count=True)
            
            stats = {
                "name": collection_name,
                "total_objects": response.total_count,
                "created_at": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats for '{collection_name}': {str(e)}")
            return {}
    
    def get_collection_count(self, collection_name: str) -> int:
        """Return total object count for a collection.

        Tries SDK aggregate first, then falls back to GraphQL if needed.
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return 0
            try:
                resp = collection.aggregate.over_all(total_count=True)
                if hasattr(resp, "total_count") and resp.total_count is not None:
                    return int(resp.total_count)  # type: ignore[arg-type]
            except Exception as e:
                logger.debug(f"SDK aggregate count failed for '{collection_name}': {e}")
            # GraphQL fallback
            cnt = self._get_class_count_via_graphql(collection_name)
            return int(cnt) if cnt is not None else 0
        except Exception as e:
            logger.error(f"Error getting count for '{collection_name}': {e}")
            try:
                cnt = self._get_class_count_via_graphql(collection_name)
                return int(cnt) if cnt is not None else 0
            except Exception:
                return 0
    
    def migrate_from_faiss(self, 
                          faiss_index_path: str, 
                          collection_name: str,
                          documents: List[Dict[str, Any]]) -> bool:
        """
        Migrate documents from FAISS index to Weaviate
        
        Args:
            faiss_index_path: Path to FAISS index
            collection_name: Target Weaviate collection
            documents: Documents to migrate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create collection if it doesn't exist
            if collection_name not in self.list_collections():
                self.create_collection(
                    collection_name=collection_name,
                    description=f"Migrated from FAISS index: {faiss_index_path}"
                )
            
            # Add documents to Weaviate
            success = self.add_documents(collection_name, documents)
            
            if success:
                logger.info(f"Successfully migrated {len(documents)} documents from FAISS to Weaviate collection '{collection_name}'")
            
            return success
            
        except Exception as e:
            logger.error(f"Error migrating from FAISS: {str(e)}")
            return False
    
    def invalidate_cache(self, 
                       collection_name: str = None,
                       tab_name: str = None,
                       document_id: str = None):
        """
        Invalidate cache entries based on:
        - Collection name
        - Tab name 
        - Specific document
        """
        if document_id:
            # Invalidate all cache entries containing this document
            self.cache = {
                k: [doc for doc in v if doc.get('uuid') != document_id]
                for k, v in self.cache.items()
            }
        elif tab_name:
            # Invalidate all entries for this tab
            self.cache = {
                k: v for k, v in self.cache.items() 
                if not k.startswith(f"{collection_name or '*'}:{tab_name}:")
            }
        elif collection_name:
            # Invalidate all entries for this collection
            self.cache = {
                k: v for k, v in self.cache.items()
                if not k.startswith(f"{collection_name}:")
            }
        else:
            # Full cache clear
            self.cache = {}
            
        logger.info(f"Cache invalidated - collection: {collection_name}, tab: {tab_name}, doc: {document_id}")
        return True
    
    def close(self):
        """Close Weaviate connection"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Closed Weaviate connection")
        try:
            if self._http is not None:
                self._http.close()
                self._http = None
                logger.info("Closed HTTP client")
        except Exception:
            pass


# Global instance
_weaviate_manager = None

def _cleanup_weaviate_client():
    """Ensure the global Weaviate client is closed on process exit to avoid ResourceWarning."""
    global _weaviate_manager
    try:
        if _weaviate_manager is not None:
            _weaviate_manager.close()
    except Exception:
        # Swallow errors during interpreter shutdown
        pass

atexit.register(_cleanup_weaviate_client)

def get_weaviate_manager() -> WeaviateManager:
    """Get global Weaviate manager instance"""
    global _weaviate_manager
    if _weaviate_manager is None:
        # Load configuration from environment or config file
        from dotenv import load_dotenv
        
        # Respect Storage Settings (config/storage.env) as the source of truth.
        # Precedence: weaviate.env (legacy, loaded first), then storage.env (overrides), then .env (non-destructive)
        try:
            root_dir = os.path.dirname(os.path.dirname(__file__))
            wv_path = os.path.join(root_dir, 'config', 'weaviate.env')
            stg_path = os.path.join(root_dir, 'config', 'storage.env')
            # Load legacy weaviate.env without overriding existing env vars
            if os.path.exists(wv_path):
                load_dotenv(dotenv_path=wv_path, override=False)
                logger.info(f"Loaded legacy env from {wv_path} (override=False)")
            # Load storage.env last so UI-saved values take precedence
            if os.path.exists(stg_path):
                load_dotenv(dotenv_path=stg_path, override=True)
                logger.info(f"Loaded env from {stg_path} (override=True)")
            # Finally load .env without clobbering storage values
            env_path = os.path.join(root_dir, '.env')
            if os.path.exists(env_path):
                load_dotenv(dotenv_path=env_path, override=False)
        except Exception as _e:
            logger.debug(f"Env preload in get_weaviate_manager skipped or failed: {_e}")
        
        url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
        api_key = os.getenv("WEAVIATE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        logger.info(f"Initializing WeaviateManager with URL: {url}, API Key set: {api_key is not None}")
        
        _weaviate_manager = WeaviateManager(
            url=url,
            api_key=api_key,
            openai_api_key=openai_key
        )
        # Optional preflight after init
        try:
            preflight_on_init = os.getenv("WEAVIATE_PREFLIGHT_ON_INIT", "true").lower() in ("1", "true", "yes")
            preflight_fatal = os.getenv("WEAVIATE_PREFLIGHT_FAIL_FATAL", "false").lower() in ("1", "true", "yes")
            if preflight_on_init:
                ok = _weaviate_manager._run_preflight()
                if not ok and preflight_fatal:
                    raise RuntimeError("Weaviate preflight failed (init)")
        except Exception as e:
            logger.warning(f"Preflight-on-init handling encountered an error: {e}")
    else:
        # If environment has changed since the global instance was created, rebuild manager
        try:
            from dotenv import load_dotenv
            root_dir = os.path.dirname(os.path.dirname(__file__))
            # Maintain precedence: weaviate.env first (no override), then storage.env (override), then .env (no override)
            wv_path = os.path.join(root_dir, 'config', 'weaviate.env')
            stg_path = os.path.join(root_dir, 'config', 'storage.env')
            if os.path.exists(wv_path):
                load_dotenv(dotenv_path=wv_path, override=False)
            if os.path.exists(stg_path):
                load_dotenv(dotenv_path=stg_path, override=True)
            env_path = os.path.join(root_dir, '.env')
            if os.path.exists(env_path):
                load_dotenv(dotenv_path=env_path, override=False)
            env_url = os.getenv("WEAVIATE_URL")
            env_api = os.getenv("WEAVIATE_API_KEY")
            env_openai = os.getenv("OPENAI_API_KEY")
            url_changed = bool(env_url and hasattr(_weaviate_manager, 'url') and env_url.rstrip('/') != str(_weaviate_manager.url).rstrip('/'))
            api_changed = bool(env_api is not None and getattr(_weaviate_manager, 'api_key', None) != env_api)
            openai_changed = bool(env_openai is not None and getattr(_weaviate_manager, 'openai_api_key', None) != env_openai)
            if url_changed or api_changed or openai_changed:
                logger.info(
                    "Rebuilding WeaviateManager due to env change(s): %s",
                    ", ".join([
                        *("url" if url_changed else "",),
                        *("api_key" if api_changed else "",),
                        *("openai_api_key" if openai_changed else "",),
                    ]).strip(', ')
                )
                try:
                    _weaviate_manager.close()
                except Exception:
                    pass
                _weaviate_manager = WeaviateManager(
                    url=env_url or getattr(_weaviate_manager, 'url', None) or "http://localhost:8080",
                    api_key=env_api,
                    openai_api_key=env_openai,
                )
                # Optional preflight after change
                try:
                    preflight_on_change = os.getenv("WEAVIATE_PREFLIGHT_ON_URL_CHANGE", "true").lower() in ("1", "true", "yes")
                    preflight_fatal = os.getenv("WEAVIATE_PREFLIGHT_FAIL_FATAL", "false").lower() in ("1", "true", "yes")
                    if preflight_on_change:
                        ok = _weaviate_manager._run_preflight()
                        if not ok and preflight_fatal:
                            raise RuntimeError("Weaviate preflight failed (env change)")
                except Exception as e2:
                    logger.warning(f"Preflight-on-change handling encountered an error: {e2}")
            else:
                # Even if URL/API didn't change, prefix-related env may have changed.
                # Clear cached REST prefix and candidates so discovery will re-run using new env.
                try:
                    if hasattr(_weaviate_manager, '_rest_prefix'):
                        _weaviate_manager._rest_prefix = None  # type: ignore[attr-defined]
                    if hasattr(_weaviate_manager, '_prefix_candidates'):
                        _weaviate_manager._prefix_candidates = None  # type: ignore[attr-defined]
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Dynamic manager rebuild check failed: {e}")

    return _weaviate_manager
