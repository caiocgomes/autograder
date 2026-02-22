## Context

O V1 do bulk messaging está implementado e funcional: `POST /messaging/send` despacha uma Celery task que envia mensagens com throttling (10-30s entre envios) via Evolution API. O endpoint retorna 202 com um `task_id`, mas não há persistência de campanhas, tracking de progresso, ou mecanismo de retry. A integração com Evolution API (`send_message(phone, text) -> bool`) permanece inalterada. O campo `User.whatsapp_number` armazena o número. O frontend já tem a página de compose em `/professor/messaging` com seleção de destinatários e preview.

Os modelos `MessageCampaign` e `MessageRecipient` foram projetados no design do V1 (D6) mas não implementados. Este V2 materializa esses modelos e adiciona o ciclo completo de observabilidade.

## Goals / Non-Goals

**Goals:**
- Persistir cada envio como campanha com status individual por destinatário
- Permitir acompanhar progresso de envios em andamento (update progressivo no DB, polling no frontend)
- Permitir retry de mensagens falhadas por campanha
- Manter backward-compatible: a experiência de compose não muda, só ganha visibilidade pós-envio

**Non-Goals:**
- Templates salvos (CRUD de templates fica para V3)
- Agendamento de envio futuro
- Media (imagens, PDFs) no WhatsApp
- WebSocket/SSE para progresso (polling é suficiente dado o throttling de 10-30s)
- Analytics de entrega (WhatsApp não expõe read receipts via Evolution API)

## Decisions

**D1 — Update progressivo no DB a cada envio**

A Celery task atualiza `MessageRecipient.status` e incrementa `MessageCampaign.sent_count`/`failed_count` após cada chamada a `send_message()`. Como o throttling já é de 10-30s entre envios, um UPDATE por mensagem no Postgres é imperceptível em termos de carga. O frontend faz polling no endpoint de detalhe a cada 5s enquanto `status = sending`.

*Alternativa*: manter progresso no Redis e consolidar no banco ao final. Descartada porque perde durabilidade (worker crash = progresso perdido) e o volume de writes é trivial.

**D2 — Quatro status de campanha: sending, completed, partial_failure, failed**

| Status | Significado |
|--------|-------------|
| `sending` | Task rodando, progresso sendo atualizado |
| `completed` | Todos enviados com sucesso |
| `partial_failure` | Terminou, mas pelo menos um falhou |
| `failed` | Todos falharam (ou task crashou) |

O design V1 tinha só `sending | completed | failed`. Adicionar `partial_failure` dá leitura mais honesta na listagem: é o caso mais comum na prática e precisa ser distinguido de falha catastrófica.

A lógica de transição no final da task:
- `failed_count == 0` → `completed`
- `failed_count > 0 && sent_count > 0` → `partial_failure`
- `sent_count == 0` → `failed`

**D3 — Retry reseta falhados para pending e despacha nova task**

`POST /campaigns/{id}/retry`:
1. Valida que `status != sending` (409 se estiver enviando)
2. Filtra recipients com `status = failed` (400 se nenhum)
3. Reseta esses recipients para `status = pending`, limpa `error_message`
4. Recalcula `failed_count = 0` na campanha, mantém `sent_count` intacto
5. Seta `campaign.status = sending`
6. Despacha Celery task com `campaign_id` e flag `only_pending=True`

A task com `only_pending=True` só processa recipients da campanha que estão `pending`. Os que já estão `sent` ficam intactos. O `sent_count` é cumulativo entre tentativas.

Guard de concorrência: não permitir retry enquanto `status = sending`. Isso evita dois workers atualizando a mesma campanha.

**D4 — Campanha criada no endpoint, não na task**

O `POST /messaging/send` agora cria `MessageCampaign` + N `MessageRecipient` (com `status=pending`) antes de despachar a Celery task. O response muda de `{task_id, total, skipped}` para `{campaign_id, task_id, total, skipped}`. Isso garante que a campanha existe no banco imediatamente para consulta, mesmo que a task ainda não tenha começado.

**D5 — Task recebe campaign_id, não lista de recipients**

A task V1 recebia a lista de recipients como argumento. A task V2 recebe `campaign_id` e `message_template`, faz query no banco para buscar os recipients pendentes. Isso desacopla a task do endpoint e permite reuso para retry (mesma task, mesma campanha, recipients diferentes).

A task precisa de session do banco (import `SessionLocal` ou equivalente). A resolução de variáveis continua idêntica.

**D6 — Modelos MessageCampaign e MessageRecipient**

```
MessageCampaign
├── id (PK, Integer, autoincrement)
├── message_template (Text, not null)
├── course_id (Integer, FK → products.id, nullable)
├── course_name (String, snapshot do nome no momento do envio)
├── sent_by (Integer, FK → users.id, not null)
├── status (Enum: sending, completed, partial_failure, failed)
├── total_recipients (Integer, not null)
├── sent_count (Integer, default 0)
├── failed_count (Integer, default 0)
├── created_at (DateTime, server_default=now)
├── completed_at (DateTime, nullable)
└── recipients → MessageRecipient[] (cascade delete)

MessageRecipient
├── id (PK, Integer, autoincrement)
├── campaign_id (Integer, FK → message_campaigns.id, ON DELETE CASCADE, not null)
├── user_id (Integer, FK → users.id, not null)
├── phone (String, not null — snapshot do número no momento)
├── name (String — snapshot do nome para display)
├── resolved_message (Text, nullable — preenchido após envio)
├── status (Enum: pending, sent, failed)
├── sent_at (DateTime, nullable)
├── error_message (Text, nullable)
├── created_at (DateTime, server_default=now)
```

`phone` e `name` são snapshots: refletem o estado no momento do envio, não mudam se o aluno atualizar dados depois. `resolved_message` é preenchido pela task após resolver variáveis, antes de tentar enviar.

`course_name` na campanha é snapshot para não precisar de JOIN na listagem.

**D7 — Polling no frontend com auto-stop**

O frontend faz `GET /messaging/campaigns/{id}` a cada 5 segundos enquanto `status === "sending"`. Quando o status muda para qualquer outro valor, para o polling. Implementação via `setInterval` com cleanup no `useEffect`. Sem dependência de biblioteca externa.

**D8 — Response do POST /send inclui campaign_id**

O response do `POST /messaging/send` passa a incluir `campaign_id` além do `task_id`. O frontend usa o `campaign_id` para redirecionar ao detalhe da campanha e iniciar polling.

## Risks / Trade-offs

- **Session na Celery task**: a task passa a abrir e fechar session do banco. Precisa importar `SessionLocal` de `app/database.py`. Se o worker estiver em processo separado (padrão), funciona normalmente. Cuidado com connection pool exhaustion se múltiplas tasks rodarem em paralelo (improvável no fluxo atual, mas monitorar).
- **Campanha órfã**: se a task nunca rodar (Celery down), a campanha fica em `sending` eternamente. Não há mecanismo de timeout automático nesta versão. O admin pode identificar pela `created_at` velha sem progresso.
- **Contadores incrementais vs. count query**: os contadores `sent_count`/`failed_count` são incrementados inline na task, não recalculados via COUNT. Em caso de bug, podem ficar inconsistentes com os recipients reais. Aceitável dado a simplicidade; se necessário, um script de reconciliação resolve.
- **WhatsApp ban**: risco inalterado do V1. O throttling de 10-30s continua sendo a mitigação principal.

## Migration Plan

Migração Alembic com 2 tabelas novas (`message_campaigns`, `message_recipients`). Sem alteração em tabelas existentes. Sem dados para migrar (V1 não persistia campanhas).

Rollback: `alembic downgrade -1` remove as tabelas. Nenhum dado crítico perdido (campanhas são operacionais, não transacionais).

Deploy: migração pode rodar antes do deploy do novo código. As tabelas novas não interferem no V1 existente.
