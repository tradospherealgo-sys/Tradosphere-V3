"""
Error Handling Middleware for Tradosphere V3.1
Catches all exceptions and returns properly formatted error responses
"""

import logging
import time
from flask import jsonify, request, g
from exceptions import TradosphereException, handle_exception
from response_handler import APIResponse

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Register all error handlers with Flask app"""

    @app.errorhandler(TradosphereException)
    def handle_tradosphere_exception(error):
        """Handle custom Tradosphere exceptions"""
        handle_exception(error, context=error.__class__.__name__)
        return jsonify({
            "status": "error",
            "error": error.message,
            "code": error.error_code,
            "details": error.details if error.details else None
        }), error.status_code

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request"""
        logger.warning(f"Bad request: {str(error)}")
        return APIResponse.error(
            "Invalid request - check your input data",
            code="BAD_REQUEST",
            status_code=400
        ), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized"""
        logger.warning(f"Unauthorized: {str(error)}")
        return APIResponse.error(
            "Authentication required",
            code="UNAUTHORIZED",
            status_code=401
        ), 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden"""
        logger.warning(f"Forbidden: {str(error)}")
        return APIResponse.error(
            "Access denied",
            code="FORBIDDEN",
            status_code=403
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found"""
        logger.info(f"Resource not found: {request.path}")
        return APIResponse.error(
            "Resource not found",
            code="NOT_FOUND",
            status_code=404
        ), 404

    @app.errorhandler(429)
    def rate_limit(error):
        """Handle 429 Rate Limit"""
        logger.warning(f"Rate limit exceeded for {request.remote_addr}")
        return APIResponse.error(
            "Too many requests - please try again later",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429
        ), 429

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(
            f"Internal server error: {str(error)}",
            exc_info=True
        )
        return APIResponse.error(
            "Internal server error",
            code="INTERNAL_ERROR",
            status_code=500
        ), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable"""
        logger.warning(f"Service unavailable: {str(error)}")
        return APIResponse.error(
            "Service temporarily unavailable",
            code="SERVICE_UNAVAILABLE",
            status_code=503
        ), 503

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        """Handle unexpected errors"""
        logger.error(
            f"Unexpected error: {type(error).__name__}: {str(error)}",
            exc_info=True
        )
        return APIResponse.error(
            "An unexpected error occurred",
            code="UNEXPECTED_ERROR",
            status_code=500
        ), 500


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
