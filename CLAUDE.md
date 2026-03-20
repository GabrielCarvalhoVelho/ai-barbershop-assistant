# AI Barbershop Assistant

## O que é este projeto

Sistema backend de atendimento e agendamento automatizado para barbearias, usando Inteligência Artificial Generativa. Desenvolvido como TCC (Trabalho de Conclusão de Curso).

O sistema recebe mensagens de clientes, interpreta intenções com IA e gera respostas automatizadas — simulando um atendente virtual 24/7 para barbearias de pequeno/médio porte.

## Estado atual

**Fase: MVP inicial** — estrutura base com respostas mock e validação completa. Sem IA real nem banco de dados ainda.

- FastAPI + Uvicorn rodando com metadados (title, version via `Settings`)
- Endpoints: `GET /` (root), `GET /api/v1/health`, `POST /api/v1/chat`
- Endpoints async (`async def`) — preparados para I/O não-bloqueante
- Chat retorna echo: `"Você disse: {message}"`
- Validação em 3 camadas:
  - **Schema (Pydantic):** formato — vazio, tamanho (1-500), strip whitespace, só especiais, char repetido único → `422`
  - **Service (negócio):** conteúdo — spam (10+ chars repetidos, palavra 5x seguida), sanitização de espaços internos → `400`
  - **Middleware (catch-all):** erros internos inesperados → `500`
- Schemas Pydantic: `ChatRequest`, `ChatResponse` (timestamp UTC), `HealthResponse`, `ErrorResponse` (com campo `details` opcional)
- Exception handlers registrados: `RequestValidationError` (422), `BusinessError` (400), `RateLimitExceeded` (429)
- CORS seguro por padrão: origens restritas (`http://localhost:3000`), wildcard `["*"]` só permitido com `DEBUG=true`
- Validador `warn_wildcard_cors` impede `CORS_ORIGINS=["*"]` em produção (levanta `ValueError`)
- Rate limiting via `slowapi` (padrão: `10/minute`, configurável via `RATE_LIMIT`). Aplicado ao `/chat`, rotas `/` e `/health` isentas
- Autenticação por API key (`X-API-Key` header) no `/chat`. Opcional: se `API_KEY` vazio, acesso livre; se definido, exige header válido (401/403)
- Módulo `core/auth.py`: dependência `require_api_key` com `APIKeyHeader`
- Módulo `core/rate_limiter.py`: instância `Limiter` centralizada com `get_remote_address`
- Configuração centralizada: `pydantic-settings` + `.env` (com `.env.example` documentando variáveis)
- Logger configurado com lazy formatting (`%s`) — sem log injection
- Camada de controllers: `ChatController` (orquestra chat) e `HealthController` (orquestra health)
- 69 testes automatizados (schemas, controllers, services, API integração, segurança) — todos passando
- `conftest.py` com fixtures `client` e `reset_rate_limiter` (autouse) para testes de integração
- Dependências separadas: `requirements.txt` (prod) e `requirements-dev.txt` (dev)
- Placeholders vazios: `database.py`, `models/message.py`

## Arquitetura

Monolito em camadas (preparado para futura evolução a microserviços):

```
backend/
  app/
    api/routes.py              # Rotas HTTP async — root_router (/) e router (/api/v1/*)
    controllers/
      chat_controller.py       # Orquestração do chat (monta ChatResponse a partir do service)
      health_controller.py     # Orquestração do health check
    core/config.py             # Settings centralizado (pydantic-settings + .env + validador CORS)
    core/auth.py           # Autenticação por API key (X-API-Key header)
    core/rate_limiter.py   # Rate limiting centralizado (slowapi)
    core/error_handler.py  # Handlers de erro (validação 422, negócio 400, rate limit 429, catch-all 500)
    core/exceptions.py     # Exceções customizadas (BusinessError)
    core/logger.py         # Setup de logging
    db/database.py         # Conexão com banco (placeholder)
    models/message.py      # Models do banco (placeholder)
    schemas/chat_schema.py   # ChatRequest (validado) + ChatResponse (timestamp UTC)
    schemas/health_schema.py # HealthResponse
    schemas/error_schema.py  # ErrorResponse (usado no error handler)
    services/chat_service.py # Lógica de negócio pura (retorna str, sem schemas)
    main.py                # Entry point (config, CORS, middleware, handlers — sem rotas)
  tests/
    conftest.py            # Fixtures compartilhadas (client)
    test_schemas.py        # Testes unitários dos schemas Pydantic (16 testes)
    test_controllers.py    # Testes unitários dos controllers (7 testes)
    test_services.py       # Testes unitários do chat_service (11 testes)
    test_api.py            # Testes de integração dos endpoints (13 testes)
    test_security.py       # Testes de segurança: rate limit, auth, CORS (12 testes)
```

**Fluxo:** Cliente → Routes (HTTP puro) → Controllers (orquestração + monta response) → Services (negócio, retorna dados puros) → (futuramente: IA + DB) → Resposta

## Stack

- **Linguagem:** Python 3.13
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Validação:** Pydantic
- **Ambiente:** venv + pip
- **Testes:** pytest + httpx (TestClient do FastAPI)
- **Configuração:** pydantic-settings (carrega `.env` automaticamente)
- **Rate Limiting:** slowapi
- **Autenticação:** API key via header (fastapi.security)
- **Dependências prod:** `requirements.txt` (fastapi==0.135.1, uvicorn==0.42.0, pydantic-settings==2.13.1, slowapi==0.1.9)
- **Dependências dev:** `requirements-dev.txt` (inclui prod + pytest==9.0.2, httpx==0.28.1)

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
3. Integração com IA generativa (OpenAI API + LangChain)
4. Banco de dados (PostgreSQL)
5. Histórico de conversas
6. RAG (Retrieval Augmented Generation) para respostas contextualizadas
7. Agendamento automático de horários
8. Integração com WhatsApp/Instagram
9. Autenticação e dashboard administrativo
10. Docker + deploy

## Convenções

- Código e nomes de variáveis em **inglês**
- Documentação e comunicação em **português brasileiro**
- Arquitetura em camadas — manter separação de responsabilidades (routes → controllers → services → schemas/core/db)
- Abordagem incremental: validar antes de evoluir
- Manter este arquivo e os arquivos de memória atualizados a cada mudança significativa
