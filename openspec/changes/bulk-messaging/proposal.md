## Why

O sistema já envia mensagens transacionais (lifecycle events: onboarding, welcome, churn) via Evolution API. Isso funciona, mas é reativo: só dispara quando algo acontece no lifecycle do aluno. Não existe mecanismo para enviar mensagens de marketing, lembretes de aula, avisos gerais ou comunicação proativa para um grupo de alunos. O professor/admin precisa de uma interface onde seleciona destinatários, escreve a mensagem e dispara.

## What Changes

### V1 — Disparo manual com compose

- Backend: endpoint `POST /messaging/send` que recebe filtros de destinatários + template de mensagem, despacha via Celery task com throttling para não triggar anti-spam do WhatsApp
- Backend: endpoint `GET /messaging/recipients` que lista alunos filtráveis por classe/grupo, com flag de quem tem `whatsapp_number` preenchido
- Frontend: página `/professor/messaging` (admin-only) com seleção de destinatários, compose com tags (`{nome}`, `{turma}`), preview e feedback de envio

### V2 — Campanhas, templates e histórico

- Backend: modelo `MessageCampaign` que persiste cada envio com status por destinatário
- Backend: CRUD de templates salvos
- Backend: retry de mensagens falhadas por campanha
- Frontend: histórico de campanhas, detalhe por campanha, gestão de templates

## Capabilities

### New Capabilities

- `bulk-messaging-api`: Endpoint e Celery task para disparo em massa via Evolution API, com throttling e feedback de resultado
- `messaging-compose-ui`: Página frontend para compor e disparar mensagens de marketing
- `message-campaigns` (v2): Persistência de campanhas enviadas com status por destinatário
- `message-templates` (v2): CRUD de templates reutilizáveis com variáveis

### Modified Capabilities

- `evolution-api`: Spec atualizada para incluir cenário de envio em massa (a função `send_message` em si não muda)

## Impact

- `autograder-back/app/routers/`: novo router `messaging.py`
- `autograder-back/app/tasks.py`: novo task `send_bulk_messages`
- `autograder-back/app/schemas/`: novo schema `messaging.py`
- `autograder-back/app/models/`: novos modelos `MessageCampaign`, `MessageRecipient`, `MessageTemplate` (v2)
- `autograder-back/alembic/versions/`: migração para modelos v2
- `autograder-web/src/pages/`: novo `MessagingPage.tsx`
- `autograder-web/src/api/`: novo `messaging.ts`
- `autograder-web/src/App.tsx`: nova rota
- `autograder-web/src/components/ProfessorLayout.tsx`: novo item na sidebar
