## Context

A integração com Evolution API já funciona via `app/integrations/evolution.py` com `send_message(phone, text) -> bool`. O campo `User.whatsapp_number` armazena o número. Students são associados a classes via `ClassEnrollment` e a grupos via `GroupMembership`. O frontend usa React + TypeScript com inline styles, sem component library, e segue o layout professor/student com sidebar.

## Goals / Non-Goals

**Goals:**
- V1: endpoint de envio em massa + page de compose no frontend, funcional end-to-end
- V2: persistência de campanhas com status por destinatário, templates salvos, retry
- Specs TDD-ready: cada cenário mapeia direto para um test case (backend via pytest, frontend via testes de componente se/quando adicionados)

**Non-Goals:**
- Agendamento de envio futuro (cron de campanha)
- Media (imagens, PDFs) no WhatsApp (só texto por agora)
- Analytics de entrega (WhatsApp não expõe read receipts via Evolution API)
- Rate limiting adaptativo (v1 usa delay fixo entre envios)

## Decisions

**D1 — Throttling fixo de 1s entre envios**

O WhatsApp detecta spam por volume e velocidade. Um delay fixo de 1 segundo entre chamadas a `send_message()` é conservador o suficiente para lotes de até ~200 alunos (3min20s de task) sem triggar bloqueio. Para lotes maiores, pode precisar de backoff progressivo, mas isso é v3.

*Alternativa*: fila dedicada com rate limiter (ex: Celery rate_limit). Descartada porque adiciona complexidade sem ganho mensurável no volume atual.

**D2 — V1 sem persistência de campanha, V2 com**

V1 retorna 202 com task_id e feedback síncrono (total, skipped). O admin sabe o que mandou e para quem no momento do envio. Histórico formal com status por destinatário é V2.

Isso simplifica V1 significativamente: sem modelos novos, sem migração, só router + task + schemas.

*Risco*: admin perde visibilidade se fechar o browser. Aceitável para V1 dado o volume esperado (dezenas de alunos, não milhares).

**D3 — Variáveis resolvidas no Celery task, não no endpoint**

O endpoint valida que as variáveis no template são conhecidas, mas não resolve os valores. A resolução acontece no Celery task, por destinatário, no momento do envio. Isso evita pré-computar dados que podem mudar entre o dispatch e o envio (ex: nome alterado).

**D4 — Rota no ProfessorLayout com guard de admin**

Em vez de criar um AdminLayout separado, adiciona o item "Mensagens" na sidebar do ProfessorLayout condicionado a `user.role === 'admin'`. A rota em App.tsx usa o mesmo `ProtectedRoute` com `requiredRoles={['admin']}`.

*Justificativa*: o frontend não tem seção admin separada e criar uma agora para um único item é over-engineering. Quando houver mais funcionalidades admin-only, faz sentido extrair.

**D5 — Preview client-side**

A resolução de variáveis no preview é feita no frontend, usando os dados do primeiro aluno selecionado. Não precisa de round-trip ao backend para preview. Simples e instantâneo.

*Limitação*: se a lógica de resolução divergir entre front e back, o preview mente. Mitigado porque as regras de substituição são triviais (string replace).

**D6 — (V2) Modelos MessageCampaign e MessageRecipient**

```
MessageCampaign
├── id (PK)
├── message_template (Text)
├── class_id (FK nullable, para contexto da variável {turma})
├── sent_by (FK → users.id)
├── status (Enum: sending, completed, failed)
├── total_recipients (int)
├── sent_count (int)
├── failed_count (int)
├── created_at
├── completed_at (nullable)
└── recipients → MessageRecipient[]

MessageRecipient
├── id (PK)
├── campaign_id (FK → message_campaigns.id, ON DELETE CASCADE)
├── user_id (FK → users.id)
├── phone (String, snapshot no momento do envio)
├── resolved_message (Text, mensagem final enviada)
├── status (Enum: pending, sent, failed)
├── sent_at (nullable)
├── error_message (nullable)
└── created_at
```

O `phone` é snapshot: se o aluno trocar de número depois, o histórico reflete o que foi usado.
O `resolved_message` persiste a mensagem final (com variáveis resolvidas), não o template.

**D7 — (V2) MessageTemplate simples**

```
MessageTemplate
├── id (PK)
├── name (String, unique)
├── content (Text)
├── created_by (FK → users.id)
├── created_at
└── updated_at
```

Sem versionamento, sem categorias, sem ownership compartilhado. Um nome, um conteúdo, um dono. CRUD mínimo.

## Risks / Trade-offs

- **WhatsApp ban**: envio em massa pode triggar bloqueio do número da Evolution API. Throttling de 1s mitiga, mas o risco existe. Monitorar manualmente nas primeiras campanhas.
- **Sem confirmação de entrega**: `send_message()` retorna True se a Evolution API aceitou, não se o WhatsApp entregou. O "sent" no sistema significa "aceito pela API", não "lido pelo aluno".
- **Preview divergente**: lógica de substituição duplicada no front (JS) e no back (Python). Para as 4 variáveis atuais, o risco de divergência é baixo.
- **V1 sem histórico**: se o admin enviar a mesma mensagem duas vezes por engano, não há como saber pela plataforma. Aceitável para V1.

## Migration Plan

**V1**: sem migração. Apenas router, schemas, task, frontend page.

**V2**: migração Alembic com 3 tabelas (`message_campaigns`, `message_recipients`, `message_templates`). Sem impacto em tabelas existentes.
