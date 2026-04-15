# AI Barbershop Assistant

## O que é este projeto

Sistema backend de atendimento e agendamento automatizado para barbearias, usando Inteligência Artificial Generativa. Desenvolvido como TCC (Trabalho de Conclusão de Curso).

O sistema recebe mensagens de clientes, interpreta intenções com IA e gera respostas automatizadas — simulando um atendente virtual 24/7 para barbearias de pequeno/médio porte.

## Estado atual

**Fase: RAG + Fallback concluídos** — 460 testes automatizados. IA generativa (Groq + LangChain), prompts modulares com dados do negócio, base de conhecimento com 11 documentos seed, **pipeline RAG completo** (busca → formatação → injeção no prompt), **fallback explícito** para off-topic e informação desconhecida (orienta contato por telefone). Próximo: agendamento automático.

**Fallback para respostas desconhecidas concluído:** Regras reforçadas em `_RULES` do prompt — (1) perguntas off-topic: LLM informa explicitamente que só atende assuntos da barbearia (serviços, preços, horários, agendamentos); (2) informação desconhecida: LLM orienta cliente a entrar em contato pelo telefone da barbearia (telefone real já está no prompt via `_build_business_details`, sem hardcode). Prompt-level only, zero novos models/endpoints.

**RAG concluído (item 14):** Pipeline completo de busca de contexto. `KnowledgeDocumentRepository.get_by_company()` carrega todos os documentos ativos da empresa (~11-50 docs, ~600 tokens — cabe nos 128k do Llama 3.3 70B). `format_knowledge_context()` em `app/modules/ai/context_service.py` agrupa por categoria com labels PT-BR ([Serviços], [Horário de Funcionamento], [Políticas], [Perguntas Frequentes], [Informações Gerais]). Controller injeta o contexto via `build_system_prompt(business_info, context)`. Estratégia: carregar tudo, deixar o LLM filtrar — zero falsos negativos, zero complexidade desnecessária. Sem keyword matching, sem embeddings.

**Base de conhecimento concluída (item 13):** Model `KnowledgeDocument` (id, company_id FK, title, content, category enum, is_active, created_at, updated_at), `DocumentCategory` enum (services/hours/policies/faq/general), `KnowledgeDocumentRepository` (get_by_company, get_by_category, create), índice composto (company_id, category), seed com 11 documentos realistas, migration Alembic.

**Estrutura de prompts concluída (item 12):** Prompt modular por seções (persona, regras, detalhes do negócio, contexto RAG). `BusinessInfo` dataclass (DTO desacoplado do ORM), `build_system_prompt(business_info, context)` monta prompt dinâmico com dados reais da empresa. `context` aceita string do RAG (preenchido pelo pipeline RAG). `llm_service` recebe `system_prompt` por parâmetro (Single Responsibility).

**Integração com IA concluída (item 11):** Módulo `app/modules/ai/` com LangChain + Groq (Llama 3.3 70B), histórico de conversa no contexto (últimas N mensagens), `AIServiceError` (503, AI_001), timeout 30s, GROQ_API_KEY obrigatória em produção.

**Hardening concluído (5 itens alta prioridade):** ownership IDOR, API key em prod, enums tipados, Unit of Work, request ID server-only.

**Refatoração concluída (10 itens média/baixa prioridade):** repositórios compartilhados (UserRepository, CompanyRepository em `app/repositories/`), schemas tipados em controllers (ChatResponse, ConversationResponse, ConversationSummaryResponse, ConversationMessagesResponse, PaginationResponse), decorator `@db_operation` eliminou ~200 linhas boilerplate, `create_tables()` condicional a debug, logs sem conteúdo de mensagens (LGPD), índice composto em messages, dead code removido, pytest-asyncio nativo, health check com DB validation, pool config para Supabase (pool_size=5, max_overflow=10, pool_recycle=300).

- FastAPI + Uvicorn rodando com metadados (title, version via `Settings`)
- **Estrutura modular por domínio:** `app/modules/chat/` e `app/modules/health/` — cada módulo com routes, controller, service, repository e schemas próprios
- Endpoints: `GET /` (root), `GET /api/v1/health`, `POST /api/v1/chat`, `POST /api/v1/conversations`, `GET /api/v1/conversations/{id}`, `GET /api/v1/conversations/{id}/messages`, `PATCH /api/v1/conversations/{id}/close`
- Endpoints async (`async def`) — I/O não-bloqueante
- **Chat com persistência completa:**
  - `POST /api/v1/chat` recebe `message`, `user_id`, `company_id`, `conversation_id` (opcional)
  - Valida user e company contra o banco (404 se não existem)
  - Sem `conversation_id`: cria nova conversa automaticamente
  - Com `conversation_id`: reutiliza conversa existente (404 se não encontrada, 403 se não pertence ao user/company, 400 se encerrada)
  - **Validação de ownership:** verifica que `conversation.user_id == request.user_id` e `conversation.company_id == request.company_id` antes de qualquer operação (proteção contra IDOR)
  - Salva mensagem do user → gera resposta via LLM (Groq + LangChain) → salva resposta do bot → retorna `{response, conversation_id}`
  - **Transação única (Unit of Work):** toda a operação (criar conversa + salvar mensagens) roda em uma única transação — se qualquer etapa falhar, tudo é desfeito (sem conversas órfãs)
  - **Histórico no contexto:** controller busca últimas N mensagens (`LLM_MAX_HISTORY`, default 10) e envia ao LLM junto com a mensagem atual
  - **RAG (busca de contexto):** controller busca todos os documentos ativos da empresa via `KnowledgeDocumentRepository.get_by_company()`, formata como string agrupada por categoria via `format_knowledge_context()` e injeta no `build_system_prompt(business_info, context)`. O LLM responde com dados reais (preços, horários, políticas) sem inventar informações.
- **CRUD de conversas:**
  - `POST /api/v1/conversations` — cria conversa manualmente (recebe `user_id`, `company_id`, valida contra o banco, retorna 201)
  - `GET /api/v1/conversations/{id}` — detalhes de uma conversa com `message_count`
  - `GET /api/v1/conversations/{id}/messages` — histórico de mensagens paginado (`limit` 1-100 default 50, `offset` ≥ 0), retorna `messages[]` + `pagination{limit, offset, total}`
  - `PATCH /api/v1/conversations/{id}/close` — encerra conversa (`status → closed`, `ended_at` preenchido, 400 se já encerrada)
  - Todos com auth (API key), rate limiting, error codes no Swagger
- Validação em 3 camadas:
  - **Schema (Pydantic):** formato — vazio, tamanho (1-500), strip whitespace, só especiais, chars repetidos (2+) → `422`
  - **Service (negócio):** conteúdo — spam (10+ chars repetidos, palavra 5x seguida), sanitização de espaços internos → `400`
  - **Middleware (catch-all):** erros internos inesperados → `500`
- **Respostas padronizadas com envelope:**
  - **Sucesso:** `SuccessResponse` — `{success: true, data: {...}, timestamp}`
  - **Erro:** `ErrorResponse` — `{success: false, request_id, error: {code, message, field?, details?}, timestamp}`
  - Schemas compartilhados: `BaseResponse`, `SuccessResponse`, `ErrorDetail`, `ErrorResponse` em `app/schemas/`
  - Schemas de domínio: `ChatRequest`, `CreateConversationRequest`, `ChatResponse`, `MessageResponse`, `ConversationResponse`, `ConversationDetailResponse` em `app/modules/chat/schemas.py`; `HealthResponse` em `app/modules/health/schemas.py`
  - Erros documentados no Swagger/OpenAPI em todos os endpoints (400, 401, 403, 404, 409, 422, 429, 500, 503)
- **Hierarquia de exceções customizadas (`AppError` base):**
  - `AuthenticationError` (401, AUTH_001) — API key ausente
  - `AuthorizationError` (403, AUTH_002) — API key inválida ou ownership de conversa violado
  - `BusinessError` (400, CHAT_001) — regra de negócio
  - `ValidationError` (422, VAL_001) — validação customizada
  - `NotFoundError` (404, RES_001) — recurso não encontrado
  - `ConflictError` (409, DB_002) — violação de constraint
  - `DatabaseError` (500, DB_001) — erro genérico de banco
  - `ServiceUnavailableError` (503, DB_003) — banco/serviço indisponível
  - `RateLimitError` (429, RATE_001) — rate limit excedido
  - `AIServiceError` (503, AI_001) — serviço de IA indisponível
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
  - `RequestIDMiddleware`: gera UUID hex por request **sempre server-side** (ignora header do cliente — previne log injection), propaga via `contextvars`, retorna no header `X-Request-ID`
  - `RequestIDFilter`: injeta `request_id` em todo log record automaticamente
  - Formato: `timestamp | LEVEL | module | rid=abc123 | mensagem`
  - `request_id` no body de `ErrorResponse` (correlação header ↔ body)
  - Logging em todas as camadas: controllers (início/fim), repositories (operações DB), services (mensagem recebida)
  - Stack traces completos nos erros 500 (logados, nunca expostos ao cliente)
- **Hardening nas camadas:**
  - Repository: try-except traduz `IntegrityError` → `ConflictError`, `OperationalError`/`TimeoutError` → `ServiceUnavailableError`, `SQLAlchemyError` → `DatabaseError`
  - **Unit of Work:** repositories usam `flush()` (não `commit()`). O `get_session()` gerencia a transação — `commit()` no sucesso, `rollback()` em qualquer erro. Uma transação por request HTTP.
  - Controller: captura `AppError` do repository, loga com contexto e re-raise
  - Timeout guard: `asyncio.wait_for(..., timeout=10s)` em todas as operações async de banco
  - Validation handler: extrai field name do Pydantic error, inclui no `ErrorDetail.field`
- **Validações de produção (`model_validator` em Settings):** CORS wildcard bloqueado, API key obrigatória e GROQ_API_KEY obrigatória quando `DEBUG=false`. Em modo debug, todas são relaxadas para conveniência de dev.
- CORS seguro por padrão: origens restritas (`http://localhost:3000`), wildcard `["*"]` só permitido com `DEBUG=true`
- Rate limiting via `slowapi` (padrão: `10/minute`, configurável via `RATE_LIMIT`). Aplicado ao `/chat` e `/conversations*`, rotas `/` e `/health` isentas
- Autenticação por API key (`X-API-Key` header) no `/chat` e `/conversations*` com `secrets.compare_digest` (proteção contra timing attack)
- **Identificação temporária:** `user_id` e `company_id` enviados no body do `/chat` (validados contra o banco, 404 se inexistentes). Serão migrados para token JWT na task 15 (Autenticação + Dashboard)
- **Banco de dados async (3 ambientes):**
  - **Testes:** SQLite in-memory (aiosqlite) — rápido, sem dependência
  - **Dev local:** PostgreSQL 18.1 (Postgres.app) — banco `barbershop`
  - **Produção:** Supabase PostgreSQL (us-west-2, Session Pooler) — banco `postgres`
  - `database.py`: engine, async_session, Base, get_session, create_tables, dispose_engine
  - `seed.py`: seed de dados para dev (1 Company + 1 User + 11 KnowledgeDocuments), idempotente, roda apenas com `DEBUG=true`
  - Lifespan handler no `main.py`: cria tabelas no startup, seed de dev (se debug), fecha engine no shutdown
- **Migrations (Alembic):**
  - `alembic.ini` + `migrations/env.py` configurados com async + URL dinâmica via Settings
  - Migration inicial: cria 4 tabelas, 4 FKs, 4 índices, 2 UNIQUE constraints
  - Migration `f97c79dc2341`: converte `status` e `sender` de VARCHAR para ENUM nativo no PostgreSQL (com `USING cast`, `checkfirst=True`)
- **5 Models SQLAlchemy** (centralizados em `app/models/`):
  - `Company`: id, name, address, phone, created_at, updated_at
  - `User`: id, company_id (FK RESTRICT), name, phone (UNIQUE), email (UNIQUE), is_active (default true), role (`UserRole` enum: customer/admin, default customer), password_hash, created_at, updated_at
  - `Conversation`: id, user_id (FK RESTRICT), company_id (FK RESTRICT), status (`ConversationStatus` enum: active/closed), started_at, ended_at
  - `Message`: id, conversation_id (FK CASCADE), sender (`MessageSender` enum: user/bot), content, created_at
  - `KnowledgeDocument`: id, company_id (FK RESTRICT), title, content (Text), category (`DocumentCategory` enum), is_active (default true), created_at, updated_at — índice composto (company_id, category)
  - **Enums tipados** (`app/models/enums.py`): `ConversationStatus` (active, closed), `MessageSender` (user, bot), `DocumentCategory` (services, hours, policies, faq, general) — todos `str, Enum`. Usados nos models (SQLAlchemy `Enum` type), controllers, repositories e schemas. Previnem dados inválidos na fonte.
- Configuração centralizada: `pydantic-settings` + `.env` (10 campos: app_name, app_version, debug, cors_origins, api_key, rate_limit, database_url, groq_api_key, llm_model, llm_max_history)
- Logger estruturado com `RequestIDFilter` + lazy formatting (`%s`) — sem log injection, sem conteúdo de mensagens (LGPD compliance)
- **Repositórios refatorados:** `app/repositories/` com UserRepository, CompanyRepository e KnowledgeDocumentRepository compartilhados (reutilizáveis por outros módulos), repositories chat usam decorator `@db_operation` eliminou ~200 linhas de boilerplate try/except
- **Controllers com schemas tipados:** ChatResponse, ConversationResponse, ConversationSummaryResponse, ConversationMessagesResponse, PaginationResponse garantem type safety e autocomplete
- **Health check com validação de banco:** GET `/api/v1/health` retorna 200 (status="ok", database="ok") ou 503 (status="degraded", database="unavailable")
- **Pool config otimizado para Supabase:** SQLite usa StaticPool (testes), PostgreSQL usa pool_size=5, max_overflow=10, pool_recycle=300, pool_pre_ping=True
- **Índices otimizados:** índice composto (conversation_id, created_at) em messages cobre query paginada (index-only scan)
- **Teste modernizados:** pytest.ini com `asyncio_mode = auto`, fixtures async nativas (`@pytest_asyncio.fixture`), sem `asyncio.new_event_loop()` manual
- **460 testes automatizados** — todos passando (prompts: 27, knowledge model: 11, knowledge repository: 12, LLM service: 9, context_service: 9, GROQ_API_KEY prod: 4, AIServiceError: 4, RAG controller: 4, RAG service: 3, RAG integração: 2, fallback: 4)
- `conftest.py` com fixtures `client`, `reset_rate_limiter` (autouse), `setup_db`, `db_session`, `mock_llm` (autouse global — nenhum teste chama API real do Groq) — todas async nativas com pytest-asyncio. `os.environ.setdefault("DEBUG", "true")` antes dos imports para compatibilidade com o validator de API key.
- Dependências separadas: `requirements.txt` (prod) e `requirements-dev.txt` (dev)

### Catálogo de Error Codes

| Code | Domínio | HTTP | Descrição |
|------|---------|------|-----------|
| APP_000 | Geral | 500 | Erro não tratado (catch-all) |
| AUTH_001 | Autenticação | 401 | API key ausente |
| AUTH_002 | Autorização | 403 | API key inválida ou ownership violado |
| CHAT_001 | Chat | 400 | Conteúdo repetitivo (spam) ou conversa encerrada |
| VAL_001 | Validação | 422 | Erro de validação (Pydantic) |
| RES_001 | Recurso | 404 | Recurso não encontrado |
| DB_001 | Banco | 500 | Erro genérico de banco |
| DB_002 | Banco | 409 | Violação de constraint (FK, UNIQUE) |
| DB_003 | Banco | 503 | Banco/serviço indisponível |
| RATE_001 | Rate Limit | 429 | Limite de requisições excedido |
| AI_001 | IA | 503 | Serviço de IA indisponível |
| HTTP_* | HTTP | varia | HTTPException do FastAPI/Starlette (404, 405, etc.) |

## Arquitetura

Monolito modular por domínio de negócio (preparado para futura evolução a microserviços):

```
backend/
  app/
    modules/                       # Módulos de domínio (auto-contidos)
      ai/
        prompts.py                 # BusinessInfo dataclass, seções modulares, build_system_prompt(business_info, context)
        llm_service.py             # LangChain + Groq: generate_ai_response(message, history, system_prompt), _build_history_messages
        context_service.py         # format_knowledge_context(documents) — agrupa docs por categoria com labels PT-BR
      chat/
        routes.py                  # POST /api/v1/chat (auth + rate limit)
        conversation_routes.py     # CRUD /api/v1/conversations (POST, GET /{id}, GET /{id}/messages, PATCH /{id}/close)
        controller.py              # ChatController + ConversationController (orquestração, validação, persistência)
        service.py                 # Lógica de negócio pura (validação, sanitização)
        repository.py              # ConversationRepository, MessageRepository, UserRepository, CompanyRepository
        schemas.py                 # ChatRequest, CreateConversationRequest, ChatResponse, MessageResponse, ConversationResponse, ConversationDetailResponse
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
      exceptions.py                # Hierarquia: AppError → 10 subclasses
      logger.py                    # Logger com RequestIDFilter
      db_utils.py                  # Decorator @db_operation, DB_TIMEOUT_SECONDS
    db/
      database.py                  # Engine async (com pool config Supabase), session factory, Base, get_session (Unit of Work), lifecycle helpers
      seed.py                      # Seed de dev (Company + User + 11 KnowledgeDocuments), idempotente, só DEBUG=true
    repositories/                  # Repositories compartilhados (reutilizáveis por múltiplos módulos)
      user_repository.py           # UserRepository (com @db_operation)
      company_repository.py        # CompanyRepository (com @db_operation)
      knowledge_repository.py      # KnowledgeDocumentRepository (get_by_company, get_by_category, create)
    models/                        # Models SQLAlchemy (centralizados, compartilhados)
      enums.py                     # ConversationStatus (active/closed), MessageSender (user/bot), DocumentCategory (services/hours/policies/faq/general)
      company.py                   # Model Company
      user.py                      # Model User (FK → Company)
      conversation.py              # Model Conversation (FK → User + Company, status enum)
      message.py                   # Model Message (FK → Conversation, sender enum)
      knowledge_document.py        # Model KnowledgeDocument (FK → Company, category enum, is_active)
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
      ai/
        test_prompts.py            # 27 testes do build_system_prompt (BusinessInfo, seções, dados opcionais, contexto RAG, fallback)
        test_llm_service.py        # 9 testes do generate_ai_response (mock ChatGroq, system_prompt, histórico, erro)
        test_context_service.py    # 9 testes do format_knowledge_context (vazio, agrupamento, labels PT-BR, ordem)
      chat/
        test_controller.py         # 23 testes do ChatController (nova conversa, existente, conversa fechada, user/company 404, ownership IDOR, delegação, RAG context)
        test_conversation_controller.py  # 24 testes do ConversationController (create, get_by_id, get_messages, close)
        test_service.py            # 19 testes do chat_service (sanitização, regras, generate_response, propagação de context RAG)
        test_repository.py         # 26 testes (ConversationRepository + MessageRepository + save_pair)
        test_schemas.py            # 39 testes (ChatRequest, ChatResponse, MessageResponse, ConversationResponse, ConversationDetailResponse)
        test_routes.py             # 28 testes de integração do /chat (inclui conversa fechada, persistência, ownership IDOR, atomicidade, RAG)
        test_conversation_routes.py  # 32 testes de integração do /conversations (CRUD completo + validação + paginação)
      health/
        test_controller.py         # 9 testes do HealthController (DB ok, DB down, exceções)
        test_schemas.py            # 1 teste do HealthResponse
        test_routes.py             # 7 testes de integração do /health (200 OK, 503 DB fora, status/database fields)
    core/
      test_schemas.py              # 20 testes dos schemas compartilhados
      test_exceptions.py           # 56 testes da hierarquia de exceções
      test_error_handlers.py       # 17 testes dos handlers
      test_logging.py              # 15 testes de request ID
      test_hardening.py            # 20 testes de hardening (Message + Conversation repos, controller, validation)
      test_security.py             # 20 testes de segurança (rate limit, API key auth, CORS config, API key obrigatória em prod, GROQ_API_KEY obrigatória em prod)
    conftest.py                    # Fixtures: client, reset_rate_limiter, setup_db, db_session, mock_llm (autouse global)
    test_models.py                 # 42 testes dos models (Company, User, Conversation, Message, KnowledgeDocument + enums)
    test_knowledge_repository.py   # 12 testes do KnowledgeDocumentRepository (create, get_by_company, get_by_category, is_active, isolamento)
    test_root.py                   # 1 teste do GET /
```

**Fluxo do chat (com RAG):** Cliente → Routes → RequestIDMiddleware (UUID server-side) → Auth + Rate Limit → Controller (valida user/company → resolve/cria conversa → valida ownership → valida conversa ativa → monta BusinessInfo → busca histórico → **busca documentos via knowledge_repo.get_by_company → format_knowledge_context** → Service sanitiza/valida → build_system_prompt(business_info, context) → llm_service.generate_ai_response(msg, history, prompt) → persiste user+bot msg via save_pair) → `get_session` commit → SuccessResponse com `{response, conversation_id}`. Se qualquer etapa falhar, `get_session` faz rollback de tudo (Unit of Work).

**Fluxo de erros:** Exceção → Exception Handler (AppError/HTTP/Validation/RateLimit/DB) → ErrorResponse padronizado com code + request_id → Cliente

## Stack

- **Linguagem:** Python 3.13
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Validação:** Pydantic
- **ORM:** SQLAlchemy (async)
- **Migrations:** Alembic (async)
- **IA/LLM:** LangChain + Groq (Llama 3.3 70B Versatile)
- **DB testes:** SQLite in-memory + aiosqlite
- **DB dev:** PostgreSQL 18.1 (Postgres.app) + asyncpg
- **DB prod:** Supabase PostgreSQL + asyncpg (Session Pooler, us-west-2)
- **Ambiente:** venv + pip
- **Testes:** pytest + httpx + pytest-asyncio (TestClient do FastAPI)
- **Configuração:** pydantic-settings (carrega `.env` automaticamente)
- **Rate Limiting:** slowapi
- **Autenticação:** API key via header (fastapi.security + secrets)
- **Dependências prod:** `requirements.txt` (fastapi, uvicorn, pydantic-settings, slowapi, sqlalchemy[asyncio], aiosqlite, asyncpg, alembic, langchain, langchain-groq, langchain-core)
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
10. ~~Histórico de conversas (CRUD completo, persistência atômica, 340 testes)~~ ✅
10.1. ~~Hardening de segurança (ownership IDOR, API key obrigatória em prod, enums tipados, Unit of Work, request ID server-only — 358 testes)~~ ✅
10.2. ~~Refatoração de código (10 itens média/baixa prioridade, 375 testes)~~ ✅
   - ~~Extrair UserRepository + CompanyRepository para módulo compartilhado~~ ✅
   - ~~Schemas tipados em controllers~~ ✅
   - ~~Decorator @db_operation para eliminar boilerplate~~ ✅
   - ~~create_tables() condicional a debug~~ ✅
   - ~~Não logar conteúdo de mensagens~~ ✅
   - ~~Índice composto em messages~~ ✅
   - ~~Remover dead code (get_active_by_user)~~ ✅
   - ~~pytest-asyncio nativo~~ ✅
   - ~~Health check com DB validation~~ ✅
   - ~~Pool config para Supabase~~ ✅
11. ~~Criação de serviço de geração de respostas (LangChain + Groq, Llama 3.3 70B, 392 testes)~~ ✅
12. ~~Criar estrutura de prompts da IA (prompt modular, BusinessInfo, build_system_prompt, 415 testes)~~ ✅
13. ~~Criar base de conhecimento do sistema (KnowledgeDocument, DocumentCategory, seed 11 docs, 438 testes)~~ ✅
14. ~~Implementar busca de contexto (RAG) — context_service, agrupamento por categoria, integração no controller, 456 testes~~ ✅
15. ~~Fallback para respostas desconhecidas — regras de off-topic e informação desconhecida reforçadas no prompt, 460 testes~~ ✅
16. **Agendamento automático de horários** ← PRÓXIMO
16. Integração com WhatsApp/Instagram
17. Autenticação e dashboard administrativo ← `user_id`/`company_id` migram do body para token JWT nesta task
18. Docker + deploy

## Convenções

- Código e nomes de variáveis em **inglês**
- Documentação e comunicação em **português brasileiro**
- **Arquitetura modular por domínio** — cada módulo em `app/modules/<domínio>/` com routes, controller, service, repository e schemas próprios
- Infraestrutura compartilhada em `app/core/`, models em `app/models/`, schemas base em `app/schemas/`
- **Testes espelham a estrutura:** `tests/modules/<domínio>/`, `tests/core/`
- Abordagem incremental: validar antes de evoluir
- Manter este arquivo e os arquivos de memória atualizados a cada mudança significativa
