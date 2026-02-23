## Why

O frontend tem dois lugares separados para enviar mensagens WhatsApp: MessagingPage (envio batch genérico) e OnboardingPage (envio de tokens de onboarding). Ambas reimplementam o mesmo fluxo (seleção de audiência, editor de template, preview, variações LLM, throttle config) sobre o mesmo backend (`MessageCampaign`). Isso causa duplicação de código no frontend e fragmenta a visibilidade operacional: para ver todos os envios em andamento, é preciso navegar entre duas páginas.

## What Changes

- **BREAKING** Remove `OnboardingPage` e `MessagingPage` do frontend
- Cria nova seção "Envios" com lista unificada de campanhas (em andamento, concluídas, falhadas)
- Cria fluxo "Novo Envio" unificado com: seleção de curso, filtro por `lifecycle_status`, seleção de alunos, editor de template com todas as tags, variações LLM, throttle config
- Adiciona filtro `lifecycle_status` ao endpoint `GET /messaging/recipients`
- Remove rotas e links de sidebar para Onboarding e Messaging antigos
- `CampaignDetailPage` permanece sem alterações

## Capabilities

### New Capabilities
- `unified-envios`: Seção única de envios que consolida criação, monitoramento e configuração de campanhas WhatsApp (batch genérico e onboarding)

### Modified Capabilities
- `bulk-messaging-api`: Adiciona filtro `lifecycle_status` ao endpoint de recipients
- `onboarding-dashboard`: Removido como página separada; funcionalidade de envio absorvida por `unified-envios`

## Impact

- **Frontend**: Remove 2 páginas (MessagingPage, OnboardingPage), cria 1 nova seção (EnviosPage + fluxo Novo Envio). Atualiza rotas em `App.tsx` e sidebar no layout professor.
- **Backend**: Mudança mínima: adicionar parâmetro `lifecycle_status` opcional ao endpoint `GET /messaging/recipients`.
- **Sem impacto**: Pipeline de envio (Celery tasks, Evolution API, variações LLM), CampaignDetailPage, templates de lifecycle (continuam operando via webhook), TemplateConfigModal.
