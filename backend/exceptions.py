"""
Custom Exception Classes for Tradosphere V3.1
Provides structured error handling with proper HTTP status codes
"""

import logging

logger = logging.getLogger(__name__)


class TradosphereException(Exception):
    """Base exception class for all Tradosphere errors"""

    status_code = 500
    error_code = "INTERNAL_ERROR"
    message = "An internal error occurred"

    def __init__(self, message=None, error_code=None, status_code=None, details=None):
        if message:
            self.message = message
        if error_code:
            self.error_code = error_code
        if status_code:
            self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self):
        """Convert exception to dictionary for JSON response"""
        return {
            "error": self.message,
            "code": self.error_code,
            "status_code": self.status_code,
            "details": self.details
        }


# Authentication Errors
class AuthenticationError(TradosphereException):
    """User authentication failed"""
    status_code = 401
    error_code = "AUTH_FAILED"
    message = "Authentication failed"


class TokenExpiredError(AuthenticationError):
    """JWT token has expired"""
    error_code = "TOKEN_EXPIRED"
    message = "Your session has expired. Please login again."


class InvalidTokenError(AuthenticationError):
    """JWT token is invalid"""
    error_code = "INVALID_TOKEN"
    message = "Invalid authentication token"


# Authorization Errors
class AuthorizationError(TradosphereException):
    """User is not authorized"""
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission"


# Validation Errors
class ValidationError(TradosphereException):
    """Input validation failed"""
    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Invalid input data"


# Resource Errors
class ResourceNotFoundError(TradosphereException):
    """Resource not found"""
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


# Broker Connection Errors
class BrokerConnectionError(TradosphereException):
    """Failed to connect to broker"""
    status_code = 503
    error_code = "BROKER_CONNECTION_ERROR"
    message = "Unable to connect to market data broker"


class MarketDataUnavailableError(BrokerConnectionError):
    """Market data unavailable"""
    error_code = "MARKET_DATA_UNAVAILABLE"
    message = "Market data is temporarily unavailable"


# Database Errors
class DatabaseError(TradosphereException):
    """Database operation failed"""
    status_code = 500
    error_code = "DATABASE_ERROR"
    message = "Database operation failed"


# Trading Errors
class TradingError(TradosphereException):
    """Trading operation failed"""
    status_code = 400
    error_code = "TRADING_ERROR"
    message = "Trading operation failed"


class InsufficientFundsError(TradingError):
    """Insufficient funds"""
    error_code = "INSUFFICIENT_FUNDS"
    message = "Insufficient funds to execute this trade"


# AI/Analysis Errors
class AnalysisError(TradosphereException):
    """Analysis operation failed"""
    status_code = 503
    error_code = "ANALYSIS_ERROR"
    message = "Analysis service is temporarily unavailable"


# Duplicate Errors
class DuplicateError(TradosphereException):
    """Resource already exists"""
    status_code = 409
    error_code = "DUPLICATE_RESOURCE"
    message = "Resource already exists"


def handle_exception(error, context="unknown"):
    """Log exception with context"""
    if isinstance(error, TradosphereException):
        logger.warning(
            f"Tradosphere error in {context}: {error.message}",
            extra={
                "error_code": error.error_code,
                "status_code": error.status_code
            }
        )
    else:
        logger.error(
            f"Unexpected error in {context}: {str(error)}",
            exc_info=True
        )
