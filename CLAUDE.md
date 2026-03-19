# AI Barbershop Assistant

## O que é este projeto

Sistema backend de atendimento e agendamento automatizado para barbearias, usando Inteligência Artificial Generativa. Desenvolvido como TCC (Trabalho de Conclusão de Curso).

O sistema recebe mensagens de clientes, interpreta intenções com IA e gera respostas automatizadas — simulando um atendente virtual 24/7 para barbearias de pequeno/médio porte.

## Estado atual

**Fase: MVP inicial** — estrutura base com respostas mock e validação completa. Sem IA real nem banco de dados ainda.

- FastAPI + Uvicorn rodando
- Endpoints: `GET /` (root), `GET /health`, `POST /chat`
- Chat retorna echo: `"Você disse: {message}"`
- Validação em 3 camadas:
  - **Schema (Pydantic):** formato — vazio, tamanho (1-500), strip whitespace, só especiais, char repetido único → `422`
  - **Service (negócio):** conteúdo — spam (10+ chars repetidos, palavra 5x seguida), sanitização de espaços internos → `400`
  - **Middleware (catch-all):** erros internos inesperados → `500`
- Schemas Pydantic: `ChatRequest`, `ChatResponse`, `HealthResponse`, `ErrorResponse` (com campo `details` opcional)
- Exception handlers registrados: `RequestValidationError` (422), `BusinessError` (400)
- Logger configurado
- 50 testes automatizados (schemas, services, API integração) — todos passando
- Placeholders vazios: `config.py`, `database.py`, `models/message.py`

## Arquitetura

Monolito em camadas (preparado para futura evolução a microserviços):

```
backend/
  app/
    api/routes.py          # Todas as rotas da API (/, /health, /chat)
    core/config.py         # Configurações (placeholder)
    core/error_handler.py  # Handlers de erro (validação 422, negócio 400, catch-all 500)
    core/exceptions.py     # Exceções customizadas (BusinessError)
    core/logger.py         # Setup de logging
    db/database.py         # Conexão com banco (placeholder)
    models/message.py      # Models do banco (placeholder)
    schemas/chat_schema.py   # ChatRequest (validado) + ChatResponse
    schemas/health_schema.py # HealthResponse
    schemas/error_schema.py  # ErrorResponse (usado no error handler)
    services/chat_service.py # Lógica de negócio (chat)
    main.py                # Entry point (config, middleware, handlers — sem rotas)
  tests/
    test_schemas.py        # Testes unitários dos schemas Pydantic (16 testes)
    test_services.py       # Testes unitários do chat_service (11 testes)
    test_api.py            # Testes de integração dos endpoints (13 testes)
```

**Fluxo:** Cliente → API (routes) → Services (sanitização + regras de negócio) → (futuramente: IA + DB) → Resposta

## Stack

- **Linguagem:** Python 3.13
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Validação:** Pydantic
- **Ambiente:** venv + pip
- **Testes:** pytest + httpx (TestClient do FastAPI)
- **Dependências:** `requirements.txt` com versões fixas (fastapi==0.135.1, uvicorn==0.42.0, python-dotenv==1.2.2, pytest==9.0.2, httpx==0.28.1)

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
2. Integração com IA generativa (OpenAI API + LangChain)
3. Banco de dados (PostgreSQL)
4. Histórico de conversas
5. RAG (Retrieval Augmented Generation) para respostas contextualizadas
6. Agendamento automático de horários
7. Integração com WhatsApp/Instagram
8. Autenticação e dashboard administrativo
9. Docker + deploy

## Convenções

- Código e nomes de variáveis em **inglês**
- Documentação e comunicação em **português brasileiro**
- Arquitetura em camadas — manter separação de responsabilidades (routes, services, schemas, core, db)
- Abordagem incremental: validar antes de evoluir
- Manter este arquivo e os arquivos de memória atualizados a cada mudança significativa
