"""
Contexto de request — propagação de request_id entre camadas via contextvars.

Uso:
    - O middleware RequestIDMiddleware gera o UUID e seta no contexto.
    - Qualquer camada (controller, service, repository) acessa via get_request_id().
    - O logger usa o request_id automaticamente via RequestIDFilter.
"""

from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()
