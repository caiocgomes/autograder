## MODIFIED Requirements

### Requirement: Persistência de campanhas enviadas
O sistema SHALL persistir cada envio em massa como uma `MessageCampaign` com registros individuais `MessageRecipient`, criados no momento do dispatch (antes da Celery task iniciar). A campanha SHALL incluir configuração de throttle (`throttle_min_seconds`, `throttle_max_seconds`).

#### Scenario: Campanha é criada ao disparar envio
- **WHEN** admin faz `POST /messaging/send` com 20 user_ids, um template, e `throttle_min_seconds=10`, `throttle_max_seconds=20`
- **THEN** uma `MessageCampaign` é criada com `status=sending`, `total_recipients=20`, `message_template`, `course_name` (snapshot), `sent_by` (admin user_id), `created_at`, `throttle_min_seconds=10.0`, `throttle_max_seconds=20.0`
- **AND** 20 registros `MessageRecipient` são criados com `status=pending`, `phone` (snapshot), `name` (snapshot)
- **AND** response inclui `campaign_id` junto com `task_id`

#### Scenario: Campanha criada sem throttle explícito usa defaults
- **WHEN** admin faz `POST /messaging/send` com 20 user_ids e um template, sem parâmetros de throttle
- **THEN** `MessageCampaign` é criada com `throttle_min_seconds=15.0`, `throttle_max_seconds=25.0`

#### Scenario: Recipients sem WhatsApp não geram MessageRecipient
- **WHEN** admin envia para 15 user_ids, 2 sem `whatsapp_number`
- **THEN** campanha tem `total_recipients=13`
- **AND** 13 `MessageRecipient` são criados (apenas os com telefone)
- **AND** os 2 sem telefone aparecem em `skipped_users` no response
