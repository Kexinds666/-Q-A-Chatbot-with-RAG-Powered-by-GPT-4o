"""
Rate limiting middleware
"""

import time
from typing import Dict
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class RateLimiterMiddleware:
    """Rate limiting middleware"""
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.max_requests = settings.RATE_LIMIT_REQUESTS
        self.window_seconds = settings.RATE_LIMIT_WINDOW
    
    async def __call__(self, request: Request, call_next):
        """Rate limiting logic"""
        # Get client IP
        client_ip = request.client.host
        
        # Get current time
        current_time = time.time()
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < self.window_seconds
            ]
        else:
            self.requests[client_ip] = []
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                requests_count=len(self.requests[client_ip])
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.max_requests} per {self.window_seconds} seconds"
                }
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        return response
