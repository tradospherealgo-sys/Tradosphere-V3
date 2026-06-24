"""
Standardized API Response Handler
Ensures all endpoints return consistent JSON format
"""

from flask import jsonify
from datetime import datetime


class APIResponse:
    """Standardized API response wrapper"""

    @staticmethod
    def success(data, message=None, http_status=200):
        """
        Return success response

        Args:
            data: Response data dict
            message: Optional success message
            http_status: HTTP status code (default 200)

        Returns:
            Tuple of (response_dict, http_status)
        """
        response = {
            "status": "success",
            "data": data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if message:
            response["message"] = message
        return jsonify(response), http_status

    @staticmethod
    def error(code, message, http_status=400, data=None):
        """
        Return error response

        Args:
            code: Error code (e.g., "INVALID_REQUEST")
            message: Human readable error message
            http_status: HTTP status code
            data: Optional additional error data

        Returns:
            Tuple of (response_dict, http_status)
        """
        response = {
            "status": "error",
            "data": data,
            "error": {
                "code": code,
                "message": message
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return jsonify(response), http_status

    @staticmethod
    def unauthorized(message="Invalid or expired token"):
        """Return 401 unauthorized response"""
        return APIResponse.error(
            code="UNAUTHORIZED",
            message=message,
            http_status=401
        )

    @staticmethod
    def forbidden(message="Access denied"):
        """Return 403 forbidden response"""
        return APIResponse.error(
            code="FORBIDDEN",
            message=message,
            http_status=403
        )

    @staticmethod
    def not_found(message="Resource not found"):
        """Return 404 not found response"""
        return APIResponse.error(
            code="NOT_FOUND",
            message=message,
            http_status=404
        )

    @staticmethod
    def bad_request(message="Invalid request"):
        """Return 400 bad request response"""
        return APIResponse.error(
            code="INVALID_REQUEST",
            message=message,
            http_status=400
        )

    @staticmethod
    def server_error(message="Internal server error", exception=None):
        """Return 500 server error response"""
        error_data = None
        if exception:
            error_data = {"exception": str(exception)}
        return APIResponse.error(
            code="SERVER_ERROR",
            message=message,
            http_status=500,
            data=error_data
        )

    @staticmethod
    def conflict(message="Resource conflict"):
        """Return 409 conflict response"""
        return APIResponse.error(
            code="CONFLICT",
            message=message,
            http_status=409
        )
