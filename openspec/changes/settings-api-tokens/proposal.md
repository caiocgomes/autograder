## Why

Os tokens da OpenAI e Anthropic estão hardcoded no `.env`. Toda vez que um token precisa ser rotacionado, o stack inteiro precisa ser reiniciado (backend + worker Celery), o que interrompe jobs em andamento e exige acesso SSH ao servidor. A feature de variações de mensagem (que usa Haiku) e o grading de exercícios (que usa OpenAI ou Anthropic) ficam indisponíveis durante esse processo. Um admin deveria conseguir trocar tokens pela interface sem downtime.

## What Changes

- Nova tabela `system_settings` no banco para armazenar configurações globais do sistema como key-value, com suporte a valores encriptados para secrets
- Novo endpoint CRUD de configurações do sistema (admin-only)
- Nova tela "Configurações" no frontend com campos para os tokens de OpenAI e Anthropic
- `message_rewriter.py` e `app/tasks.py` passam a buscar tokens primeiro do banco; se não existirem, fallback para `.env` (retrocompatível)
- Tokens armazenados encriptados no banco (não em plaintext)

## Capabilities

### New Capabilities

- `system-settings`: Armazenamento de configurações globais do sistema em banco de dados, com suporte a valores sensíveis (encrypted). CRUD via API admin-only. UI de configurações no frontend.

### Modified Capabilities

_(nenhuma capability existente tem seus requisitos alterados; o fallback para `.env` mantém o comportamento atual)_

## Impact

- **Banco**: Nova tabela `system_settings` + migration Alembic
- **Backend**: Novo model, router, schema. Alteração no `message_rewriter.py` (resolve token) e `app/tasks.py` (resolve token para grading). `app/config.py` continua existindo como fallback.
- **Frontend**: Nova página/modal de configurações acessível pelo layout do professor/admin. Novo item no sidebar ou botão de settings.
- **Segurança**: Tokens encriptados no banco via Fernet (symmetric key no `.env`, mas essa raramente muda). Endpoint de leitura retorna tokens mascarados (`sk-...****`), nunca o valor completo.
- **Deploy**: Zero downtime para rotação de tokens. Não precisa reiniciar nada.
