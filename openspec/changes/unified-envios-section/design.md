## Context

O frontend tem `MessagingPage` e `OnboardingPage` como páginas separadas, cada uma reimplementando: seleção de audiência, editor de template com inserção de tags, preview, variações LLM, throttle config e envio. O backend já unifica tudo no modelo `MessageCampaign` + task Celery `send_bulk_messages`. A divergência é puramente frontend.

O único gap no backend: `GET /messaging/recipients` filtra por `course_id` e `has_whatsapp`, mas não por `lifecycle_status`. Para a audiência unificada, esse filtro é necessário.

Usuário único (admin), sem necessidade de guardrails ou permissões granulares.

## Goals / Non-Goals

**Goals:**
- Uma única seção "Envios" que lista todas as campanhas e permite criar novos envios
- Eliminar duplicação de código no frontend (editor, preview, variações, throttle)
- Filtro de audiência por `lifecycle_status` para cobrir tanto envios genéricos quanto onboarding
- Manter acesso a `TemplateConfigModal` para templates de lifecycle

**Non-Goals:**
- Refatorar o backend de campanhas (já funciona)
- Extrair sub-componentes reutilizáveis (por ora, uma página monolítica é ok, como as atuais)
- Dashboard de funil de onboarding (dados existem na API, podem ser consultados depois se necessário)
- Mudar `CampaignDetailPage` (já funciona, permanece como está)

## Decisions

### 1. Uma página nova em vez de refatorar MessagingPage

**Decisão**: Criar `EnviosPage.tsx` do zero, remover `MessagingPage.tsx` e `OnboardingPage.tsx`.

**Rationale**: MessagingPage é um arquivo monolítico com ~600 linhas de inline styles e lógica misturada. Refatorar incrementalmente não economiza tempo. Criar do zero usando a mesma estrutura (inline styles, sem sub-componentes) mantém consistência com o codebase e dá liberdade para o layout novo (filtro de lifecycle_status, tags contextuais).

**Alternativa descartada**: Refatorar MessagingPage adicionando o filtro. Mais arriscado, não elimina OnboardingPage, mantém dois caminhos.

### 2. Filtro de lifecycle_status como chips/botões, não dropdown

**Decisão**: Botões tipo toggle (Todos, Pending Payment, Pending Onboarding, Active, Churned) acima da lista de alunos.

**Rationale**: São poucos estados (4 + "todos"), cabem visualmente. Mais rápido que dropdown, o admin vê o filtro ativo de relance.

### 3. Tags sempre visíveis, sem lógica contextual

**Decisão**: Todas as tags (`{nome}`, `{primeiro_nome}`, `{email}`, `{turma}`, `{token}`) ficam sempre disponíveis.

**Rationale**: Usuário único que sabe o que está fazendo. A tag `{token}` já é tratada no backend: se o template contém `{token}`, o Celery task gera/regenera o token automaticamente. Não precisa de guardrail no frontend.

### 4. Rota `/professor/envios` substituindo `/professor/messaging` e `/professor/onboarding`

**Decisão**: Nova rota `/professor/envios` com sub-rota `/professor/envios/campaigns/:id` para detail.

**Rationale**: Naming em português consistente com o conceito ("Envios"). CampaignDetailPage migra de rota mas o componente não muda.

### 5. Backend: adicionar `lifecycle_status` como query param no endpoint existente

**Decisão**: Adicionar `lifecycle_status: Optional[str] = None` ao `GET /messaging/recipients`. Filtra na query SQLAlchemy se presente.

**Rationale**: Mudança mínima (3-5 linhas). Não precisa de endpoint novo. O filtro é um `User.lifecycle_status == LifecycleStatus[value]` simples.

### 6. Manter TemplateConfigModal acessível via botão na seção Envios

**Decisão**: Botão "Configurar templates" no topo da EnviosPage, abrindo o modal existente sem modificação.

**Rationale**: O `TemplateConfigModal` já existe como componente standalone. Só precisa importar e conectar.

### 7. Variações LLM: manter fluxo inline (como MessagingPage faz hoje)

**Decisão**: O fluxo de gerar variações, revisar e aprovar fica inline na mesma página.

**Rationale**: Funciona bem hoje, sem necessidade de mudar.

## Risks / Trade-offs

- **[Perda de visibilidade do funil de onboarding]** → O summary bar (total, activated, pending, no_whatsapp) da OnboardingPage desaparece. Mitigação: se fizer falta, pode ser adicionado depois como card. Dados continuam disponíveis no endpoint `/onboarding/summary`.
- **[Token status não visível na lista de alunos]** → OnboardingPage mostrava token_status (valid, expired, none) por aluno. Na EnviosPage unificada, a lista de recipients não tem essa info. Mitigação: se fizer falta, adicionar ao `RecipientOut` do backend. Por ora, o admin sabe quem precisa de token pelo lifecycle_status.
- **[Rotas quebradas em bookmarks/links]** → `/professor/messaging` e `/professor/onboarding` deixam de existir. Mitigação: como é um único usuário, não é risco real.
