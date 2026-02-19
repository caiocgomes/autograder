# Autograder

Plataforma de correção automática de código com execução isolada em sandbox Docker e feedback via LLM. Monorepo com backend FastAPI + frontend React.

## O que faz

- Professor cria turmas, listas de exercícios e casos de teste
- Aluno submete código via interface web ou API
- Sistema executa o código em container Docker isolado (sem rede, filesystem read-only, user não-root, timeout de 30s, 512MB RAM)
- Opcionalmente chama OpenAI ou Anthropic para feedback qualitativo além da nota dos testes
- Score final = `test_weight * test_score + llm_weight * llm_score`, com penalidade configurável por dia de atraso
- Integra com Hotmart (gestão de matrículas via webhook), Discord (bot de onboarding) e ManyChat (notificações WhatsApp)

---

## Stack

| Camada | Tecnologia |
|---|---|
| API | Python 3.12 + FastAPI + SQLAlchemy |
| Workers | Celery + Redis |
| Banco | PostgreSQL 16 |
| Sandbox | Docker SDK (não CLI) |
| Frontend | React + TypeScript + Vite + Zustand |
| Auth | JWT (access 15min / refresh 7 dias) + bcrypt |

---

## Quick Start (dev)

### Pré-requisitos

- Docker Desktop rodando
- `uv` instalado (`pip install uv` ou `brew install uv`)
- Node 18+

### 1. Infraestrutura

```bash
# Da raiz do repo
docker compose up -d
```

Sobe Postgres (5432), Redis (6379), backend (8000) e worker Celery. O backend dentro do container já roda com hot-reload via volume mount.

### 2. Banco de dados

```bash
cd autograder-back
uv sync --all-extras
uv run alembic upgrade head
```

### 3. Sandbox image (obrigatório para execução de código)

```bash
# Da raiz do repo
docker build -f Dockerfile.sandbox -t autograder-sandbox .
```

### 4. Variáveis de ambiente

```bash
cp autograder-back/.env.example autograder-back/.env
```

Para rodar sem integrações externas, os únicos campos que você precisa alterar são `JWT_SECRET_KEY` (qualquer string) e a chave LLM se quiser testar grading com IA. Todos os demais têm defaults funcionais para dev.

### 5. Frontend

```bash
cd autograder-web
npm install
npm run dev   # http://localhost:5173
```

API docs em http://localhost:8000/docs

---

## Referência de Configuração

Todas as variáveis vão em `autograder-back/.env`. O backend lê via Pydantic Settings — qualquer variável ausente usa o default listado abaixo.

### Banco e fila (obrigatórias em produção)

| Variável | Default | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql://autograder:autograder@localhost:5432/autograder` | Connection string Postgres |
| `REDIS_URL` | `redis://localhost:6379/0` | URL Redis para Celery broker/backend |
| `REDIS_HOST` | `localhost` | Host Redis (usado pelo rate limiter de login) |
| `REDIS_PORT` | `6379` | Porta Redis |
| `REDIS_DB` | `0` | Database Redis |
| `REDIS_PASSWORD` | _(vazio)_ | Senha Redis — obrigatória em produção |

### Auth JWT

| Variável | Default | Descrição |
|---|---|---|
| `JWT_SECRET_KEY` | `dev-secret-key-change-in-production` | **Trocar em produção.** Assina todos os tokens |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de assinatura |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Validade do access token |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Validade do refresh token |
| `BCRYPT_COST_FACTOR` | `12` | Custo do hash de senha (aumentar = mais lento) |
| `RATE_LIMIT_FAILED_LOGINS` | `5` | Tentativas antes de bloquear login |
| `RATE_LIMIT_WINDOW_MINUTES` | `15` | Janela do rate limit de login |

### LLM (opcional — só para grading com IA)

Exercícios têm um toggle individual para LLM. Se desabilitado no exercício, nenhuma chave é necessária.

| Variável | Default | Descrição |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Qual provedor usar: `openai` ou `anthropic` |
| `OPENAI_API_KEY` | _(vazio)_ | Chave OpenAI — necessária se `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | _(vazio)_ | Chave Anthropic — necessária se `LLM_PROVIDER=anthropic` |

### Sandbox Docker

| Variável | Default | Descrição |
|---|---|---|
| `DOCKER_IMAGE_SANDBOX` | `autograder-sandbox:latest` | Image usada para executar código dos alunos |
| `SANDBOX_TIMEOUT_SECONDS` | `30` | Tempo máximo de execução por submission |
| `SANDBOX_MEMORY_LIMIT_MB` | `512` | Limite de RAM do container |
| `SANDBOX_CPU_LIMIT` | `1` | Limite de CPUs |

Em macOS, se o Docker não encontrar o socket padrão, o código tenta automaticamente `~/.docker/run/docker.sock`.

### Uploads de arquivo

Usado quando o exercício aceita envio de arquivo (PDFs, notebooks, etc.) além de código.

| Variável | Default | Descrição |
|---|---|---|
| `UPLOAD_BASE_DIR` | `./uploads` | Diretório base para arquivos enviados |
| `MAX_EXERCISE_FILE_SIZE_MB` | `10` | Tamanho máximo de arquivo de exercício |
| `MAX_SUBMISSION_FILE_SIZE_MB` | `10` | Tamanho máximo de submission de arquivo |

### API e CORS

| Variável | Default | Descrição |
|---|---|---|
| `CORS_ORIGINS` | `*` | Origins permitidos. Em produção: `https://meusite.com,https://outro.com` |
| `ENVIRONMENT` | `development` | `development`, `staging` ou `production` |
| `DEBUG` | `true` | Ativa modo debug do FastAPI |
| `LOG_LEVEL` | `INFO` | Nível de log: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | `text` | `text` para dev, `json` para coleta em produção |

### Email (para reset de senha)

| Variável | Default | Descrição |
|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | Servidor SMTP |
| `SMTP_PORT` | `587` | Porta SMTP |
| `SMTP_USER` | _(vazio)_ | Usuário SMTP |
| `SMTP_PASSWORD` | _(vazio)_ | Senha do app Gmail (não a senha da conta) |
| `SMTP_FROM` | `noreply@autograder.com` | Endereço remetente |

### Hotmart (webhook de compras)

Ativado com `HOTMART_WEBHOOK_ENABLED=true`. Recebe eventos de compra/cancelamento e dispara a máquina de estados de lifecycle do aluno.

Eventos suportados: `PURCHASE_APPROVED`, `PURCHASE_DELAYED`, `PURCHASE_REFUNDED`, `SUBSCRIPTION_CANCELLATION`.

| Variável | Default | Descrição |
|---|---|---|
| `HOTMART_WEBHOOK_ENABLED` | `false` | Liga o processamento de webhooks Hotmart |
| `HOTMART_HOTTOK` | _(vazio)_ | Token secreto configurado no painel Hotmart (header `X-Hotmart-Hottok`) |

Endpoint: `POST /webhooks/hotmart`

### Discord (bot de onboarding)

Ativado com `DISCORD_ENABLED=true`. O bot é um processo separado — não roda dentro do FastAPI.

| Variável | Default | Descrição |
|---|---|---|
| `DISCORD_ENABLED` | `false` | Liga gerenciamento de roles e notificações via Discord |
| `DISCORD_BOT_TOKEN` | _(vazio)_ | Token do bot (Discord Developer Portal) |
| `DISCORD_GUILD_ID` | _(vazio)_ | ID do servidor Discord |
| `DISCORD_REGISTRATION_CHANNEL_ID` | _(vazio)_ | Canal onde o bot responde ao `/registrar` |

O bot expõe o slash command `/registrar <token>` que vincula a conta Discord ao registro do aluno. O token de onboarding é gerado automaticamente quando um aluno entra em `pending_onboarding`.

Para rodar o bot localmente:
```bash
cd autograder-back
uv run python -m app.discord_bot
```

Para rodar via Docker:
```bash
docker compose --profile discord up -d
```

### ManyChat (notificações WhatsApp)

Ativado com `MANYCHAT_ENABLED=true`. Dispara flows automáticos em eventos de lifecycle (welcome, churn, nova atividade, etc.).

| Variável | Default | Descrição |
|---|---|---|
| `MANYCHAT_ENABLED` | `false` | Liga envio de mensagens via ManyChat |
| `MANYCHAT_API_TOKEN` | _(vazio)_ | API token do ManyChat |
| `MANYCHAT_ONBOARDING_FLOW_ID` | _(vazio)_ | Flow disparado ao entrar em `pending_onboarding` |
| `MANYCHAT_WELCOME_FLOW_ID` | _(vazio)_ | Flow disparado ao ativar |
| `MANYCHAT_CHURN_FLOW_ID` | _(vazio)_ | Flow disparado ao churnar |
| `MANYCHAT_WELCOME_BACK_FLOW_ID` | _(vazio)_ | Flow disparado na reativação |
| `MANYCHAT_NEW_ASSIGNMENT_FLOW_ID` | _(vazio)_ | Flow disparado ao publicar nova lista |
| `MANYCHAT_DEADLINE_REMINDER_FLOW_ID` | _(vazio)_ | Flow de lembrete de prazo |

---

## Lifecycle de Alunos

Máquina de estados disparada por webhooks Hotmart ou eventos manuais via admin:

```
(novo) ──purchase_approved──► pending_onboarding ──discord_registered──► active
(novo) ──purchase_delayed───► pending_payment
pending_payment ──purchase_approved──► pending_onboarding
active ──subscription_cancelled / purchase_refunded──► churned
churned ──purchase_approved──► active
```

Cada transição executa side-effects em ordem (enroll em turma, Discord role, ManyChat notification). Falhas de side-effect são retentadas uma vez via Celery; falhas persistentes são logadas sem bloquear a transição de estado.

---

## Roles de Usuário

| Role | Acesso |
|---|---|
| `admin` | Tudo, incluindo gestão de produtos e eventos |
| `professor` | Criar turmas, exercícios, ver correções |
| `ta` | Mesmo que professor (alias) |
| `student` | Submeter código, ver próprias notas |

---

## Comandos úteis

```bash
# Backend (rodar de autograder-back/)
uv run pytest                                    # todos os testes
uv run pytest tests/test_auth_router.py          # arquivo específico
uv run pytest -k "test_create_class"             # teste por nome
uv run alembic upgrade head                      # aplicar migrations
uv run alembic revision --autogenerate -m "desc" # gerar migration

# Infraestrutura (da raiz)
docker compose logs -f backend    # logs da API
docker compose logs -f worker     # logs do worker Celery
docker compose restart backend    # restart sem rebuild

# Frontend (de autograder-web/)
npm run dev      # dev server porta 5173
npm run build    # build de produção
npm run lint     # ESLint
```

---

## Produção

```bash
docker compose -f docker-compose.prod.yml up -d
```

O compose de produção adiciona:
- Nginx (portas 80/443) com config em `nginx/nginx.conf` e certs em `nginx/certs/`
- Backup diário do Postgres (retém 7 dias) em `./backups/`
- Redis com senha obrigatória
- `ENVIRONMENT=production`, `DEBUG=false`

Variáveis adicionais necessárias em produção no `.env`:
```
POSTGRES_PASSWORD=senha-forte
REDIS_PASSWORD=senha-forte
JWT_SECRET_KEY=string-aleatoria-longa
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://seudominio.com
LOG_FORMAT=json
```
