"""
Monitoring & Logging Module
Structured logging, performance metrics, and observability
Production-ready monitoring for 24x7 operation
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import os

# Configure structured JSON logging
class JsonFormatter(logging.Formatter):
    """Format logs as JSON for easier parsing"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        # Add custom fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


def setup_logging(app_name: str = "tradosphere", log_level: str = "INFO"):
    """Setup structured logging for the application"""

    # Create logs directory if it doesn't exist
    log_dir = "/var/log/tradosphere"
    os.makedirs(log_dir, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # File handler - structured JSON logs
    file_handler = logging.FileHandler(f"{log_dir}/tradosphere.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(file_handler)

    # Error file handler - errors only
    error_handler = logging.FileHandler(f"{log_dir}/tradosphere-errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(error_handler)

    # Console handler - human-readable
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Get app logger
    logger = logging.getLogger(app_name)
    logger.info(f"✅ Logging initialized for {app_name}")

    return logger


# Module-level logger
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor performance metrics"""

    def __init__(self):
        self.metrics = {}
        self.endpoint_times = {}
        self.database_query_times = {}
        self.api_call_times = {}

    def record_endpoint_call(self, endpoint: str, method: str, duration_ms: float, status_code: int):
        """Record API endpoint call"""
        key = f"{method} {endpoint}"

        if key not in self.endpoint_times:
            self.endpoint_times[key] = {
                "count": 0,
                "total_time": 0,
                "min_time": float('inf'),
                "max_time": 0,
                "errors": 0
            }

        metric = self.endpoint_times[key]
        metric["count"] += 1
        metric["total_time"] += duration_ms
        metric["min_time"] = min(metric["min_time"], duration_ms)
        metric["max_time"] = max(metric["max_time"], duration_ms)

        if status_code >= 400:
            metric["errors"] += 1

        logger.debug(f"📊 Endpoint {key}: {duration_ms}ms (status: {status_code})")

    def record_database_query(self, query_type: str, duration_ms: float, success: bool = True):
        """Record database query"""
        if query_type not in self.database_query_times:
            self.database_query_times[query_type] = {
                "count": 0,
                "total_time": 0,
                "min_time": float('inf'),
                "max_time": 0,
                "failures": 0
            }

        metric = self.database_query_times[query_type]
        metric["count"] += 1
        metric["total_time"] += duration_ms
        metric["min_time"] = min(metric["min_time"], duration_ms)
        metric["max_time"] = max(metric["max_time"], duration_ms)

        if not success:
            metric["failures"] += 1

        logger.debug(f"🗄️  Query {query_type}: {duration_ms}ms")

    def record_api_call(self, api_name: str, duration_ms: float, success: bool = True):
        """Record external API call"""
        if api_name not in self.api_call_times:
            self.api_call_times[api_name] = {
                "count": 0,
                "total_time": 0,
                "min_time": float('inf'),
                "max_time": 0,
                "failures": 0
            }

        metric = self.api_call_times[api_name]
        metric["count"] += 1
        metric["total_time"] += duration_ms
        metric["min_time"] = min(metric["min_time"], duration_ms)
        metric["max_time"] = max(metric["max_time"], duration_ms)

        if not success:
            metric["failures"] += 1

        logger.debug(f"🔗 API {api_name}: {duration_ms}ms")

    def get_endpoint_metrics(self) -> Dict[str, Any]:
        """Get endpoint performance metrics"""
        metrics = {}
        for endpoint, data in self.endpoint_times.items():
            avg_time = data["total_time"] / data["count"] if data["count"] > 0 else 0
            error_rate = (data["errors"] / data["count"] * 100) if data["count"] > 0 else 0

            metrics[endpoint] = {
                "count": data["count"],
                "avg_time_ms": round(avg_time, 2),
                "min_time_ms": round(data["min_time"], 2),
                "max_time_ms": round(data["max_time"], 2),
                "error_rate_percent": round(error_rate, 2)
            }

        return metrics

    def get_database_metrics(self) -> Dict[str, Any]:
        """Get database query metrics"""
        metrics = {}
        for query_type, data in self.database_query_times.items():
            avg_time = data["total_time"] / data["count"] if data["count"] > 0 else 0
            failure_rate = (data["failures"] / data["count"] * 100) if data["count"] > 0 else 0

            metrics[query_type] = {
                "count": data["count"],
                "avg_time_ms": round(avg_time, 2),
                "min_time_ms": round(data["min_time"], 2),
                "max_time_ms": round(data["max_time"], 2),
                "failure_rate_percent": round(failure_rate, 2)
            }

        return metrics

    def get_api_metrics(self) -> Dict[str, Any]:
        """Get external API call metrics"""
        metrics = {}
        for api_name, data in self.api_call_times.items():
            avg_time = data["total_time"] / data["count"] if data["count"] > 0 else 0
            failure_rate = (data["failures"] / data["count"] * 100) if data["count"] > 0 else 0

            metrics[api_name] = {
                "count": data["count"],
                "avg_time_ms": round(avg_time, 2),
                "min_time_ms": round(data["min_time"], 2),
                "max_time_ms": round(data["max_time"], 2),
                "failure_rate_percent": round(failure_rate, 2)
            }

        return metrics

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics"""
        return {
            "endpoints": self.get_endpoint_metrics(),
            "database": self.get_database_metrics(),
            "external_apis": self.get_api_metrics(),
            "generated_at": datetime.utcnow().isoformat()
        }


class RequestLogger:
    """Log HTTP requests and responses"""

    @staticmethod
    def log_request(method: str, path: str, user_id: Optional[str] = None):
        """Log incoming request"""
        logger.info(f"📥 {method} {path}", extra={
            "extra_data": {
                "method": method,
                "path": path,
                "user_id": user_id,
                "type": "http_request"
            }
        })

    @staticmethod
    def log_response(method: str, path: str, status_code: int, duration_ms: float):
        """Log response"""
        logger.info(f"📤 {method} {path} -> {status_code} ({duration_ms}ms)", extra={
            "extra_data": {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "type": "http_response"
            }
        })


def log_execution_time(logger_instance=None):
    """Decorator to log function execution time"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            func_logger = logger_instance or logging.getLogger(func.__module__)

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                func_logger.info(f"✅ {func.__name__} completed in {duration_ms:.2f}ms")
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                func_logger.error(f"❌ {func.__name__} failed after {duration_ms:.2f}ms: {str(e)}")
                raise

        return wrapper
    return decorator


def log_database_operation(operation: str):
    """Decorator to log database operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            func_logger = logging.getLogger(func.__module__)

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                func_logger.debug(f"🗄️  {operation} succeeded in {duration_ms:.2f}ms")
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                func_logger.error(f"❌ {operation} failed: {str(e)}")
                raise

        return wrapper
    return decorator


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
