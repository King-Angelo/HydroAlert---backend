import time
import uuid
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging_config import metrics_logger
import logging

logger = logging.getLogger(__name__)

class APILoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging API requests and responses"""
    
    def __init__(self, app):
        super().__init__(app)
        self.api_logger = logging.getLogger("api")
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract request information
        method = request.method
        url = str(request.url)
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        # Get user ID if available (from authentication)
        user_id = getattr(request.state, 'user_id', None)
        
        # Log request start
        self.api_logger.info(
            f"Request started: {method} {path}",
            extra={
                "request_id": request_id,
                "method": method,
                "url": url,
                "path": path,
                "client_ip": client_ip,
                "user_id": user_id,
                "event_type": "request_start"
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request completion
            self.api_logger.info(
                f"Request completed: {method} {path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "path": path,
                    "client_ip": client_ip,
                    "user_id": user_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "event_type": "request_complete"
                }
            )
            
            # Log metrics for mobile API endpoints
            if path.startswith("/api/mobile/"):
                metrics_logger.log_api_request(
                    method=method,
                    endpoint=path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    user_id=user_id,
                    request_id=request_id
                )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request error
            self.api_logger.error(
                f"Request failed: {method} {path} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "path": path,
                    "client_ip": client_ip,
                    "user_id": user_id,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "event_type": "request_error"
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise e

class WebSocketLoggingMiddleware:
    """Middleware for logging WebSocket connection events"""
    
    def __init__(self):
        self.ws_logger = logging.getLogger("websocket")
        self.connection_count = 0
    
    def log_connection(self, user_id: Optional[int] = None, endpoint: str = ""):
        """Log WebSocket connection"""
        self.connection_count += 1
        self.ws_logger.info(
            f"WebSocket connected: {endpoint}",
            extra={
                "event_type": "websocket_connect",
                "user_id": user_id,
                "endpoint": endpoint,
                "connection_count": self.connection_count
            }
        )
        
        # Log metrics
        metrics_logger.log_websocket_connection(
            event_type="connect",
            user_id=user_id,
            connection_count=self.connection_count
        )
    
    def log_disconnection(self, user_id: Optional[int] = None, endpoint: str = ""):
        """Log WebSocket disconnection"""
        self.connection_count = max(0, self.connection_count - 1)
        self.ws_logger.info(
            f"WebSocket disconnected: {endpoint}",
            extra={
                "event_type": "websocket_disconnect",
                "user_id": user_id,
                "endpoint": endpoint,
                "connection_count": self.connection_count
            }
        )
        
        # Log metrics
        metrics_logger.log_websocket_connection(
            event_type="disconnect",
            user_id=user_id,
            connection_count=self.connection_count
        )
    
    def log_connection_stats(self):
        """Log periodic connection statistics"""
        self.ws_logger.info(
            f"WebSocket connection stats: {self.connection_count} active",
            extra={
                "event_type": "websocket_stats",
                "connection_count": self.connection_count
            }
        )

# Global WebSocket logging middleware instance
ws_logging_middleware = WebSocketLoggingMiddleware()
