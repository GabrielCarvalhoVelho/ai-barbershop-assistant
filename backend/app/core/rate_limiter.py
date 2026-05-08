from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def _rate_limit_key(request: Request) -> str:
    """Usa user_id do JWT como chave quando disponível, fallback para IP.

    Endpoints autenticados ficam limitados por usuário — impede que um
    cliente burle o rate limit trocando de IP.
    Endpoints públicos (login, register) continuam limitados por IP.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        if token:
            try:
                from jose import jwt as _jwt
                payload = _jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm],
                )
                sub = payload.get("sub")
                if sub:
                    return f"user:{sub}"
            except Exception:
                pass  # token inválido/expirado — usa IP
    return get_remote_address(request)


limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=[settings.rate_limit],
)
