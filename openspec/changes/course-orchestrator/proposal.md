## Why

O autograder hoje gerencia exercícios e submissions, mas o lifecycle do aluno (pagamento, onboarding, acesso ao Discord, notificações) é todo manual. Com 400 alunos e churn médio no produto mais barato, o trabalho de adicionar/remover alunos do Discord, enviar instruções por WhatsApp e manter cadastros sincronizados consome horas recorrentes. O sistema precisa se tornar o orquestrador central que conecta Hotmart (pagamento), Discord (comunidade e acesso), e ManyChat/WhatsApp (comunicação).

## What Changes

- Novo modelo de **Product** mapeando produtos Hotmart a regras de acesso (Discord roles, classes, tags ManyChat)
- **Máquina de estados do aluno** (pending_payment → pending_onboarding → active → churned) com side-effects automáticos por transição
- **Webhook receiver** para eventos Hotmart (compra, cancelamento, reembolso) com processamento assíncrono e idempotente
- **Discord bot** como worker separado: gerencia roles automaticamente e oferece comando `/registrar` para linking de conta
- **Integração ManyChat**: state management (tags por produto) e triggers transacionais (onboarding, notificações)
- **Event log** append-only para auditoria e painel de side-effects com falha
- User model estendido com campos de integração (hotmart_id, discord_id, whatsapp_number, lifecycle_status)
- Enrollment automático por produto (coexiste com invite codes manuais)

## Capabilities

### New Capabilities
- `product-catalog`: Produtos Hotmart → regras de acesso (Discord roles, classes, tags ManyChat)
- `student-lifecycle`: Máquina de estados com side-effects por transição e handling de falhas
- `hotmart-webhooks`: Receiver, validação HMAC, processamento assíncrono idempotente via Celery
- `discord-bot`: Worker separado com role management e comando /registrar
- `manychat-integration`: State management (tags/fields) e flow triggers transacionais
- `event-log`: Append-only event log, auditoria, painel admin de falhas

### Modified Capabilities
- `user-authentication`: User model ganha campos de integração (hotmart_id, discord_id, whatsapp_number, lifecycle_status, onboarding_token)
- `class-management`: Enrollment automático por produto; unenrollment no churn preservando histórico
- `code-submission`: Marcação de submissão via Discord como feature futura (não MVP)

## Impact

- **Backend**: Novos models (Product, ProductAccessRule, Event), novos routers (webhooks, products, admin events), novos services (lifecycle, enrollment automático, integrações Discord/ManyChat), novo worker (Discord bot)
- **Infraestrutura**: Discord bot como serviço adicional no docker-compose; novas env vars para tokens Hotmart/Discord/ManyChat
- **Dependências Python**: discord.py (bot), httpx ou requests para APIs ManyChat/Hotmart
- **Database**: Migração para novos models e campos adicionais no User
- **Frontend**: Painel admin para produtos, regras de acesso, e eventos com falha (escopo futuro, não bloqueia MVP backend)
