"""
Middlewares HTTP da aplicação.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"

_SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
_HSTS_VALUE = "max-age=31536000; includeSubDomains"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Gera um UUID por request e propaga via contextvars + response header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = uuid.uuid4().hex
        token = request_id_var.set(rid)

        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = rid
            return response
        finally:
            request_id_var.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injeta security headers em todas as responses.

    HSTS só é adicionado em produção (debug=False) para não forçar HTTPS em dev.
    """

    def __init__(self, app, debug: bool = False) -> None:
        super().__init__(app)
        self._debug = debug

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        if not self._debug:
            response.headers["Strict-Transport-Security"] = _HSTS_VALUE
        return response
