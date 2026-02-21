## Why

O sistema atual só mantém status de alunos que já fizeram onboarding na plataforma. Não existe visibilidade sobre todos os compradores da Hotmart — quem comprou o quê, qual status de pagamento, se já criou conta ou não. Isso impede operações de CRM, segmentação, suporte proativo e diagnóstico de churn antes do onboarding.

## What Changes

- Nova tabela `hotmart_buyers`: snapshot de todos os compradores da Hotmart, com status de ativação e flag de conta criada na plataforma
- Nova tabela `hotmart_product_mapping`: relação configurável de produto comprado (Hotmart) → produtos internos concedidos (de/para)
- Novo Celery task `sync_hotmart_buyers`: popula e mantém `hotmart_buyers` atualizado via API Hotmart
- Migrações Alembic para ambas as tabelas

## Capabilities

### New Capabilities

- `hotmart-buyer-snapshot`: Tabela e sync que reflete todos os compradores da Hotmart no banco local, com status de pagamento e flag de conta na plataforma
- `hotmart-product-mapping`: Configuração de/para entre produto Hotmart comprado e produtos internos concedidos

### Modified Capabilities

*(nenhuma)*

## Impact

- `autograder-back/app/models/`: dois novos modelos (`HotmartBuyer`, `HotmartProductMapping`)
- `autograder-back/app/tasks.py`: novo task `sync_hotmart_buyers`
- `autograder-back/alembic/versions/`: nova migração com as duas tabelas
- Lê `app/integrations/hotmart.py` (sem modificações) e `app/models/product.py` (referenciado via FK)
- Sem mudanças no `docker-compose.yml`, configuração Alembic, ou no task `sync_student_course_status` existente
