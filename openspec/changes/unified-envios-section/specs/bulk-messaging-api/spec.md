## MODIFIED Requirements

### Requirement: Enviar mensagem em massa via Celery
O sistema SHALL expor `POST /messaging/send` que aceita lista de user IDs + template de mensagem, cria uma `MessageCampaign` com `MessageRecipient` registros, e despacha um Celery task para envio com throttling. Acessível apenas por admin.

#### Scenario: Envio bem-sucedido para múltiplos alunos
- **GIVEN** existem 3 alunos com IDs [1, 2, 3], todos com `whatsapp_number` preenchido
- **WHEN** admin faz `POST /messaging/send` com `{"user_ids": [1, 2, 3], "message_template": "Olá {nome}, aula amanhã!"}`
- **THEN** retorna 202 Accepted com `{"campaign_id": <id>, "task_id": "<celery_task_id>", "total_recipients": 3, "skipped_no_phone": 0}`
- **AND** `MessageCampaign` é criada com `status=sending`, `total_recipients=3`
- **AND** 3 `MessageRecipient` registros são criados com `status=pending`
- **AND** o Celery task é enfileirado com `campaign_id`

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

## ADDED Requirements

### Requirement: Filtro de lifecycle_status no endpoint de recipients
O sistema SHALL aceitar um query parameter opcional `lifecycle_status` no endpoint `GET /messaging/recipients` para filtrar alunos pelo status no ciclo de vida.

#### Scenario: Filtrar por lifecycle_status
- **WHEN** admin chama `GET /messaging/recipients?course_id=5&lifecycle_status=pending_onboarding`
- **THEN** retorna apenas recipients cujo `User.lifecycle_status` é `PENDING_ONBOARDING`

#### Scenario: Sem filtro retorna todos
- **WHEN** admin chama `GET /messaging/recipients?course_id=5` sem `lifecycle_status`
- **THEN** retorna todos os recipients do curso, independente do lifecycle_status

#### Scenario: Lifecycle status inválido
- **WHEN** admin chama `GET /messaging/recipients?course_id=5&lifecycle_status=banana`
- **THEN** retorna 422 com erro indicando valor inválido
