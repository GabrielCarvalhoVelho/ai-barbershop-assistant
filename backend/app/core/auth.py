import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
) -> str:
    if not settings.api_key:
        return "no-auth"

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key ausente. Envie o header X-API-Key.",
        )

    if not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=403,
            detail="API key inválida.",
        )

    return api_key
