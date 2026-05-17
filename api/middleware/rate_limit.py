"""
VaultMind Rate Limiting Middleware
Prevents API abuse with configurable rate limits

Phase 3: API-First Architecture
"""

import logging
import time
from collections import defaultdict
from typing import Dict, Tuple
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.
    For production, use Redis-based rate limiting.
    
    Limits:
    - Default: 100 requests per minute per IP
    - Auth endpoints: 10 requests per minute per IP
    - Ingest endpoints: 30 requests per minute per tenant
    """
    
    # Rate limit configurations (requests, window_seconds)
    RATE_LIMITS = {
        "default": (100, 60),
        "auth": (10, 60),
        "ingest": (30, 60),
    }
    
    def __init__(self, app):
        super().__init__(app)
        # Track requests: {key: [(timestamp, count)]}
        self._requests: Dict[str, list] = defaultdict(list)
        
        # Load custom limits from env
        self._load_custom_limits()
    
    def _load_custom_limits(self):
        """Load custom rate limits from environment"""
        for key in self.RATE_LIMITS:
            env_key = f"RATE_LIMIT_{key.upper()}"
            if os.getenv(env_key):
                try:
                    limit = int(os.getenv(env_key))
                    window = self.RATE_LIMITS[key][1]
                    self.RATE_LIMITS[key] = (limit, window)
                except ValueError:
                    pass
    
    async def dispatch(self, request: Request, call_next):
        # Determine rate limit category
        path = request.url.path
        
        if path.startswith("/v1/auth"):
            category = "auth"
        elif path.startswith("/v1/ingest"):
            category = "ingest"
        else:
            category = "default"
        
        # Get rate limit key
        rate_key = self._get_rate_key(request, category)
        
        # Check rate limit
        limit, window = self.RATE_LIMITS[category]
        is_allowed, remaining, reset_time = self._check_rate_limit(
            rate_key, limit, window
        )
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded: {rate_key}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": reset_time
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_rate_key(self, request: Request, category: str) -> str:
        """Generate rate limit key based on category"""
        
        # For ingest, rate limit by tenant
        if category == "ingest":
            tenant_id = request.headers.get("X-Tenant-ID", "unknown")
            return f"ingest:{tenant_id}"
        
        # For others, rate limit by IP
        client_ip = self._get_client_ip(request)
        return f"{category}:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        # Check X-Forwarded-For for proxied requests
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Fall back to client host
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Returns:
            (is_allowed, remaining_requests, reset_time_seconds)
        """
        now = time.time()
        window_start = now - window
        
        # Clean old entries
        self._requests[key] = [
            ts for ts in self._requests[key]
            if ts > window_start
        ]
        
        # Count requests in window
        request_count = len(self._requests[key])
        
        if request_count >= limit:
            # Calculate reset time
            oldest = min(self._requests[key]) if self._requests[key] else now
            reset_time = int(oldest + window - now)
            return False, 0, max(1, reset_time)
        
        # Add current request
        self._requests[key].append(now)
        
        remaining = limit - request_count - 1
        reset_time = int(window - (now - min(self._requests[key])))
        
        return True, remaining, max(1, reset_time)
