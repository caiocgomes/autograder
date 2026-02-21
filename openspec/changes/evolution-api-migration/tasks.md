## 1. Evolution API client

- [x] 1.1 Criar `app/integrations/evolution.py` com função `send_message(phone: str, text: str) -> bool` usando `httpx` — POST para `{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}` com header `apikey`
- [x] 1.2 Adicionar feature flag check: se `evolution_enabled` é False, logar e retornar True (mesmo padrão do ManyChat)
- [x] 1.3 Tratar erros: non-200 loga status + body e retorna False; exceção de rede loga e retorna False

## 2. Configuração

- [x] 2.1 Adicionar em `app/config.py`: `evolution_api_url`, `evolution_api_key`, `evolution_instance`, `evolution_enabled: bool = False`
- [x] 2.2 Remover de `app/config.py`: `manychat_api_token`, `manychat_enabled`, `manychat_onboarding_flow_id`, `manychat_welcome_flow_id`, `manychat_churn_flow_id`, `manychat_welcome_back_flow_id`, `manychat_new_assignment_flow_id`, `manychat_deadline_reminder_flow_id`
- [x] 2.3 Atualizar `.env.example`: substituir vars ManyChat pelas vars Evolution API

## 3. Database — remover manychat_subscriber_id e MANYCHAT_TAG

- [x] 3.1 Gerar migration Alembic: `uv run alembic revision --autogenerate -m "remove manychat fields"`
- [x] 3.2 Ajustar migration gerada para incluir: (a) `op.execute("DELETE FROM product_access_rules WHERE rule_type='manychat_tag'")` antes de alterar o enum, (b) `op.drop_column('users', 'manychat_subscriber_id')`, (c) remover `'manychat_tag'` do enum `AccessRuleType`
- [x] 3.3 Aplicar migration: `uv run alembic upgrade head`

## 4. Model — remover referências ManyChat

- [x] 4.1 Em `app/models/user.py`: remover `manychat_subscriber_id = Column(...)`
- [x] 4.2 Em `app/models/product.py`: remover `MANYCHAT_TAG = "manychat_tag"` do enum `AccessRuleType`

## 5. Lifecycle — substituir side-effects

- [x] 5.1 Em `app/services/lifecycle.py`: remover import de `manychat`, adicionar import de `evolution`
- [x] 5.2 Em `_side_effects_for_pending_onboarding`: remover `manychat.add_tag` call; substituir `manychat.trigger_flow` por `evolution.send_message` com texto de onboarding (nome, token, produto)
- [x] 5.3 Em `_side_effects_for_active`: remover loop `MANYCHAT_TAG` e `manychat.trigger_flow`; adicionar `evolution.send_message` com texto de welcome (ou welcome-back se reativação)
- [x] 5.4 Em `_side_effects_for_churned`: remover loop `MANYCHAT_TAG` e `manychat.trigger_flow`; adicionar `evolution.send_message` com texto de churn
- [x] 5.5 Remover todas as condições `if user.manychat_subscriber_id` — checar `user.whatsapp_number` em vez disso
- [x] 5.6 Definir constantes de texto das mensagens no topo do `lifecycle.py` (onboarding, welcome, welcome-back, churn)

## 6. Notifications service

- [x] 6.1 Em `app/services/notifications.py`: substituir `notify_student_welcome` para usar `evolution.send_message` em vez de `manychat.trigger_flow`
- [x] 6.2 Remover import de `manychat`

## 7. Sync job — remover aplicação de tags

- [x] 7.1 Em `app/tasks.py`: remover função `_apply_manychat_tags`
- [x] 7.2 Remover chamada de `_apply_manychat_tags` do loop principal do `sync_manychat_tags`
- [x] 7.3 Renomear task Celery `sync_manychat_tags` → `sync_student_course_status`
- [x] 7.4 Atualizar beat schedule em `app/celery_app.py` para usar o novo nome da task
- [x] 7.5 Atualizar endpoint admin `POST /admin/events/manychat-sync` → `/admin/events/course-status-sync` e apontar para nova task

## 8. Deletar manychat.py

- [x] 8.1 Deletar `app/integrations/manychat.py`
- [x] 8.2 Verificar que não há mais imports de `manychat` em nenhum arquivo: `grep -r "from app.integrations import manychat\|from app.integrations.manychat" autograder-back/`

## 9. Testes

- [x] 9.1 Criar `tests/test_evolution.py`: testar `send_message` com mock de httpx — success (200), API error (4xx/5xx), exception, evolution_enabled=False
- [x] 9.2 Atualizar `tests/test_lifecycle_service.py`: substituir mocks de ManyChat por mocks de Evolution API; verificar que side-effects chamam `evolution.send_message` com o phone correto
- [x] 9.3 Remover ou atualizar `tests/test_manychat.py` (se existir) — arquivo pode ser deletado
- [x] 9.4 Rodar suite completa: `uv run pytest` — zero falhas
