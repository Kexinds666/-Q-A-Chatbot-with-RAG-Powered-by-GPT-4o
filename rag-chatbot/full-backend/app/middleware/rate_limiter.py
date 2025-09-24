"""
Rate limiting middleware
"""

import time
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app, redis_client: redis.Redis):
        super().__init__(app)
        self.redis_client = redis_client
        self.requests_per_window = settings.RATE_LIMIT_REQUESTS
        self.window_seconds = settings.RATE_LIMIT_WINDOW
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/health"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not await self._check_rate_limit(client_id):
            logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={
                    "client_id": client_id,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "type": "RateLimitExceeded",
                        "message": "Rate limit exceeded",
                        "details": f"Maximum {self.requests_per_window} requests per {self.window_seconds} seconds"
                    }
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Window": str(self.window_seconds)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = await self._get_remaining_requests(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get user ID from JWT token if available
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # This is a simplified approach - in production, you'd decode the JWT
                # For now, we'll use IP + User-Agent as fallback
                pass
            except:
                pass
        
        # Fallback to IP + User-Agent
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        return f"{client_ip}:{hash(user_agent) % 10000}"
    
    async def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limit"""
        try:
            current_time = int(time.time())
            window_start = current_time - self.window_seconds
            
            # Use Redis sorted set for sliding window
            key = f"rate_limit:{client_id}"
            
            # Remove old entries
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            current_requests = await self.redis_client.zcard(key)
            
            if current_requests >= self.requests_per_window:
                return False
            
            # Add current request
            await self.redis_client.zadd(key, {str(current_time): current_time})
            await self.redis_client.expire(key, self.window_seconds)
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Allow request if Redis is down
            return True
    
    async def _get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client"""
        try:
            current_time = int(time.time())
            window_start = current_time - self.window_seconds
            
            key = f"rate_limit:{client_id}"
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            current_requests = await self.redis_client.zcard(key)
            
            return max(0, self.requests_per_window - current_requests)
            
        except Exception:
            return self.requests_per_window


class EndpointRateLimit:
    """Rate limiting for specific endpoints"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60
    
    async def __call__(self, request: Request):
        """Check endpoint-specific rate limit"""
        endpoint = f"{request.method}:{request.url.path}"
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not await self._check_endpoint_rate_limit(endpoint, client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {endpoint}"
            )
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier"""
        client_ip = request.client.host if request.client else "unknown"
        return client_ip
    
    async def _check_endpoint_rate_limit(self, endpoint: str, client_id: str) -> bool:
        """Check endpoint-specific rate limit"""
        # Implementation would be similar to the main rate limiter
        # but with endpoint-specific keys
        return True


def setup_rate_limiting(app: FastAPI):
    """Setup rate limiting for the application"""
    try:
        # This would be called with the Redis client from the main app
        # For now, we'll skip it and implement it in the main app
        pass
    except Exception as e:
        logger.warning(f"Failed to setup rate limiting: {e}")


# Rate limit decorators
def rate_limit(requests_per_minute: int = 60):
    """Decorator for endpoint-specific rate limiting"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Rate limiting logic would go here
            return await func(*args, **kwargs)
        return wrapper
    return decorator
