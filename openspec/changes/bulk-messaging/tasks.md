## V1 — Disparo manual com compose

### 1. Backend: Schemas e Router

- [x] 1.1 Criar `autograder-back/app/schemas/messaging.py` com: `RecipientOut` (id, name, email, whatsapp_number, has_whatsapp), `RecipientListResponse`, `BulkSendRequest` (user_ids: list[int], message_template: str, class_id: int | None), `BulkSendResponse` (task_id, total_recipients, skipped_no_phone, skipped_users)
- [x] 1.2 Criar `autograder-back/app/routers/messaging.py` com `GET /messaging/recipients` (filtros: class_id, group_id, has_whatsapp) e `POST /messaging/send`
- [x] 1.3 Registrar router em `main.py`

### 2. Backend: Celery Task

- [x] 2.1 Adicionar task `send_bulk_messages` em `app/tasks.py`: recebe lista de (user_id, phone, name, class_name) + template, resolve variáveis, chama `send_message()` por destinatário com `time.sleep(1)` entre envios, retorna contadores {sent, failed, total}
- [x] 2.2 Implementar resolução de variáveis: `{nome}`, `{primeiro_nome}`, `{email}`, `{turma}` (string replace simples)

### 3. Backend: Testes

- [x] 3.1 Criar `autograder-back/tests/test_messaging_router.py` cobrindo:
  - GET recipients com filtro por class_id
  - GET recipients com filtro por group_id
  - GET recipients com filtro has_whatsapp
  - GET recipients: 403 para student e professor
  - POST send com user_ids válidos → 202 + task dispatch
  - POST send com user_ids onde alguns sem whatsapp → skipped reportados
  - POST send com variável inválida → 422
  - POST send com user_ids vazio → 422
  - POST send com template vazio → 422
- [x] 3.2 Criar `autograder-back/tests/test_bulk_send_task.py` cobrindo:
  - Resolução de variáveis {nome}, {primeiro_nome}, {turma}
  - Throttling (mock time.sleep chamado entre envios)
  - Falha em um destinatário não aborta demais
  - Contadores de resultado (sent, failed, total)

### 4. Frontend: API client

- [x] 4.1 Criar `autograder-web/src/api/messaging.ts` com `getRecipients(params)`, `sendBulk(request)`, interfaces TypeScript correspondentes

### 5. Frontend: Página de Compose

- [x] 5.1 Criar `autograder-web/src/pages/MessagingPage.tsx` com:
  - Dropdown de classe (carrega via `classesApi.list()`)
  - Dropdown de grupo (carrega ao selecionar classe)
  - Lista de alunos com checkboxes e indicador de WhatsApp
  - "Selecionar todos" / "Desselecionar todos"
  - Contador de selecionados (total e com WhatsApp)
  - Textarea de composição
  - Botões de tags ({nome}, {primeiro_nome}, {email}, {turma})
  - Preview renderizado com dados do primeiro selecionado
  - Botão "Enviar" (desabilitado se sem destinatários ou sem texto)
  - Confirmação via `confirm()` antes de enviar
  - Feedback pós-envio (sucesso com contadores, ou erro)
- [x] 5.2 Adicionar rota em `App.tsx`: `/professor/messaging` com `requiredRoles={['admin']}`
- [x] 5.3 Adicionar item "Mensagens" na sidebar do `ProfessorLayout.tsx` condicionado a `user.role === 'admin'`

---

## V2 — Campanhas, templates e histórico

### 6. Backend: Modelos de campanha

- [ ] 6.1 Criar `autograder-back/app/models/message_campaign.py` com `MessageCampaign` e `MessageRecipient`
- [ ] 6.2 Criar `autograder-back/app/models/message_template.py` com `MessageTemplate`
- [ ] 6.3 Migração Alembic com as 3 tabelas

### 7. Backend: Endpoints de campanha

- [ ] 7.1 Adicionar ao router: `GET /messaging/campaigns` (paginado, filtro por status), `GET /messaging/campaigns/{id}` (detalhe com recipients), `POST /messaging/campaigns/{id}/retry`
- [ ] 7.2 Adaptar `POST /messaging/send` para criar `MessageCampaign` + `MessageRecipient` registros antes de despachar task
- [ ] 7.3 Adaptar task `send_bulk_messages` para atualizar `MessageRecipient.status` e `MessageCampaign` contadores ao final

### 8. Backend: Endpoints de templates

- [ ] 8.1 Adicionar ao router: `POST /messaging/templates`, `GET /messaging/templates`, `PUT /messaging/templates/{id}`, `DELETE /messaging/templates/{id}`

### 9. Backend: Testes V2

- [ ] 9.1 Testes de campanha: criação ao enviar, status por recipient, contadores finais, retry de falhados, retry sem falhados → 400, retry durante sending → 409
- [ ] 9.2 Testes de templates: CRUD completo, nome duplicado → 409, inexistente → 404

### 10. Frontend: Histórico e templates

- [ ] 10.1 Adicionar listagem de campanhas anteriores na MessagingPage (tabela abaixo do compose, ou tab separada)
- [ ] 10.2 Página de detalhe de campanha com status por destinatário + botão retry
- [ ] 10.3 Dropdown de templates no compose, preenchendo textarea ao selecionar
- [ ] 10.4 Tela de gestão de templates (CRUD inline ou modal)
