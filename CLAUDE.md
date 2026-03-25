# AI Barbershop Assistant

## O que é este projeto

Sistema backend de atendimento e agendamento automatizado para barbearias, usando Inteligência Artificial Generativa. Desenvolvido como TCC (Trabalho de Conclusão de Curso).

O sistema recebe mensagens de clientes, interpreta intenções com IA e gera respostas automatizadas — simulando um atendente virtual 24/7 para barbearias de pequeno/médio porte.

## Estado atual

**Fase: MVP com persistência** — arquitetura em camadas completa com banco de dados async, repositories, segurança reforçada, modelagem de dados em andamento. Sem IA real ainda.

- FastAPI + Uvicorn rodando com metadados (title, version via `Settings`)
- Endpoints: `GET /` (root), `GET /api/v1/health`, `POST /api/v1/chat`
- Endpoints async (`async def`) — I/O não-bloqueante
- Chat retorna echo: `"Você disse: {message}"`
- Validação em 3 camadas:
  - **Schema (Pydantic):** formato — vazio, tamanho (1-500), strip whitespace, só especiais, chars repetidos (2+) → `422`
  - **Service (negócio):** conteúdo — spam (10+ chars repetidos, palavra 5x seguida), sanitização de espaços internos → `400`
  - **Middleware (catch-all):** erros internos inesperados → `500`
- Schemas Pydantic: `ChatRequest`, `ChatResponse` (timestamp UTC), `HealthResponse`, `ErrorResponse` (com campo `details` opcional)
- Exception handlers registrados: `RequestValidationError` (422), `BusinessError` (400), `RateLimitExceeded` (429 — handler customizado com `ErrorResponse`)
- CORS seguro por padrão: origens restritas (`http://localhost:3000`), wildcard `["*"]` só permitido com `DEBUG=true`
- Validador `warn_wildcard_cors` impede `CORS_ORIGINS=["*"]` em produção (levanta `ValueError`)
- Rate limiting via `slowapi` (padrão: `10/minute`, configurável via `RATE_LIMIT`). Aplicado ao `/chat`, rotas `/` e `/health` isentas
- Autenticação por API key (`X-API-Key` header) no `/chat` com `secrets.compare_digest` (proteção contra timing attack). Opcional: se `API_KEY` vazio, acesso livre; se definido, exige header válido (401/403)
- **Banco de dados async:**
  - SQLAlchemy async engine + aiosqlite (dev), configurável via `DATABASE_URL` para PostgreSQL + asyncpg (prod)
  - `database.py`: engine, async_session, Base, get_session, create_tables, dispose_engine
  - Lifespan handler no `main.py`: cria tabelas no startup, fecha engine no shutdown
- **Model `Message` (atual):** id, user_message, bot_response, created_at — será refatorado para novo modelo de dados
- **Camada de repositories:** `MessageRepository(session)` com save(), get_by_id(), get_recent() — injetado via `Depends(get_session)`
- Camada de controllers async: `ChatController` (orquestra chat + persistência) e `HealthController` (orquestra health)
- Configuração centralizada: `pydantic-settings` + `.env` (7 campos: app_name, app_version, debug, cors_origins, api_key, rate_limit, database_url)
- Logger configurado com lazy formatting (`%s`) — sem log injection
- 75 testes automatizados — todos passando
- `conftest.py` com fixtures `client`, `reset_rate_limiter` (autouse), `setup_db` (SQLite in-memory), `db_session`
- Dependências separadas: `requirements.txt` (prod) e `requirements-dev.txt` (dev)

### Modelo de dados (em andamento)

4 entidades MVP definidas: **User**, **Company**, **Conversation**, **Message**

- Todos relacionamentos 1:N, 4 FKs NOT NULL indexadas, 3ª Forma Normal
- Checklist de modelagem: 4/9 concluídos (faltam: comportamento de deleção, diagrama ER, dicionário de dados, decisões de design, validação)

## Arquitetura

Monolito em camadas (preparado para futura evolução a microserviços):

```
backend/
  app/
    api/routes.py              # Rotas HTTP async — root_router (/) e router (/api/v1/*)
    controllers/
      chat_controller.py       # Orquestração do chat (async, recebe repository opcional)
      health_controller.py     # Orquestração do health check
    core/config.py             # Settings centralizado (pydantic-settings + .env + validador CORS)
    core/auth.py               # Autenticação por API key (secrets.compare_digest)
    core/rate_limiter.py       # Rate limiting centralizado (slowapi)
    core/error_handler.py      # Handlers de erro (422, 400, 429 customizado, 500)
    core/exceptions.py         # Exceções customizadas (BusinessError)
    core/logger.py             # Setup de logging
    db/database.py             # Engine async, session factory, Base, lifecycle helpers
    models/message.py          # Model Message (SQLAlchemy) — será refatorado
    repositories/
      message_repository.py    # MessageRepository: save, get_by_id, get_recent
    schemas/chat_schema.py     # ChatRequest (validado) + ChatResponse (timestamp UTC)
    schemas/health_schema.py   # HealthResponse
    schemas/error_schema.py    # ErrorResponse (usado nos error handlers)
    services/chat_service.py   # Lógica de negócio pura (retorna str, sem schemas)
    main.py                    # Entry point (config, CORS, middleware, lifespan, handlers)
  tests/
    conftest.py                # Fixtures: client, reset_rate_limiter, setup_db, db_session
    test_schemas.py            # 17 testes unitários dos schemas Pydantic
    test_controllers.py        # 7 testes unitários dos controllers (async)
    test_services.py           # 11 testes unitários do chat_service
    test_repositories.py       # 5 testes unitários do repository (async)
    test_api.py                # 13 testes de integração dos endpoints
    test_security.py           # 12 testes de segurança: rate limit, auth, CORS
```

**Fluxo:** Cliente → Routes (HTTP) → Auth + Rate Limit → Controllers (async, orquestração) → Services (negócio) + Repositories (persistência) → DB → Resposta

## Stack

- **Linguagem:** Python 3.13
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Validação:** Pydantic
- **ORM:** SQLAlchemy (async)
- **DB dev:** SQLite + aiosqlite
- **DB prod:** PostgreSQL + asyncpg (configurável via DATABASE_URL)
- **Ambiente:** venv + pip
- **Testes:** pytest + httpx + pytest-asyncio (TestClient do FastAPI)
- **Configuração:** pydantic-settings (carrega `.env` automaticamente)
- **Rate Limiting:** slowapi
- **Autenticação:** API key via header (fastapi.security + secrets)
- **Dependências prod:** `requirements.txt` (fastapi, uvicorn, pydantic-settings, slowapi, sqlalchemy[asyncio], aiosqlite)
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
5. Modelagem de dados (User, Company, Conversation, Message) 🔄
6. Implementar models SQLAlchemy + migrations (Alembic)
7. Padronizar respostas da API
8. Integração com IA generativa (OpenAI API + LangChain)
9. Histórico de conversas
10. RAG (Retrieval Augmented Generation) para respostas contextualizadas
11. Agendamento automático de horários
12. Integração com WhatsApp/Instagram
13. Autenticação e dashboard administrativo
14. Docker + deploy

## Convenções

- Código e nomes de variáveis em **inglês**
- Documentação e comunicação em **português brasileiro**
- Arquitetura em camadas — manter separação de responsabilidades (routes → controllers → services → repositories → schemas/core/db)
- Abordagem incremental: validar antes de evoluir
- Manter este arquivo e os arquivos de memória atualizados a cada mudança significativa
