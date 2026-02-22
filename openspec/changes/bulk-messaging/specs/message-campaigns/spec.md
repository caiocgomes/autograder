## ADDED Requirements (V2)

### Requirement: Persistência de campanhas enviadas
O sistema SHALL persistir cada envio em massa como uma `MessageCampaign` com status por destinatário, permitindo auditoria e retry.

#### Scenario: Campanha é criada ao disparar envio
- **GIVEN** admin dispara envio para 20 alunos com template "Olá {nome}"
- **WHEN** `POST /messaging/send` é processado
- **THEN** uma `MessageCampaign` é criada com `status=sending`, `total_recipients=20`, `message_template`, `sent_by` (admin user_id), `created_at`
- **AND** 20 registros `MessageRecipient` são criados com `status=pending`

#### Scenario: Status de destinatário atualizado após envio
- **GIVEN** campanha com 3 destinatários, todos `status=pending`
- **WHEN** Celery task processa cada destinatário
- **THEN** status de cada `MessageRecipient` é atualizado para `sent` (sucesso) ou `failed` (erro)
- **AND** `sent_at` é preenchido para destinatários com sucesso
- **AND** `error_message` é preenchido para destinatários falhados

#### Scenario: Campanha finalizada atualiza status agregado
- **GIVEN** campanha com 10 destinatários, 8 sent, 2 failed
- **WHEN** Celery task finaliza o lote
- **THEN** `MessageCampaign.status` é atualizado para `completed`
- **AND** `MessageCampaign.sent_count=8`, `failed_count=2`, `completed_at` é preenchido

#### Scenario: Campanha com todas as mensagens falhadas
- **GIVEN** campanha com 5 destinatários, todos falharam (Evolution API fora do ar)
- **WHEN** Celery task finaliza
- **THEN** `MessageCampaign.status = failed`, `sent_count=0`, `failed_count=5`

---

### Requirement: Listar histórico de campanhas
O sistema SHALL expor `GET /messaging/campaigns` que retorna campanhas ordenadas por data, com paginação.

#### Scenario: Listar campanhas recentes
- **GIVEN** existem 25 campanhas no sistema
- **WHEN** admin faz `GET /messaging/campaigns`
- **THEN** retorna as 20 mais recentes com `id`, `message_template` (truncado a 100 chars), `total_recipients`, `sent_count`, `failed_count`, `status`, `created_at`, `sent_by_name`

#### Scenario: Paginação
- **GIVEN** existem 25 campanhas
- **WHEN** admin faz `GET /messaging/campaigns?page=2&per_page=20`
- **THEN** retorna as 5 campanhas restantes

#### Scenario: Filtrar por status
- **GIVEN** existem campanhas com status `completed`, `failed`, `sending`
- **WHEN** admin faz `GET /messaging/campaigns?status=failed`
- **THEN** retorna apenas campanhas falhadas

---

### Requirement: Detalhe de campanha com status por destinatário
O sistema SHALL expor `GET /messaging/campaigns/{id}` com a lista completa de destinatários e seus status individuais.

#### Scenario: Visualizar detalhe de campanha
- **GIVEN** campanha 42 com 3 destinatários: João (sent), Maria (sent), Pedro (failed)
- **WHEN** admin faz `GET /messaging/campaigns/42`
- **THEN** retorna campanha com template, timestamp, totais, e lista de recipients com `user_name`, `phone`, `status`, `sent_at`, `error_message`

#### Scenario: Campanha inexistente retorna 404
- **GIVEN** não existe campanha com ID 999
- **WHEN** admin faz `GET /messaging/campaigns/999`
- **THEN** retorna 404

---

### Requirement: Retry de mensagens falhadas
O sistema SHALL permitir reenviar apenas os destinatários falhados de uma campanha.

#### Scenario: Retry reenvia apenas falhados
- **GIVEN** campanha 42 com 10 destinatários: 8 sent, 2 failed
- **WHEN** admin faz `POST /messaging/campaigns/42/retry`
- **THEN** novo Celery task é enfileirado apenas para os 2 destinatários falhados
- **AND** status desses 2 `MessageRecipient` volta para `pending`
- **AND** `MessageCampaign.status` volta para `sending`

#### Scenario: Retry em campanha sem falhados retorna 400
- **GIVEN** campanha com todos destinatários `status=sent`
- **WHEN** admin faz `POST /messaging/campaigns/42/retry`
- **THEN** retorna 400 com "Nenhum destinatário falhado para reenviar"

#### Scenario: Retry em campanha que ainda está enviando retorna 409
- **GIVEN** campanha com `status=sending`
- **WHEN** admin faz `POST /messaging/campaigns/42/retry`
- **THEN** retorna 409 com "Campanha ainda está sendo processada"
