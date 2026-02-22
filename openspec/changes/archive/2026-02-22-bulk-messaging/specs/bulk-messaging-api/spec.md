## ADDED Requirements

### Requirement: Listar destinatários com status de telefone
O sistema SHALL expor `GET /messaging/recipients` que retorna alunos filtráveis, incluindo flag de disponibilidade de WhatsApp, acessível apenas por admin.

#### Scenario: Listar alunos de uma classe
- **GIVEN** existem 3 alunos matriculados na classe 1, sendo 2 com `whatsapp_number` preenchido e 1 sem
- **WHEN** admin faz `GET /messaging/recipients?class_id=1`
- **THEN** retorna 3 registros, cada um com `id`, `name`, `email`, `whatsapp_number` (ou null), `has_whatsapp: bool`

#### Scenario: Filtrar por classe e grupo
- **GIVEN** classe 1 tem grupo A com 2 alunos e grupo B com 1 aluno
- **WHEN** admin faz `GET /messaging/recipients?class_id=1&group_id=<grupo_A_id>`
- **THEN** retorna apenas os 2 alunos do grupo A

#### Scenario: Filtrar apenas alunos com WhatsApp
- **GIVEN** existem 5 alunos na classe, 3 com `whatsapp_number` preenchido
- **WHEN** admin faz `GET /messaging/recipients?class_id=1&has_whatsapp=true`
- **THEN** retorna apenas os 3 alunos com `whatsapp_number` não-nulo

#### Scenario: Acesso negado para não-admin
- **GIVEN** usuário autenticado com role `student`
- **WHEN** faz `GET /messaging/recipients?class_id=1`
- **THEN** retorna 403 Forbidden

#### Scenario: Acesso negado para professor
- **GIVEN** usuário autenticado com role `professor`
- **WHEN** faz `GET /messaging/recipients?class_id=1`
- **THEN** retorna 403 Forbidden

---

### Requirement: Enviar mensagem em massa via Celery
O sistema SHALL expor `POST /messaging/send` que aceita lista de user IDs + template de mensagem, valida os inputs, e despacha um Celery task para envio com throttling. Acessível apenas por admin.

#### Scenario: Envio bem-sucedido para múltiplos alunos
- **GIVEN** existem 3 alunos com IDs [1, 2, 3], todos com `whatsapp_number` preenchido
- **WHEN** admin faz `POST /messaging/send` com `{"user_ids": [1, 2, 3], "message_template": "Olá {nome}, aula amanhã!"}`
- **THEN** retorna 202 Accepted com `{"task_id": "<celery_task_id>", "total_recipients": 3, "skipped_no_phone": 0}`
- **AND** o Celery task é enfileirado

#### Scenario: Alunos sem WhatsApp são reportados mas não bloqueiam envio
- **GIVEN** user_ids [1, 2, 3] onde user 2 tem `whatsapp_number = NULL`
- **WHEN** admin faz `POST /messaging/send` com esses IDs
- **THEN** retorna 202 com `{"total_recipients": 2, "skipped_no_phone": 1, "skipped_users": [{"id": 2, "name": "...", "reason": "no_whatsapp"}]}`
- **AND** o Celery task é enfileirado apenas para users 1 e 3

#### Scenario: Template com variáveis é validado
- **GIVEN** template contém `{nome}` e `{turma}`
- **WHEN** admin faz `POST /messaging/send` com esse template
- **THEN** sistema aceita (variáveis conhecidas são permitidas)

#### Scenario: Template com variável desconhecida é rejeitado
- **GIVEN** template contém `{saldo_bancario}`
- **WHEN** admin faz `POST /messaging/send` com esse template
- **THEN** retorna 422 com erro indicando variáveis inválidas: `["saldo_bancario"]`

#### Scenario: Lista vazia de user_ids é rejeitada
- **GIVEN** request com `user_ids: []`
- **WHEN** admin faz `POST /messaging/send`
- **THEN** retorna 422 com erro "user_ids não pode ser vazio"

#### Scenario: Mensagem vazia é rejeitada
- **GIVEN** request com `message_template: ""`
- **WHEN** admin faz `POST /messaging/send`
- **THEN** retorna 422 com erro "message_template não pode ser vazio"

---

### Requirement: Celery task envia com throttling
O sistema SHALL implementar o task `send_bulk_messages` que itera sobre os destinatários, resolve variáveis, chama `send_message()` por destinatário com pausa entre envios para evitar anti-spam.

#### Scenario: Mensagem com variáveis é resolvida por destinatário
- **GIVEN** user João (nome="João Silva") está na classe "Python 101"
- **WHEN** task processa template "Olá {nome}, sua turma {turma} tem novidades"
- **THEN** a mensagem enviada é "Olá João Silva, sua turma Python 101 tem novidades"

#### Scenario: Throttling entre envios
- **GIVEN** 3 destinatários para envio
- **WHEN** task processa o lote
- **THEN** há pelo menos 1 segundo de pausa entre cada chamada a `send_message()`

#### Scenario: Falha em um destinatário não aborta os demais
- **GIVEN** 3 destinatários, e `send_message` retorna False para o segundo
- **WHEN** task processa o lote
- **THEN** os 3 são processados (não para no erro do segundo)
- **AND** o resultado final indica 2 enviados, 1 falhado

#### Scenario: Task retorna contadores de resultado
- **GIVEN** lote de 5 destinatários, 4 enviados com sucesso, 1 falhou
- **WHEN** task completa
- **THEN** retorna `{"sent": 4, "failed": 1, "total": 5}`

---

### Requirement: Variáveis disponíveis para templates
O sistema SHALL suportar as seguintes variáveis em templates de mensagem.

#### Variáveis suportadas

| Variável | Resolução | Fonte |
|----------|-----------|-------|
| `{nome}` | `user.name` | User model |
| `{primeiro_nome}` | `user.name.split()[0]` | User model, primeiro token |
| `{email}` | `user.email` | User model |
| `{turma}` | Nome da classe usada no filtro | Class model (do contexto de envio) |

#### Scenario: Variável sem valor disponível é substituída por string vazia
- **GIVEN** template usa `{turma}` mas o envio não foi filtrado por classe (envio direto por IDs)
- **WHEN** task resolve as variáveis
- **THEN** `{turma}` é substituída por "" (string vazia)
