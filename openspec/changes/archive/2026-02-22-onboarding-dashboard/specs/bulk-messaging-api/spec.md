## MODIFIED Requirements

### Requirement: Celery task envia com throttling e update progressivo
O sistema SHALL implementar o task `send_bulk_messages` que recebe `campaign_id` e `message_template`, busca recipients pendentes no banco, resolve variáveis, envia via `send_message()` com throttling, e atualiza status no banco a cada envio.

#### Scenario: Task busca recipients pendentes da campanha
- **WHEN** task inicia com `campaign_id=42` e `only_pending=False`
- **THEN** faz query por `MessageRecipient` com `campaign_id=42` e `status=pending`

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

#### Scenario: Token auto-management when template uses {token}
- **GIVEN** template contains `{token}` variable
- **WHEN** task processes a recipient with no `onboarding_token` (NULL)
- **THEN** generates a new token (8 chars, 7-day expiry) for the user before resolving template

- **GIVEN** template contains `{token}` variable
- **WHEN** task processes a recipient with expired `onboarding_token`
- **THEN** regenerates token (new value, new 7-day expiry) for the user before resolving template

- **GIVEN** template contains `{token}` variable
- **WHEN** task processes a recipient with valid non-expired `onboarding_token`
- **THEN** uses existing token value for template resolution without regenerating

#### Scenario: Token variable resolves to user's onboarding_token
- **GIVEN** template is `"Seu token: {token}"` and user has `onboarding_token = "ABC12345"`
- **WHEN** task resolves template for that recipient
- **THEN** resolved message is `"Seu token: ABC12345"`
