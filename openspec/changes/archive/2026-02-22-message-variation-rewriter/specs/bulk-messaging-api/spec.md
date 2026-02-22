## MODIFIED Requirements

### Requirement: Enviar mensagem em massa via Celery
O sistema SHALL expor `POST /messaging/send` que aceita lista de user IDs + template de mensagem + lista opcional de variações aprovadas, cria uma `MessageCampaign` com `MessageRecipient` registros, e despacha um Celery task para envio com throttling. Acessível apenas por admin.

#### Scenario: Envio bem-sucedido para múltiplos alunos
- **GIVEN** existem 3 alunos com IDs [1, 2, 3], todos com `whatsapp_number` preenchido
- **WHEN** admin faz `POST /messaging/send` com `{"user_ids": [1, 2, 3], "message_template": "Olá {nome}, aula amanhã!"}`
- **THEN** retorna 202 Accepted com `{"campaign_id": <id>, "task_id": "<celery_task_id>", "total_recipients": 3, "skipped_no_phone": 0}`
- **AND** `MessageCampaign` é criada com `status=sending`, `total_recipients=3`
- **AND** 3 `MessageRecipient` registros são criados com `status=pending`
- **AND** o Celery task é enfileirado com `campaign_id`

#### Scenario: Envio com variações aprovadas
- **GIVEN** existem 5 alunos com WhatsApp
- **WHEN** admin faz `POST /messaging/send` com `{"user_ids": [1,2,3,4,5], "message_template": "Olá {nome}!", "variations": ["Oi {nome}!", "E aí {nome}!", "Fala {nome}!"]}`
- **THEN** retorna 202 com campanha criada normalmente
- **AND** Celery task recebe a lista de variações junto com campaign_id e message_template

#### Scenario: Variações com variáveis desconhecidas são rejeitadas
- **GIVEN** variations contém `"Olá {nome}, seu saldo é {saldo}"`
- **WHEN** admin faz `POST /messaging/send` com essas variações
- **THEN** retorna 422 com erro indicando variáveis inválidas na variação

#### Scenario: Alunos sem WhatsApp são reportados mas não bloqueiam envio
- **GIVEN** user_ids [1, 2, 3] onde user 2 tem `whatsapp_number = NULL`
- **WHEN** admin faz `POST /messaging/send` com esses IDs
- **THEN** retorna 202 com `{"campaign_id": <id>, "total_recipients": 2, "skipped_no_phone": 1, "skipped_users": [{"id": 2, "name": "...", "reason": "no_whatsapp"}]}`
- **AND** campanha tem `total_recipients=2` e 2 `MessageRecipient` registros

#### Scenario: Template com variável desconhecida é rejeitado
- **GIVEN** template contém `{saldo_bancario}`
- **WHEN** admin faz `POST /messaging/send` com esse template
- **THEN** retorna 422 com erro indicando variáveis inválidas
- **AND** nenhuma campanha é criada

#### Scenario: Lista vazia de user_ids é rejeitada
- **GIVEN** request com `user_ids: []`
- **WHEN** admin faz `POST /messaging/send`
- **THEN** retorna 422

#### Scenario: Mensagem vazia é rejeitada
- **GIVEN** request com `message_template: ""`
- **WHEN** admin faz `POST /messaging/send`
- **THEN** retorna 422

### Requirement: Celery task envia com throttling e update progressivo
O sistema SHALL implementar o task `send_bulk_messages` que recebe `campaign_id`, `message_template` e opcionalmente `variations`, busca recipients pendentes no banco, resolve variáveis (usando variação sorteada quando disponível), envia via `send_message()` com throttling, e atualiza status no banco a cada envio.

#### Scenario: Task busca recipients pendentes da campanha
- **WHEN** task inicia com `campaign_id=42` e `only_pending=False`
- **THEN** faz query por `MessageRecipient` com `campaign_id=42` e `status=pending`

#### Scenario: Task usa variação sorteada quando disponível
- **GIVEN** task recebe `variations=["Oi {nome}!", "E aí {nome}!", "Fala {nome}!"]`
- **WHEN** task processa cada recipient
- **THEN** para cada recipient, seleciona uma variação aleatória da lista via `random.choice(variations)`
- **AND** resolve template variables na variação selecionada
- **AND** armazena a mensagem final em `MessageRecipient.resolved_message`

#### Scenario: Task usa message_template quando sem variações
- **GIVEN** task recebe `variations=None` ou lista vazia
- **WHEN** task processa cada recipient
- **THEN** usa `message_template` diretamente (comportamento atual)

#### Scenario: Task atualiza recipient e campanha após cada envio
- **WHEN** task envia mensagem para um recipient
- **THEN** atualiza `MessageRecipient.status`, `resolved_message`, `sent_at` (ou `error_message`)
- **AND** incrementa `MessageCampaign.sent_count` ou `failed_count`
- **AND** faz commit no banco antes de prosseguir para o próximo

#### Scenario: Throttling entre envios
- **GIVEN** 3 destinatários pendentes
- **WHEN** task processa o lote
- **THEN** há pausa de 10-30 segundos entre cada chamada a `send_message()`

#### Scenario: Falha em um destinatário não aborta os demais
- **GIVEN** 3 destinatários, e `send_message` retorna False para o segundo
- **WHEN** task processa o lote
- **THEN** os 3 são processados
- **AND** o segundo fica com `status=failed`, os outros com `sent` (se bem-sucedidos)

#### Scenario: Task define status final da campanha
- **WHEN** task finaliza processamento de todos os recipients
- **THEN** status da campanha é `completed` se nenhum falhou, `partial_failure` se pelo menos um falhou e pelo menos um enviou, `failed` se todos falharam
- **AND** `completed_at` é preenchido

#### Scenario: Task com only_pending=True (retry)
- **GIVEN** campanha tem 8 recipients `sent` e 2 recipients `pending` (resetados pelo retry)
- **WHEN** task roda com `only_pending=True`
- **THEN** processa apenas os 2 pendentes
- **AND** `sent_count` final reflete total acumulado (8 + novos enviados)
