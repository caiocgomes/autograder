## ADDED Requirements (V2)

### Requirement: CRUD de templates de mensagem
O sistema SHALL permitir criar, listar, editar e deletar templates de mensagem reutilizáveis, acessíveis apenas por admin.

#### Scenario: Criar template
- **GIVEN** admin autenticado
- **WHEN** faz `POST /messaging/templates` com `{"name": "Lembrete de aula", "content": "Olá {primeiro_nome}, amanhã tem aula de {turma}!"}`
- **THEN** retorna 201 com o template criado incluindo `id`, `name`, `content`, `created_at`

#### Scenario: Nome duplicado é rejeitado
- **GIVEN** template com nome "Lembrete de aula" já existe
- **WHEN** admin faz `POST /messaging/templates` com mesmo nome
- **THEN** retorna 409 com "Template com este nome já existe"

#### Scenario: Listar templates
- **GIVEN** existem 5 templates
- **WHEN** admin faz `GET /messaging/templates`
- **THEN** retorna lista ordenada por nome com `id`, `name`, `content`, `created_at`, `updated_at`

#### Scenario: Editar template
- **GIVEN** template ID 3 existe com content "texto antigo"
- **WHEN** admin faz `PUT /messaging/templates/3` com `{"name": "Novo nome", "content": "texto novo"}`
- **THEN** retorna 200 com template atualizado, `updated_at` reflete a mudança

#### Scenario: Deletar template
- **GIVEN** template ID 3 existe
- **WHEN** admin faz `DELETE /messaging/templates/3`
- **THEN** retorna 204
- **AND** `GET /messaging/templates/3` retorna 404

#### Scenario: Template inexistente retorna 404
- **GIVEN** não existe template com ID 99
- **WHEN** admin faz `GET /messaging/templates/99`
- **THEN** retorna 404

---

### Requirement: Usar template salvo no compose
O sistema SHALL permitir que o admin selecione um template salvo ao compor mensagem, preenchendo o textarea automaticamente.

#### Scenario: Selecionar template preenche textarea
- **GIVEN** admin está na página de compose, templates "Lembrete de aula" e "Boas vindas" existem
- **WHEN** admin seleciona "Lembrete de aula" no dropdown de templates
- **THEN** textarea é preenchida com o content do template
- **AND** admin pode editar livremente antes de enviar

#### Scenario: Mudar de template sobrescreve o textarea
- **GIVEN** textarea tem texto modificado (baseado em template anterior)
- **WHEN** admin seleciona outro template
- **THEN** textarea é substituída pelo content do novo template (sem merge)

#### Scenario: Opção "Mensagem livre" limpa o dropdown
- **GIVEN** admin selecionou um template
- **WHEN** seleciona a opção vazia / "Mensagem livre" no dropdown
- **THEN** textarea é limpa e admin pode escrever do zero
