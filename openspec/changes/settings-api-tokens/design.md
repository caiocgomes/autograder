## Context

Tokens de LLM (OpenAI e Anthropic) são configurados hoje via `.env` e carregados pelo Pydantic Settings no singleton `settings` em `app/config.py`. A troca de um token exige editar o arquivo no servidor e reiniciar backend + worker Celery. Isso é um problema operacional: interrompe jobs, exige SSH, e gera downtime nas features de variação de mensagem (`message_rewriter.py` usa Haiku) e grading de exercícios (`tasks.py` usa OpenAI ou Anthropic).

O sistema já tem um padrão estabelecido de tabelas auxiliares admin-only (ex: `message_templates`) com routers dedicados e modais no frontend.

## Goals / Non-Goals

**Goals:**

- Admin consegue configurar tokens de OpenAI e Anthropic pela interface web, sem reiniciar nenhum serviço
- Tokens persistidos no banco de dados, encriptados (não em plaintext)
- Retrocompatibilidade total: se não houver token no banco, usa o do `.env` como fallback
- Endpoint de leitura retorna tokens mascarados para que o admin saiba se estão configurados sem expor o valor

**Non-Goals:**

- Não vamos encriptar outros secrets do `.env` (DB password, JWT secret, etc.) neste change
- Não vamos criar um sistema genérico de settings key-value. Escopo restrito aos dois tokens de LLM
- Não vamos adicionar rotação automática de tokens ou validação de token contra a API antes de salvar
- Não vamos mudar a lógica de qual provider usar (OpenAI vs Anthropic). O campo `llm_provider` continua no `.env`

## Decisions

### 1. Tabela dedicada em vez de key-value genérico

**Escolha:** Modelo `SystemSettings` com colunas tipadas (`openai_api_key_encrypted`, `anthropic_api_key_encrypted`) em vez de uma tabela key-value genérica.

**Alternativa considerada:** Tabela `system_settings(key, value, is_encrypted)`. Mais flexível para futuras configurações.

**Rationale:** Hoje o escopo é apenas dois tokens. Uma tabela key-value adiciona complexidade desnecessária (serialização de tipos, validação por key, etc.) para um problema que não existe ainda. Se precisar de mais settings no futuro, a migration é trivial. Preferimos o caminho mais simples: single-row table com colunas explícitas.

### 2. Encryption via Fernet (symmetric)

**Escolha:** `cryptography.fernet.Fernet` com chave derivada de `settings.jwt_secret_key` via PBKDF2.

**Alternativa considerada:** Usar um secret manager externo (AWS Secrets Manager, Vault). Ou armazenar em plaintext com acesso restrito.

**Rationale:** O projeto roda em infra simples (single server, docker compose). Secret manager é overengineering. Plaintext no banco é inaceitável para API keys. Fernet é a solução padrão do Python para symmetric encryption, já está no ecossistema (`cryptography` é dependência do `PyJWT`). A chave de encryption derivada do `jwt_secret_key` evita adicionar mais um secret no `.env`, já que o JWT secret já precisa ser protegido de qualquer forma.

### 3. Single-row pattern

**Escolha:** A tabela `system_settings` tem no máximo uma row. O router faz `upsert` (insert or update). Sem ID no endpoint, o GET e PUT operam na row única.

**Rationale:** Não faz sentido ter múltiplas configurações de sistema. O padrão single-row é comum para este tipo de tabela e simplifica a API (sem necessidade de IDs ou list endpoints).

### 4. Resolução de token com fallback

**Escolha:** Nova função `get_llm_api_key(provider: str, db: Session) -> str` em `app/services/settings.py` que:
1. Tenta buscar do banco (desencripta se existir)
2. Se não existir ou estiver vazio, usa `settings.openai_api_key` / `settings.anthropic_api_key`
3. Se ambos vazios, levanta exceção

**Alternativa considerada:** Sobrescrever o singleton `settings` em runtime.

**Rationale:** Mutar o singleton do Pydantic Settings é frágil e confuso (mix de fonte de dados). Uma função explícita deixa claro de onde o token vem e permite que o fallback para `.env` seja previsível.

### 5. UI como nova rota no sidebar (admin-only)

**Escolha:** Nova rota `/professor/settings` com página dedicada `SettingsPage`, adicionada ao sidebar do `ProfessorLayout` condicionalmente para `admin`.

**Alternativa considerada:** Modal de configurações acessível por botão de engrenagem.

**Rationale:** O padrão do projeto é sidebar com rotas. Manter consistência. Uma página dedicada também tem mais espaço para futuras settings.

### 6. Mascaramento no GET

**Escolha:** O endpoint `GET /admin/settings` retorna `{ openai_api_key: "sk-proj-...****", anthropic_api_key: "sk-ant-...****", openai_configured: true, anthropic_configured: true }`. Os primeiros 10 chars + `****`. Nunca o token completo.

**Rationale:** O admin precisa saber se o token está configurado e qual é (para debugging), mas nunca precisa ler o token de volta pela interface.

## Risks / Trade-offs

**[Token em memória no response da API]** → O token completo trafega no body do PUT request. Mitigation: HTTPS em produção (já é o caso). O GET nunca retorna o token completo.

**[Chave de encryption derivada do JWT secret]** → Se o JWT secret mudar, os tokens no banco ficam ilegíveis. Mitigation: Raro (JWT secret quase nunca muda). Se mudar, admin reconfigura os tokens pela interface. Documentar esse comportamento.

**[Single-row sem lock]** → Dois admins editando ao mesmo tempo poderiam gerar race condition. Mitigation: Há apenas um admin (o Caio). Não justifica lock mechanism.

**[DB query a cada chamada de LLM]** → Cada geração de variação ou grading faz um SELECT no banco. Mitigation: Query trivial (single-row, indexed). Latência desprezível comparada com a chamada de LLM que vem em seguida. Se necessário no futuro, pode-se adicionar cache em memória com TTL curto.
