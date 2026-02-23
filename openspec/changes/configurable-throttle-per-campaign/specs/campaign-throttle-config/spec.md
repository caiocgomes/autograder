## ADDED Requirements

### Requirement: Throttle configurável por campanha
O sistema SHALL persistir configuração de throttle (`throttle_min_seconds`, `throttle_max_seconds`) em cada `MessageCampaign`, usada pelo Celery task para controlar o delay entre envios.

#### Scenario: Campanha criada com throttle custom
- **WHEN** admin faz `POST /messaging/send` com `throttle_min_seconds=5` e `throttle_max_seconds=10`
- **THEN** `MessageCampaign` é criada com `throttle_min_seconds=5.0` e `throttle_max_seconds=10.0`
- **AND** o Celery task usa `random.uniform(5.0, 10.0)` entre cada envio

#### Scenario: Campanha criada sem throttle usa defaults
- **WHEN** admin faz `POST /messaging/send` sem parâmetros de throttle
- **THEN** `MessageCampaign` é criada com `throttle_min_seconds=15.0` e `throttle_max_seconds=25.0`

#### Scenario: Retry reutiliza throttle da campanha original
- **WHEN** admin faz `POST /messaging/campaigns/{id}/retry`
- **THEN** o Celery task usa `throttle_min_seconds` e `throttle_max_seconds` gravados na campanha original

### Requirement: Validação de piso mínimo de throttle
O sistema SHALL rejeitar configurações de throttle com `throttle_min_seconds` abaixo de 3 segundos ou com `throttle_max_seconds` menor que `throttle_min_seconds`.

#### Scenario: Throttle min abaixo do piso
- **WHEN** admin faz `POST /messaging/send` com `throttle_min_seconds=1`
- **THEN** retorna 422 com erro indicando que o mínimo é 3 segundos
- **AND** nenhuma campanha é criada

#### Scenario: Throttle max menor que min
- **WHEN** admin faz `POST /messaging/send` com `throttle_min_seconds=20` e `throttle_max_seconds=10`
- **THEN** retorna 422 com erro indicando que max deve ser >= min
- **AND** nenhuma campanha é criada

#### Scenario: Throttle min exatamente no piso
- **WHEN** admin faz `POST /messaging/send` com `throttle_min_seconds=3` e `throttle_max_seconds=5`
- **THEN** campanha é criada com sucesso

### Requirement: Time limit dinâmico do Celery task
O sistema SHALL calcular `soft_time_limit` e `time_limit` do Celery task dinamicamente com base no número de recipients e configuração de throttle.

#### Scenario: Cálculo para campanha grande
- **GIVEN** campanha com 500 recipients, `throttle_min=30`, `throttle_max=60`
- **WHEN** task é despachado via `apply_async`
- **THEN** `soft_time_limit` = max(500 * ((30+60)/2 + 2) * 1.3, 120) = 33800
- **AND** `time_limit` = soft_time_limit + 300

#### Scenario: Cálculo para campanha pequena
- **GIVEN** campanha com 3 recipients, `throttle_min=5`, `throttle_max=10`
- **WHEN** task é despachado via `apply_async`
- **THEN** `soft_time_limit` = max(3 * ((5+10)/2 + 2) * 1.3, 120) = 120 (piso)
- **AND** `time_limit` = 420

#### Scenario: Retry recalcula time limit para pendentes restantes
- **GIVEN** campanha com 500 recipients originais, 480 já enviados, 20 pendentes, `throttle_min=30`, `throttle_max=60`
- **WHEN** admin faz retry
- **THEN** `soft_time_limit` é calculado com base em 20 recipients (não 500)
