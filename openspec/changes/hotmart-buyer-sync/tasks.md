## 1. Modelos SQLAlchemy

- [x] 1.1 Criar `autograder-back/app/models/hotmart_buyer.py` com modelo `HotmartBuyer` (colunas: id, email, name, hotmart_product_id, status, user_id FK nullable com ON DELETE SET NULL, last_synced_at, created_at; UniqueConstraint em email + hotmart_product_id)
- [x] 1.2 Criar `autograder-back/app/models/hotmart_product_mapping.py` com modelo `HotmartProductMapping` (colunas: id, source_hotmart_product_id, target_product_id FK com ON DELETE CASCADE, created_at; UniqueConstraint em source + target)
- [x] 1.3 Importar os dois novos modelos em `autograder-back/app/models/__init__.py`

## 2. Migração Alembic

- [x] 2.1 Gerar migração: `uv run alembic revision --autogenerate -m "add hotmart_buyers and hotmart_product_mapping"` (rodar de dentro de `autograder-back/`)
- [x] 2.2 Revisar o arquivo gerado em `alembic/versions/` e confirmar que as duas tabelas, constraints e FKs estão corretos
- [x] 2.3 Aplicar: `uv run alembic upgrade head`

## 3. Celery Task sync_hotmart_buyers

- [x] 3.1 Adicionar task `sync_hotmart_buyers` em `autograder-back/app/tasks.py`:
  - Loop sobre `Product.is_active == True`
  - Para cada produto, chama `hotmart.get_buyer_statuses(product.hotmart_product_id)`
  - Para cada (email, status): UPSERT em `HotmartBuyer` (INSERT OR UPDATE por email+hotmart_product_id)
  - Resolve `user_id` fazendo `db.query(User).filter(User.email == email).first()`
  - Atualiza `last_synced_at = datetime.utcnow()`
  - Ao final, cria evento `hotmart_buyers.sync_completed` com contadores (inserted, updated, total, errors)
- [x] 3.2 Registrar o task no beat schedule em `autograder-back/app/celery_app.py` (diário, ex: 03:00 UTC, separado do `sync_student_course_status`)

## 4. Testes

- [x] 4.1 Criar `autograder-back/tests/test_hotmart_buyer_sync.py` cobrindo:
  - Comprador sem conta → `user_id = NULL`
  - Comprador com conta → `user_id` preenchido
  - Re-sync atualiza status e `last_synced_at` sem criar duplicata
  - Falha na API de um produto não aborta os demais
- [x] 4.2 Rodar `uv run pytest tests/test_hotmart_buyer_sync.py` e confirmar que passam

## 5. Validação manual

- [ ] 5.1 Popular `hotmart_product_mapping` com o de/para inicial (script SQL ou seed) para pelo menos um produto real
- [ ] 5.2 Rodar o task manualmente via `uv run celery -A app.celery_app call sync_hotmart_buyers` e verificar linhas em `hotmart_buyers`
- [ ] 5.3 Confirmar query de cursos por email funciona (JOIN hotmart_buyers + hotmart_product_mapping + products)
