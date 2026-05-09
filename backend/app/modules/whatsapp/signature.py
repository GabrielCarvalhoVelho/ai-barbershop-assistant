"""Validação da assinatura HMAC-SHA256 dos webhooks do Meta.

Meta envia o header `X-Hub-Signature-256: sha256=<hex>` em todos os POSTs.
O hash é HMAC-SHA256 do body bruto da request usando o App Secret como chave.
Usa compare_digest para evitar timing attacks.
"""

import hashlib
import hmac


def compute_signature(body: bytes, app_secret: str) -> str:
    """Retorna o valor esperado do header X-Hub-Signature-256, com prefixo 'sha256='."""
    digest = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def verify_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header or not app_secret:
        return False
    expected = compute_signature(body, app_secret)
    return hmac.compare_digest(expected, signature_header)
