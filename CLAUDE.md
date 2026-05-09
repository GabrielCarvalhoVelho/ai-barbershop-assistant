# AI Barbershop Assistant

TCC — backend de atendimento automatizado para barbearias via IA generativa (FastAPI + Groq + LangChain).

## Estado atual

**775 testes.** Sistema de agendamento automático + RBAC consolidado + integração WhatsApp Cloud API:
- Model `Appointment` + migração Alembic (`appointmentstatus` ENUM portável SQLite/PostgreSQL)
- `AppointmentRepository` com detecção de conflito portável (Python-side overlap check)
- Schemas Pydantic, service com regras de negócio, controller, 4 endpoints REST protegidos por JWT
- Integração LLM: assistente emite bloco `<APPOINTMENT>` → parser extrai e valida → cria no banco
- Endpoints customer: `POST /api/v1/appointments/`, `GET /api/v1/appointments/me`, `GET /api/v1/appointments/{id}`, `PATCH /api/v1/appointments/{id}/cancel`
- Endpoints admin: `GET /api/v1/admin/appointments/`, `GET /api/v1/admin/users/`, `PATCH /api/v1/admin/users/{id}/role`, `PATCH /api/v1/admin/users/{id}/active`
- Error codes por domínio: `APT_001` (conflito de horário), `CHAT_001` (spam/regras de chat), `USR_001` (auto-proteção do admin)

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

## Controle de Permissões (RBAC)

- **Roles:** `UserRole.CUSTOMER` (default no signup) e `UserRole.ADMIN`. Promoção via `PATCH /api/v1/admin/users/{id}/role`
- **Dependency factory `require_role(*roles)`** em [app/core/auth.py](backend/app/core/auth.py): aplica em rotas que exigem role específico (`Depends(require_role(UserRole.ADMIN))`)
- **Helper `ensure_owner_or_admin`** em [app/core/permissions.py](backend/app/core/permissions.py): centraliza checagem "owner do recurso OU admin da empresa". Usar com `resource_company_id` para isolar multi-tenancy (admin da empresa A não acessa dados da B)
- **Auto-proteção do admin:** admin não pode rebaixar/desativar a si mesmo; sistema bloqueia rebaixar/desativar o último admin ativo da empresa (`USR_001`)
- **Target em outra empresa retorna 404, não 403** — para não vazar existência do recurso
- **Mudanças de role/active são logadas** (auditoria sem dados sensíveis): `admin_id`, `target_id`, `old_role/new_role` ou `is_active`

## WhatsApp Cloud API

- **Webhook:** `GET/POST /api/v1/webhooks/whatsapp` em [app/modules/whatsapp/routes.py](backend/app/modules/whatsapp/routes.py)
- **GET (verify):** Meta envia `hub.mode`, `hub.verify_token`, `hub.challenge`. Se `verify_token` bater com `WHATSAPP_VERIFY_TOKEN`, retorna o challenge cru. Caso contrário 403.
- **POST (events):** Valida `X-Hub-Signature-256` (HMAC SHA256 do body bruto com `WHATSAPP_APP_SECRET`). Sem header válido → 403.
- **Idempotência:** mensagens persistem com `whatsapp_message_id` (UNIQUE). Mesma `wamid` recebida duas vezes é processada uma única vez.
- **Auto-cadastro:** phone desconhecido cria User com `role=CUSTOMER`, `password_hash="!"` (sentinel — não permite login pelo painel até definir senha). Empresa = `WHATSAPP_DEFAULT_COMPANY_ID` (1 número → 1 empresa hoje).
- **Reuso:** o service WhatsApp chama `chat.service.generate_response`, `appointment_parser` e `appointment_repo` — mesmo pipeline de IA do chat REST, apenas com adapter diferente de entrada/saída.
- **Cliente outbound:** `WhatsAppClient.send_text()` em [client.py](backend/app/modules/whatsapp/client.py) usa httpx; injetado via `Depends(get_whatsapp_client)` para facilitar mock em testes.
- **Setup local de webhook:** Cloudflare Tunnel → URL pública → configurar no painel Meta como webhook callback URL com verify token igual ao `.env`.
