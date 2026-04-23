# AI Barbershop Assistant

TCC — backend de atendimento automatizado para barbearias via IA generativa (FastAPI + Groq + LangChain).

## Estado atual

**508 testes.** JWT concluído (`POST /chat` e `POST /conversations` usam JWT; GET/PATCH de conversas ainda usam API key). Próximo: agendamento automático de horários.

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

## Arquitetura

Monolito modular por domínio em `app/modules/<domínio>/` (routes, controller, service, repository, schemas). Infraestrutura compartilhada em `app/core/`, models em `app/models/`, repositories reutilizáveis em `app/repositories/`.

Bancos: SQLite in-memory (testes), PostgreSQL local (dev, banco `barbershop`), Supabase PostgreSQL (prod).

## Convenções

- Código e variáveis em **inglês**; docs e comunicação em **português brasileiro**
- Testes espelham a estrutura: `tests/modules/<domínio>/`, `tests/core/`
- `conftest.py`: `mock_llm` é autouse global — nenhum teste chama a API real do Groq
- `os.environ.setdefault("DEBUG", "true")` no topo do `conftest.py` — necessário para o validator de Settings não exigir API key nos testes
- Unit of Work: repositories usam `flush()`, nunca `commit()`. O `get_session()` faz commit/rollback
- Validações de prod em `Settings`: CORS wildcard e API keys obrigatórias quando `DEBUG=false`
- Logs nunca incluem conteúdo de mensagens (LGPD)
- Request ID sempre gerado server-side (ignora header do cliente — previne log injection)
