"""
Input Validation Schemas (Tier 2 #7)

Marshmallow schemas + a @validate_body decorator that gates write endpoints.
Invalid input is rejected early with a clean, field-level 400 response
(via the standardized APIResponse error format) BEFORE it reaches the handler.

On success the cleaned/validated data is stashed in flask.g.validated so
handlers can use it (handlers may also continue using request.get_json()).
"""

import logging
from functools import wraps

from flask import request, g
from marshmallow import Schema, fields, validate, ValidationError, EXCLUDE

from response_handler import APIResponse

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Decorator
# ─────────────────────────────────────────────────────────────────────
def validate_body(schema_cls):
    """Validate the JSON request body against `schema_cls`.

    - Missing/Non-JSON body          -> 400 VALIDATION_ERROR
    - Schema validation failure       -> 400 VALIDATION_ERROR + per-field errors
    - Success                         -> g.validated = cleaned dict, call handler
    """
    schema = schema_cls()

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # silent=True so a malformed/absent body gives None instead of raising.
            raw = request.get_json(silent=True)
            # A missing/empty body is treated as {} so schemas with all-optional
            # fields (e.g. signal generation) still work; required-field schemas
            # will surface clean per-field "is required" errors.
            if raw is None:
                raw = {}
            if not isinstance(raw, dict):
                return APIResponse.error(
                    code="VALIDATION_ERROR",
                    message="Request body must be a JSON object",
                    http_status=400
                )
            try:
                cleaned = schema.load(raw)
            except ValidationError as err:
                # err.messages = {field: [reasons...]}
                logger.info(f"Validation failed on {request.path}: {err.messages}")
                return APIResponse.error(
                    code="VALIDATION_ERROR",
                    message="Invalid input data",
                    http_status=400,
                    data={"fields": err.messages}
                )
            g.validated = cleaned
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ─────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────
class _Base(Schema):
    class Meta:
        # Ignore unexpected keys rather than 400-ing on them — keeps the API
        # forgiving to extra client fields while still validating known ones.
        unknown = EXCLUDE


# ─────────────────────────────────────────────────────────────────────
# Auth schemas
# ─────────────────────────────────────────────────────────────────────
class LoginSchema(_Base):
    email = fields.Email(required=True, error_messages={"required": "Email is required"})
    password = fields.String(
        required=True,
        validate=validate.Length(min=1, max=128),
        error_messages={"required": "Password is required"},
    )


class SignupSchema(_Base):
    email = fields.Email(required=True, error_messages={"required": "Email is required"})
    password = fields.String(
        required=True,
        validate=validate.Length(min=6, max=128, error="Password must be 6-128 characters"),
        error_messages={"required": "Password is required"},
    )
    first_name = fields.String(required=False, validate=validate.Length(max=80), load_default="")
    last_name = fields.String(required=False, validate=validate.Length(max=80), load_default="")


class RefreshSchema(_Base):
    refresh_token = fields.String(
        required=True, validate=validate.Length(min=10),
        error_messages={"required": "refresh_token is required"},
    )


class ResetPasswordSchema(_Base):
    old_password = fields.String(required=True, validate=validate.Length(min=1, max=128))
    new_password = fields.String(
        required=True,
        validate=validate.Length(min=6, max=128, error="New password must be 6-128 characters"),
    )


class GoogleAuthSchema(_Base):
    credential = fields.String(
        required=True, validate=validate.Length(min=10),
        error_messages={"required": "Google credential is required"},
    )


# ─────────────────────────────────────────────────────────────────────
# Trading / signal schemas
# ─────────────────────────────────────────────────────────────────────
_VALID_SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]


class GenerateSignalSchema(_Base):
    symbol = fields.String(
        required=False, load_default="NIFTY",
        validate=validate.OneOf(_VALID_SYMBOLS, error="symbol must be one of {choices}"),
    )


class BatchGenerateSchema(_Base):
    symbols = fields.List(
        fields.String(validate=validate.OneOf(_VALID_SYMBOLS)),
        required=False,
        load_default=["NIFTY", "BANKNIFTY", "FINNIFTY"],
        validate=validate.Length(min=1, max=20, error="symbols must contain 1-20 entries"),
    )


_VALID_TRADE_DIRECTIONS = ["BUY_CALL", "BUY_PUT", "SELL_CALL", "SELL_PUT"]


class CreateTradeSchema(_Base):
    symbol = fields.String(
        required=False, load_default="NIFTY",
        validate=validate.OneOf(_VALID_SYMBOLS, error="symbol must be one of {choices}"),
    )
    direction = fields.String(
        required=True,
        validate=validate.OneOf(
            _VALID_TRADE_DIRECTIONS,
            error="direction must be one of {choices}",
        ),
    )
    entry_price = fields.Float(
        required=True,
        validate=validate.Range(min=0, min_inclusive=False, error="entry_price must be > 0"),
    )
    target_price = fields.Float(
        required=True,
        validate=validate.Range(min=0, min_inclusive=False, error="target_price must be > 0"),
    )
    stop_loss = fields.Float(
        required=True,
        validate=validate.Range(min=0, min_inclusive=False, error="stop_loss must be > 0"),
    )
    quantity = fields.Integer(
        required=False, load_default=1,
        validate=validate.Range(min=1, max=100000, error="quantity must be 1-100000"),
    )
    strike_price = fields.Float(required=False, allow_none=True)
