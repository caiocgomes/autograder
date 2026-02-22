## Why

O V1 do bulk messaging funciona como fire-and-forget: o admin dispara mensagens e recebe um task_id do Celery, mas não há como acompanhar o progresso do envio, ver histórico de campanhas anteriores, ou reenviar mensagens que falharam. Se o admin fecha o browser, perde toda referência do que foi enviado. Para um volume crescente de alunos e comunicações frequentes, falta visibilidade e controle operacional sobre os envios.

## What Changes

- Backend: modelos `MessageCampaign` e `MessageRecipient` para persistir cada envio com status individual por destinatário
- Backend: `POST /messaging/send` adaptado para criar campanha + recipients no banco antes de despachar a Celery task
- Backend: Celery task `send_bulk_messages` adaptada para atualizar status de cada recipient e contadores da campanha progressivamente (a cada envio)
- Backend: `GET /messaging/campaigns` para listar campanhas com progresso
- Backend: `GET /messaging/campaigns/{id}` para detalhe com status por destinatário
- Backend: `POST /messaging/campaigns/{id}/retry` para reenviar mensagens falhadas
- Frontend: tabela de campanhas recentes na MessagingPage com barra de progresso
- Frontend: página de detalhe de campanha com lista de destinatários e status
- Frontend: polling automático enquanto campanha está em status `sending`
- Frontend: botão "Reenviar falhados" no detalhe de campanha

## Capabilities

### New Capabilities

- `message-campaigns`: Persistência de campanhas com status por destinatário, tracking de progresso em tempo real via polling, e retry de mensagens falhadas

### Modified Capabilities

- `bulk-messaging-api`: Endpoint de envio adaptado para criar campanha antes do dispatch; task adaptada para update progressivo no DB; novos endpoints de listagem, detalhe e retry

## Impact

- `autograder-back/app/models/`: novos modelos `MessageCampaign`, `MessageRecipient`
- `autograder-back/alembic/versions/`: migração com 2 tabelas novas
- `autograder-back/app/routers/messaging.py`: endpoints adaptados + novos (campaigns, retry)
- `autograder-back/app/schemas/messaging.py`: schemas de campanha e recipient
- `autograder-back/app/tasks.py`: task adaptada para update progressivo + suporte a retry (only_pending)
- `autograder-back/tests/`: testes de campanha, retry, progresso
- `autograder-web/src/api/messaging.ts`: novas chamadas (campaigns, retry)
- `autograder-web/src/pages/MessagingPage.tsx`: tabela de campanhas, detalhe, polling, retry
