## ADDED Requirements

### Requirement: Snapshot de compradores Hotmart no banco local
O sistema SHALL manter uma tabela `hotmart_buyers` com uma linha por (email, hotmart_product_id), refletindo todos os compradores retornados pela API Hotmart para cada produto configurado no banco, independente de eles terem conta na plataforma.

#### Scenario: Comprador sem conta na plataforma é inserido
- **WHEN** o sync roda e encontra um comprador na Hotmart cujo email não existe em `users`
- **THEN** o sistema insere uma linha em `hotmart_buyers` com `user_id = NULL`

#### Scenario: Comprador com conta na plataforma tem user_id preenchido
- **WHEN** o sync roda e encontra um comprador na Hotmart cujo email existe em `users`
- **THEN** o sistema insere ou atualiza a linha em `hotmart_buyers` com o `user_id` correspondente

#### Scenario: Status atualizado em sync subsequente
- **WHEN** o sync roda e o status do comprador na Hotmart mudou desde o último sync
- **THEN** o sistema atualiza `status` e `last_synced_at` na linha existente (UPSERT por email + hotmart_product_id)

#### Scenario: Comprador que criou conta após o sync anterior tem user_id resolvido
- **WHEN** o sync roda e um comprador que estava com `user_id = NULL` agora tem email correspondente em `users`
- **THEN** o sistema atualiza `user_id` para o id do usuário encontrado

### Requirement: Sync via Celery task agendado
O sistema SHALL expor um Celery task `sync_hotmart_buyers` que executa o sync de todos os produtos ativos, registra contadores de resultado e persiste um evento no log ao final.

#### Scenario: Execução bem-sucedida registra evento
- **WHEN** o task `sync_hotmart_buyers` completa sem erros críticos
- **THEN** um evento do tipo `hotmart_buyers.sync_completed` é criado com contadores (inserted, updated, total, errors)

#### Scenario: Falha em um produto não aborta os demais
- **WHEN** a chamada à API Hotmart falha para um produto específico
- **THEN** o sistema loga o erro, incrementa contador de erros, e continua processando os demais produtos
