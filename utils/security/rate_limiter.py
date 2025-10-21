"""
Enterprise Rate Limiting
=======================

Multi-tier rate limiting with Token Bucket and Sliding Window algorithms.
Supports both in-memory and Redis-backed storage for distributed systems.

Algorithms:
- Token Bucket: Smooth rate limiting with burst capacity
- Sliding Window: Precise rate limiting over time windows
- Fixed Window: Simple counter-based limiting

References:
- RFC 6585 (HTTP Status Code 429)
- OWASP API Security Top 10
- Redis Rate Limiting Patterns
"""

import time
import logging
import hashlib
from typing import Tuple, Optional, Dict, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class RateLimitTier(Enum):
    """Rate limit tiers for different user types"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int
    
    @staticmethod
    def get_tier_config(tier: RateLimitTier) -> 'RateLimitConfig':
        """Get configuration for a specific tier"""
        configs = {
            RateLimitTier.FREE: RateLimitConfig(
                requests_per_minute=5,
                requests_per_hour=50,
                requests_per_day=200,
                burst_size=10
            ),
            RateLimitTier.BASIC: RateLimitConfig(
                requests_per_minute=20,
                requests_per_hour=200,
                requests_per_day=1000,
                burst_size=30
            ),
            RateLimitTier.PREMIUM: RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=5000,
                burst_size=100
            ),
            RateLimitTier.ENTERPRISE: RateLimitConfig(
                requests_per_minute=200,
                requests_per_hour=5000,
                requests_per_day=50000,
                burst_size=500
            ),
            RateLimitTier.ADMIN: RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=10000,
                requests_per_day=100000,
                burst_size=2000
            )
        }
        return configs.get(tier, configs[RateLimitTier.FREE])


class TokenBucket:
    """
    Token Bucket algorithm for rate limiting
    
    Allows burst traffic while maintaining average rate.
    Tokens are added at a constant rate and consumed per request.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> Tuple[bool, Optional[str]]:
        """
        Try to consume tokens
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            (allowed, error_message)
        """
        with self.lock:
            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.refill_rate)
            )
            self.last_refill = now
            
            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, None
            else:
                wait_time = (tokens - self.tokens) / self.refill_rate
                return False, f"Rate limit exceeded. Try again in {wait_time:.1f}s"


class SlidingWindowCounter:
    """
    Sliding Window algorithm for precise rate limiting
    
    Maintains a sliding window of timestamps for accurate counting.
    More memory intensive but provides precise limits.
    """
    
    def __init__(self, window_seconds: int, max_requests: int):
        """
        Initialize sliding window counter
        
        Args:
            window_seconds: Time window in seconds
            max_requests: Maximum requests in window
        """
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests = deque()
        self.lock = threading.Lock()
    
    def is_allowed(self) -> Tuple[bool, Optional[str]]:
        """
        Check if request is allowed
        
        Returns:
            (allowed, error_message)
        """
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Remove old requests outside window
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True, None
            else:
                # Calculate when oldest request will expire
                oldest = self.requests[0]
                wait_time = oldest + self.window_seconds - now
                return False, f"Rate limit exceeded. Try again in {wait_time:.1f}s"
    
    def get_remaining(self) -> int:
        """Get remaining requests in current window"""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Remove old requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            return max(0, self.max_requests - len(self.requests))


class EnterpriseRateLimiter:
    """
    Enterprise-grade rate limiter with multi-tier support
    
    Features:
    - Multiple time windows (minute, hour, day)
    - Tier-based limits
    - Token bucket for burst handling
    - Sliding window for precision
    - Redis support for distributed systems
    - Detailed metrics and monitoring
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiter
        
        Args:
            redis_url: Optional Redis URL for distributed rate limiting
        """
        self.redis_client = None
        self.use_redis = False
        
        # Try to initialize Redis
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                self.use_redis = True
                logger.info("Redis rate limiter initialized")
            except Exception as e:
                logger.warning(f"Redis initialization failed, using in-memory: {e}")
        
        # In-memory storage (fallback or standalone)
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, Dict[str, SlidingWindowCounter]] = defaultdict(dict)
        self.metrics: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0
        })
        self.lock = threading.Lock()
    
    def check_rate_limit(self, user_id: str, tier: RateLimitTier = RateLimitTier.FREE,
                        operation: str = "query") -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check if request is allowed under rate limits
        
        Args:
            user_id: User identifier
            tier: User's rate limit tier
            operation: Operation type (for separate limits)
            
        Returns:
            (allowed, error_message, rate_limit_info)
        """
        config = RateLimitConfig.get_tier_config(tier)
        key = f"{user_id}:{operation}"
        
        # Track metrics
        with self.lock:
            self.metrics[key]['total_requests'] += 1
        
        # Use Redis if available
        if self.use_redis:
            return self._check_redis_rate_limit(key, config)
        else:
            return self._check_memory_rate_limit(key, config)
    
    def _check_memory_rate_limit(self, key: str, config: RateLimitConfig) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Check rate limit using in-memory storage"""
        
        # Initialize token bucket if needed
        if key not in self.token_buckets:
            with self.lock:
                if key not in self.token_buckets:
                    self.token_buckets[key] = TokenBucket(
                        capacity=config.burst_size,
                        refill_rate=config.requests_per_minute / 60.0
                    )
        
        # Check token bucket (for burst handling)
        bucket = self.token_buckets[key]
        burst_allowed, burst_msg = bucket.consume()
        
        if not burst_allowed:
            with self.lock:
                self.metrics[key]['blocked_requests'] += 1
            return False, burst_msg, self._get_rate_limit_info(key, config)
        
        # Initialize sliding windows if needed
        if key not in self.sliding_windows:
            with self.lock:
                if key not in self.sliding_windows:
                    self.sliding_windows[key] = {
                        'minute': SlidingWindowCounter(60, config.requests_per_minute),
                        'hour': SlidingWindowCounter(3600, config.requests_per_hour),
                        'day': SlidingWindowCounter(86400, config.requests_per_day)
                    }
        
        # Check all time windows
        windows = self.sliding_windows[key]
        
        for window_name, window in windows.items():
            allowed, msg = window.is_allowed()
            if not allowed:
                with self.lock:
                    self.metrics[key]['blocked_requests'] += 1
                return False, f"Rate limit exceeded ({window_name}). {msg}", self._get_rate_limit_info(key, config)
        
        # All checks passed
        with self.lock:
            self.metrics[key]['allowed_requests'] += 1
        
        return True, None, self._get_rate_limit_info(key, config)
    
    def _check_redis_rate_limit(self, key: str, config: RateLimitConfig) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Check rate limit using Redis"""
        try:
            now = time.time()
            pipe = self.redis_client.pipeline()
            
            # Check minute window
            minute_key = f"ratelimit:{key}:minute"
            pipe.zadd(minute_key, {str(now): now})
            pipe.zremrangebyscore(minute_key, 0, now - 60)
            pipe.zcard(minute_key)
            pipe.expire(minute_key, 60)
            
            # Check hour window
            hour_key = f"ratelimit:{key}:hour"
            pipe.zadd(hour_key, {str(now): now})
            pipe.zremrangebyscore(hour_key, 0, now - 3600)
            pipe.zcard(hour_key)
            pipe.expire(hour_key, 3600)
            
            # Check day window
            day_key = f"ratelimit:{key}:day"
            pipe.zadd(day_key, {str(now): now})
            pipe.zremrangebyscore(day_key, 0, now - 86400)
            pipe.zcard(day_key)
            pipe.expire(day_key, 86400)
            
            results = pipe.execute()
            
            minute_count = results[2]
            hour_count = results[6]
            day_count = results[10]
            
            # Check limits
            if minute_count > config.requests_per_minute:
                return False, f"Rate limit exceeded (minute). Try again in 60s", {
                    'minute_remaining': 0,
                    'hour_remaining': max(0, config.requests_per_hour - hour_count),
                    'day_remaining': max(0, config.requests_per_day - day_count)
                }
            
            if hour_count > config.requests_per_hour:
                return False, f"Rate limit exceeded (hour). Try again later", {
                    'minute_remaining': max(0, config.requests_per_minute - minute_count),
                    'hour_remaining': 0,
                    'day_remaining': max(0, config.requests_per_day - day_count)
                }
            
            if day_count > config.requests_per_day:
                return False, f"Rate limit exceeded (day). Try again tomorrow", {
                    'minute_remaining': max(0, config.requests_per_minute - minute_count),
                    'hour_remaining': max(0, config.requests_per_hour - hour_count),
                    'day_remaining': 0
                }
            
            return True, None, {
                'minute_remaining': max(0, config.requests_per_minute - minute_count),
                'hour_remaining': max(0, config.requests_per_hour - hour_count),
                'day_remaining': max(0, config.requests_per_day - day_count)
            }
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fallback to memory-based limiting
            return self._check_memory_rate_limit(key, config)
    
    def _get_rate_limit_info(self, key: str, config: RateLimitConfig) -> Dict[str, Any]:
        """Get current rate limit status"""
        info = {
            'minute_limit': config.requests_per_minute,
            'hour_limit': config.requests_per_hour,
            'day_limit': config.requests_per_day,
            'burst_size': config.burst_size
        }
        
        if key in self.sliding_windows:
            windows = self.sliding_windows[key]
            info['minute_remaining'] = windows['minute'].get_remaining()
            info['hour_remaining'] = windows['hour'].get_remaining()
            info['day_remaining'] = windows['day'].get_remaining()
        
        return info
    
    def get_metrics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get rate limiting metrics
        
        Args:
            user_id: Optional user ID to filter metrics
            
        Returns:
            Metrics dictionary
        """
        with self.lock:
            if user_id:
                # Filter metrics for specific user
                user_metrics = {k: v for k, v in self.metrics.items() if k.startswith(user_id)}
                return user_metrics
            else:
                # Return all metrics
                return dict(self.metrics)
    
    def reset_user_limits(self, user_id: str):
        """Reset rate limits for a user (admin function)"""
        with self.lock:
            # Remove from token buckets
            keys_to_remove = [k for k in self.token_buckets.keys() if k.startswith(user_id)]
            for key in keys_to_remove:
                del self.token_buckets[key]
            
            # Remove from sliding windows
            keys_to_remove = [k for k in self.sliding_windows.keys() if k.startswith(user_id)]
            for key in keys_to_remove:
                del self.sliding_windows[key]
        
        # Reset Redis if available
        if self.use_redis:
            try:
                pattern = f"ratelimit:{user_id}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Failed to reset Redis limits: {e}")
        
        logger.info(f"Reset rate limits for user: {user_id}")


# Global rate limiter instance
_rate_limiter_instance = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter(redis_url: Optional[str] = None) -> EnterpriseRateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter_instance
    
    if _rate_limiter_instance is None:
        with _rate_limiter_lock:
            if _rate_limiter_instance is None:
                _rate_limiter_instance = EnterpriseRateLimiter(redis_url)
    
    return _rate_limiter_instance


# Convenience function
def check_rate_limit(user_id: str, tier: str = "free", operation: str = "query") -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Convenience function to check rate limit
    
    Args:
        user_id: User identifier
        tier: Rate limit tier (free, basic, premium, enterprise, admin)
        operation: Operation type
        
    Returns:
        (allowed, error_message, rate_limit_info)
    """
    limiter = get_rate_limiter()
    tier_enum = RateLimitTier(tier.lower())
    return limiter.check_rate_limit(user_id, tier_enum, operation)
