# Configuration Documentation

Documentação detalhada de todas as variáveis de ambiente e opções de configuração do Autograder Backend.

## Visão Geral

O sistema usa **Pydantic Settings** para gerenciar configurações. As variáveis podem ser definidas via:

1. Arquivo `.env` no diretório `autograder-back/`
2. Variáveis de ambiente do sistema
3. Valores default (para desenvolvimento apenas)

**IMPORTANTE**: Nunca faça commit do arquivo `.env`. Use `.env.example` como template.

## Variáveis de Ambiente

### Database

#### `DATABASE_URL`

- **Tipo**: String (PostgreSQL connection URL)
- **Obrigatório**: Sim
- **Default**: `postgresql://autograder:autograder@localhost:5432/autograder`
- **Formato**: `postgresql://[user]:[password]@[host]:[port]/[database]`
- **Exemplo**:
  ```
  DATABASE_URL=postgresql://prod_user:secure_pass@db.example.com:5432/autograder_prod
  ```
- **Notas**:
  - Use connection pooling em produção
  - Recomendado usar PostgreSQL 14+
  - Para SSL: adicione `?sslmode=require` ao final da URL

### Redis

#### `REDIS_URL`

- **Tipo**: String (Redis connection URL)
- **Obrigatório**: Sim (usado por Celery)
- **Default**: `redis://localhost:6379/0`
- **Formato**: `redis://[password]@[host]:[port]/[db]`
- **Exemplo**:
  ```
  REDIS_URL=redis://:mypassword@redis.example.com:6379/0
  ```

#### `REDIS_HOST`

- **Tipo**: String
- **Default**: `localhost`
- **Uso**: Fallback se REDIS_URL não estiver disponível

#### `REDIS_PORT`

- **Tipo**: Integer
- **Default**: `6379`

#### `REDIS_DB`

- **Tipo**: Integer
- **Default**: `0`
- **Range**: 0-15 (databases Redis)

#### `REDIS_PASSWORD`

- **Tipo**: String (opcional)
- **Default**: `None`
- **Nota**: Em produção, SEMPRE use senha no Redis

### Celery

#### `CELERY_BROKER_URL`

- **Tipo**: String
- **Default**: Mesmo valor de `REDIS_URL`
- **Nota**: Celery usa Redis como message broker

#### `CELERY_RESULT_BACKEND`

- **Tipo**: String
- **Default**: Mesmo valor de `REDIS_URL`
- **Nota**: Armazena resultados de tasks no Redis

### JWT (JSON Web Tokens)

#### `JWT_SECRET_KEY`

- **Tipo**: String
- **Obrigatório**: **SIM (CRÍTICO EM PRODUÇÃO)**
- **Default**: `dev-secret-key-change-in-production`
- **Geração segura**:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- **Nota**: **NUNCA** use o default em produção. Trocar essa chave invalida todos os tokens JWT existentes.

#### `JWT_ALGORITHM`

- **Tipo**: String
- **Default**: `HS256`
- **Opções**: `HS256`, `HS384`, `HS512`
- **Nota**: HS256 é adequado para maioria dos casos

#### `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`

- **Tipo**: Integer
- **Default**: `15`
- **Range recomendado**: 5-30 minutos
- **Nota**: Tokens de curta duração aumentam segurança

#### `JWT_REFRESH_TOKEN_EXPIRE_DAYS`

- **Tipo**: Integer
- **Default**: `7`
- **Range recomendado**: 7-30 dias
- **Nota**: Usuários precisam fazer login novamente após expiração

### Security

#### `BCRYPT_COST_FACTOR`

- **Tipo**: Integer
- **Default**: `12`
- **Range**: 10-14
- **Nota**:
  - Valores maiores = mais seguro, mas mais lento
  - 12 é balanceado para maioria dos casos
  - Cada incremento dobra o tempo de hashing

#### `RATE_LIMIT_FAILED_LOGINS`

- **Tipo**: Integer
- **Default**: `5`
- **Descrição**: Número de tentativas de login falhadas permitidas

#### `RATE_LIMIT_WINDOW_MINUTES`

- **Tipo**: Integer
- **Default**: `15`
- **Descrição**: Janela de tempo para rate limiting (minutos)
- **Comportamento**: Após `RATE_LIMIT_FAILED_LOGINS` falhas, bloqueia por `RATE_LIMIT_WINDOW_MINUTES`

### Email (SMTP)

Usado para reset de senha e notificações.

#### `SMTP_HOST`

- **Tipo**: String
- **Default**: `smtp.gmail.com`
- **Exemplos**:
  - Gmail: `smtp.gmail.com`
  - SendGrid: `smtp.sendgrid.net`
  - AWS SES: `email-smtp.us-east-1.amazonaws.com`

#### `SMTP_PORT`

- **Tipo**: Integer
- **Default**: `587`
- **Opções**:
  - `587` - STARTTLS (recomendado)
  - `465` - SSL/TLS
  - `25` - Não criptografado (não recomendado)

#### `SMTP_USER`

- **Tipo**: String
- **Exemplo**: `your-email@gmail.com`
- **Nota**: Para Gmail, use App Password, não senha da conta

#### `SMTP_PASSWORD`

- **Tipo**: String
- **Nota**: Para Gmail, crie um [App Password](https://support.google.com/accounts/answer/185833)

#### `SMTP_FROM`

- **Tipo**: String
- **Default**: `noreply@autograder.com`
- **Descrição**: Endereço que aparece como remetente

### LLM API

#### `OPENAI_API_KEY`

- **Tipo**: String
- **Obrigatório**: Sim (se `LLM_PROVIDER=openai`)
- **Obtenção**: [OpenAI Platform](https://platform.openai.com/api-keys)
- **Formato**: `sk-...`

#### `ANTHROPIC_API_KEY`

- **Tipo**: String
- **Obrigatório**: Sim (se `LLM_PROVIDER=anthropic`)
- **Obtenção**: [Anthropic Console](https://console.anthropic.com/)
- **Formato**: `sk-ant-...`

#### `LLM_PROVIDER`

- **Tipo**: Literal["openai", "anthropic"]
- **Default**: `openai`
- **Opções**:
  - `openai` - Usa GPT-4/GPT-3.5 da OpenAI
  - `anthropic` - Usa Claude da Anthropic
- **Nota**: O provider escolhido afeta custos e qualidade do feedback

### Sandbox Execution

#### `DOCKER_IMAGE_SANDBOX`

- **Tipo**: String
- **Default**: `autograder-sandbox:latest`
- **Descrição**: Nome da imagem Docker usada para execução de código
- **Build**:
  ```bash
  docker build -f Dockerfile.sandbox -t autograder-sandbox:latest .
  ```

#### `SANDBOX_TIMEOUT_SECONDS`

- **Tipo**: Integer
- **Default**: `30`
- **Range recomendado**: 10-60 segundos
- **Nota**:
  - Timeout muito baixo pode interromper código legítimo
  - Timeout muito alto permite ataques de DoS

#### `SANDBOX_MEMORY_LIMIT_MB`

- **Tipo**: Integer
- **Default**: `512`
- **Range recomendado**: 256-1024 MB
- **Nota**: Ajuste baseado nos exercícios (ex: ML pode precisar mais)

#### `SANDBOX_CPU_LIMIT`

- **Tipo**: Integer
- **Default**: `1`
- **Descrição**: Número de CPUs disponíveis para o container
- **Nota**: Valores fracionários permitidos (ex: `0.5`)

### File Uploads

#### `MAX_EXERCISE_FILE_SIZE_MB`

- **Tipo**: Integer
- **Default**: `10`
- **Descrição**: Tamanho máximo de datasets para exercícios (MB)
- **Nota**: Datasets grandes podem incluir CSVs de treino

#### `MAX_SUBMISSION_FILE_SIZE_MB`

- **Tipo**: Integer
- **Default**: `1`
- **Descrição**: Tamanho máximo de arquivo de submission (MB)
- **Nota**: Código Python raramente excede 1MB

### Environment

#### `ENVIRONMENT`

- **Tipo**: Literal["development", "staging", "production"]
- **Default**: `development`
- **Comportamento**:
  - `development`: Logs verbose, debug mode
  - `staging`: Simula produção para testes
  - `production`: Otimizações, logs estruturados

#### `DEBUG`

- **Tipo**: Boolean
- **Default**: `true`
- **Comportamento**:
  - `true`: Auto-reload, stack traces detalhados, logs verbose
  - `false`: Sem auto-reload, logs otimizados
- **Nota**: **SEMPRE** use `DEBUG=false` em produção

#### `BASE_DIR`

- **Tipo**: Path
- **Default**: Diretório raiz do projeto (auto-detectado)
- **Descrição**: Usado para paths relativos (datasets, uploads)
- **Nota**: Geralmente não precisa ser alterado

## Configurações por Ambiente

### Development

```env
# .env para desenvolvimento local
DATABASE_URL=postgresql://autograder:autograder@localhost:5432/autograder
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=dev-secret-key-change-in-production
DEBUG=true
ENVIRONMENT=development

# LLM API (escolha um)
OPENAI_API_KEY=sk-...
# ou
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=openai

# Email (opcional para dev)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=dev@example.com
SMTP_PASSWORD=app-password
```

### Staging

```env
# .env para staging
DATABASE_URL=postgresql://user:pass@staging-db.internal:5432/autograder_staging
REDIS_URL=redis://:password@staging-redis.internal:6379/0
JWT_SECRET_KEY=<gerado-com-secrets.token_urlsafe>
DEBUG=false
ENVIRONMENT=staging

# Usar mesmos providers de produção
OPENAI_API_KEY=sk-staging-...
LLM_PROVIDER=openai

# SMTP real
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_FROM=noreply-staging@autograder.com
```

### Production

```env
# .env para produção
DATABASE_URL=postgresql://prod_user:secure_pass@prod-db.internal:5432/autograder?sslmode=require
REDIS_URL=redis://:redis_password@prod-redis.internal:6379/0
JWT_SECRET_KEY=<gerado-com-secrets.token_urlsafe-64-chars>
DEBUG=false
ENVIRONMENT=production

# LLM API
OPENAI_API_KEY=sk-prod-...
LLM_PROVIDER=openai

# SMTP
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_FROM=noreply@autograder.com

# Sandbox - limites ajustados
SANDBOX_TIMEOUT_SECONDS=45
SANDBOX_MEMORY_LIMIT_MB=768
SANDBOX_CPU_LIMIT=1

# Security
BCRYPT_COST_FACTOR=12
RATE_LIMIT_FAILED_LOGINS=3
RATE_LIMIT_WINDOW_MINUTES=30
```

## Validação de Configuração

### Verificar configuração atual

```python
# Python REPL
from app.config import settings
print(settings.model_dump())
```

### Verificar variáveis obrigatórias

Antes de deploy, verifique:

```bash
# Database conectável
psql $DATABASE_URL -c "SELECT 1"

# Redis acessível
redis-cli -u $REDIS_URL ping

# Docker disponível
docker ps

# LLM API válida (OpenAI)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# LLM API válida (Anthropic)
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-sonnet-20240229","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'
```

## Secrets Management

### Desenvolvimento

Para desenvolvimento local, `.env` é aceitável. **Nunca** faça commit deste arquivo.

### Produção

Use um secrets manager:

#### Docker Secrets

```yaml
# docker-compose.yml
services:
  api:
    secrets:
      - jwt_secret
      - openai_key
    environment:
      JWT_SECRET_KEY_FILE: /run/secrets/jwt_secret
      OPENAI_API_KEY_FILE: /run/secrets/openai_key

secrets:
  jwt_secret:
    external: true
  openai_key:
    external: true
```

#### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: autograder-secrets
type: Opaque
data:
  jwt-secret: <base64-encoded>
  openai-key: <base64-encoded>
```

#### AWS Secrets Manager / HashiCorp Vault

Integre via SDK e carregue secrets na inicialização da aplicação.

## Troubleshooting

### `pydantic_core._pydantic_core.ValidationError`

**Causa**: Variável de ambiente com tipo incorreto.

**Solução**: Verifique tipos (ex: `DEBUG=true` não `DEBUG=True`, `REDIS_PORT=6379` não `REDIS_PORT="6379"`)

### `JWT_SECRET_KEY` muito curto

**Causa**: Secret key insegura.

**Solução**: Gere uma chave de pelo menos 32 caracteres:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Celery não conecta ao Redis

**Causa**: `CELERY_BROKER_URL` incorreto ou Redis inacessível.

**Solução**:

```bash
# Testar conexão Redis
redis-cli -u $CELERY_BROKER_URL ping
```

### LLM API retorna 401

**Causa**: API key inválida ou expirada.

**Solução**: Regenere a chave no dashboard do provider (OpenAI/Anthropic).

## Referências

- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [FastAPI Configuration](https://fastapi.tiangolo.com/advanced/settings/)
- [12-Factor App: Config](https://12factor.net/config)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
