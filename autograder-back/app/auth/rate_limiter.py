from datetime import datetime, timedelta
from typing import Dict
from app.config import settings
from app.redis_client import get_redis_client


class RateLimiter:
    """Rate limiter for login attempts using Redis"""

    def __init__(self):
        self.redis = get_redis_client()
        self.max_attempts = settings.rate_limit_failed_logins
        self.window_minutes = settings.rate_limit_window_minutes

    def _get_key(self, identifier: str) -> str:
        """Generate Redis key for rate limiting"""
        return f"rate_limit:login:{identifier}"

    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is currently blocked"""
        key = self._get_key(identifier)
        attempts = self.redis.get(key)
        if attempts is None:
            return False
        return int(attempts) >= self.max_attempts

    def record_failed_attempt(self, identifier: str) -> int:
        """Record a failed login attempt and return current count"""
        key = self._get_key(identifier)
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window_minutes * 60)
        result = pipe.execute()
        return result[0]

    def reset(self, identifier: str):
        """Reset rate limit for identifier (after successful login)"""
        key = self._get_key(identifier)
        self.redis.delete(key)

    def get_attempts(self, identifier: str) -> int:
        """Get current number of attempts"""
        key = self._get_key(identifier)
        attempts = self.redis.get(key)
        return int(attempts) if attempts else 0


rate_limiter = RateLimiter()
