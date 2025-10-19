"""
Rate Limiter
Provides rate limiting functionality to prevent abuse of expensive API calls
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import DefaultDict, List

from loguru import logger


class RateLimiter:
    """
    Rate limiter using sliding window algorithm

    Tracks requests per user and enforces limits based on configurable window and max requests.
    Thread-safe using asyncio locks.

    Example:
        rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
        if not await rate_limiter.acquire(user_id):
            # Rate limited
            return
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum number of requests allowed within the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self._requests: DefaultDict[int, List[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()
        logger.info(
            f"RateLimiter initialized: {max_requests} requests per {window_seconds}s window"
        )

    async def acquire(self, user_id: int) -> bool:
        """
        Try to acquire rate limit token for a user

        Args:
            user_id: User ID

        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = datetime.now()

            # Clean old requests outside the window
            cutoff_time = now - self.window
            self._requests[user_id] = [
                request_time
                for request_time in self._requests[user_id]
                if request_time > cutoff_time
            ]

            # Check if under limit
            if len(self._requests[user_id]) >= self.max_requests:
                logger.warning(
                    f"Rate limit exceeded for user {user_id}: "
                    f"{len(self._requests[user_id])}/{self.max_requests} requests in window"
                )
                return False

            # Allow request and record it
            self._requests[user_id].append(now)
            logger.debug(
                f"Rate limit check passed for user {user_id}: "
                f"{len(self._requests[user_id])}/{self.max_requests} requests"
            )
            return True

    async def get_remaining(self, user_id: int) -> int:
        """
        Get remaining requests for a user within current window

        Args:
            user_id: User ID

        Returns:
            Number of remaining requests
        """
        async with self._lock:
            now = datetime.now()
            cutoff_time = now - self.window

            # Count valid requests in window
            valid_requests = [
                request_time
                for request_time in self._requests[user_id]
                if request_time > cutoff_time
            ]

            return max(0, self.max_requests - len(valid_requests))

    async def get_reset_time(self, user_id: int) -> datetime:
        """
        Get time when rate limit will reset for a user

        Args:
            user_id: User ID

        Returns:
            Datetime when the oldest request will expire
        """
        async with self._lock:
            if not self._requests[user_id]:
                return datetime.now()

            # Clean old requests
            now = datetime.now()
            cutoff_time = now - self.window
            valid_requests = [
                request_time
                for request_time in self._requests[user_id]
                if request_time > cutoff_time
            ]

            if not valid_requests:
                return now

            # Reset time is when the oldest request expires
            oldest_request = min(valid_requests)
            return oldest_request + self.window

    async def reset_user(self, user_id: int) -> None:
        """
        Reset rate limit for a specific user (admin function)

        Args:
            user_id: User ID
        """
        async with self._lock:
            if user_id in self._requests:
                del self._requests[user_id]
                logger.info(f"Rate limit reset for user {user_id}")

    async def get_stats(self) -> dict:
        """
        Get rate limiter statistics

        Returns:
            Dictionary with statistics
        """
        async with self._lock:
            now = datetime.now()
            cutoff_time = now - self.window

            total_users = len(self._requests)
            active_users = 0
            total_requests = 0

            for user_id, requests in self._requests.items():
                valid_requests = [req for req in requests if req > cutoff_time]
                if valid_requests:
                    active_users += 1
                    total_requests += len(valid_requests)

            return {
                "total_users_tracked": total_users,
                "active_users_in_window": active_users,
                "total_requests_in_window": total_requests,
                "max_requests_per_window": self.max_requests,
                "window_seconds": self.window.total_seconds(),
            }
