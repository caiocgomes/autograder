## Context

A tabela `hotmart_buyers` contém 276 compradores ativos (`status='Ativo'`) com `user_id=NULL` — pessoas que compraram antes do sistema de webhooks estar em produção ou cujos eventos foram perdidos. O sistema já tem toda a infraestrutura necessária: `lifecycle.transition("purchase_approved")` cria o User, gera token, envia WhatsApp. A única lacuna é um caller que processe esses compradores históricos em lote.

Compradores ativos já têm `name` e `phone` populados em `hotmart_buyers` (resultado da feature anterior de enriquecimento via `/sales/users`).

## Goals / Non-Goals

**Goals:**
- Criar `User` para cada comprador ativo em `hotmart_buyers` sem `user_id`
- Disparar o fluxo de onboarding existente (token + WhatsApp) para cada um
- Atualizar `hotmart_buyers.user_id` após criação
- Ser idempotente: re-execuções não criam duplicatas nem enviam WhatsApp duas vezes

**Non-Goals:**
- Modificar o fluxo de onboarding existente (`lifecycle.py`)
- Processar compradores com status diferente de `Ativo`
- Integrar ao `sync_hotmart_buyers` automático (fase futura)
- Envio por email (canal paralelo, fora do escopo)
- Normalização de telefone para E.164 (tratado pela camada Evolution API)

## Decisions

### Reutilizar `lifecycle.transition("purchase_approved")` sem modificação

A função já encadeia: geração de token → WhatsApp se `whatsapp_number` preenchido → log de evento. Criar um caminho alternativo seria duplicação desnecessária. O caller apenas garante que o User existe com os campos corretos antes de chamar.

**Alternativa considerada**: chamar `generate_onboarding_token()` + Evolution diretamente. Rejeitada porque bypassaria o log de eventos e o retry de side-effects.

### Deduplicação por email antes de criar User

Um comprador pode ter múltiplos rows em `hotmart_buyers` (um por produto). A query de elegíveis agrupa por email e seleciona todos os `hotmart_product_id` desse email. O User é criado uma vez; `hotmart_buyers.user_id` é atualizado em todos os rows do email.

**Alternativa considerada**: um loop simples sem dedup, com `get_or_create` no User. Funciona, mas envia WhatsApp múltiplas vezes para multi-produto. Rejeitada.

### `password_hash` como string aleatória inutilizável

Buyers históricos não têm senha. O campo é `NOT NULL` no modelo. Solução: `bcrypt(secrets.token_hex(32))` — hash de string aleatória que nunca será conhecida pelo usuário. Login via senha não é o fluxo esperado; o acesso real é via Discord.

**Alternativa**: tornar `password_hash` nullable. Rejeitada por exigir migração e alterar contrato do modelo.

### Idempotência via checagem de `user_id` no início

A query filtra `hotmart_buyers WHERE status='Ativo' AND user_id IS NULL`. Se a task rodar duas vezes, na segunda execução esses rows já terão `user_id` preenchido e serão ignorados. Não é necessário lock adicional.

## Risks / Trade-offs

- **WhatsApp em massa**: 272 mensagens enviadas na execução. Risco de rate limit da Evolution API. Mitigação: a task processa sequencialmente com commit por buyer — falha individual não aborta os demais.
- **Buyers sem phone**: 4 dos 276 não têm `phone` em `hotmart_buyers`. Para eles, `user.whatsapp_number` ficará `None` e o WhatsApp não será enviado (comportamento já existente no lifecycle). Receberão onboarding via email (canal separado).
- **Email duplicado em `users`**: se por algum motivo um User já existir com o mesmo email, o `INSERT` vai falhar na constraint UNIQUE. Mitigação: checar `User.email` antes de criar.

## Migration Plan

1. Aplicar esta task em produção com `EVOLUTION_ENABLED=true` e `DISCORD_ENABLED=false` (Discord roles só são atribuídas no `discord_registered`, não neste passo)
2. Executar manualmente: `celery call app.tasks.onboard_historical_buyers`
3. Verificar counters no log e na tabela `events`
4. Sem rollback necessário: Users criados sem `discord_id` não têm acesso ativo ao Discord ainda — o dano é nulo se a task precisar ser revertida (basta deletar os Users criados)
