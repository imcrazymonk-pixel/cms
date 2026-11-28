"""Structured error codes for CMS API responses.

Usage:
    from web.backend.core.errors import api_error, E
    raise api_error(404, E.USER_NOT_FOUND)
    raise api_error(400, E.INVALID_INPUT, "Description")

Pattern matches remnawave's web/backend/core/errors.py.
"""
from enum import Enum
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from typing import Optional


class ErrorCode(str, Enum):
    """API error codes — frontend can map to i18n."""

    # Auth
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_REQUIRED = "TOKEN_REQUIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    FORBIDDEN = "FORBIDDEN"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"

    # CRUD
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    CREATE_FAILED = "CREATE_FAILED"
    UPDATE_FAILED = "UPDATE_FAILED"
    DELETE_FAILED = "DELETE_FAILED"
    INVALID_INPUT = "INVALID_INPUT"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # Media
    UPLOAD_FAILED = "UPLOAD_FAILED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"

    # Database
    DB_ERROR = "DB_ERROR"
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"

    # Support (phase 1+)
    REPLY_WINDOW_CLOSED = "REPLY_WINDOW_CLOSED"
    CLIENT_WROTE = "CLIENT_WROTE"
    LOCKED_BY_OTHER = "LOCKED_BY_OTHER"

    # Support — ИИ и база знаний (Этап B)
    AI_DISABLED = "AI_DISABLED"
    AI_PAUSED = "AI_PAUSED"
    AI_KEY_MISSING = "AI_KEY_MISSING"
    AI_UPSTREAM_ERROR = "AI_UPSTREAM_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    KB_VERSION_CONFLICT = "KB_VERSION_CONFLICT"
    KB_DOC_PUBLISHED = "KB_DOC_PUBLISHED"
    IMPORT_TOO_LARGE = "IMPORT_TOO_LARGE"
    IMPORT_PARSE_FAILED = "IMPORT_PARSE_FAILED"
    JOB_BUSY = "JOB_BUSY"

    # Support — этап C (шаблоны, заметки, SLA)
    TEMPLATE_EXISTS = "TEMPLATE_EXISTS"
    SLA_POLICY_NOT_FOUND = "SLA_POLICY_NOT_FOUND"
    NOTE_NOT_FOUND = "NOTE_NOT_FOUND"

    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    RATE_LIMITED = "RATE_LIMITED"


def api_error(status_code: int, code: ErrorCode, detail: Optional[str] = None):
    """Raise HTTPException with CMS-compatible format.

    The response body follows PHP convention:
        { "success": false, "error": "..." }
    but with additional 'code' field for programmatic handling.
    """
    message = detail or code.value.replace("_", " ").title()
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": message,
            "code": code.value,
        },
    )


def api_raise(status_code: int, code: ErrorCode, detail: Optional[str] = None):
    """Raise as HTTPException (for middleware/interceptors)."""
    raise HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "error": detail or code.value.replace("_", " ").title(),
            "code": code.value,
        },
    )


# Convenience aliases matching remnawave's E.* pattern
E = ErrorCode