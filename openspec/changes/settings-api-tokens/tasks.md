## 1. Model e Migration

- [x] 1.1 Criar model `SystemSettings` em `app/models/system_settings.py` com colunas: `id`, `openai_api_key_encrypted` (Text, nullable), `anthropic_api_key_encrypted` (Text, nullable), `updated_at` (DateTime com server_default), `updated_by` (FK users.id nullable)
- [x] 1.2 Registrar model no `app/models/__init__.py`
- [x] 1.3 Gerar migration Alembic com `alembic revision --autogenerate`

## 2. Encryption Service

- [x] 2.1 Criar `app/services/encryption.py` com funções `encrypt_value(plaintext: str) -> str` e `decrypt_value(ciphertext: str) -> str` usando Fernet com chave derivada de `settings.jwt_secret_key` via PBKDF2
- [x] 2.2 Criar `app/services/settings.py` com função `get_llm_api_key(provider: Literal["openai", "anthropic"], db: Session) -> str` que busca token do banco (decrypt) com fallback para `.env`

## 3. Backend API

- [x] 3.1 Criar schema `app/schemas/system_settings.py` com `SystemSettingsUpdate` (campos opcionais para cada token) e `SystemSettingsResponse` (tokens mascarados + flags `openai_configured`, `anthropic_configured`)
- [x] 3.2 Criar router `app/routers/admin_settings.py` com `GET /admin/settings` (retorna mascarado) e `PUT /admin/settings` (upsert com encryption)
- [x] 3.3 Registrar router no `main.py`
- [x] 3.4 Adicionar função de mascaramento: primeiros 10 chars + `****`, ou `****` se token < 10 chars

## 4. Integrar resolucao de token

- [x] 4.1 Alterar `app/services/message_rewriter.py` para usar `get_llm_api_key("anthropic", db)` em vez de `settings.anthropic_api_key` direto. Ajustar `_call_haiku` e `generate_variations` para receber db session
- [x] 4.2 Alterar `app/routers/messaging.py` endpoint `/variations` para passar db session ao `generate_variations`
- [x] 4.3 Alterar `app/tasks.py` nas funcoes de grading LLM para usar `get_llm_api_key()` com fallback

## 5. Frontend

- [x] 5.1 Criar API client `src/api/settings.ts` com `getSettings()` e `updateSettings()`
- [x] 5.2 Criar pagina `src/pages/professor/SettingsPage.tsx` com dois campos de input para tokens, botao salvar, feedback de sucesso/erro. Placeholder mostra valor mascarado atual
- [x] 5.3 Adicionar rota `/professor/settings` no `App.tsx` dentro do bloco professor (admin-only)
- [x] 5.4 Adicionar item "Configuracoes" no sidebar do `ProfessorLayout.tsx`, condicional a `user?.role === 'admin'`

## 6. Testes

- [x] 6.1 Testes unitarios para `encryption.py` (encrypt/decrypt round-trip, token vazio, chave invalida)
- [x] 6.2 Testes para `settings.py` service (fallback para env, prioridade do banco, token ausente)
- [x] 6.3 Testes para router `admin_settings.py` (GET mascarado, PUT upsert, acesso negado para non-admin, partial update, clear token)
