from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.rate_limiting import rate_limiter, get_rate_limit_policy
import logging
import time

logger = logging.getLogger(__name__)

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for applying rate limiting to all requests"""
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for health checks and static files
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Determine rate limit policy based on endpoint
        endpoint_type = self._get_endpoint_type(request)
        policy = get_rate_limit_policy(endpoint_type)
        
        try:
            # Check rate limit
            rate_limit_info = rate_limiter.check_rate_limit(
                request=request,
                endpoint=f"{endpoint_type}:{request.url.path}",
                max_requests=policy["max_requests"],
                window_seconds=policy["window_seconds"]
            )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])
            
            return response
            
        except Exception as e:
            # Handle rate limit exceeded
            if hasattr(e, 'status_code') and e.status_code == 429:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": str(e.detail),
                        "retry_after": e.headers.get("Retry-After", 60)
                    },
                    headers={
                        "X-RateLimit-Limit": str(policy["max_requests"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + policy["window_seconds"]),
                        "Retry-After": str(policy["window_seconds"])
                    }
                )
            else:
                # Re-raise other exceptions
                raise e
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Determine if rate limiting should be skipped for this request"""
        skip_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/static/",
            "/assets/"
        ]
        
        path = request.url.path
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _get_endpoint_type(self, request: Request) -> str:
        """Determine endpoint type for rate limiting policy"""
        path = request.url.path
        
        # Authentication endpoints
        if path.startswith("/auth/"):
            return "auth"
        
        # File upload endpoints
        if "/upload" in path or "/submit" in path:
            return "file_upload"
        
        # Admin endpoints
        if path.startswith("/api/admin/"):
            return "admin"
        
        # Mobile API endpoints (authenticated)
        if path.startswith("/api/mobile/"):
            return "authenticated"
        
        # Web API endpoints (authenticated)
        if path.startswith("/api/web/"):
            return "authenticated"
        
        # Map API endpoints (authenticated)
        if path.startswith("/api/map/"):
            return "authenticated"
        
        # WebSocket endpoints (authenticated)
        if path.startswith("/ws/"):
            return "authenticated"
        
        # Default to public for other endpoints
        return "public"
