## Why

O throttle entre mensagens WhatsApp é hardcoded em `random.uniform(10, 30)` para todas as campanhas. Envios pequenos (5 pessoas) ficam desnecessariamente lentos, e envios grandes (500+) podem ser arriscados demais com intervalos curtos. Cada campanha tem um perfil de risco diferente e precisa de controle individual.

## What Changes

- Adicionar campos `throttle_min_seconds` e `throttle_max_seconds` ao modelo `MessageCampaign` (default 15/25)
- Aceitar esses parâmetros no `BulkSendRequest` schema e no endpoint `POST /messaging/send`
- Calcular `soft_time_limit` e `time_limit` do Celery task dinamicamente com base no número de recipients e throttle configurado
- Substituir o delay hardcoded no task `send_bulk_messages` pelos valores da campanha
- Separar mensagens transacionais (lifecycle) e bulk em Celery queues distintas (`whatsapp_rt` e `whatsapp_bulk`) para que campanhas longas não bloqueiem mensagens de onboarding/welcome
- Validar piso mínimo de 3 segundos para `throttle_min_seconds`

## Capabilities

### New Capabilities
- `campaign-throttle-config`: Configuração de throttle por campanha (min/max delay em segundos), cálculo dinâmico de time limits do Celery, e validação de piso mínimo
- `whatsapp-queue-separation`: Separação de filas Celery para mensagens transacionais (real-time) vs. campanhas bulk, garantindo que envios longos não bloqueiem mensagens de lifecycle

### Modified Capabilities
- `message-campaigns`: Throttle entre envios passa de hardcoded para configurável por campanha
- `bulk-messaging-api`: Schema e endpoint aceitam parâmetros de throttle

## Impact

- **Modelo**: `MessageCampaign` ganha 2 colunas (migration Alembic)
- **Schema**: `BulkSendRequest` ganha 2 campos opcionais com defaults
- **Router**: `POST /messaging/send` propaga throttle para o modelo e calcula time limits
- **Task**: `send_bulk_messages` recebe throttle como parâmetros, usa no sleep
- **Retry**: `POST /campaigns/{id}/retry` lê throttle do modelo, recalcula time limits para pendentes restantes
- **Celery config**: Duas queues definidas, tasks roteadas por tipo
- **Deploy**: Workers precisam ser iniciados com queue routing (`-Q whatsapp_rt` / `-Q whatsapp_bulk`)
- **Testes**: `test_bulk_send_task.py` precisa cobrir throttle configurável e time limit dinâmico
