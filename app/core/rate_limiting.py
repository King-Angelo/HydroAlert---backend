import time
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """In-memory rate limiter for API endpoints"""
    
    def __init__(self):
        # Store request counts and timestamps
        self.request_counts: Dict[str, Dict[str, float]] = {}
        self.cleanup_interval = 300  # Clean up old entries every 5 minutes
        self.last_cleanup = time.time()
    
    def _get_client_identifier(self, request: Request, user_id: Optional[int] = None) -> str:
        """Get unique identifier for rate limiting"""
        if user_id:
            return f"user:{user_id}"
        else:
            # Use IP address for unauthenticated requests
            client_ip = request.client.host
            # Handle forwarded IPs (e.g., from load balancers)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            return f"ip:{client_ip}"
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory leaks"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - 3600  # Remove entries older than 1 hour
        
        for client_id in list(self.request_counts.keys()):
            client_data = self.request_counts[client_id]
            # Remove old timestamps
            self.request_counts[client_id] = {
                endpoint: timestamp for endpoint, timestamp in client_data.items()
                if isinstance(timestamp, (int, float)) and timestamp > cutoff_time
            }
            # Remove empty client entries
            if not self.request_counts[client_id]:
                del self.request_counts[client_id]
        
        self.last_cleanup = current_time
    
    def _is_rate_limited(
        self, 
        client_id: str, 
        endpoint: str, 
        max_requests: int, 
        window_seconds: int
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if client is rate limited for specific endpoint
        
        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Initialize client data if not exists
        if client_id not in self.request_counts:
            self.request_counts[client_id] = {}
        
        # Get existing requests for this endpoint
        client_data = self.request_counts[client_id]
        endpoint_requests = [
            timestamp for timestamp in client_data.get(endpoint, [])
            if timestamp > window_start
        ]
        
        # Add current request
        endpoint_requests.append(current_time)
        self.request_counts[client_id][endpoint] = endpoint_requests
        
        # Check if rate limit exceeded
        is_limited = len(endpoint_requests) > max_requests
        
        # Calculate rate limit info
        remaining_requests = max(0, max_requests - len(endpoint_requests))
        reset_time = int(window_start + window_seconds)
        
        rate_limit_info = {
            "limit": max_requests,
            "remaining": remaining_requests,
            "reset": reset_time,
            "retry_after": max(0, reset_time - int(current_time)) if is_limited else 0
        }
        
        return is_limited, rate_limit_info
    
    def check_rate_limit(
        self, 
        request: Request, 
        endpoint: str,
        max_requests: int,
        window_seconds: int,
        user_id: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Check rate limit for request
        
        Args:
            request: FastAPI request object
            endpoint: Endpoint identifier for rate limiting
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            user_id: Optional user ID for authenticated requests
            
        Returns:
            Rate limit information dict
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        # Get client identifier
        client_id = self._get_client_identifier(request, user_id)
        
        # Check rate limit
        is_limited, rate_limit_info = self._is_rate_limited(
            client_id, endpoint, max_requests, window_seconds
        )
        
        if is_limited:
            logger.warning(
                f"Rate limit exceeded for {client_id} on {endpoint}: "
                f"{len(self.request_counts[client_id][endpoint])} requests in {window_seconds}s"
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {max_requests} per {window_seconds} seconds",
                    "retry_after": rate_limit_info["retry_after"]
                },
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_limit_info["reset"]),
                    "Retry-After": str(rate_limit_info["retry_after"])
                }
            )
        
        return rate_limit_info

# Global rate limiter instance
rate_limiter = RateLimiter()

# Rate limit policies
RATE_LIMIT_POLICIES = {
    # Public endpoints (unauthenticated)
    "public": {
        "max_requests": 10,
        "window_seconds": 60  # 10 requests per minute
    },
    # Authenticated user endpoints
    "authenticated": {
        "max_requests": 60,
        "window_seconds": 60  # 60 requests per minute
    },
    # Admin endpoints
    "admin": {
        "max_requests": 120,
        "window_seconds": 60  # 120 requests per minute
    },
    # File upload endpoints (more restrictive)
    "file_upload": {
        "max_requests": 5,
        "window_seconds": 60  # 5 uploads per minute
    },
    # Authentication endpoints (very restrictive)
    "auth": {
        "max_requests": 5,
        "window_seconds": 300  # 5 attempts per 5 minutes
    }
}

def get_rate_limit_policy(endpoint_type: str) -> Dict[str, int]:
    """Get rate limit policy for endpoint type"""
    return RATE_LIMIT_POLICIES.get(endpoint_type, RATE_LIMIT_POLICIES["authenticated"])

def create_rate_limit_dependency(endpoint_type: str):
    """Create FastAPI dependency for rate limiting"""
    policy = get_rate_limit_policy(endpoint_type)
    
    async def rate_limit_dependency(request: Request):
        try:
            rate_limit_info = rate_limiter.check_rate_limit(
                request=request,
                endpoint=f"{endpoint_type}:{request.url.path}",
                max_requests=policy["max_requests"],
                window_seconds=policy["window_seconds"]
            )
            
            # Add rate limit headers to response
            response = JSONResponse(
                content={"rate_limit": rate_limit_info},
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_limit_info["reset"])
                }
            )
            return response
            
        except HTTPException as e:
            # Re-raise rate limit exceptions
            raise e
    
    return rate_limit_dependency

def create_authenticated_rate_limit_dependency(endpoint_type: str):
    """Create FastAPI dependency for rate limiting with user authentication"""
    policy = get_rate_limit_policy(endpoint_type)
    
    async def authenticated_rate_limit_dependency(
        request: Request,
        current_user = None  # Will be injected by FastAPI
    ):
        try:
            user_id = current_user.id if current_user else None
            rate_limit_info = rate_limiter.check_rate_limit(
                request=request,
                endpoint=f"{endpoint_type}:{request.url.path}",
                max_requests=policy["max_requests"],
                window_seconds=policy["window_seconds"],
                user_id=user_id
            )
            
            return rate_limit_info
            
        except HTTPException as e:
            # Re-raise rate limit exceptions
            raise e
    
    return authenticated_rate_limit_dependency
