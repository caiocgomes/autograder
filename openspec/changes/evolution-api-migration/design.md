## Context

O sistema usa ManyChat para duas coisas: tags de segmentação por produto e envio de mensagens WhatsApp via flows. Com a migração, tags saem completamente (estado vive no banco via `student_course_status`) e mensagens passam a ser enviadas diretamente via Evolution API. Chatwoot opera externamente como inbox de conversas, conectado ao mesmo número do Evolution API — sem integração no código do autograder.

A integração ManyChat está espalhada em: `app/integrations/manychat.py`, `app/services/lifecycle.py`, `app/services/notifications.py`, `app/models/user.py`, `app/models/product.py`, e `app/config.py`.

## Goals / Non-Goals

**Goals:**
- Substituir `manychat.py` por `evolution.py` com interface mínima (`send_message`)
- Remover todas as referências a tags ManyChat do lifecycle
- Remover `User.manychat_subscriber_id` do model e do banco
- Remover `AccessRuleType.MANYCHAT_TAG` — sem quebrar ProductAccessRules existentes (limpar antes)
- Manter feature flag (`EVOLUTION_ENABLED`) com mesmo padrão de fallback/log

**Non-Goals:**
- Integrar Chatwoot no código — configuração é operacional
- Substituir broadcasts (nova atribuição, lembrete de deadline) — fora de escopo desta change
- Alterar o job `sync_manychat_tags` além de remover a parte de aplicação de tags (SCD2 sync continua funcionando)

## Decisions

### 1. Interface do cliente Evolution API

**Decisão**: `evolution.py` expõe uma única função pública: `send_message(phone: str, text: str) -> bool`.

**Alternativas**:
- (a) Espelhar a estrutura do `manychat.py` com múltiplas funções — desnecessário; Evolution API tem uma primitiva central.
- (b) Classe com estado (instância configurada) — over-engineering para o padrão atual do projeto (funções stateless com settings via Pydantic).

**Rationale**: A simplificação é o ponto. Um send_message cobre todos os casos de uso do lifecycle.

### 2. Mensagens de lifecycle: texto hardcoded vs. templates configuráveis

**Decisão**: Textos das mensagens hardcoded no Python com f-strings, em constantes no próprio `lifecycle.py`.

**Alternativas**:
- (a) Templates configuráveis via env vars — flexível mas adiciona complexidade desnecessária.
- (b) Tabela de templates no banco — over-engineering para 4 mensagens.
- (c) **Hardcoded** — simples, versionado com o código, fácil de encontrar e editar.

**Rationale**: São 4 mensagens (onboarding, welcome, churn, welcome-back). Mudar texto é um deploy. Aceitável.

### 3. Remoção de `AccessRuleType.MANYCHAT_TAG`

**Decisão**: Remover o valor do enum e adicionar script/migration que deleta registros `ProductAccessRule` com `rule_type='manychat_tag'` antes de remover o enum.

**Alternativas**:
- (a) Manter o enum como `deprecated` — cria confusão, valor sem handler no lifecycle.
- (b) **Deletar com migration** — limpo, sem estado inconsistente.

**Rationale**: `MANYCHAT_TAG` rules no lifecycle já são no-op após remover o handler. Manter seria ruído.

### 4. Destino do `sync_manychat_tags` job

**Decisão**: Renomear para `sync_student_course_status` e remover a seção que chama `_apply_manychat_tags`. O loop de sync Hotmart → SCD2 permanece intacto.

**Alternativas**:
- (a) Deletar o job inteiro — perde o sync histórico do SCD2, que é valioso para segmentação.
- (b) **Manter só o SCD2 sync** — preserva o valor analítico sem a dependência externa.

**Rationale**: O `student_course_status` é a fonte de segmentação. Mantê-lo atualizado via batch diário da Hotmart é independente de qual ferramenta de mensagem usamos.

### 5. `manychat_subscriber_id` no User

**Decisão**: Remover via migration Alembic (`op.drop_column`). Campo não tem valor depois da migração.

**Alternativas**:
- (a) Manter como `nullable` para histórico — ocupa espaço, cria confusão.
- (b) **Dropar** — simples e limpo.

## Risks / Trade-offs

- **Evolution API indisponível**: Mensagens de lifecycle falham silenciosamente (side-effect returns False, retry, admin alert). Aluno não recebe WhatsApp mas estado no banco está correto. Risco aceitável — mesmo comportamento do ManyChat hoje.
- **Registros MANYCHAT_TAG existentes no banco**: Se houver `ProductAccessRule` com `rule_type='manychat_tag'` em produção antes da migration, o `op.alter_enum` vai falhar. Migration deve deletar essas rows antes de alterar o enum.
- **Mensagens hardcoded em português**: Sem flexibilidade para múltiplos idiomas. Não é um requisito hoje.

## Migration Plan

1. Deletar `ProductAccessRule` rows com `rule_type='manychat_tag'` (migration ou script manual antes do deploy)
2. Aplicar migration Alembic: remover `manychat_subscriber_id`, alterar enum `AccessRuleType`
3. Deploy do código: `evolution.py` novo, `manychat.py` removido, lifecycle refatorado
4. Configurar env vars: adicionar `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE`, `EVOLUTION_ENABLED=true`; remover vars ManyChat
5. Testar envio manual via admin endpoint antes de ativar `EVOLUTION_ENABLED`

**Rollback**: Reverter migration Alembic e redeploy da versão anterior. ManyChat vars ainda estarão no `.env` se não removidas.
