"""
Error Handling Middleware for Tradosphere V3.1
Catches all exceptions and returns properly formatted error responses
"""

import logging
import time
from flask import jsonify, request, g
from werkzeug.exceptions import HTTPException
from exceptions import TradosphereException, handle_exception
from response_handler import APIResponse

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Register all error handlers with Flask app"""

    @app.errorhandler(TradosphereException)
    def handle_tradosphere_exception(error):
        """Handle custom Tradosphere exceptions.

        AUDIT FIX #6: return the SAME standardized envelope as every other
        endpoint (status/data/error{code,message}/timestamp) so clients can
        parse error.code uniformly. Previously this returned a divergent shape
        ({error: <string>, code, details}) that broke generic error parsing.
        """
        handle_exception(error, context=error.__class__.__name__)
        return APIResponse.error(
            code=error.error_code,
            message=error.message,
            http_status=error.status_code,
            data=({"details": error.details} if error.details else None)
        )

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request"""
        logger.warning(f"Bad request: {str(error)}")
        return APIResponse.error(
            code="BAD_REQUEST",
            message="Invalid request - check your input data",
            http_status=400
        )

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized"""
        logger.warning(f"Unauthorized: {str(error)}")
        return APIResponse.error(
            code="UNAUTHORIZED",
            message="Authentication required",
            http_status=401
        )

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden"""
        logger.warning(f"Forbidden: {str(error)}")
        return APIResponse.error(
            code="FORBIDDEN",
            message="Access denied",
            http_status=403
        )

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found"""
        logger.info(f"Resource not found: {request.path}")
        return APIResponse.error(
            code="NOT_FOUND",
            message="Resource not found",
            http_status=404
        )

    @app.errorhandler(429)
    def rate_limit(error):
        """Handle 429 Rate Limit"""
        logger.warning(f"Rate limit exceeded for {request.remote_addr}")
        return APIResponse.error(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests - please try again later",
            http_status=429
        )

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(
            f"Internal server error: {str(error)}",
            exc_info=True
        )
        return APIResponse.error(
            code="INTERNAL_ERROR",
            message="Internal server error",
            http_status=500
        )

    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable"""
        logger.warning(f"Service unavailable: {str(error)}")
        return APIResponse.error(
            code="SERVICE_UNAVAILABLE",
            message="Service temporarily unavailable",
            http_status=503
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle ANY werkzeug HTTPException without a more-specific handler.

        AUDIT FIX #3: the catch-all Exception handler below also matches
        HTTPException subclasses, so codes lacking a dedicated handler
        (405 Method Not Allowed, 408, 413, 415, 422, ...) were being mislabeled
        as 500 UNEXPECTED_ERROR. This preserves the real HTTP status and emits
        a clean, standardized body. Specific handlers (400/401/403/404/429/503)
        still take precedence over this one.
        """
        code = error.code or 500
        # Derive a stable machine code from the exception name, e.g.
        # "MethodNotAllowed" -> "METHOD_NOT_ALLOWED".
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", type(error).__name__).upper()
        if code >= 500:
            logger.error(f"HTTP {code} {name}: {error.description}", exc_info=True)
        else:
            logger.warning(f"HTTP {code} {name}: {error.description}")
        return APIResponse.error(
            code=name,
            message=error.description or f"HTTP {code}",
            http_status=code
        )

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        """Handle unexpected (non-HTTP) errors.

        AUDIT FIX #3: defensively re-dispatch any HTTPException that reaches
        here (e.g. raised after handler resolution) so it keeps its real status
        instead of collapsing to 500.
        """
        if isinstance(error, HTTPException):
            return handle_http_exception(error)
        logger.error(
            f"Unexpected error: {type(error).__name__}: {str(error)}",
            exc_info=True
        )
        return APIResponse.error(
            code="UNEXPECTED_ERROR",
            message="An unexpected error occurred",
            http_status=500
        )


def register_logging_middleware(app):
    """Register request/response logging middleware"""

    @app.before_request
    def before_request():
        """Log incoming request"""
        g.start_time = time.time()
        logger.debug(
            f"Incoming {request.method} {request.path}",
            extra={
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr
            }
        )

    @app.after_request
    def after_request(response):
        """Log response"""
        try:
            duration_ms = (time.time() - g.start_time) * 1000
            log_level = "info"
            if response.status_code >= 500:
                log_level = "error"
            elif response.status_code >= 400:
                log_level = "warning"

            getattr(logger, log_level)(
                f"Response {request.method} {request.path} {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "remote_addr": request.remote_addr
                }
            )
        except Exception as e:
            logger.error(f"Error logging response: {e}")

        return response
