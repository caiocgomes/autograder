## ADDED Requirements

### Requirement: Página de compose acessível por admin
O sistema SHALL exibir uma página em `/professor/messaging` acessível apenas por usuários com role `admin`, com link na sidebar do ProfessorLayout.

#### Scenario: Admin vê link na sidebar
- **GIVEN** usuário logado com role `admin`
- **WHEN** acessa qualquer página do painel professor
- **THEN** sidebar exibe item "Mensagens" com link para `/professor/messaging`

#### Scenario: Professor não vê link na sidebar
- **GIVEN** usuário logado com role `professor`
- **WHEN** acessa qualquer página do painel professor
- **THEN** sidebar NÃO exibe item "Mensagens"

#### Scenario: Acesso direto por não-admin é bloqueado
- **GIVEN** usuário logado com role `professor`
- **WHEN** navega diretamente para `/professor/messaging`
- **THEN** é redirecionado para a página principal do professor

---

### Requirement: Seleção de destinatários com filtros
O sistema SHALL exibir um painel de seleção de destinatários com filtros por classe e grupo, mostrando status de WhatsApp de cada aluno.

#### Scenario: Selecionar classe carrega alunos
- **GIVEN** admin está na página de messaging
- **WHEN** seleciona "Python 101" no dropdown de classe
- **THEN** lista de alunos é carregada via `GET /messaging/recipients?class_id=X`
- **AND** cada aluno exibe nome, email, e indicador de WhatsApp (verde se tem, cinza se não)

#### Scenario: Filtrar por grupo dentro da classe
- **GIVEN** classe "Python 101" está selecionada e tem grupos "A" e "B"
- **WHEN** admin seleciona "Grupo A" no dropdown de grupo
- **THEN** lista de alunos atualiza para mostrar apenas membros do grupo A

#### Scenario: Selecionar todos / desselecionar todos
- **GIVEN** lista mostra 10 alunos
- **WHEN** admin clica "Selecionar todos"
- **THEN** todos os 10 checkboxes são marcados
- **AND** botão muda para "Desselecionar todos"

#### Scenario: Contador de selecionados é atualizado em tempo real
- **GIVEN** lista mostra 10 alunos, 3 selecionados
- **WHEN** admin marca mais 2 checkboxes
- **THEN** contador mostra "5 selecionados (4 com WhatsApp)" se 1 dos 5 não tem `whatsapp_number`

#### Scenario: Aluno sem WhatsApp é selecionável mas com aviso visual
- **GIVEN** aluno "Pedro" não tem `whatsapp_number`
- **WHEN** aparece na lista
- **THEN** exibe ícone de aviso e texto "(sem WhatsApp)" ao lado do nome
- **AND** checkbox está disponível mas o aluno será reportado como skipped no envio

---

### Requirement: Composição de mensagem com tags
O sistema SHALL exibir uma área de composição com textarea e botões para inserir variáveis (tags) na posição do cursor.

#### Scenario: Inserir tag via botão
- **GIVEN** cursor está posicionado no meio do texto "Olá , tudo bem?"
- **WHEN** admin clica no botão `{nome}`
- **THEN** texto fica "Olá {nome}, tudo bem?" com tag inserida na posição do cursor

#### Scenario: Tags disponíveis são exibidas como botões
- **GIVEN** admin está na área de composição
- **THEN** os seguintes botões de tag são exibidos: `{nome}`, `{primeiro_nome}`, `{email}`, `{turma}`

#### Scenario: Textarea vazia desabilita botão de envio
- **GIVEN** textarea está vazia
- **THEN** botão "Enviar" está desabilitado

#### Scenario: Nenhum destinatário selecionado desabilita botão de envio
- **GIVEN** textarea tem texto mas nenhum aluno está selecionado
- **THEN** botão "Enviar" está desabilitado

---

### Requirement: Preview da mensagem antes do envio
O sistema SHALL exibir um preview da mensagem renderizada com as variáveis resolvidas para o primeiro aluno selecionado.

#### Scenario: Preview renderiza variáveis
- **GIVEN** primeiro aluno selecionado é "João Silva" da turma "Python 101"
- **AND** template é "Olá {nome}, sua turma {turma} começa amanhã"
- **WHEN** admin visualiza o preview
- **THEN** preview mostra "Olá João Silva, sua turma Python 101 começa amanhã"

#### Scenario: Preview atualiza ao mudar template
- **GIVEN** preview está exibindo mensagem renderizada
- **WHEN** admin edita o template na textarea
- **THEN** preview atualiza em tempo real

#### Scenario: Preview mostra aviso quando não há destinatários
- **GIVEN** nenhum aluno selecionado
- **THEN** área de preview mostra "Selecione destinatários para ver o preview"

---

### Requirement: Confirmação e feedback de envio
O sistema SHALL pedir confirmação antes de enviar e exibir resultado do envio.

#### Scenario: Confirmação antes do envio
- **GIVEN** 15 alunos selecionados, 13 com WhatsApp
- **WHEN** admin clica "Enviar"
- **THEN** exibe confirmação: "Enviar mensagem para 13 alunos? (2 sem WhatsApp serão ignorados)"
- **AND** admin deve confirmar para prosseguir

#### Scenario: Feedback de envio bem-sucedido
- **GIVEN** admin confirmou envio para 13 alunos
- **WHEN** `POST /messaging/send` retorna 202 com task_id
- **THEN** exibe mensagem de sucesso: "Mensagem enfileirada para 13 destinatários"

#### Scenario: Feedback inclui skipped
- **GIVEN** envio foi disparado com 15 user_ids, 2 sem WhatsApp
- **WHEN** resposta inclui `skipped_no_phone: 2`
- **THEN** feedback mostra "Enfileirada para 13. 2 alunos sem WhatsApp foram ignorados."
