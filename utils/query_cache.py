"""
Enterprise Query Caching System
===============================

Provides Redis-based caching for query results with TTL, compression, and enterprise features.

Features:
- Query result caching with configurable TTL
- Compression for large results
- Cache invalidation strategies
- Performance metrics
- Enterprise security features
"""

import json
import hashlib
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import os

# Make Redis optional - fallback to in-memory cache if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

# Make security module optional
try:
    from utils.security import encrypt_data, decrypt_data
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    def encrypt_data(data: str) -> str:
        return data
    def decrypt_data(data: str) -> str:
        return data

logger = logging.getLogger(__name__)

class QueryCache:
    """Enterprise-grade query caching with Redis backend (with in-memory fallback)"""

    def __init__(self, host: str = None, port: int = 6379, db: int = 0, password: str = None):
        """Initialize Redis connection with enterprise settings"""
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port
        self.db = db
        self.password = password or os.getenv("REDIS_PASSWORD")

        # Enterprise settings
        self.max_memory = os.getenv("REDIS_MAX_MEMORY", "1gb")
        self.ttl_default = int(os.getenv("QUERY_CACHE_TTL", "3600"))  # 1 hour default
        self.compression_threshold = int(os.getenv("CACHE_COMPRESSION_THRESHOLD", "1024"))  # 1KB
        self.encryption_enabled = os.getenv("CACHE_ENCRYPTION_ENABLED", "true").lower() == "true" and SECURITY_AVAILABLE

        self._connection = None
        self._memory_cache: Dict[str, Tuple[Any, float, Dict[str, Any]]] = {}  # In-memory fallback: {key: (data, expiry, metadata)}
        self._connect()

    def _connect(self):
        """Establish Redis connection with retry logic"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis module not available - using in-memory cache fallback")
            self._connection = None
            return None
            
        try:
            self._connection = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20
            )

            # Test connection
            self._connection.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")

            # Configure Redis for enterprise use
            self._configure_redis()

            return self._connection

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Fallback to in-memory cache for development
            logger.warning("Using in-memory cache as fallback")
            self._connection = None
            return None

    def _configure_redis(self):
        """Configure Redis for enterprise caching"""
        try:
            # Set max memory policy
            self._connection.config_set('maxmemory', self.max_memory)
            self._connection.config_set('maxmemory-policy', 'allkeys-lru')

            # Enable keyspace notifications for monitoring
            self._connection.config_set('notify-keyspace-events', 'Ex')

        except Exception as e:
            logger.warning(f"Failed to configure Redis: {e}")

    def _generate_cache_key(self, query: str, index_name: str, backend: str, top_k: int, user_id: str = None) -> str:
        """Generate deterministic cache key with security considerations"""
        # Include user_id for multi-tenancy
        key_components = [
            query.strip().lower()[:100],  # Normalize and limit query length
            index_name,
            backend,
            str(top_k),
            user_id or "anonymous"
        ]

        key_string = "|".join(key_components)
        cache_key = f"query:{hashlib.sha256(key_string.encode()).hexdigest()[:16]}"

        return cache_key

    def _compress_data(self, data: str) -> Tuple[str, bool]:
        """Compress data if it exceeds threshold"""
        if len(data) > self.compression_threshold:
            import gzip
            compressed = gzip.compress(data.encode('utf-8'))
            return compressed.hex(), True
        return data, False

    def _decompress_data(self, data: str, compressed: bool) -> str:
        """Decompress data if it was compressed"""
        if compressed:
            import gzip
            return gzip.decompress(bytes.fromhex(data)).decode('utf-8')
        return data

    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive cache data"""
        if self.encryption_enabled:
            return encrypt_data(data)
        return data

    def _decrypt_data(self, data: str) -> str:
        """Decrypt sensitive cache data"""
        if self.encryption_enabled:
            return decrypt_data(data)
        return data

    def get(self, query: str, index_name: str, backend: str, top_k: int, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached query result"""
        cache_key = self._generate_cache_key(query, index_name, backend, top_k, user_id)
        
        # Use in-memory cache if Redis not available
        if not self._connection:
            try:
                if cache_key in self._memory_cache:
                    data, expiry, metadata = self._memory_cache[cache_key]
                    if time.time() < expiry:
                        metadata['access_count'] = metadata.get('access_count', 0) + 1
                        metadata['last_accessed'] = time.time()
                        logger.debug(f"In-memory cache hit for query: {query[:50]}...")
                        return data
                    else:
                        # Expired
                        del self._memory_cache[cache_key]
                return None
            except Exception as e:
                logger.warning(f"In-memory cache retrieval failed: {e}")
                return None

        try:
            # Get cache metadata
            meta_key = f"{cache_key}:meta"
            meta_data = self._connection.hgetall(meta_key)

            if not meta_data:
                return None

            # Check TTL
            created_at = float(meta_data.get('created_at', 0))
            ttl = int(meta_data.get('ttl', self.ttl_default))

            if time.time() - created_at > ttl:
                # Expired, clean up
                self._connection.delete(cache_key, meta_key)
                return None

            # Get cached data
            cached_data = self._connection.get(cache_key)
            if not cached_data:
                return None

            # Decrypt and decompress
            decrypted_data = self._decrypt_data(cached_data)
            decompressed_data = self._decompress_data(decrypted_data, meta_data.get('compressed') == 'true')

            result = json.loads(decompressed_data)

            # Update access metrics
            self._connection.hincrby(meta_key, 'access_count', 1)
            self._connection.hset(meta_key, 'last_accessed', time.time())

            logger.debug(f"Cache hit for query: {query[:50]}...")
            return result

        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None

    def set(self, query: str, index_name: str, backend: str, top_k: int, result: Dict[str, Any],
            user_id: str = None, ttl: int = None) -> bool:
        """Store query result in cache"""
        if not result:
            return False
            
        cache_key = self._generate_cache_key(query, index_name, backend, top_k, user_id)
        ttl = ttl or self.ttl_default
        
        # Use in-memory cache if Redis not available
        if not self._connection:
            try:
                expiry = time.time() + ttl
                metadata = {
                    'query': query[:200],
                    'index_name': index_name,
                    'backend': backend,
                    'top_k': top_k,
                    'user_id': user_id or "anonymous",
                    'created_at': time.time(),
                    'ttl': ttl,
                    'access_count': 0,
                    'last_accessed': time.time()
                }
                self._memory_cache[cache_key] = (result, expiry, metadata)
                logger.debug(f"Cached query result in memory: {query[:50]}... (TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.warning(f"In-memory cache storage failed: {e}")
                return False

        try:
            # Serialize result
            result_json = json.dumps(result, default=str)

            # Compress if needed
            processed_data, compressed = self._compress_data(result_json)

            # Encrypt if enabled
            encrypted_data = self._encrypt_data(processed_data)

            # Store data
            self._connection.setex(cache_key, ttl, encrypted_data)

            # Store metadata
            meta_key = f"{cache_key}:meta"
            meta_data = {
                'query': query[:200],  # Truncate for storage
                'index_name': index_name,
                'backend': backend,
                'top_k': top_k,
                'user_id': user_id or "anonymous",
                'created_at': time.time(),
                'ttl': ttl,
                'compressed': str(compressed).lower(),
                'encrypted': str(self.encryption_enabled).lower(),
                'size_bytes': len(encrypted_data),
                'access_count': 0,
                'last_accessed': time.time()
            }

            self._connection.hset(meta_key, mapping=meta_data)
            self._connection.expire(meta_key, ttl)

            logger.debug(f"Cached query result: {query[:50]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
            return False

    def invalidate(self, pattern: str = None) -> int:
        """Invalidate cache entries matching pattern"""
        if not self._connection:
            return 0

        try:
            if pattern:
                # Find keys matching pattern
                keys = self._connection.keys(pattern)
                if keys:
                    # Also find metadata keys
                    meta_keys = [f"{key}:meta" for key in keys]
                    all_keys = keys + meta_keys
                    deleted = self._connection.delete(*all_keys)
                    logger.info(f"Invalidated {deleted} cache entries matching {pattern}")
                    return deleted
            else:
                # Clear all query cache
                query_keys = self._connection.keys("query:*")
                if query_keys:
                    deleted = self._connection.delete(*query_keys)
                    logger.info(f"Cleared all {deleted} query cache entries")
                    return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if not self._connection:
            # Return in-memory cache stats
            try:
                total_accesses = sum(meta.get('access_count', 0) for _, _, meta in self._memory_cache.values())
                oldest_entry = min((meta.get('created_at', time.time()) for _, _, meta in self._memory_cache.values()), default=time.time())
                newest_entry = max((meta.get('created_at', 0) for _, _, meta in self._memory_cache.values()), default=0)
                
                return {
                    "status": "in-memory",
                    "total_entries": len(self._memory_cache),
                    "total_accesses": total_accesses,
                    "avg_accesses_per_entry": round(total_accesses / max(1, len(self._memory_cache)), 2),
                    "oldest_entry_age_seconds": int(time.time() - oldest_entry) if oldest_entry else 0,
                    "newest_entry_age_seconds": int(time.time() - newest_entry) if newest_entry else 0,
                }
            except Exception as e:
                return {"status": "in-memory", "error": str(e)}

        try:
            info = self._connection.info()
            keys = self._connection.keys("query:*")

            total_size = 0
            total_accesses = 0
            oldest_entry = time.time()
            newest_entry = 0

            for key in keys:
                if key.endswith(":meta"):
                    meta = self._connection.hgetall(key)
                    if meta:
                        total_size += int(meta.get('size_bytes', 0))
                        total_accesses += int(meta.get('access_count', 0))

                        created_at = float(meta.get('created_at', time.time()))
                        oldest_entry = min(oldest_entry, created_at)
                        newest_entry = max(newest_entry, created_at)

            return {
                "status": "connected",
                "total_entries": len([k for k in keys if not k.endswith(":meta")]),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_accesses": total_accesses,
                "avg_accesses_per_entry": round(total_accesses / max(1, len(keys) // 2), 2),
                "oldest_entry_age_seconds": int(time.time() - oldest_entry),
                "newest_entry_age_seconds": int(time.time() - newest_entry),
                "redis_info": {
                    "used_memory": info.get('used_memory_human', 'unknown'),
                    "connected_clients": info.get('connected_clients', 0),
                    "uptime_days": info.get('uptime_in_days', 0)
                }
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache system"""
        try:
            if not self._connection:
                return {"status": "disconnected", "healthy": False}

            # Test basic operations
            test_key = "health_check"
            self._connection.setex(test_key, 10, "ok")
            result = self._connection.get(test_key)
            self._connection.delete(test_key)

            if result == "ok":
                stats = self.get_stats()
                return {
                    "status": "healthy",
                    "healthy": True,
                    "response_time_ms": 0,  # Could measure this
                    "stats": stats
                }
            else:
                return {"status": "unhealthy", "healthy": False, "error": "Basic operations failed"}

        except Exception as e:
            return {"status": "error", "healthy": False, "error": str(e)}

# Global cache instance
_cache_instance = None

def get_query_cache() -> QueryCache:
    """Get singleton cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = QueryCache()
    return _cache_instance

# Convenience functions for easy integration
def cache_query_result(query: str, index_name: str, backend: str, top_k: int,
                      result: Dict[str, Any], user_id: str = None, ttl: int = None) -> bool:
    """Cache a query result"""
    cache = get_query_cache()
    return cache.set(query, index_name, backend, top_k, result, user_id, ttl)

def get_cached_result(query: str, index_name: str, backend: str, top_k: int,
                     user_id: str = None) -> Optional[Dict[str, Any]]:
    """Get cached query result"""
    cache = get_query_cache()
    return cache.get(query, index_name, backend, top_k, user_id)

def invalidate_query_cache(pattern: str = None) -> int:
    """Invalidate cache entries"""
    cache = get_query_cache()
    return cache.invalidate(pattern)

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    cache = get_query_cache()
    return cache.get_stats()

if __name__ == "__main__":
    # Test the cache system
    cache = get_query_cache()

    # Test basic operations
    test_result = {"content": "test content", "results": [{"content": "test", "score": 0.9}]}
    success = cache.set("test query", "test_index", "faiss", 5, test_result, "test_user", 60)

    if success:
        retrieved = cache.get("test query", "test_index", "faiss", 5, "test_user")
        print(f"Cache test successful: {retrieved is not None}")

    # Print stats
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")
