"""
Middlewares HTTP da aplicação.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Gera um UUID por request e propaga via contextvars + response header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = request_id_var.set(rid)

        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = rid
            return response
        finally:
            request_id_var.reset(token)
