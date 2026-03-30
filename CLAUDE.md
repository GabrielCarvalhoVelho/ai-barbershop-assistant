# AI Barbershop Assistant

## O que é este projeto

Sistema backend de atendimento e agendamento automatizado para barbearias, usando Inteligência Artificial Generativa. Desenvolvido como TCC (Trabalho de Conclusão de Curso).

O sistema recebe mensagens de clientes, interpreta intenções com IA e gera respostas automatizadas — simulando um atendente virtual 24/7 para barbearias de pequeno/médio porte.

## Estado atual

**Fase: MVP modular com tratamento de erros robusto** — arquitetura modular por domínio de negócio, banco de dados async, 4 models, segurança reforçada, respostas padronizadas com envelope, hierarquia de exceções com error codes, logging estruturado com request ID e hardening nas camadas. Sem IA real ainda.

- FastAPI + Uvicorn rodando com metadados (title, version via `Settings`)
- **Estrutura modular por domínio:** `app/modules/chat/` e `app/modules/health/` — cada módulo com routes, controller, service, repository e schemas próprios
- Endpoints: `GET /` (root), `GET /api/v1/health`, `POST /api/v1/chat`
- Endpoints async (`async def`) — I/O não-bloqueante
- Chat retorna echo: `"Você disse: {message}"`
- Validação em 3 camadas:
  - **Schema (Pydantic):** formato — vazio, tamanho (1-500), strip whitespace, só especiais, chars repetidos (2+) → `422`
  - **Service (negócio):** conteúdo — spam (10+ chars repetidos, palavra 5x seguida), sanitização de espaços internos → `400`
  - **Middleware (catch-all):** erros internos inesperados → `500`
- **Respostas padronizadas com envelope:**
  - **Sucesso:** `SuccessResponse` — `{success: true, data: {...}, timestamp}`
  - **Erro:** `ErrorResponse` — `{success: false, request_id, error: {code, message, field?, details?}, timestamp}`
  - Schemas compartilhados: `BaseResponse`, `SuccessResponse`, `ErrorDetail`, `ErrorResponse` em `app/schemas/`
  - Schemas de domínio: `ChatRequest`, `ChatResponse` em `app/modules/chat/schemas.py`; `HealthResponse` em `app/modules/health/schemas.py`
  - Erros documentados no Swagger/OpenAPI (400, 401, 403, 409, 422, 429, 500, 503 no `/chat`)
- **Hierarquia de exceções customizadas (`AppError` base):**
  - `AuthenticationError` (401, AUTH_001) — API key ausente
  - `AuthorizationError` (403, AUTH_002) — API key inválida
  - `BusinessError` (400, CHAT_001) — regra de negócio
  - `ValidationError` (422, VAL_001) — validação customizada
  - `NotFoundError` (404, RES_001) — recurso não encontrado
  - `ConflictError` (409, DB_002) — violação de constraint
  - `DatabaseError` (500, DB_001) — erro genérico de banco
  - `ServiceUnavailableError` (503, DB_003) — banco/serviço indisponível
  - `RateLimitError` (429, RATE_001) — rate limit excedido
- **Exception handlers registrados (7):**
  - `AppError` → handler unificado (usa status_code/code da exceção)
  - `HTTPException` → handler padronizado (404, 405, etc. no formato ErrorResponse)
  - `RequestValidationError` → 422 com field name e detalhes
  - `RateLimitExceeded` → 429
  - `IntegrityError` → 409 (FK/UNIQUE violation)
  - `OperationalError` → 503 (DB indisponível/timeout)
  - `SQLAlchemyError` → 500 (fallback genérico de banco)
  - Middleware catch-all → 500 com stack trace logado (exc_info=True)
- **Logging estruturado com request ID:**
  - `RequestIDMiddleware`: gera UUID hex por request, propaga via `contextvars`, retorna no header `X-Request-ID`
  - `RequestIDFilter`: injeta `request_id` em todo log record automaticamente
  - Formato: `timestamp | LEVEL | module | rid=abc123 | mensagem`
  - `request_id` no body de `ErrorResponse` (correlação header ↔ body)
  - Logging em todas as camadas: controllers (início/fim), repositories (operações DB), services (mensagem recebida)
  - Stack traces completos nos erros 500 (logados, nunca expostos ao cliente)
- **Hardening nas camadas:**
  - Repository: try-except traduz `IntegrityError` → `ConflictError`, `OperationalError`/`TimeoutError` → `ServiceUnavailableError`, `SQLAlchemyError` → `DatabaseError`; rollback automático após erro
  - Controller: captura `AppError` do repository, loga com contexto e re-raise
  - Timeout guard: `asyncio.wait_for(..., timeout=10s)` em todas as operações async de banco
  - Validation handler: extrai field name do Pydantic error, inclui no `ErrorDetail.field`
- CORS seguro por padrão: origens restritas (`http://localhost:3000`), wildcard `["*"]` só permitido com `DEBUG=true`
- Rate limiting via `slowapi` (padrão: `10/minute`, configurável via `RATE_LIMIT`). Aplicado ao `/chat`, rotas `/` e `/health` isentas
- Autenticação por API key (`X-API-Key` header) no `/chat` com `secrets.compare_digest` (proteção contra timing attack)
- **Banco de dados async (3 ambientes):**
  - **Testes:** SQLite in-memory (aiosqlite) — rápido, sem dependência
  - **Dev local:** PostgreSQL 18.1 (Postgres.app) — banco `barbershop`
  - **Produção:** Supabase PostgreSQL (us-west-2, Session Pooler) — banco `postgres`
  - `database.py`: engine, async_session, Base, get_session, create_tables, dispose_engine
  - Lifespan handler no `main.py`: cria tabelas no startup, fecha engine no shutdown
- **Migrations (Alembic):**
  - `alembic.ini` + `migrations/env.py` configurados com async + URL dinâmica via Settings
  - Migration inicial: cria 4 tabelas, 4 FKs, 4 índices, 2 UNIQUE constraints
- **4 Models SQLAlchemy** (centralizados em `app/models/`):
  - `Company`: id, name, address, phone, created_at, updated_at
  - `User`: id, company_id (FK RESTRICT), name, phone (UNIQUE), email (UNIQUE), created_at, updated_at
  - `Conversation`: id, user_id (FK RESTRICT), company_id (FK RESTRICT), status, started_at, ended_at
  - `Message`: id, conversation_id (FK CASCADE), sender, content, created_at
- Configuração centralizada: `pydantic-settings` + `.env` (7 campos: app_name, app_version, debug, cors_origins, api_key, rate_limit, database_url)
- Logger estruturado com `RequestIDFilter` + lazy formatting (`%s`) — sem log injection
- 215 testes automatizados — todos passando
- `conftest.py` com fixtures `client`, `reset_rate_limiter` (autouse), `setup_db` (SQLite in-memory), `db_session`
- Dependências separadas: `requirements.txt` (prod) e `requirements-dev.txt` (dev)

### Catálogo de Error Codes

| Code | Domínio | HTTP | Descrição |
|------|---------|------|-----------|
| APP_000 | Geral | 500 | Erro não tratado (catch-all) |
| AUTH_001 | Autenticação | 401 | API key ausente |
| AUTH_002 | Autorização | 403 | API key inválida |
| CHAT_001 | Chat | 400 | Conteúdo repetitivo (spam) |
| VAL_001 | Validação | 422 | Erro de validação (Pydantic) |
| RES_001 | Recurso | 404 | Recurso não encontrado |
| DB_001 | Banco | 500 | Erro genérico de banco |
| DB_002 | Banco | 409 | Violação de constraint (FK, UNIQUE) |
| DB_003 | Banco | 503 | Banco/serviço indisponível |
| RATE_001 | Rate Limit | 429 | Limite de requisições excedido |
| HTTP_* | HTTP | varia | HTTPException do FastAPI/Starlette (404, 405, etc.) |

## Arquitetura

Monolito modular por domínio de negócio (preparado para futura evolução a microserviços):

```
backend/
  app/
    modules/                       # Módulos de domínio (auto-contidos)
      chat/
        routes.py                  # POST /api/v1/chat (auth + rate limit)
        controller.py              # ChatController (orquestração async)
        service.py                 # Lógica de negócio pura (validação, sanitização)
        repository.py              # MessageRepository (save, get_by_id, get_by_conversation)
        schemas.py                 # ChatRequest (validado) + ChatResponse
      health/
        routes.py                  # GET /api/v1/health
        controller.py              # HealthController
        schemas.py                 # HealthResponse
    api/routes.py                  # Root router (GET /)
    core/                          # Infraestrutura compartilhada
      config.py                    # Settings centralizado (pydantic-settings + .env)
      auth.py                      # Autenticação por API key
      context.py                   # ContextVar para request_id
      middleware.py                # RequestIDMiddleware
      rate_limiter.py              # Rate limiting (slowapi)
      error_handler.py             # 7 handlers + middleware catch-all
      exceptions.py                # Hierarquia: AppError → 9 subclasses
      logger.py                    # Logger com RequestIDFilter
    db/database.py                 # Engine async, session factory, Base, lifecycle helpers
    models/                        # Models SQLAlchemy (centralizados, compartilhados)
      company.py                   # Model Company
      user.py                      # Model User (FK → Company)
      conversation.py              # Model Conversation (FK → User + Company)
      message.py                   # Model Message (FK → Conversation)
    schemas/                       # Schemas compartilhados (envelope de resposta)
      base_schema.py               # BaseResponse, SuccessResponse, ErrorDetail
      error_schema.py              # ErrorResponse
    main.py                        # Entry point (config, middlewares, lifespan, handlers, routers)
  migrations/
    env.py                         # Configuração Alembic async
    versions/                      # Scripts de migration versionados
  alembic.ini                      # Config do Alembic
  tests/
    modules/
      chat/
        test_controller.py         # 5 testes do ChatController (async)
        test_service.py            # 11 testes do chat_service
        test_repository.py         # 6 testes do MessageRepository (async)
        test_schemas.py            # 18 testes do ChatRequest/ChatResponse
        test_routes.py             # 11 testes de integração do /chat
      health/
        test_controller.py         # 2 testes do HealthController
        test_schemas.py            # 1 teste do HealthResponse
        test_routes.py             # 1 teste de integração do /health
    core/
      test_schemas.py              # 20 testes dos schemas compartilhados
      test_exceptions.py           # 52 testes da hierarquia de exceções
      test_error_handlers.py       # 17 testes dos handlers
      test_logging.py              # 15 testes de request ID
      test_hardening.py            # 15 testes de hardening
      test_security.py             # 12 testes de segurança
    conftest.py                    # Fixtures: client, reset_rate_limiter, setup_db, db_session
    test_models.py                 # 27 testes dos models
    test_root.py                   # 1 teste do GET /
```

**Fluxo:** Cliente → Routes (módulo) → RequestIDMiddleware → Auth + Rate Limit → Controller → Service (negócio) + Repository (persistência) → DB → Resposta

**Fluxo de erros:** Exceção → Exception Handler (AppError/HTTP/Validation/RateLimit/DB) → ErrorResponse padronizado com code + request_id → Cliente

## Stack

- **Linguagem:** Python 3.13
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Validação:** Pydantic
- **ORM:** SQLAlchemy (async)
- **Migrations:** Alembic (async)
- **DB testes:** SQLite in-memory + aiosqlite
- **DB dev:** PostgreSQL 18.1 (Postgres.app) + asyncpg
- **DB prod:** Supabase PostgreSQL + asyncpg (Session Pooler, us-west-2)
- **Ambiente:** venv + pip
- **Testes:** pytest + httpx + pytest-asyncio (TestClient do FastAPI)
- **Configuração:** pydantic-settings (carrega `.env` automaticamente)
- **Rate Limiting:** slowapi
- **Autenticação:** API key via header (fastapi.security + secrets)
- **Dependências prod:** `requirements.txt` (fastapi, uvicorn, pydantic-settings, slowapi, sqlalchemy[asyncio], aiosqlite, asyncpg, alembic)
- **Dependências dev:** `requirements-dev.txt` (inclui prod + pytest, httpx, pytest-asyncio)

## Como rodar

```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload
```

## Como testar

```bash
cd backend
source ../venv/bin/activate
python -m pytest tests/ -v
```

## Roadmap (próximos passos)

1. ~~Testes automatizados (pytest)~~ ✅
2. ~~Segurança base (CORS restrito, rate limiting, autenticação API key)~~ ✅
3. ~~Correções de segurança (timing attack, handler 429, regex)~~ ✅
4. ~~Camada de repositories + banco async~~ ✅
5. ~~Modelagem de dados (User, Company, Conversation, Message)~~ ✅
6. ~~Implementar models SQLAlchemy + migrations (Alembic)~~ ✅
7. ~~Padronizar respostas da API~~ ✅
8. ~~Melhorar tratamento de erros (níveis e tipos de execução)~~ ✅
9. ~~Refatorar estrutura por módulos (chat, health)~~ ✅
10. Histórico de conversas
11. Integração com IA generativa (OpenAI API + LangChain)
12. RAG (Retrieval Augmented Generation) para respostas contextualizadas
13. Agendamento automático de horários
14. Integração com WhatsApp/Instagram
15. Autenticação e dashboard administrativo
16. Docker + deploy

## Convenções

- Código e nomes de variáveis em **inglês**
- Documentação e comunicação em **português brasileiro**
- **Arquitetura modular por domínio** — cada módulo em `app/modules/<domínio>/` com routes, controller, service, repository e schemas próprios
- Infraestrutura compartilhada em `app/core/`, models em `app/models/`, schemas base em `app/schemas/`
- **Testes espelham a estrutura:** `tests/modules/<domínio>/`, `tests/core/`
- Abordagem incremental: validar antes de evoluir
- Manter este arquivo e os arquivos de memória atualizados a cada mudança significativa
