"""
exceptions.py
-------------
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


# ---------------------------------------------------------------------------
# Exceptions métier
# ---------------------------------------------------------------------------

class EventLogError(Exception):
    http_status: int = 500
    code: str = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(EventLogError):
    http_status = 404
    code = "not_found"


class DuplicateEventError(EventLogError):
    http_status = 409
    code = "duplicate_event"


class ValidationError(EventLogError):
    http_status = 400
    code = "validation_error"


class PayloadTooLargeError(EventLogError):
    http_status = 400
    code = "payload_too_large"


# ---------------------------------------------------------------------------
# Handlers FastAPI
# ---------------------------------------------------------------------------

def _error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": code},
    )


async def eventlog_exception_handler(request: Request, exc: EventLogError):
    return _error_response(exc.http_status, exc.code, exc.message)


async def validation_exception_handler(request: Request, exc: RequestValidationError):

    first = exc.errors()[0]
    # loc = ("body", "tags") → "tags"
    field = ".".join(str(x) for x in first["loc"] if x != "body")
    msg = first["msg"]
    detail = f"{field}: {msg}" if field else msg
    return _error_response(400, "validation_error", detail)


def register_exception_handlers(app) -> None:
    app.add_exception_handler(EventLogError, eventlog_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)