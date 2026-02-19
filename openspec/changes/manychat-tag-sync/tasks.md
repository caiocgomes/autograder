## 1. Database — StudentCourseStatus (SCD Type 2)

- [x] 1.1 Criar model SQLAlchemy `StudentCourseStatus` com colunas: `id`, `user_id` (FK), `product_id` (FK), `status` (str), `valid_from`, `valid_to`, `is_current`, `source`
- [x] 1.2 Adicionar `unique_constraint` em `(user_id, product_id)` apenas para a linha `is_current = true` (partial unique index no PostgreSQL)
- [x] 1.3 Gerar migration Alembic: `uv run alembic revision --autogenerate -m "add student_course_status scd2"`
- [x] 1.4 Aplicar migration: `uv run alembic upgrade head`

## 2. Hotmart integration — phone e status por produto

- [x] 2.1 Adicionar função `list_buyers_with_phone(product_id) -> Iterator[dict]` em `app/integrations/hotmart.py` usando `GET /sales/users` — yield `{email, phone, product_id}`
- [x] 2.2 Adicionar função `get_buyer_statuses(product_id, years=6) -> dict[email, str]` que varre janelas de 30 dias no `sales/history` e mapeia email → status (`Ativo`, `Inadimplente`, `Cancelado`, `Reembolsado`)
- [x] 2.3 Atualizar `sync_hotmart_students` em `app/tasks.py` para popular `user.whatsapp_number` a partir do `cellphone` ou `phone` do `GET /sales/users` ao criar/atualizar usuário

## 3. Core — sync_manychat_tags task

- [x] 3.1 Criar task Celery `sync_manychat_tags(product_id=None)` em `app/tasks.py`
- [x] 3.2 Implementar helper `_resolve_hotmart_status(email, product_id, db)` — retorna status atual do aluno naquele produto
- [x] 3.3 Implementar helper `_update_scd2(user_id, product_id, new_status, db)` — fecha linha atual e insere nova se status mudou; no-op se igual
- [x] 3.4 Implementar helper `_apply_manychat_tags(subscriber_id, course_name, new_status)` — brute-force remove todos os status-tags, add course tag + novo status tag
- [x] 3.5 Implementar loop principal: para cada produto configurado → buscar buyers → match com User no banco → resolver status → atualizar SCD2 → aplicar tags ManyChat
- [x] 3.6 Lidar com acesso derivado: para cada produto, expandir via `ProductAccessRule` para incluir produtos derivados (ex: "A Base de Tudo" → aplica tags do CDO também)
- [x] 3.7 Logar evento `manychat.sync_completed` com contadores: `synced`, `status_changes`, `skipped_no_phone`, `skipped_no_subscriber`, `skipped_error`

## 4. Admin endpoint e beat schedule

- [x] 4.1 Adicionar `POST /admin/events/manychat-sync` em `app/routers/admin_events.py` — admin only, aceita `product_id: Optional[int]`, enfileira `sync_manychat_tags.delay(product_id)`
- [x] 4.2 Adicionar beat schedule `manychat-tag-sync-daily` em `app/celery_app.py` — `crontab(hour=2, minute=0)` (02:00 UTC)

## 5. Configuração de produtos no banco

- [x] 5.1 Criar script ou seed para cadastrar os 5 produtos Hotmart na tabela `products` com seus `hotmart_product_id`
- [x] 5.2 Criar registros `ProductAccessRule` com `rule_type=MANYCHAT_TAG` para cada produto — incluindo a regra derivada "A Base de Tudo" → "De analista a CDO"

## 6. Testes

- [x] 6.1 Testes unitários para `_update_scd2`: inserção inicial, mudança de status, no-op em status igual
- [x] 6.2 Testes unitários para `_apply_manychat_tags`: verifica brute-force remove + add com mocks do ManyChat
- [x] 6.3 Teste do endpoint `POST /admin/events/manychat-sync`: verifica enfileiramento e resposta
- [x] 6.4 Teste de integração de `sync_manychat_tags` com mocks de Hotmart API e ManyChat API
