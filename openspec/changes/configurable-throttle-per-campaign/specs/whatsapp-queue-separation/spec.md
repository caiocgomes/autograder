## ADDED Requirements

### Requirement: Filas Celery separadas para WhatsApp transacional e bulk
O sistema SHALL rotear tasks de envio WhatsApp para filas Celery distintas: `whatsapp_rt` para mensagens transacionais (lifecycle side-effects) e `whatsapp_bulk` para campanhas em massa.

#### Scenario: Campanha bulk vai para fila whatsapp_bulk
- **WHEN** `send_bulk_messages` é despachado via `apply_async`
- **THEN** o task é enfileirado na queue `whatsapp_bulk`

#### Scenario: Side-effect transacional vai para fila whatsapp_rt
- **WHEN** `execute_side_effect` é despachado com ação de envio WhatsApp
- **THEN** o task é enfileirado na queue `whatsapp_rt`

#### Scenario: Campanha longa não bloqueia mensagem transacional
- **GIVEN** campanha de 500 msgs em execução no worker bulk (estimativa 7h)
- **WHEN** aluno compra curso e lifecycle dispara WhatsApp onboarding
- **THEN** a mensagem de onboarding é processada pelo worker `whatsapp_rt` sem esperar a campanha

#### Scenario: Tasks não-WhatsApp continuam na fila default
- **WHEN** tasks como `process_hotmart_event` ou `sync_student_course_status` são despachados
- **THEN** são enfileirados na fila default do Celery (sem mudança)
