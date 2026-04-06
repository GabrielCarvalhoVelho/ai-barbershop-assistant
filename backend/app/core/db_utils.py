"""
Utilitários para operações de banco de dados.
"""

import asyncio
import functools
import logging
from collections.abc import Callable

from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.core.exceptions import ConflictError, DatabaseError, ServiceUnavailableError

DB_TIMEOUT_SECONDS = 10


def db_operation(context: str) -> Callable:
    """Decorator para operações de banco de dados.

    Traduz exceções SQLAlchemy para AppError e loga com contexto.
    O logger usa o módulo da função decorada, mantendo rastreabilidade.

    Usage:
        @db_operation("criar conversa")
        async def create(self, ...) -> Conversation:
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            log = logging.getLogger(func.__module__)
            try:
                return await func(*args, **kwargs)
            except IntegrityError as e:
                log.warning("IntegrityError ao %s: %s", context, e.orig)
                raise ConflictError(
                    message=f"Não foi possível {context}. Verifique os dados enviados.",
                ) from e
            except (OperationalError, asyncio.TimeoutError) as e:
                log.error("Banco indisponível ao %s: %s", context, e)
                raise ServiceUnavailableError(
                    message="Serviço de banco de dados indisponível.",
                ) from e
            except SQLAlchemyError as e:
                log.error("Erro de banco ao %s: %s", context, e)
                raise DatabaseError(
                    message=f"Erro ao {context}.",
                ) from e

        return wrapper

    return decorator
