"""
Error Handling & Recovery Module
Handles graceful degradation, auto-retry, and fallback strategies
Production-ready error management for 24x7 operation
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from functools import wraps
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Non-critical, can retry
    MEDIUM = "medium"     # Affects some functionality
    HIGH = "high"         # Affects core functionality
    CRITICAL = "critical" # System down


class RetryStrategy:
    """Exponential backoff retry strategy"""

    def __init__(self, max_retries: int = 3, base_delay: int = 1):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retry_count = 0
        self.last_error = None
        self.last_error_time = None

    def should_retry(self) -> bool:
        """Check if we should retry"""
        return self.retry_count < self.max_retries

    def get_delay(self) -> int:
        """Get exponential backoff delay in seconds"""
        return self.base_delay * (2 ** self.retry_count)

    def record_error(self, error: Exception):
        """Record error and update retry count"""
        self.retry_count += 1
        self.last_error = error
        self.last_error_time = datetime.now()
        logger.warning(f"Retry {self.retry_count}/{self.max_retries}: {str(error)}")

    def reset(self):
        """Reset retry counter on success"""
        if self.retry_count > 0:
            logger.info(f"✅ Retry successful after {self.retry_count} attempts")
        self.retry_count = 0
        self.last_error = None
        self.last_error_time = None

    def get_status(self) -> Dict:
        """Get retry status"""
        return {
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_retry": self.should_retry(),
            "last_error": str(self.last_error) if self.last_error else None,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None
        }


class ApiCallHandler:
    """Handle API calls with retry and fallback"""

    def __init__(self, name: str, timeout: int = 10):
        self.name = name
        self.timeout = timeout
        self.retry_strategy = RetryStrategy(max_retries=3, base_delay=1)
        self.cache = {}
        self.cache_timestamp = {}
        self.cache_ttl = 300  # 5 minutes
        self.fallback_data = None
        self.is_degraded = False

    def set_fallback_data(self, data: Any):
        """Set fallback data for when API fails"""
        self.fallback_data = data
        logger.info(f"✅ Fallback data set for {self.name}")

    def cache_response(self, key: str, data: Any):
        """Cache API response"""
        self.cache[key] = data
        self.cache_timestamp[key] = datetime.now()
        logger.debug(f"💾 Cached {key} for {self.name}")

    def get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if still fresh"""
        if key not in self.cache:
            return None

        age = (datetime.now() - self.cache_timestamp[key]).total_seconds()
        if age > self.cache_ttl:
            logger.warning(f"⚠️  Cache expired for {key}")
            del self.cache[key]
            del self.cache_timestamp[key]
            return None

        logger.debug(f"✅ Using cached data for {key}")
        return self.cache[key]

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Optional[Any]:
        """Execute API call with automatic retry"""
        while self.retry_strategy.should_retry():
            try:
                result = func(*args, **kwargs)
                self.retry_strategy.reset()
                self.is_degraded = False
                return result
            except Exception as e:
                self.retry_strategy.record_error(e)

                if not self.retry_strategy.should_retry():
                    logger.error(f"❌ All retries exhausted for {self.name}")
                    self.is_degraded = True
                    break

                delay = self.retry_strategy.get_delay()
                logger.info(f"⏳ Retrying in {delay}s...")
                time.sleep(delay)

        # Return fallback if available
        if self.fallback_data is not None:
            logger.warning(f"⚠️  Using fallback data for {self.name}")
            return self.fallback_data

        return None

    def get_status(self) -> Dict:
        """Get handler status"""
        return {
            "name": self.name,
            "is_degraded": self.is_degraded,
            "cached_keys": list(self.cache.keys()),
            "retry_status": self.retry_strategy.get_status(),
            "has_fallback": self.fallback_data is not None
        }


class ConnectionRecovery:
    """Automatic connection recovery handler"""

    def __init__(self, max_attempts: int = 5, backoff_multiplier: float = 1.5):
        self.max_attempts = max_attempts
        self.backoff_multiplier = backoff_multiplier
        self.attempt = 0
        self.last_successful_connection = None
        self.reconnect_scheduled = False

    def record_connection_failure(self, error: Exception) -> bool:
        """Record connection failure, return True if should retry"""
        self.attempt += 1
        logger.error(f"Connection failure #{self.attempt}: {str(error)}")

        if self.attempt >= self.max_attempts:
            logger.critical(f"❌ Max connection attempts ({self.max_attempts}) exceeded")
            return False

        return True

    def record_successful_connection(self):
        """Record successful connection"""
        self.attempt = 0
        self.last_successful_connection = datetime.now()
        self.reconnect_scheduled = False
        logger.info("✅ Connection re-established")

    def get_backoff_delay(self) -> int:
        """Get exponential backoff delay"""
        delay = int(1 * (self.backoff_multiplier ** (self.attempt - 1)))
        return min(delay, 300)  # Cap at 5 minutes

    def get_status(self) -> Dict:
        """Get recovery status"""
        return {
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "can_retry": self.attempt < self.max_attempts,
            "next_backoff_delay": self.get_backoff_delay(),
            "last_successful": self.last_successful_connection.isoformat() if self.last_successful_connection else None,
            "reconnect_scheduled": self.reconnect_scheduled
        }


def retry_on_failure(max_retries: int = 3, backoff: int = 1, exceptions: tuple = (Exception,)):
    """Decorator for automatic retry on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_retries - 1:
                        delay = backoff * (2 ** attempt)
                        logger.warning(f"⚠️  Retry {attempt + 1}/{max_retries} for {func.__name__} after {delay}s")
                        time.sleep(delay)
                    else:
                        logger.error(f"❌ All retries failed for {func.__name__}")
                        raise
            return None
        return wrapper
    return decorator


def handle_api_error(severity: ErrorSeverity, fallback: Any = None):
    """Decorator for API error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"API Error ({severity.value}): {func.__name__} - {str(e)}")

                if severity == ErrorSeverity.CRITICAL:
                    # Log and re-raise critical errors
                    logger.critical(f"CRITICAL API ERROR: {str(e)}")
                    raise
                elif severity in [ErrorSeverity.HIGH, ErrorSeverity.MEDIUM]:
                    # Log but return fallback for non-critical
                    logger.warning(f"Returning fallback for {func.__name__}")
                    return fallback
                else:
                    # For low severity, just log and return fallback
                    logger.info(f"Low severity error, returning fallback")
                    return fallback
        return wrapper
    return decorator


class ErrorMetrics:
    """Track error metrics for monitoring"""

    def __init__(self):
        self.error_count = 0
        self.error_by_type = {}
        self.error_by_severity = {s.value: 0 for s in ErrorSeverity}
        self.last_error_time = None
        self.recovery_attempts = 0
        self.successful_recoveries = 0

    def record_error(self, error: Exception, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        """Record an error"""
        self.error_count += 1
        self.last_error_time = datetime.now()
        self.error_by_severity[severity.value] += 1

        error_type = type(error).__name__
        self.error_by_type[error_type] = self.error_by_type.get(error_type, 0) + 1

        logger.info(f"Error recorded: {error_type} ({severity.value})")

    def record_recovery_attempt(self, success: bool):
        """Record recovery attempt"""
        self.recovery_attempts += 1
        if success:
            self.successful_recoveries += 1

    def get_metrics(self) -> Dict:
        """Get error metrics"""
        recovery_rate = (
            (self.successful_recoveries / self.recovery_attempts * 100)
            if self.recovery_attempts > 0
            else 0
        )

        return {
            "total_errors": self.error_count,
            "errors_by_type": self.error_by_type,
            "errors_by_severity": self.error_by_severity,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "recovery_attempts": self.recovery_attempts,
            "successful_recoveries": self.successful_recoveries,
            "recovery_rate_percent": round(recovery_rate, 2)
        }


# Global error metrics instance
error_metrics = ErrorMetrics()
