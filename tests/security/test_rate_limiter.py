"""
Tests for Rate Limiter
=====================

Comprehensive test suite for enterprise rate limiting.
Tests cover Token Bucket, Sliding Window, and multi-tier limiting.
"""

import pytest
import time
from utils.security.rate_limiter import (
    EnterpriseRateLimiter,
    RateLimitTier,
    RateLimitConfig,
    TokenBucket,
    SlidingWindowCounter,
    get_rate_limiter,
    check_rate_limit
)


class TestRateLimitConfig:
    """Test rate limit configuration"""
    
    def test_free_tier_config(self):
        """Test free tier configuration"""
        config = RateLimitConfig.get_tier_config(RateLimitTier.FREE)
        assert config.requests_per_minute == 5
        assert config.requests_per_hour == 50
        assert config.requests_per_day == 200
        assert config.burst_size == 10
    
    def test_premium_tier_config(self):
        """Test premium tier configuration"""
        config = RateLimitConfig.get_tier_config(RateLimitTier.PREMIUM)
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 5000
    
    def test_admin_tier_config(self):
        """Test admin tier has highest limits"""
        config = RateLimitConfig.get_tier_config(RateLimitTier.ADMIN)
        assert config.requests_per_minute >= 1000
        assert config.requests_per_day >= 100000


class TestTokenBucket:
    """Test Token Bucket algorithm"""
    
    def test_initial_capacity(self):
        """Test bucket starts at full capacity"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        allowed, msg = bucket.consume(5)
        assert allowed is True
        assert msg is None
    
    def test_consume_all_tokens(self):
        """Test consuming all tokens"""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # Consume all tokens
        for i in range(5):
            allowed, msg = bucket.consume(1)
            assert allowed is True
        
        # Next request should fail
        allowed, msg = bucket.consume(1)
        assert allowed is False
        assert "Rate limit exceeded" in msg
    
    def test_token_refill(self):
        """Test tokens refill over time"""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/second
        
        # Consume all tokens
        bucket.consume(10)
        
        # Wait for refill
        time.sleep(0.5)  # Should refill ~5 tokens
        
        # Should be able to consume some tokens
        allowed, msg = bucket.consume(3)
        assert allowed is True
    
    def test_burst_handling(self):
        """Test burst traffic handling"""
        bucket = TokenBucket(capacity=20, refill_rate=5.0)
        
        # Burst of 15 requests should succeed
        for i in range(15):
            allowed, msg = bucket.consume(1)
            assert allowed is True
        
        # Next 5 should fail (over capacity)
        for i in range(5):
            allowed, msg = bucket.consume(1)
            assert allowed is False


class TestSlidingWindowCounter:
    """Test Sliding Window algorithm"""
    
    def test_initial_requests_allowed(self):
        """Test initial requests are allowed"""
        window = SlidingWindowCounter(window_seconds=60, max_requests=10)
        
        for i in range(10):
            allowed, msg = window.is_allowed()
            assert allowed is True
    
    def test_exceeds_limit(self):
        """Test exceeding limit is blocked"""
        window = SlidingWindowCounter(window_seconds=60, max_requests=5)
        
        # First 5 should succeed
        for i in range(5):
            allowed, msg = window.is_allowed()
            assert allowed is True
        
        # 6th should fail
        allowed, msg = window.is_allowed()
        assert allowed is False
        assert "Rate limit exceeded" in msg
    
    def test_window_expiration(self):
        """Test old requests expire from window"""
        window = SlidingWindowCounter(window_seconds=1, max_requests=3)
        
        # Use up limit
        for i in range(3):
            window.is_allowed()
        
        # Should be blocked
        allowed, msg = window.is_allowed()
        assert allowed is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        allowed, msg = window.is_allowed()
        assert allowed is True
    
    def test_get_remaining(self):
        """Test getting remaining requests"""
        window = SlidingWindowCounter(window_seconds=60, max_requests=10)
        
        assert window.get_remaining() == 10
        
        window.is_allowed()
        assert window.get_remaining() == 9
        
        window.is_allowed()
        window.is_allowed()
        assert window.get_remaining() == 7


class TestEnterpriseRateLimiter:
    """Test Enterprise Rate Limiter"""
    
    def test_free_tier_limits(self):
        """Test free tier rate limits"""
        limiter = EnterpriseRateLimiter()
        user_id = "test_user_free"
        
        # Should allow first 5 requests (per minute limit)
        for i in range(5):
            allowed, msg, info = limiter.check_rate_limit(user_id, RateLimitTier.FREE)
            assert allowed is True, f"Request {i+1} should be allowed"
        
        # 6th request should be blocked
        allowed, msg, info = limiter.check_rate_limit(user_id, RateLimitTier.FREE)
        assert allowed is False
        assert "Rate limit exceeded" in msg
    
    def test_premium_tier_higher_limits(self):
        """Test premium tier has higher limits than free"""
        limiter = EnterpriseRateLimiter()
        user_id = "test_user_premium"
        
        # Premium should allow more requests
        success_count = 0
        for i in range(30):
            allowed, msg, info = limiter.check_rate_limit(user_id, RateLimitTier.PREMIUM)
            if allowed:
                success_count += 1
        
        # Should allow significantly more than free tier (5)
        assert success_count > 20
    
    def test_different_operations_separate_limits(self):
        """Test different operations have separate limits"""
        limiter = EnterpriseRateLimiter()
        user_id = "test_user_ops"
        
        # Use up query limit
        for i in range(5):
            limiter.check_rate_limit(user_id, RateLimitTier.FREE, operation="query")
        
        # Should still be able to do other operations
        allowed, msg, info = limiter.check_rate_limit(user_id, RateLimitTier.FREE, operation="upload")
        assert allowed is True
    
    def test_rate_limit_info_returned(self):
        """Test rate limit info is returned"""
        limiter = EnterpriseRateLimiter()
        user_id = "test_user_info"
        
        allowed, msg, info = limiter.check_rate_limit(user_id, RateLimitTier.FREE)
        
        assert 'minute_limit' in info
        assert 'hour_limit' in info
        assert 'day_limit' in info
        assert 'burst_size' in info
    
    def test_metrics_tracking(self):
        """Test metrics are tracked"""
        limiter = EnterpriseRateLimiter()
        user_id = "test_user_metrics"
        
        # Make some requests
        for i in range(3):
            limiter.check_rate_limit(user_id, RateLimitTier.FREE)
        
        # Check metrics
        metrics = limiter.get_metrics(user_id)
        assert len(metrics) > 0
        
        # Should have tracked requests
        for key, data in metrics.items():
            if user_id in key:
                assert data['total_requests'] >= 3
    
    def test_reset_user_limits(self):
        """Test resetting user limits"""
        limiter = EnterpriseRateLimiter()
        user_id = "test_user_reset"
        
        # Use up limit
        for i in range(5):
            limiter.check_rate_limit(user_id, RateLimitTier.FREE)
        
        # Should be blocked
        allowed, msg, info = limiter.check_rate_limit(user_id, RateLimitTier.FREE)
        assert allowed is False
        
        # Reset limits
        limiter.reset_user_limits(user_id)
        
        # Should be allowed again
        allowed, msg, info = limiter.check_rate_limit(user_id, RateLimitTier.FREE)
        assert allowed is True
    
    def test_concurrent_users(self):
        """Test multiple users don't interfere"""
        limiter = EnterpriseRateLimiter()
        
        # User 1 uses up their limit
        for i in range(5):
            limiter.check_rate_limit("user1", RateLimitTier.FREE)
        
        # User 2 should still have full limit
        allowed, msg, info = limiter.check_rate_limit("user2", RateLimitTier.FREE)
        assert allowed is True


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_get_rate_limiter_singleton(self):
        """Test get_rate_limiter returns singleton"""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2
    
    def test_check_rate_limit_wrapper(self):
        """Test check_rate_limit convenience function"""
        allowed, msg, info = check_rate_limit("test_user", tier="free")
        assert isinstance(allowed, bool)
        assert isinstance(info, dict)


class TestRateLimitPerformance:
    """Test rate limiter performance"""
    
    def test_check_performance(self, benchmark):
        """Benchmark rate limit check performance"""
        limiter = EnterpriseRateLimiter()
        
        def check():
            return limiter.check_rate_limit("perf_user", RateLimitTier.FREE)
        
        result = benchmark(check)
        assert result[0] is True  # First request should be allowed
    
    def test_concurrent_check_performance(self):
        """Test performance with concurrent checks"""
        import threading
        
        limiter = EnterpriseRateLimiter()
        results = []
        
        def make_request(user_id):
            allowed, msg, info = limiter.check_rate_limit(user_id, RateLimitTier.FREE)
            results.append(allowed)
        
        # Create 10 threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(f"user_{i}",))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All should have succeeded (different users)
        assert all(results)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_negative_tokens(self):
        """Test consuming negative tokens"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should handle gracefully
        try:
            allowed, msg = bucket.consume(-1)
            # Implementation dependent - either allow or reject
            assert isinstance(allowed, bool)
        except ValueError:
            # Also acceptable to raise error
            pass
    
    def test_zero_capacity_bucket(self):
        """Test bucket with zero capacity"""
        bucket = TokenBucket(capacity=0, refill_rate=1.0)
        allowed, msg = bucket.consume(1)
        assert allowed is False
    
    def test_very_high_refill_rate(self):
        """Test bucket with very high refill rate"""
        bucket = TokenBucket(capacity=100, refill_rate=1000.0)
        
        # Should handle without overflow
        bucket.consume(50)
        time.sleep(0.1)
        allowed, msg = bucket.consume(50)
        assert allowed is True
    
    def test_empty_user_id(self):
        """Test with empty user ID"""
        limiter = EnterpriseRateLimiter()
        
        # Should handle gracefully
        allowed, msg, info = limiter.check_rate_limit("", RateLimitTier.FREE)
        assert isinstance(allowed, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
