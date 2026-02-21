## Context

A integração com Hotmart já existe e funciona em dois modos: webhooks (eventos em tempo real) e API REST (`get_buyer_statuses()`, que varre 6 anos de histórico em janelas de 30 dias). O task `sync_student_course_status` já usa a API REST, mas só processa emails que batem com um `User` cadastrado — descartando qualquer comprador que nunca fez onboarding.

O banco já roda em Postgres via Docker Compose. Alembic já está configurado com migrações versionadas. Celery já gerencia tasks assíncronas e agendadas.

## Goals / Non-Goals

**Goals:**
- Snapshot completo de todos os compradores Hotmart no banco local, independente de onboarding
- Coluna `user_id` (nullable) que indica se o comprador tem conta na plataforma
- Tabela de/para configurável entre produto Hotmart e produtos internos
- Sync automático via Celery task reutilizando a infra existente

**Non-Goals:**
- UI/admin para gerenciar o de/para (próxima iteração)
- Modificar o `sync_student_course_status` existente
- Criar contas automaticamente para compradores sem onboarding
- Sincronizar dados além de email, nome, produto e status

## Decisions

**D1 — Tabela separada `hotmart_buyers` em vez de estender `users`**

Estender `users` com `hotmart_product_id` e `hotmart_status` causaria múltiplas linhas por comprador (um por produto), violando a semântica de usuário. A tabela separada mantém a modelagem limpa: `users` é identidade, `hotmart_buyers` é snapshot de compra.

*Alternativa considerada*: view materializada sobre `student_course_status`. Descartada porque `student_course_status` exige FK para `users.id`, o que não funciona para compradores sem conta.

**D2 — `user_id` como FK nullable em vez de boolean `has_account`**

FK nullable resolve na query sem second lookup. Se `user_id IS NOT NULL`, tem conta. JOIN direto com `users` para pegar Discord ID, WhatsApp, lifecycle_status. Boolean seria mais simples mas perderia o link.

*Risco*: FK pode ficar stale se o usuário for deletado. Mitigado com `ON DELETE SET NULL`.

**D3 — `source_hotmart_product_id` como string (não FK para `products`)**

O de/para mapeia o produto comprado na Hotmart para produtos internos. O produto comprado pode não existir como `Product` no banco (produto descontinuado, produto de parceiro, etc.). String raw preserva a informação sem exigir configuração prévia. O `target_product_id` é FK para `products.id` porque o produto interno tem que estar configurado para ser útil.

**D4 — UPSERT por (email, hotmart_product_id)**

A cada sync, status pode mudar (Ativo → Inadimplente). UPSERT garante idempotência: re-rodar o sync não cria duplicatas. `last_synced_at` atualizado em cada run.

**D5 — Novo task `sync_hotmart_buyers`, sem tocar em `sync_student_course_status`**

Os dois tasks têm propósitos distintos: um é snapshot bruto (todos os compradores), outro é SCD2 para usuários registrados. Mantê-los separados permite agendar com frequências diferentes e debugar independentemente.

## Risks / Trade-offs

- **Volume de API calls**: `get_buyer_statuses()` varre 6 anos em janelas de 30 dias × todos os status possíveis × todos os produtos. Para produto com muitos compradores, pode demorar vários minutos. → Mitigação: rodar fora do horário de pico, configurar timeout por produto.
- **Stale data em `user_id`**: se um usuário mudar de email na plataforma, o link pode ficar desatualizado. → Mitigação: o sync re-resolve `user_id` a cada run, não apenas na inserção.
- **De/para desatualizado**: se um produto Hotmart for rebundled, as linhas antigas em `hotmart_product_mapping` continuam apontando para os produtos antigos. → Mitigação: operação de gerenciamento de mapping é explícita (admin apaga e recria linhas). Sem soft-delete por ora.

## Migration Plan

1. Gerar migração Alembic com as duas tabelas novas (`hotmart_buyers`, `hotmart_product_mapping`)
2. Aplicar: `uv run alembic upgrade head`
3. Popular `hotmart_product_mapping` manualmente (ou via script de seed) com o de/para inicial
4. Registrar `sync_hotmart_buyers` no beat schedule do Celery (diário, horário separado do `sync_student_course_status`)
5. Rodar o sync manualmente pela primeira vez para validar o snapshot

Rollback: `uv run alembic downgrade -1` remove as duas tabelas. Sem impacto nas tabelas existentes.
