## Why

O custo e a complexidade do ManyChat não fazem mais sentido para o volume atual. A comunicação com alunos via WhatsApp passa a ser feita diretamente via Evolution API (envio transacional) com Chatwoot como inbox para respostas — mesmo número, sem fragmentação.

## What Changes

- **BREAKING**: Remover integração ManyChat completamente (`app/integrations/manychat.py`, settings, flow IDs)
- Criar cliente Evolution API (`app/integrations/evolution.py`) para envio de mensagens WhatsApp
- Refatorar side-effects do lifecycle: tags ManyChat caem, `trigger_flow` vira `send_message` via Evolution API
- Remover `User.manychat_subscriber_id` (Evolution API endereça por número de telefone diretamente)
- **BREAKING**: Remover `AccessRuleType.MANYCHAT_TAG` do `ProductAccessRule` — regras de tag não existem mais
- Limpar `app/config.py`: remover settings ManyChat, adicionar settings Evolution API
- Migration Alembic para remover coluna `manychat_subscriber_id`
- Refatorar `sync_manychat_tags` para apenas sincronizar `student_course_status` sem tocar em API externa

## Capabilities

### New Capabilities
- `evolution-api`: Cliente HTTP para Evolution API — `send_message(phone, text)` como primitiva central de envio WhatsApp

### Modified Capabilities
- `manychat-integration`: **Substituída** por `evolution-api`. Spec existente descreve contrato que deixa de existir; nova spec descreve o contrato de envio via Evolution API.
- `student-lifecycle`: Side-effects de notificação mudam de `manychat.trigger_flow` para `evolution.send_message`. Sem mudança nas transições de estado ou regras de negócio.

## Impact

- **Backend**: `app/integrations/manychat.py` deletado; `app/integrations/evolution.py` criado; `app/services/lifecycle.py` refatorado; `app/services/notifications.py` atualizado
- **Models**: `User.manychat_subscriber_id` removido; `AccessRuleType.MANYCHAT_TAG` removido
- **Config**: settings ManyChat removidos, `EVOLUTION_API_URL` e `EVOLUTION_API_KEY` e `EVOLUTION_INSTANCE` adicionados
- **Database**: migration Alembic para remover `manychat_subscriber_id` da tabela `users`
- **Operacional**: Chatwoot configurado externamente com Evolution API como canal — sem mudança de código no autograder para isso
