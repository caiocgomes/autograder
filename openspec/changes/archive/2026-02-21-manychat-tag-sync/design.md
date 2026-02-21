## Context

O sistema já tem lifecycle de aluno via webhooks Hotmart e uma integração ManyChat que adiciona/remove uma única tag por produto em transições de estado. Dois problemas:

1. **Sem estado por (aluno, produto)**: `User.lifecycle_status` é um campo único — não reflete que um aluno pode estar ativo em LLMs e cancelado no CDO simultaneamente.
2. **Tags ManyChat sem histórico de status**: a tag é removida no churn, impossibilitando segmentos como "cancelados do LLMs nos últimos 30 dias".

A solução é um job de sync em batch que lê o estado atual da Hotmart via REST API, mantém o histórico num design SCD Type 2, e aplica tags duais no ManyChat.

## Goals / Non-Goals

**Goals:**
- Tabela `student_course_status` com histórico completo por `(user, product)` via SCD Type 2
- Tags ManyChat: `{Curso}` (permanente) + `{Curso}, {Status}` (mutável) por produto com acesso
- Sync batch diário a partir da Hotmart API (complementa webhooks em tempo real)
- Suporte a acesso derivado: "A Base de Tudo" concede as mesmas tags que "De analista a CDO"
- Trigger manual via `POST /admin/events/manychat-sync`

**Non-Goals:**
- Substituir o lifecycle via webhooks (continua como está)
- Sync em tempo real de tags ManyChat (webhooks já cobrem isso para novos eventos)
- Lookup de telefone fora do contexto do sync (whatsapp_number já é populado pelo lifecycle)

## Decisions

### 1. SCD Type 2 para histórico de status por (user, product)

**Decisão**: Nova tabela `student_course_status` com colunas `valid_from`, `valid_to`, `is_current`.

**Alternativas**:
- (a) SCD Type 1 (sobrescrever): perde histórico, impossibilita análise de padrões de churn.
- (b) SCD Type 3 (current + previous na mesma linha): só 1 nível de histórico, quebra no terceiro estado.
- (c) SCD Type 4 (tabela de current + tabela de history separadas): over-engineering para a escala atual (400 alunos × 5 produtos).
- (d) **SCD Type 2 (nova linha por mudança)**: histórico completo em uma tabela, queries de estado atual via `is_current = true`.

**Rationale**: (d) resolve todas as queries analíticas relevantes sem overhead operacional. O volume (≤10.000 linhas totais) nunca vai exigir otimização.

### 2. Schema de tags: dual tag por curso

**Decisão**: 2 tags por curso para cada aluno — `{Curso}` (permanente) + `{Curso}, {Status}` (mutável).

**Status vocabulary**:
```
Hotmart status              → tag de status
────────────────────────────────────────────────────────
APPROVED, COMPLETE          → "Ativo"
OVERDUE                     → "Inadimplente"
CANCELLED, EXPIRED          → "Cancelado"
REFUNDED, CHARGEBACK        → "Reembolsado"
```

**Rationale**: A tag de curso permite segmentar "todo mundo que já comprou X" independente do status atual. A tag de status permite segmentar por situação: campanhas de cobrança (inadimplentes), win-back (cancelados), feedback (reembolsados). São audiências com mensagens diferentes.

### 3. Brute-force para atualização de status tag

**Decisão**: Ao atualizar status, remover todas as possíveis status-tags do curso e adicionar a atual.

```python
for status in ["Ativo", "Inadimplente", "Cancelado", "Reembolsado"]:
    manychat.remove_tag(subscriber_id, f"{course_name}, {status}")
manychat.add_tag(subscriber_id, f"{course_name}, {new_status}")
```

**Alternativas**:
- (a) Ler status anterior do banco antes de remover: economiza 3 chamadas à API, mas cria acoplamento frágil ao estado do banco.
- (b) **Brute-force**: idempotente, resiliente a desync. ManyChat ignora `remove_tag` em tags que o subscriber não tem.

**Rationale**: (b) é mais robusto. O custo de chamadas extras à API é irrelevante no contexto de um job diário.

### 4. Acesso derivado via ProductAccessRule

**Decisão**: Produto "A Base de Tudo" tem dois registros `ProductAccessRule` de tipo `MANYCHAT_TAG`:
- `rule_value = "A Base de Tudo"` (tag do produto comprado)
- `rule_value = "De analista a CDO"` (tag do conteúdo acessado)

O sync aplica as tags de todos os `ProductAccessRule` do produto — sem lógica especial no código.

**Rationale**: A regra é configuração no banco, não código. Adicionar um novo produto com acesso derivado é um INSERT, não um deploy.

### 5. Fonte de verdade para "ativo hoje"

**Decisão**: Para cada produto:
- **Produtos com assinatura**: considerar ACTIVE no endpoint `/subscriptions` como autoridade para status "Ativo"
- **Produtos one-time**: COMPLETE ou APPROVED no histórico de vendas sem REFUNDED/CHARGEBACK posterior
- **OVERDUE**: status explícito via `/sales/history?transaction_status=OVERDUE`

O job varre o histórico de 6 anos em janelas de 30 dias por produto para garantir cobertura completa.

### 6. Phone para lookup no ManyChat

**Decisão**: O sync usa `user.whatsapp_number` (já armazenado) para encontrar o subscriber no ManyChat. Ao importar via `sync_hotmart_students`, o campo `whatsapp_number` é populado a partir do campo `cellphone` ou `phone` do endpoint `GET /sales/users`.

Se o subscriber não for encontrado no ManyChat (`find_subscriber` retorna None), o sync loga e avança — o aluno pode não ter interagido com o bot ainda.

## Risks / Trade-offs

- **Alunos sem whatsapp_number**: ~4/270 (1.5%) não têm telefone na Hotmart. Tags não são aplicadas. Risco aceitável.
- **Alunos sem ManyChat**: alunos que nunca interagiram com o bot WhatsApp não existem no ManyChat. O sync não consegue tagear — logs indicam quem ficou de fora.
- **Hotmart API rate limits**: o sync varre até 6 anos em janelas de 30 dias. Para 5 produtos = ~360 requests. Dentro dos limites documentados.
- **Brute-force vs ManyChat**: 4 chamadas de remove por status update. A 270 alunos × 5 produtos = 5.400 chamadas no pior caso. Aceitável para um job diário.
- **Consistência entre webhook e batch**: um churn via webhook atualiza o lifecycle e tags em tempo real. O batch diário confirma/corrige qualquer divergência.

## Migration Plan

1. Criar migration Alembic para `student_course_status`
2. Popular tabela SCD a partir do estado atual dos Users no banco (seed inicial de `is_current = true`)
3. Configurar ProductAccessRule para cada produto com as tags corretas
4. Rodar `POST /admin/events/manychat-sync` manualmente uma vez para popular tags
5. Ativar beat schedule diário
