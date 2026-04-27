# AI Barbershop Assistant

TCC — backend de atendimento automatizado para barbearias via IA generativa (FastAPI + Groq + LangChain).

## Estado atual

**556 testes.** Checklist de autenticação fechado: middleware de segurança, account lockout, log de falhas de auth (LGPD-safe, sem phone/password nos logs), admin CRUD da base de conhecimento com `require_role(ADMIN)` em `/api/v1/admin/knowledge`. Próximo: agendamento automático de horários.

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
- Logs nunca incluem conteúdo de mensagens nem dados sensíveis (LGPD): phone, email, passwords nunca são logados
- Request ID sempre gerado server-side (ignora header do cliente — previne log injection)

## Segurança de Autenticação

- **Login (`POST /api/v1/auth/login`):** Rate limit 5/minute (contra brute force), validação de telefone (10-20 chars), password (6+ chars)
- **JWT:** HS256, expira em 30 minutos, sempre validado em endpoints protegidos
- **Password hashing:** bcrypt (timing-attack safe), nunca armazenado em plaintext
- **Error messages:** Genéricas ("Credenciais inválidas") — mesmo erro para usuário não encontrado ou senha errada (previne user enumeration)
- **DB indexes:** phone e email têm índices únicos (UNIQUE constraint auto-cria B-tree em PostgreSQL)
