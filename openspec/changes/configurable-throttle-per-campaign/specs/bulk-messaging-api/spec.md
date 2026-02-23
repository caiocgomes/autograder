## MODIFIED Requirements

### Requirement: Enviar mensagem em massa via Celery
O sistema SHALL expor `POST /messaging/send` que aceita lista de user IDs + template de mensagem + configuração opcional de throttle, cria uma `MessageCampaign` com `MessageRecipient` registros, e despacha um Celery task para envio com throttling configurável. Acessível apenas por admin.

#### Scenario: Envio com throttle custom
- **GIVEN** existem 3 alunos com IDs [1, 2, 3], todos com `whatsapp_number` preenchido
- **WHEN** admin faz `POST /messaging/send` com `{"user_ids": [1, 2, 3], "message_template": "Olá {nome}!", "throttle_min_seconds": 5, "throttle_max_seconds": 10}`
- **THEN** retorna 202 Accepted com `{"campaign_id": <id>, "task_id": "<celery_task_id>", "total_recipients": 3, "skipped_no_phone": 0}`
- **AND** `MessageCampaign` é criada com `throttle_min_seconds=5.0`, `throttle_max_seconds=10.0`
- **AND** Celery task recebe parâmetros de throttle e time limits calculados dinamicamente

#### Scenario: Envio sem throttle usa defaults
- **WHEN** admin faz `POST /messaging/send` com `{"user_ids": [1, 2, 3], "message_template": "Olá {nome}!"}`
- **THEN** campanha usa `throttle_min_seconds=15.0`, `throttle_max_seconds=25.0`

#### Scenario: Alunos sem WhatsApp são reportados mas não bloqueiam envio
- **GIVEN** user_ids [1, 2, 3] onde user 2 tem `whatsapp_number = NULL`
- **WHEN** admin faz `POST /messaging/send` com esses IDs
- **THEN** retorna 202 com `{"campaign_id": <id>, "total_recipients": 2, "skipped_no_phone": 1, "skipped_users": [{"id": 2, "name": "...", "reason": "no_whatsapp"}]}`

#### Scenario: Template com variável desconhecida é rejeitado
- **GIVEN** template contém `{saldo_bancario}`
- **WHEN** admin faz `POST /messaging/send` com esse template
- **THEN** retorna 422 com erro indicando variáveis inválidas

#### Scenario: Throttle inválido é rejeitado
- **WHEN** admin faz `POST /messaging/send` com `throttle_min_seconds=1`
- **THEN** retorna 422 com erro de validação

### Requirement: Celery task envia com throttling configurável e update progressivo
O sistema SHALL implementar o task `send_bulk_messages` que recebe `campaign_id`, `message_template`, e parâmetros de throttle, busca recipients pendentes no banco, resolve variáveis, envia via `send_message()` com throttling configurável, e atualiza status no banco a cada envio.

#### Scenario: Task usa throttle da campanha
- **GIVEN** campanha com `throttle_min_seconds=10`, `throttle_max_seconds=20` e 3 recipients pendentes
- **WHEN** task processa o lote
- **THEN** há pausa de `random.uniform(10, 20)` segundos entre cada chamada a `send_message()`

#### Scenario: Task sem throttle explícito usa defaults
- **GIVEN** task recebe `throttle_min=None` e `throttle_max=None`
- **WHEN** task processa o lote
- **THEN** usa `random.uniform(15, 25)` como fallback

#### Scenario: Task atualiza recipient e campanha após cada envio
- **WHEN** task envia mensagem para um recipient
- **THEN** atualiza `MessageRecipient.status`, `resolved_message`, `sent_at` (ou `error_message`)
- **AND** incrementa `MessageCampaign.sent_count` ou `failed_count`
- **AND** faz commit no banco antes de prosseguir para o próximo

#### Scenario: Falha em um destinatário não aborta os demais
- **GIVEN** 3 destinatários, e `send_message` retorna False para o segundo
- **WHEN** task processa o lote
- **THEN** os 3 são processados
- **AND** o segundo fica com `status=failed`, os outros com `sent` (se bem-sucedidos)

#### Scenario: Task define status final da campanha
- **WHEN** task finaliza processamento de todos os recipients
- **THEN** status da campanha é `completed` se nenhum falhou, `partial_failure` se pelo menos um falhou e pelo menos um enviou, `failed` se todos falharam
- **AND** `completed_at` é preenchido
