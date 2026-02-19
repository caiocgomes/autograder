## Why

O sistema hoje gerencia o lifecycle do aluno via webhooks da Hotmart, mas não mantém um estado por `(aluno, produto)` nem sincroniza esse estado com as tags do ManyChat de forma estruturada. Sem isso, não é possível enviar comunicações segmentadas por curso e situação — ex: "todos os inadimplentes do Senhor das LLMs" ou "cancelados do CDO nos últimos 30 dias".

## What Changes

- Nova tabela `student_course_status` com design SCD Type 2 — uma linha por versão de `(user, product)`, com `valid_from`, `valid_to` e `is_current`
- Job Celery `sync_manychat_tags` que lê o estado atual da Hotmart via API REST, atualiza a tabela SCD e aplica as tags correspondentes no ManyChat
- Cada aluno recebe 2 tags por curso no ManyChat: `{Curso}` (permanente, histórica) e `{Curso}, {Status}` (mutável, reflete estado atual)
- Status possíveis: `Ativo`, `Inadimplente`, `Cancelado`, `Reembolsado`
- Regra de acesso derivado: produto "A Base de Tudo" concede acesso ao "De analista a CDO" — ambas as tags são aplicadas ao comprador
- Atualização de status usa abordagem brute-force: remove todos os status-tags possíveis do curso antes de adicionar o atual
- Endpoint admin `POST /admin/events/manychat-sync` para trigger manual
- Beat schedule Celery: execução diária (complementa o sync horário de alunos já existente)

## Capabilities

### New Capabilities

- `student-course-status`: Tabela SCD Type 2 que mantém o histórico completo de status por `(user, product)`, com queries eficientes para estado atual e transições recentes

### Modified Capabilities

- `manychat-integration`: Adiciona a lógica de tag dual (curso + status) e o job de sync em batch; a integração existente via lifecycle (webhooks) continua inalterada

## Impact

- **Novo modelo SQLAlchemy**: `StudentCourseStatus` com migration Alembic
- **`app/tasks.py`**: nova task `sync_manychat_tags`
- **`app/integrations/hotmart.py`**: reutiliza `list_active_subscriptions` e `list_active_sales` já implementadas; adiciona lógica de status por produto
- **`app/integrations/manychat.py`**: sem mudanças na API; reutiliza `add_tag` e `remove_tag`
- **`app/routers/admin_events.py`**: novo endpoint de trigger manual
- **`app/celery_app.py`**: novo beat schedule diário
- **`app/models/product.py`**: `ProductAccessRule` com `MANYCHAT_TAG` já suporta regras de acesso derivado via configuração — sem mudança no modelo
- **Dependência nova**: nenhuma — reutiliza Hotmart API client e ManyChat client já existentes
