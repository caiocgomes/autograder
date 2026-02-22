## 1. Modelos e migração

- [x] 1.1 Criar `autograder-back/app/models/message_campaign.py` com modelos `MessageCampaign` (id, message_template, course_id, course_name, sent_by, status enum [sending/completed/partial_failure/failed], total_recipients, sent_count, failed_count, created_at, completed_at) e `MessageRecipient` (id, campaign_id FK cascade, user_id FK, phone, name, resolved_message, status enum [pending/sent/failed], sent_at, error_message, created_at)
- [x] 1.2 Registrar modelos em `app/models/__init__.py`
- [x] 1.3 Criar migração Alembic com as 2 tabelas (`message_campaigns`, `message_recipients`)

## 2. Schemas

- [x] 2.1 Adicionar schemas em `app/schemas/messaging.py`: `CampaignOut` (listagem com template truncado a 100 chars), `CampaignDetailOut` (detalhe com template completo + lista de recipients), `RecipientStatusOut` (user_id, name, phone, status, resolved_message, sent_at, error_message), `RetryResponse` (retrying, campaign_id)
- [x] 2.2 Atualizar `BulkSendResponse` para incluir `campaign_id: int`

## 3. Adaptar endpoint POST /messaging/send

- [x] 3.1 Adaptar `POST /messaging/send` para criar `MessageCampaign` + N `MessageRecipient` (status=pending) antes de despachar Celery task
- [x] 3.2 Passar `campaign_id` e `message_template` para a Celery task (em vez de lista de recipients)
- [x] 3.3 Incluir `campaign_id` no response

## 4. Novos endpoints de campanha

- [x] 4.1 Implementar `GET /messaging/campaigns` com paginação (limit/offset), filtro por status, ordenado por created_at desc
- [x] 4.2 Implementar `GET /messaging/campaigns/{id}` com detalhe completo incluindo lista de recipients
- [x] 4.3 Implementar `POST /messaging/campaigns/{id}/retry`: validar status != sending (409), filtrar falhados (400 se nenhum), resetar para pending, zerar failed_count, setar status=sending, despachar task com only_pending=True

## 5. Adaptar Celery task

- [x] 5.1 Adaptar `send_bulk_messages` para receber `campaign_id` + `message_template` + `only_pending` flag em vez de lista de recipients
- [x] 5.2 Task abre session do banco, busca recipients pendentes da campanha
- [x] 5.3 Após cada envio: UPDATE recipient (status, resolved_message, sent_at ou error_message) + INCREMENT campaign counters + commit
- [x] 5.4 Ao final: definir status da campanha (completed/partial_failure/failed) e setar completed_at

## 6. Testes backend

- [x] 6.1 Testes do endpoint `POST /messaging/send` adaptado: verifica criação de campanha + recipients, response com campaign_id
- [x] 6.2 Testes do `GET /messaging/campaigns`: paginação, filtro por status, ordenação, acesso negado para não-admin
- [x] 6.3 Testes do `GET /messaging/campaigns/{id}`: detalhe com recipients, 404 para inexistente
- [x] 6.4 Testes do `POST /messaging/campaigns/{id}/retry`: retry ok, sem falhados → 400, campanha sending → 409, inexistente → 404, contadores acumulados
- [x] 6.5 Testes da task adaptada: update progressivo, status final, only_pending=True processa apenas pendentes

## 7. Frontend: API client

- [x] 7.1 Adicionar em `src/api/messaging.ts`: `getCampaigns(params)`, `getCampaign(id)`, `retryCampaign(id)` com interfaces TypeScript correspondentes
- [x] 7.2 Atualizar interface `BulkSendResponse` para incluir `campaign_id`

## 8. Frontend: listagem e detalhe de campanhas

- [x] 8.1 Adicionar tabela de campanhas recentes na MessagingPage (abaixo do compose), com colunas: preview da mensagem, curso, progresso (sent/total), status com badge colorido, data
- [x] 8.2 Criar componente/página de detalhe de campanha com: info da campanha, barra de progresso, tabela de recipients com status individual, mensagem de erro quando houver
- [x] 8.3 Implementar polling automático (5s) no detalhe enquanto status === "sending", com auto-stop quando muda
- [x] 8.4 Adicionar botão "Reenviar falhados (N)" visível quando status é partial_failure ou failed, com confirm antes de disparar
- [x] 8.5 Após envio no compose, redirecionar para detalhe da campanha recém-criada (usando campaign_id do response)
