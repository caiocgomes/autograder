## ADDED Requirements

### Requirement: Persistência de campanhas enviadas
O sistema SHALL persistir cada envio em massa como uma `MessageCampaign` com registros individuais `MessageRecipient`, criados no momento do dispatch (antes da Celery task iniciar).

#### Scenario: Campanha é criada ao disparar envio
- **WHEN** admin faz `POST /messaging/send` com 20 user_ids e um template
- **THEN** uma `MessageCampaign` é criada com `status=sending`, `total_recipients=20`, `message_template`, `course_name` (snapshot), `sent_by` (admin user_id), `created_at`
- **AND** 20 registros `MessageRecipient` são criados com `status=pending`, `phone` (snapshot), `name` (snapshot)
- **AND** response inclui `campaign_id` junto com `task_id`

#### Scenario: Recipients sem WhatsApp não geram MessageRecipient
- **WHEN** admin envia para 15 user_ids, 2 sem `whatsapp_number`
- **THEN** campanha tem `total_recipients=13`
- **AND** 13 `MessageRecipient` são criados (apenas os com telefone)
- **AND** os 2 sem telefone aparecem em `skipped_users` no response

### Requirement: Update progressivo de status durante envio
O sistema SHALL atualizar o status de cada `MessageRecipient` e os contadores da `MessageCampaign` progressivamente durante a execução da Celery task.

#### Scenario: Recipient enviado com sucesso
- **WHEN** Celery task envia mensagem para um recipient com sucesso
- **THEN** `MessageRecipient.status` é atualizado para `sent`
- **AND** `MessageRecipient.sent_at` é preenchido com timestamp atual
- **AND** `MessageRecipient.resolved_message` é preenchido com a mensagem final (variáveis resolvidas)
- **AND** `MessageCampaign.sent_count` é incrementado em 1

#### Scenario: Recipient com falha no envio
- **WHEN** `send_message()` retorna False para um recipient
- **THEN** `MessageRecipient.status` é atualizado para `failed`
- **AND** `MessageRecipient.error_message` é preenchido
- **AND** `MessageRecipient.resolved_message` é preenchido (a mensagem que tentou enviar)
- **AND** `MessageCampaign.failed_count` é incrementado em 1

#### Scenario: Campanha finalizada com sucesso total
- **WHEN** Celery task processa todos os recipients e nenhum falhou
- **THEN** `MessageCampaign.status` é atualizado para `completed`
- **AND** `MessageCampaign.completed_at` é preenchido

#### Scenario: Campanha finalizada com falhas parciais
- **WHEN** Celery task processa todos os recipients e pelo menos um falhou mas pelo menos um teve sucesso
- **THEN** `MessageCampaign.status` é atualizado para `partial_failure`
- **AND** `MessageCampaign.completed_at` é preenchido

#### Scenario: Campanha com todas as mensagens falhadas
- **WHEN** Celery task processa todos os recipients e todos falharam
- **THEN** `MessageCampaign.status` é atualizado para `failed`
- **AND** `MessageCampaign.completed_at` é preenchido

### Requirement: Listar histórico de campanhas
O sistema SHALL expor `GET /messaging/campaigns` que retorna campanhas ordenadas por data de criação (mais recente primeiro), acessível apenas por admin.

#### Scenario: Listar campanhas recentes
- **WHEN** admin faz `GET /messaging/campaigns`
- **THEN** retorna campanhas com `id`, `message_template` (truncado a 100 chars), `course_name`, `total_recipients`, `sent_count`, `failed_count`, `status`, `created_at`, `completed_at`
- **AND** ordenadas por `created_at` descendente

#### Scenario: Paginação com limit e offset
- **WHEN** admin faz `GET /messaging/campaigns?limit=10&offset=20`
- **THEN** retorna no máximo 10 campanhas, pulando as 20 primeiras

#### Scenario: Filtrar por status
- **WHEN** admin faz `GET /messaging/campaigns?status=partial_failure`
- **THEN** retorna apenas campanhas com status `partial_failure`

#### Scenario: Acesso negado para não-admin
- **WHEN** usuário com role `professor` ou `student` faz `GET /messaging/campaigns`
- **THEN** retorna 403

### Requirement: Detalhe de campanha com status por destinatário
O sistema SHALL expor `GET /messaging/campaigns/{id}` com a lista completa de destinatários e seus status individuais, acessível apenas por admin.

#### Scenario: Visualizar detalhe de campanha
- **WHEN** admin faz `GET /messaging/campaigns/42`
- **THEN** retorna campanha com `message_template` (completo), `course_name`, `status`, `total_recipients`, `sent_count`, `failed_count`, `created_at`, `completed_at`
- **AND** lista de recipients com `user_id`, `name`, `phone`, `status`, `resolved_message`, `sent_at`, `error_message`

#### Scenario: Campanha inexistente
- **WHEN** admin faz `GET /messaging/campaigns/999`
- **THEN** retorna 404

#### Scenario: Campanha em andamento mostra progresso parcial
- **WHEN** admin faz `GET /messaging/campaigns/42` e campanha tem `status=sending`
- **THEN** retorna contadores atuais (`sent_count`, `failed_count`) e recipients com mix de `pending`, `sent`, `failed`

### Requirement: Retry de mensagens falhadas
O sistema SHALL expor `POST /messaging/campaigns/{id}/retry` que reenvia apenas os destinatários falhados de uma campanha, acessível apenas por admin.

#### Scenario: Retry reenvia apenas falhados
- **WHEN** admin faz `POST /messaging/campaigns/42/retry` e campanha tem 8 sent + 2 failed
- **THEN** os 2 `MessageRecipient` falhados são resetados para `status=pending` com `error_message` limpo
- **AND** `MessageCampaign.status` volta para `sending`
- **AND** `MessageCampaign.failed_count` é zerado
- **AND** nova Celery task é despachada para processar apenas recipients `pending`
- **AND** retorna 202 com `{"retrying": 2, "campaign_id": 42}`

#### Scenario: Retry em campanha sem falhados
- **WHEN** admin faz `POST /messaging/campaigns/42/retry` e todos recipients estão `sent`
- **THEN** retorna 400 com "Nenhum destinatário falhado para reenviar"

#### Scenario: Retry em campanha que ainda está enviando
- **WHEN** admin faz `POST /messaging/campaigns/42/retry` e `status=sending`
- **THEN** retorna 409 com "Campanha ainda está sendo processada"

#### Scenario: Retry em campanha inexistente
- **WHEN** admin faz `POST /messaging/campaigns/999/retry`
- **THEN** retorna 404

#### Scenario: Retry acumula enviados de tentativas anteriores
- **WHEN** campanha tinha 8 sent + 2 failed, retry envia 1 com sucesso e 1 falha novamente
- **THEN** campanha final tem `sent_count=9`, `failed_count=1`, `status=partial_failure`
