"""
Hierarquia de exceções customizadas da aplicação.

Todas as exceções herdam de AppError, que carrega:
- message: descrição legível para o cliente
- code: código de erro por domínio (ex: CHAT_001, AUTH_001)
- status_code: HTTP status correspondente
- details: informações adicionais opcionais (lista de strings)

Catálogo de error codes por domínio:
    AUTH_001  — API key ausente
    AUTH_002  — API key inválida
    AUTH_003  — JWT inválido ou expirado
    AUTH_004  — Telefone ou email já registrado
    CHAT_001  — Conteúdo repetitivo (spam)
    DB_001    — Erro genérico de banco de dados
    DB_002    — Violação de constraint (FK, UNIQUE, NOT NULL)
    DB_003    — Serviço de banco indisponível
    RES_001   — Recurso não encontrado
    RATE_001  — Limite de requisições excedido
    VAL_001   — Erro de validação customizada
    AI_001    — Serviço de IA indisponível
"""


class AppError(Exception):
    """Exceção base da aplicação. Todas as exceções customizadas herdam desta."""

    status_code: int = 500
    code: str = "APP_000"

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: list[str] | None = None,
    ):
        self.message = message
        if code is not None:
            self.code = code
        self.details = details
        super().__init__(message)


# --- Erros de autenticação/autorização ---


class AuthenticationError(AppError):
    """Credenciais ausentes ou mal formadas."""

    status_code = 401
    code = "AUTH_001"


class AuthorizationError(AppError):
    """Credenciais presentes mas inválidas ou sem permissão."""

    status_code = 403
    code = "AUTH_002"


class InvalidTokenError(AppError):
    """JWT ausente, expirado ou com assinatura inválida."""

    status_code = 401
    code = "AUTH_003"


class RegistrationError(AppError):
    """Dados de cadastro em conflito — phone ou email já registrado."""

    status_code = 400
    code = "AUTH_004"


# --- Erros de negócio ---


class BusinessError(AppError):
    """Violação de regra de negócio na camada de serviço."""

    status_code = 400
    code = "CHAT_001"


class ValidationError(AppError):
    """Erro de validação customizada (não Pydantic)."""

    status_code = 422
    code = "VAL_001"


# --- Erros de recurso ---


class NotFoundError(AppError):
    """Recurso solicitado não encontrado."""

    status_code = 404
    code = "RES_001"


class ConflictError(AppError):
    """Conflito de dados — violação de constraint (FK, UNIQUE, NOT NULL)."""

    status_code = 409
    code = "DB_002"


# --- Erros de infraestrutura ---


class DatabaseError(AppError):
    """Erro genérico de banco de dados."""

    status_code = 500
    code = "DB_001"


class ServiceUnavailableError(AppError):
    """Serviço externo ou banco de dados indisponível."""

    status_code = 503
    code = "DB_003"


class RateLimitError(AppError):
    """Limite de requisições excedido."""

    status_code = 429
    code = "RATE_001"


class AIServiceError(AppError):
    """Serviço de IA (LLM) indisponível ou com falha."""

    status_code = 503
    code = "AI_001"
