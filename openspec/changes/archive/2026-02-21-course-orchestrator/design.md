## Context

O autograder é um monorepo (FastAPI backend + React frontend) que hoje gerencia exercícios, submissions e grading. O lifecycle do aluno (pagamento na Hotmart, acesso ao Discord, comunicação via WhatsApp) é inteiramente manual. Com 400 alunos ativos, 2-3 produtos com acessos distintos e churn médio, a automação desse ciclo é o próximo passo natural.

O sistema atual já tem: User (com roles), Class, ClassEnrollment, Exercise, Submission, e processamento assíncrono via Celery. A base está pronta para ser estendida.

## Goals / Non-Goals

**Goals:**
- Automatizar o ciclo completo: pagamento → onboarding → acesso → churn
- Orquestrar Discord (roles), ManyChat (tags + flows), e classes internas a partir de eventos Hotmart
- Manter auditoria completa via event log
- Operar com resiliência suficiente pra 400 alunos (retry 1x + alerta manual)

**Non-Goals:**
- Substituir Discord, ManyChat ou Hotmart (o sistema orquestra, não replica)
- Frontend admin completo nesta fase (API-first, painel admin vem depois)
- Submissão via Discord `/submit` (feature futura, não MVP)
- Suporte a múltiplos servidores Discord (1 guild por instalação)
- Migração de alunos existentes de forma automatizada (seed manual do estado inicial)

## Decisions

### 1. Discord bot como worker separado
**Decisão**: O bot roda como processo independente no docker-compose, não dentro da FastAPI.

**Alternativas**:
- (a) Bot dentro do FastAPI via background task: mistura lifecycle de WebSocket com HTTP, se o bot cair o API server também é afetado.
- (b) Bot como microserviço separado com seu próprio DB: over-engineering pra escala de 400 alunos.
- (c) **Bot como worker no mesmo repo, compartilhando models e services**: isolamento de processo sem duplicação de código. Se o bot cai, a API e o Celery continuam.

**Rationale**: (c) dá isolamento sem complexidade. O bot importa `app.models` e `app.services` diretamente. Docker-compose adiciona um serviço `discord-bot` com restart policy.

### 2. Webhook processing: receive-fast, process-async
**Decisão**: O endpoint `/webhooks/hotmart` valida HMAC, persiste o evento raw, retorna 200 em < 1s, e enfileira processamento via Celery.

**Alternativas**:
- (a) Processamento síncrono no request: Hotmart tem timeout curto (~5s), qualquer falha no Discord/ManyChat causa retry da Hotmart e duplicação.
- (b) **Async via Celery**: desacopla recepção de processamento, idempotência natural por transaction_id.

**Rationale**: (b) é o padrão consolidado pra webhooks. O Celery já existe no projeto.

### 3. Lifecycle service como ponto único de coordenação
**Decisão**: `app/services/lifecycle.py` implementa a máquina de estados e coordena todos os side-effects. Nenhum router ou integration chama outra integration diretamente.

**Alternativas**:
- (a) Cada router chama as integrations que precisa: acoplamento forte, regras de negócio espalhadas.
- (b) Event-driven com message broker: overkill pra escala atual, adiciona complexidade de infra.
- (c) **Service layer centralizado**: um lugar pra toda lógica de transição, testável com mocks.

**Rationale**: (c) é o padrão que o projeto já usa (services/ existe). Escala suficiente, fácil de testar.

### 4. Integrações como módulos desacoplados
**Decisão**: `app/integrations/discord.py`, `app/integrations/manychat.py`, `app/integrations/hotmart.py`. Cada um expõe funções puras (`assign_role`, `add_tag`, `trigger_flow`) que o lifecycle service chama.

**Rationale**: Se uma integração muda de API, só o módulo correspondente muda. Fácil de mockar nos testes. Feature flags (`DISCORD_ENABLED`, `MANYCHAT_ENABLED`) permitem desativar integrações individualmente.

### 5. Event log como tabela simples, não message broker
**Decisão**: Tabela `events` com JSONB payload. Insert-only (com exceção de status update no retry manual).

**Alternativas**:
- (a) Redis streams ou RabbitMQ: infraestrutura adicional, operational overhead.
- (b) **Tabela PostgreSQL**: já temos o banco, queries SQL pra debug, sem nova dependência.

**Rationale**: O event log é pra auditoria e debug, não pra event sourcing. Tabela simples resolve.

### 6. Linking aluno ↔ Discord via token no /registrar
**Decisão**: Na transição pra `pending_onboarding`, o sistema gera um token de 8 caracteres. O ManyChat envia o token por WhatsApp. O aluno digita `/registrar codigo:ABC123` no Discord. O bot valida e vincula o `discord_id`.

**Alternativas**:
- (a) Discord OAuth na web: mais robusto, mas exige que o aluno navegue pra plataforma web.
- (b) Match por username: Discord usernames não são mais únicos desde 2023.
- (c) **Token via WhatsApp + slash command**: zero-friction no mobile, resolução unívoca.

**Rationale**: (c) funciona no mobile (onde a maioria dos alunos está), não exige web login, e o token garante identificação correta.

### 7. Estrutura de diretórios no backend

```
autograder-back/app/
├── integrations/          # NEW: módulos de integração
│   ├── __init__.py
│   ├── discord.py         # Discord API client (role management)
│   ├── manychat.py        # ManyChat API client (tags, flows)
│   └── hotmart.py         # Hotmart webhook parsing/validation
├── services/
│   ├── lifecycle.py       # NEW: state machine + side-effect orchestration
│   ├── enrollment.py      # NEW: auto-enrollment logic
│   ├── grading.py         # existing
│   ├── content_extractor.py  # existing
│   └── file_storage.py    # existing
├── routers/
│   ├── webhooks.py        # NEW: Hotmart webhook endpoint
│   ├── products.py        # NEW: CRUD de produtos e access rules
│   ├── admin_events.py    # NEW: event log viewer + retry
│   ├── ...existing...
├── models/
│   ├── product.py         # NEW: Product, ProductAccessRule
│   ├── event.py           # NEW: Event
│   ├── user.py            # MODIFIED: integration fields
│   ├── ...existing...
├── schemas/
│   ├── products.py        # NEW
│   ├── webhooks.py        # NEW
│   ├── events.py          # NEW
│   ├── ...existing...
├── discord_bot.py         # NEW: bot entrypoint (runs as separate process)
```

## Risks / Trade-offs

**[Hotmart webhook format changes] → Mitigation**: Isolar parsing em `integrations/hotmart.py`. Logar raw payload no event log. Se formato muda, o raw payload permite debug e reprocessamento.

**[Discord rate limits em bulk operations] → Mitigation**: Na escala de 400 alunos, bulk não acontece (é individual por webhook). Se acontecer migração inicial, rate limiter com sleep entre calls.

**[ManyChat subscriber não encontrado] → Mitigation**: Se o aluno nunca interagiu com ManyChat, o subscriber não existe. Side-effect falha, admin é alertado. Resolução manual (admin dispara first contact).

**[Bot do Discord cai e aluno tenta /registrar] → Mitigation**: docker-compose restart policy. Token permanece válido por 7 dias. Aluno pode tentar novamente quando bot volta.

**[Aluno não completa onboarding] → Mitigation**: Follow-up via ManyChat em 24h. Painel admin mostra alunos stuck em `pending_onboarding` há mais de X dias.

**[Migração de alunos existentes] → Mitigation**: Script manual de seed. Mapeia alunos atuais do Discord pra registros no sistema. Não é automatizado, é one-time.

## Migration Plan

1. Deploy: migration de banco (novos models + campos no User)
2. Configurar env vars (tokens Hotmart/Discord/ManyChat) com feature flags desabilitados
3. Seed manual: criar Products e ProductAccessRules pra produtos existentes
4. Seed manual: importar alunos ativos atuais com lifecycle_status=active
5. Habilitar feature flags um por um (hotmart → discord → manychat)
6. Monitorar event log por 1 semana antes de confiar plenamente

## Open Questions

- Formato exato do payload de webhook da Hotmart (precisa testar com webhook real ou docs atualizados)
- ManyChat API: confirmar se `sendFlow` aceita custom fields inline ou precisa setar antes
- Definir canal(is) do Discord onde notificações de exercício são postadas (por produto? canal único?)
