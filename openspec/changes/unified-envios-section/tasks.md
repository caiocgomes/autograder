## 1. Backend: filtro lifecycle_status

- [x] 1.1 Adicionar query param `lifecycle_status: Optional[str]` ao `GET /messaging/recipients` em `app/routers/messaging.py`, filtrando por `User.lifecycle_status` quando presente. Retornar 422 para valores inválidos.
- [x] 1.2 Adicionar teste para o filtro de lifecycle_status no endpoint de recipients (filtro válido, sem filtro, valor inválido).

## 2. Frontend: criar EnviosPage

- [x] 2.1 Criar `autograder-web/src/pages/professor/EnviosPage.tsx` com lista de campanhas (tabela com curso, status badge, progresso, data) e botão "+ Novo Envio".
- [x] 2.2 Implementar fluxo "Novo Envio" inline na EnviosPage: seleção de curso (dropdown), filtro de audiência por lifecycle_status (botões toggle), lista de recipients com checkboxes e contagem.
- [x] 2.3 Implementar editor de template com inserção de tags (`{nome}`, `{primeiro_nome}`, `{email}`, `{turma}`, `{token}`), preview da mensagem resolvida, e campo de throttle config (min/max).
- [x] 2.4 Implementar fluxo de variações LLM: botão gerar, display de variações com checkboxes de aprovação, inclusão das aprovadas no request de envio.
- [x] 2.5 Implementar confirmação e dispatch: dialog de confirmação com contagem, chamada a `POST /messaging/send`, navegação para campaign detail on success.

## 3. Frontend: atualizar API client

- [x] 3.1 Adicionar parâmetro `lifecycle_status?: string` à função `getRecipients` em `autograder-web/src/api/messaging.ts`.

## 4. Frontend: rotas e navegação

- [x] 4.1 Atualizar `App.tsx`: remover rotas `/professor/messaging` e `/professor/onboarding`, adicionar `/professor/envios` e `/professor/envios/campaigns/:id`.
- [x] 4.2 Atualizar `ProfessorLayout.tsx`: substituir links "Mensagens" e "Onboarding" por "Envios" apontando para `/professor/envios`.
- [x] 4.3 Importar e conectar `TemplateConfigModal` na EnviosPage com botão "Configurar templates".

## 5. Cleanup

- [x] 5.1 Remover `autograder-web/src/pages/professor/MessagingPage.tsx` e `OnboardingPage.tsx`.
- [x] 5.2 Remover imports órfãos desses arquivos em App.tsx e qualquer outro lugar.
- [x] 5.3 Verificar que `npm run build` passa sem erros.
