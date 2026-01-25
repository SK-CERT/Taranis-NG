"""Cache manager module for Redis operations."""

import os

import redis

# Redis client for caching (works across multiple workers/processes)
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis"), decode_responses=False)


def initialize(app: object) -> None:
    """Initialize the Redis cache with the given Flask application.

    This function can be used to perform any Redis-specific initialization
    if needed in the future.

    Args:
        app (Flask): The Flask application instance.
    """
    # Redis client is already initialized at module level
    # This function is here for consistency with other managers
