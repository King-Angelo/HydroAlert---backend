import logging
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from app.core.config import settings

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)

class APILoggingFilter(logging.Filter):
    """Filter to add API-specific context to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add request context if available
        if hasattr(record, 'request_id'):
            record.request_id = getattr(record, 'request_id', None)
        if hasattr(record, 'user_id'):
            record.user_id = getattr(record, 'user_id', None)
        if hasattr(record, 'endpoint'):
            record.endpoint = getattr(record, 'endpoint', None)
        if hasattr(record, 'method'):
            record.method = getattr(record, 'method', None)
        if hasattr(record, 'status_code'):
            record.status_code = getattr(record, 'status_code', None)
        if hasattr(record, 'duration_ms'):
            record.duration_ms = getattr(record, 'duration_ms', None)
        
        return True

def setup_logging():
    """Configure structured logging for the application"""
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = StructuredFormatter()
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(APILoggingFilter())
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.FileHandler(logs_dir / "app.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = StructuredFormatter()
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(APILoggingFilter())
    root_logger.addHandler(file_handler)
    
    # Error file handler for errors and above
    error_handler = logging.FileHandler(logs_dir / "errors.log")
    error_handler.setLevel(logging.ERROR)
    error_formatter = StructuredFormatter()
    error_handler.setFormatter(error_formatter)
    error_handler.addFilter(APILoggingFilter())
    root_logger.addHandler(error_handler)
    
    # API-specific logger for request/response logging
    api_logger = logging.getLogger("api")
    api_handler = logging.FileHandler(logs_dir / "api.log")
    api_handler.setLevel(logging.INFO)
    api_formatter = StructuredFormatter()
    api_handler.setFormatter(api_formatter)
    api_handler.addFilter(APILoggingFilter())
    api_logger.addHandler(api_handler)
    api_logger.propagate = False  # Don't propagate to root logger
    
    # WebSocket logger for connection events
    ws_logger = logging.getLogger("websocket")
    ws_handler = logging.FileHandler(logs_dir / "websocket.log")
    ws_handler.setLevel(logging.INFO)
    ws_formatter = StructuredFormatter()
    ws_handler.setFormatter(ws_formatter)
    ws_handler.addFilter(APILoggingFilter())
    ws_logger.addHandler(ws_handler)
    ws_logger.propagate = False
    
    # Performance logger for metrics
    perf_logger = logging.getLogger("performance")
    perf_handler = logging.FileHandler(logs_dir / "performance.log")
    perf_handler.setLevel(logging.INFO)
    perf_formatter = StructuredFormatter()
    perf_handler.setFormatter(perf_formatter)
    perf_handler.addFilter(APILoggingFilter())
    perf_logger.addHandler(perf_handler)
    perf_logger.propagate = False
    
    # Security logger for security events
    security_logger = logging.getLogger("security")
    security_handler = logging.FileHandler(logs_dir / "security.log")
    security_handler.setLevel(logging.WARNING)
    security_formatter = StructuredFormatter()
    security_handler.setFormatter(security_formatter)
    security_handler.addFilter(APILoggingFilter())
    security_logger.addHandler(security_handler)
    security_logger.propagate = False

class MetricsLogger:
    """Logger for application metrics and performance data"""
    
    def __init__(self):
        self.logger = logging.getLogger("performance")
        self.start_times: Dict[str, float] = {}
    
    def start_timer(self, operation_id: str):
        """Start timing an operation"""
        self.start_times[operation_id] = time.time()
    
    def end_timer(self, operation_id: str, **extra_data):
        """End timing an operation and log the duration"""
        if operation_id in self.start_times:
            duration_ms = (time.time() - self.start_times[operation_id]) * 1000
            del self.start_times[operation_id]
            
            self.logger.info(
                f"Operation completed: {operation_id}",
                extra={
                    "operation_id": operation_id,
                    "duration_ms": round(duration_ms, 2),
                    **extra_data
                }
            )
    
    def log_api_request(
        self, 
        method: str, 
        endpoint: str, 
        status_code: int, 
        duration_ms: float,
        user_id: Optional[int] = None,
        request_id: Optional[str] = None
    ):
        """Log API request metrics"""
        self.logger.info(
            f"API request: {method} {endpoint}",
            extra={
                "event_type": "api_request",
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "user_id": user_id,
                "request_id": request_id
            }
        )
    
    def log_websocket_connection(
        self, 
        event_type: str, 
        user_id: Optional[int] = None,
        connection_count: Optional[int] = None
    ):
        """Log WebSocket connection events"""
        self.logger.info(
            f"WebSocket {event_type}",
            extra={
                "event_type": f"websocket_{event_type}",
                "user_id": user_id,
                "connection_count": connection_count
            }
        )
    
    def log_triage_time(
        self, 
        report_id: int, 
        submission_time: datetime, 
        triage_time: datetime,
        triaged_by: int
    ):
        """Log report triage timing"""
        duration_seconds = (triage_time - submission_time).total_seconds()
        duration_minutes = duration_seconds / 60
        
        self.logger.info(
            f"Report triaged: {report_id}",
            extra={
                "event_type": "report_triage",
                "report_id": report_id,
                "triage_duration_seconds": round(duration_seconds, 2),
                "triage_duration_minutes": round(duration_minutes, 2),
                "submission_time": submission_time.isoformat(),
                "triage_time": triage_time.isoformat(),
                "triaged_by": triaged_by
            }
        )
    
    def log_file_upload(
        self, 
        file_size: int, 
        file_type: str, 
        storage_type: str,
        duration_ms: float,
        user_id: Optional[int] = None
    ):
        """Log file upload metrics"""
        self.logger.info(
            f"File uploaded: {file_type}",
            extra={
                "event_type": "file_upload",
                "file_size_bytes": file_size,
                "file_type": file_type,
                "storage_type": storage_type,
                "duration_ms": round(duration_ms, 2),
                "user_id": user_id
            }
        )

# Global metrics logger instance
metrics_logger = MetricsLogger()

# Initialize logging when module is imported
setup_logging()
