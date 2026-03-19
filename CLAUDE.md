# AI Barbershop Assistant

## O que é este projeto

Sistema backend de atendimento e agendamento automatizado para barbearias, usando Inteligência Artificial Generativa. Desenvolvido como TCC (Trabalho de Conclusão de Curso).

O sistema recebe mensagens de clientes, interpreta intenções com IA e gera respostas automatizadas — simulando um atendente virtual 24/7 para barbearias de pequeno/médio porte.

## Estado atual

**Fase: MVP inicial** — estrutura base com respostas mock. Sem IA real nem banco de dados ainda.

- FastAPI + Uvicorn rodando
- Endpoints: `GET /` (root), `GET /health`, `POST /chat`
- Chat retorna echo: `"Você disse: {message}"`
- Schemas Pydantic completos com validação (request, response e erro)
- Middleware de error handling com `ErrorResponse` padronizado
- Logger configurado
- Placeholders vazios: `config.py`, `database.py`, `models/message.py`

## Arquitetura

Monolito em camadas (preparado para futura evolução a microserviços):

```
backend/
  app/
    api/routes.py          # Rotas da API (endpoints)
    core/config.py         # Configurações (placeholder)
    core/error_handler.py  # Middleware de tratamento de erros
    core/logger.py         # Setup de logging
    db/database.py         # Conexão com banco (placeholder)
    models/message.py      # Models do banco (placeholder)
    schemas/chat_schema.py   # ChatRequest (validado) + ChatResponse
    schemas/health_schema.py # HealthResponse
    schemas/error_schema.py  # ErrorResponse (usado no error handler)
    services/chat_service.py # Lógica de negócio (chat)
    main.py                # Entry point da aplicação
```

**Fluxo:** Cliente → API (routes) → Services → (futuramente: IA + DB) → Resposta

## Stack

- **Linguagem:** Python 3.13
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Validação:** Pydantic
- **Ambiente:** venv + pip
- **Dependências:** `requirements.txt` (fastapi, uvicorn, python-dotenv)

## Como rodar

```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload
```

## Roadmap (próximos passos)

1. Integração com IA generativa (OpenAI API + LangChain)
2. Banco de dados (PostgreSQL)
3. Histórico de conversas
4. RAG (Retrieval Augmented Generation) para respostas contextualizadas
5. Agendamento automático de horários
6. Integração com WhatsApp/Instagram
7. Autenticação e dashboard administrativo
8. Docker + deploy

## Convenções

- Código e nomes de variáveis em **inglês**
- Documentação e comunicação em **português brasileiro**
- Arquitetura em camadas — manter separação de responsabilidades (routes, services, schemas, core, db)
- Abordagem incremental: validar antes de evoluir
- Manter este arquivo e os arquivos de memória atualizados a cada mudança significativa
