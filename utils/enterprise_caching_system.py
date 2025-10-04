"""
Enterprise Redis-Based Caching System

Implements intelligent caching for LLM responses with TTL, invalidation,
and cache warming strategies for enterprise-grade performance.
"""

import logging
import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

# Fallback in-memory cache when Redis is not available
_memory_cache = {}
_cache_timestamps = {}

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    cache_key: str = ""
    metadata: Dict[str, Any] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def update_access(self):
        """Update access statistics"""
        self.access_count += 1
        self.last_accessed = datetime.now()

class RedisConnectionManager:
    """Manages Redis connection with fallback"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: str = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis_client = None
        self.redis_available = False
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False  # We'll handle encoding ourselves
            )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info("Redis connection established")
        except ImportError:
            logger.warning("Redis package not available, using memory cache")
            self.redis_available = False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using memory cache")
            self.redis_available = False
    
    def get(self, key: str) -> Optional[bytes]:
        """Get value from Redis or memory cache"""
        if self.redis_available:
            try:
                return self.redis_client.get(key)
            except Exception as e:
                logger.error(f"Redis get failed: {e}")
                self.redis_available = False
        
        # Fallback to memory cache
        return _memory_cache.get(key)
    
    def set(self, key: str, value: bytes, ex: Optional[int] = None) -> bool:
        """Set value in Redis or memory cache"""
        if self.redis_available:
            try:
                return self.redis_client.set(key, value, ex=ex)
            except Exception as e:
                logger.error(f"Redis set failed: {e}")
                self.redis_available = False
        
        # Fallback to memory cache
        _memory_cache[key] = value
        if ex:
            _cache_timestamps[key] = time.time() + ex
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis or memory cache"""
        if self.redis_available:
            try:
                return bool(self.redis_client.delete(key))
            except Exception as e:
                logger.error(f"Redis delete failed: {e}")
                self.redis_available = False
        
        # Fallback to memory cache
        _memory_cache.pop(key, None)
        _cache_timestamps.pop(key, None)
        return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if self.redis_available:
            try:
                return bool(self.redis_client.exists(key))
            except Exception as e:
                logger.error(f"Redis exists failed: {e}")
                self.redis_available = False
        
        # Check memory cache and expiration
        if key in _memory_cache:
            if key in _cache_timestamps:
                if time.time() > _cache_timestamps[key]:
                    # Expired
                    _memory_cache.pop(key, None)
                    _cache_timestamps.pop(key, None)
                    return False
            return True
        return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        if self.redis_available:
            try:
                return [key.decode() if isinstance(key, bytes) else key 
                       for key in self.redis_client.keys(pattern)]
            except Exception as e:
                logger.error(f"Redis keys failed: {e}")
                self.redis_available = False
        
        # Fallback to memory cache
        import fnmatch
        return [key for key in _memory_cache.keys() if fnmatch.fnmatch(key, pattern)]

class EnterpriseCacheManager:
    """Enterprise-grade caching system with intelligent strategies"""
    
    def __init__(self, redis_config: Dict[str, Any] = None):
        self.redis_config = redis_config or {}
        self.connection = RedisConnectionManager(**self.redis_config)
        
        # Cache configuration
        self.default_ttl = 3600  # 1 hour
        self.max_cache_size = 1000  # Maximum number of cached items
        self.cache_prefix = "vaultmind_cache:"
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
    
    def get_cache_key(self, query: str, context: str, model_params: Dict[str, Any] = None) -> str:
        """Generate unique cache key for query and context"""
        # Create a deterministic hash of the input
        key_components = [
            query.strip().lower(),
            context[:1000],  # Limit context length for key generation
            json.dumps(model_params or {}, sort_keys=True)
        ]
        
        key_string = "|".join(key_components)
        cache_key = hashlib.md5(key_string.encode()).hexdigest()
        return f"{self.cache_prefix}{cache_key}"
    
    def get_cached_response(self, query: str, context: str, model_params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached LLM response"""
        try:
            cache_key = self.get_cache_key(query, context, model_params)
            
            if not self.connection.exists(cache_key):
                self.stats["misses"] += 1
                return None
            
            cached_data = self.connection.get(cache_key)
            if cached_data is None:
                self.stats["misses"] += 1
                return None
            
            # Deserialize cache entry
            cache_entry = pickle.loads(cached_data)
            
            # Check if expired
            if cache_entry.is_expired():
                self.connection.delete(cache_key)
                self.stats["misses"] += 1
                return None
            
            # Update access statistics
            cache_entry.update_access()
            
            # Re-save with updated stats
            self.connection.set(
                cache_key, 
                pickle.dumps(cache_entry), 
                ex=int((cache_entry.expires_at - datetime.now()).total_seconds()) if cache_entry.expires_at else None
            )
            
            self.stats["hits"] += 1
            logger.info(f"Cache hit for query: {query[:50]}...")
            
            return cache_entry.data
            
        except Exception as e:
            logger.error(f"Cache retrieval failed: {e}")
            self.stats["errors"] += 1
            return None
    
    def cache_response(
        self, 
        query: str, 
        context: str, 
        response: Dict[str, Any], 
        ttl: Optional[int] = None,
        model_params: Dict[str, Any] = None
    ) -> bool:
        """Cache LLM response with metadata"""
        try:
            cache_key = self.get_cache_key(query, context, model_params)
            ttl = ttl or self.default_ttl
            
            # Create cache entry
            cache_entry = CacheEntry(
                data=response,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=ttl),
                cache_key=cache_key,
                metadata={
                    "query_length": len(query),
                    "context_length": len(context),
                    "response_type": response.get("answer_type", "unknown"),
                    "model_params": model_params or {}
                }
            )
            
            # Serialize and store
            serialized_entry = pickle.dumps(cache_entry)
            success = self.connection.set(cache_key, serialized_entry, ex=ttl)
            
            if success:
                self.stats["sets"] += 1
                logger.info(f"Cached response for query: {query[:50]}...")
                
                # Cleanup old entries if cache is getting large
                self._cleanup_cache_if_needed()
                
                return True
            else:
                self.stats["errors"] += 1
                return False
                
        except Exception as e:
            logger.error(f"Cache storage failed: {e}")
            self.stats["errors"] += 1
            return False
    
    def invalidate_cache(self, pattern: str = None) -> int:
        """Invalidate cache entries matching pattern"""
        try:
            if pattern is None:
                pattern = f"{self.cache_prefix}*"
            elif not pattern.startswith(self.cache_prefix):
                pattern = f"{self.cache_prefix}*{pattern}*"
            
            keys = self.connection.keys(pattern)
            deleted_count = 0
            
            for key in keys:
                if self.connection.delete(key):
                    deleted_count += 1
            
            self.stats["deletes"] += deleted_count
            logger.info(f"Invalidated {deleted_count} cache entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            self.stats["errors"] += 1
            return 0
    
    def warm_cache(self, queries_and_contexts: List[Dict[str, str]], llm_function: Callable) -> int:
        """Pre-populate cache with common queries"""
        warmed_count = 0
        
        for item in queries_and_contexts:
            query = item.get("query", "")
            context = item.get("context", "")
            
            if not query or not context:
                continue
            
            # Check if already cached
            if self.get_cached_response(query, context) is not None:
                continue
            
            try:
                # Generate response and cache it
                response = llm_function(query, context)
                if response and self.cache_response(query, context, response):
                    warmed_count += 1
                    logger.info(f"Cache warmed for: {query[:50]}...")
                
            except Exception as e:
                logger.error(f"Cache warming failed for query: {e}")
        
        logger.info(f"Cache warming completed: {warmed_count} entries added")
        return warmed_count
    
    def _cleanup_cache_if_needed(self):
        """Clean up old cache entries if cache is getting large"""
        try:
            all_keys = self.connection.keys(f"{self.cache_prefix}*")
            
            if len(all_keys) <= self.max_cache_size:
                return
            
            # Get cache entries with access information
            entries_with_access = []
            
            for key in all_keys:
                try:
                    cached_data = self.connection.get(key)
                    if cached_data:
                        cache_entry = pickle.loads(cached_data)
                        entries_with_access.append((key, cache_entry))
                except Exception:
                    # If we can't deserialize, mark for deletion
                    self.connection.delete(key)
            
            # Sort by last accessed time and access count
            entries_with_access.sort(
                key=lambda x: (x[1].last_accessed or x[1].created_at, x[1].access_count)
            )
            
            # Delete oldest entries
            entries_to_delete = len(entries_with_access) - self.max_cache_size + 100  # Delete extra for buffer
            
            for i in range(min(entries_to_delete, len(entries_with_access))):
                key, _ = entries_with_access[i]
                self.connection.delete(key)
            
            logger.info(f"Cleaned up {entries_to_delete} old cache entries")
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        try:
            cache_size = len(self.connection.keys(f"{self.cache_prefix}*"))
        except Exception:
            cache_size = 0
        
        return {
            "hit_rate_percent": round(hit_rate, 2),
            "total_hits": self.stats["hits"],
            "total_misses": self.stats["misses"],
            "total_sets": self.stats["sets"],
            "total_deletes": self.stats["deletes"],
            "total_errors": self.stats["errors"],
            "cache_size": cache_size,
            "redis_available": self.connection.redis_available
        }
    
    def export_cache_config(self, filename: str = None) -> str:
        """Export cache configuration"""
        config = {
            "redis_config": self.redis_config,
            "default_ttl": self.default_ttl,
            "max_cache_size": self.max_cache_size,
            "cache_prefix": self.cache_prefix,
            "stats": self.get_cache_stats(),
            "exported_at": datetime.now().isoformat()
        }
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                return f"Cache config exported to {filename}"
            except Exception as e:
                logger.error(f"Export failed: {e}")
                return f"Export failed: {e}"
        else:
            return json.dumps(config, indent=2, ensure_ascii=False)

def cached_llm_response(cache_manager: EnterpriseCacheManager, ttl: int = 3600):
    """Decorator for caching LLM responses"""
    def decorator(llm_func: Callable):
        def wrapper(query: str, context: str, **kwargs):
            # Try to get cached response
            cached = cache_manager.get_cached_response(query, context, kwargs)
            if cached is not None:
                return cached
            
            # Generate fresh response
            response = llm_func(query, context, **kwargs)
            
            # Cache the response
            if response:
                cache_manager.cache_response(query, context, response, ttl, kwargs)
            
            return response
        
        return wrapper
    return decorator

def get_enterprise_cache_manager(redis_config: Dict[str, Any] = None) -> EnterpriseCacheManager:
    """Get instance of enterprise cache manager"""
    return EnterpriseCacheManager(redis_config)

# Global cache manager instance
_global_cache_manager = None

def get_global_cache_manager() -> EnterpriseCacheManager:
    """Get global cache manager instance"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = EnterpriseCacheManager()
    return _global_cache_manager
