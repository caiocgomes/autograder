## 1. Database models e migração

- [x] 1.1 Criar model `Product` e `ProductAccessRule` em `app/models/product.py`
- [x] 1.2 Criar model `Event` em `app/models/event.py`
- [x] 1.3 Adicionar campos de integração ao model `User` (hotmart_id, discord_id, whatsapp_number, lifecycle_status, onboarding_token, onboarding_token_expires_at, manychat_subscriber_id)
- [x] 1.4 Adicionar campo `enrollment_source` ao `ClassEnrollment` (manual, product) pra distinguir enrollment automático de manual
- [x] 1.5 Atualizar `app/models/__init__.py` com novos models
- [x] 1.6 Gerar migração Alembic e testar com `alembic upgrade head`

## 2. Schemas Pydantic

- [x] 2.1 Criar `app/schemas/products.py` (ProductCreate, ProductResponse, ProductAccessRuleCreate, ProductAccessRuleResponse)
- [x] 2.2 Criar `app/schemas/webhooks.py` (HotmartWebhookPayload, WebhookResponse)
- [x] 2.3 Criar `app/schemas/events.py` (EventResponse, EventListResponse com filtros)
- [x] 2.4 Atualizar `app/schemas/users.py` com campos de integração no response

## 3. Integrations layer

- [x] 3.1 Criar `app/integrations/__init__.py`
- [x] 3.2 Criar `app/integrations/hotmart.py` (validação HMAC, parsing de payload por event type)
- [x] 3.3 Criar `app/integrations/discord.py` (assign_role, revoke_role, send_channel_message via Discord REST API)
- [x] 3.4 Criar `app/integrations/manychat.py` (add_tag, remove_tag, set_custom_fields, trigger_flow, find_subscriber)
- [x] 3.5 Adicionar env vars ao `app/config.py` (HOTMART_HOTTOK, DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, MANYCHAT_API_TOKEN, feature flags)
- [x] 3.6 Atualizar `.env.example` com novas variáveis

## 4. Services layer (orquestração)

- [x] 4.1 Criar `app/services/lifecycle.py` (state machine com transitions dict, execute_transition com side-effects, retry 1x + alerta)
- [x] 4.2 Criar `app/services/enrollment.py` (auto_enroll_by_product, auto_unenroll_by_product, preservando enrollment manual)
- [x] 4.3 Criar `app/services/notifications.py` (notify_admin_failure, notify_student_welcome, abstração sobre Discord + ManyChat)

## 5. Routers (API endpoints)

- [x] 5.1 Criar `app/routers/webhooks.py` (POST /webhooks/hotmart com validação HMAC, persist + enqueue)
- [x] 5.2 Criar `app/routers/products.py` (CRUD de produtos e access rules, admin-only)
- [x] 5.3 Criar `app/routers/admin_events.py` (GET /admin/events com filtros, POST /admin/events/{id}/retry)
- [x] 5.4 Registrar novos routers no `main.py`

## 6. Celery tasks

- [x] 6.1 Criar task `process_hotmart_event` em `app/tasks.py` (parseia webhook, resolve student, chama lifecycle.transition)
- [x] 6.2 Criar task `execute_side_effect` em `app/tasks.py` (executa um side-effect individual com retry)

## 7. Discord bot

- [x] 7.1 Adicionar `discord.py` (lib) ao `pyproject.toml`
- [x] 7.2 Criar `app/discord_bot.py` (entrypoint do bot: connect, register slash commands)
- [x] 7.3 Implementar comando `/registrar` (validar token, linkar discord_id, chamar lifecycle.transition, atribuir roles)
- [x] 7.4 Implementar event handler `on_member_join` (DM de boas-vindas com instruções se não tem role)
- [x] 7.5 Adicionar serviço `discord-bot` ao `docker-compose.yml`

## 8. Configuração e infra

- [x] 8.1 Atualizar `docker-compose.yml` com serviço discord-bot
- [x] 8.2 Adicionar volume `uploads/` e config de persistência se necessário
- [x] 8.3 Atualizar CLAUDE.md com novos comandos e arquitetura

## 9. Testes

- [x] 9.1 Testes unitários para `app/integrations/hotmart.py` (validação HMAC, parsing de cada event type)
- [x] 9.2 Testes unitários para `app/services/lifecycle.py` (cada transição, side-effects mockados, retry + falha)
- [x] 9.3 Testes unitários para `app/services/enrollment.py` (auto-enroll, auto-unenroll, preservação de enrollment manual)
- [x] 9.4 Testes de integração para `app/routers/webhooks.py` (webhook válido, HMAC inválido, duplicate)
- [x] 9.5 Testes de integração para `app/routers/products.py` (CRUD completo)
- [x] 9.6 Testes de integração para `app/routers/admin_events.py` (listagem, filtros, retry)
- [x] 9.7 Testes para o Discord bot (comando /registrar com token válido, inválido, expirado)
- [x] 9.8 Testes para `app/integrations/manychat.py` (add_tag, trigger_flow, subscriber not found)
