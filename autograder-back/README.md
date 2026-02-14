# Autograder Backend

Sistema de correção automática de código Python com execução em sandbox isolado e avaliação por LLM.

## Características

- **Autenticação JWT** com refresh tokens, reset de senha e controle de rate limiting
- **Gestão de turmas** com códigos de convite, importação CSV e grupos de estudantes
- **Exercícios flexíveis** com suporte a Markdown, datasets, templates e casos de teste
- **Execução sandboxed** em containers Docker isolados (sem rede, read-only, recursos limitados)
- **Avaliação híbrida** combinando testes automatizados e feedback de LLM (OpenAI ou Anthropic)
- **Sistema de notas** com publicação manual/automática, edição de feedback e tracking de melhor tentativa
- **RBAC** com roles (admin, professor, student, TA) e controle de permissões
- **Task queue** com Celery para processamento assíncrono de submissions

## Arquitetura

### Stack

- **FastAPI** - Framework web assíncrono
- **PostgreSQL** - Database relacional com Alembic para migrations
- **Redis** - Cache e broker para Celery
- **Celery** - Task queue para execução assíncrona
- **Docker** - Containers isolados para execução de código
- **OpenAI/Anthropic** - LLMs para avaliação de código

### Fluxo de Grading

1. Estudante submete código via `POST /submissions`
2. Backend valida sintaxe, limites e deadlines
3. Submission entra na fila Celery com status "queued"
4. Worker executa código em container Docker isolado
5. Testes são executados e resultados capturados
6. Se habilitado, LLM avalia código e gera feedback
7. Sistema calcula nota composta (testes + LLM) e cria Grade
8. Nota é publicada (auto ou manual) e estudante recebe feedback

### Segurança do Sandbox

Containers executam com:
- `network_mode: none` - sem acesso à rede
- `read_only: true` - filesystem read-only (exceto /tmp)
- `user: nobody` - execução como usuário não-privilegiado
- `mem_limit: 512MB` - limite de memória
- `cpus: 1` - limite de CPU
- `timeout: 30s` - timeout de execução
- Capabilities dropped e seccomp profile aplicado

## Setup

### Pré-requisitos

- Python 3.11+
- Docker (daemon rodando)
- PostgreSQL 14+
- Redis 6+
- [uv](https://github.com/astral-sh/uv) package manager

### Instalação

1. Clone o repositório e entre no diretório backend:

```bash
cd autograder-back
```

2. Instale as dependências:

```bash
uv sync --all-extras
```

3. Configure as variáveis de ambiente:

```bash
cp .env.example .env
# Edite .env com suas configurações (database, Redis, JWT secret, API keys)
```

4. Suba os serviços de infraestrutura (PostgreSQL, Redis):

```bash
# Usando Docker Compose (na raiz do monorepo)
docker compose up -d db redis
```

5. Execute as migrations do banco:

```bash
uv run alembic upgrade head
```

6. Build a imagem Docker do sandbox:

```bash
docker build -f Dockerfile.sandbox -t autograder-sandbox:latest .
```

### Desenvolvimento

#### Rodar a API

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em `http://localhost:8000`.

#### Rodar os workers Celery

```bash
uv run celery -A app.celery_app worker --loglevel=info
```

#### Rodar os testes

```bash
# Todos os testes
uv run pytest

# Teste específico
uv run pytest tests/test_auth.py -k "test_register"

# Com coverage
uv run pytest --cov=app --cov-report=html
```

#### Criar uma migration

```bash
# Auto-generate migration
uv run alembic revision --autogenerate -m "description"

# Apply migration
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1
```

## Documentação da API

A documentação OpenAPI/Swagger está disponível automaticamente:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Principais Endpoints

### Autenticação

- `POST /auth/register` - Criar nova conta
- `POST /auth/login` - Login e obter tokens JWT
- `POST /auth/refresh` - Renovar access token
- `POST /auth/password-reset` - Solicitar reset de senha
- `POST /auth/password-reset/confirm` - Confirmar reset de senha

### Usuários

- `GET /users/me` - Perfil do usuário atual
- `PATCH /users/me` - Atualizar perfil
- `GET /users` - Listar usuários (admin only)

### Classes

- `POST /classes` - Criar turma (professor)
- `GET /classes` - Listar turmas do usuário
- `GET /classes/{id}` - Detalhes da turma
- `POST /classes/{id}/enroll` - Inscrever-se com código de convite
- `POST /classes/{id}/students` - Importar estudantes via CSV
- `POST /classes/{id}/groups` - Criar grupos

### Exercícios

- `POST /exercises` - Criar exercício (professor)
- `GET /exercises` - Listar exercícios (com filtros)
- `GET /exercises/{id}` - Detalhes do exercício
- `PATCH /exercises/{id}` - Atualizar exercício
- `POST /exercises/{id}/tests` - Adicionar casos de teste
- `POST /exercises/{id}/datasets` - Upload de datasets

### Listas de Exercícios

- `POST /exercise-lists` - Criar lista
- `POST /exercise-lists/{id}/exercises` - Adicionar exercícios
- `GET /classes/{class_id}/lists` - Listar listas da turma

### Submissions

- `POST /submissions` - Submeter código
- `GET /submissions` - Listar submissions (com filtros)
- `GET /submissions/{id}` - Detalhes da submission
- `GET /submissions/{id}/results` - Resultados de testes e feedback

### Notas

- `GET /grades` - Listar notas (professor: turma, estudante: próprias)
- `GET /grades/me` - Notas do estudante atual
- `POST /grades/{id}/publish` - Publicar nota
- `PATCH /grades/{id}` - Editar feedback/nota LLM
- `GET /grades/export/csv` - Exportar notas em CSV

## Estrutura do Projeto

```
autograder-back/
├── alembic/              # Database migrations
├── app/
│   ├── auth/             # Autenticação e autorização
│   │   ├── dependencies.py  # JWT dependencies
│   │   ├── rate_limiter.py  # Rate limiting
│   │   └── security.py      # Password hashing, JWT
│   ├── models/           # SQLAlchemy models
│   │   ├── user.py
│   │   ├── class_.py
│   │   ├── exercise.py
│   │   ├── submission.py
│   │   └── grade.py
│   ├── routers/          # FastAPI routers
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── classes.py
│   │   ├── exercises.py
│   │   ├── exercise_lists.py
│   │   ├── submissions.py
│   │   └── grades.py
│   ├── schemas/          # Pydantic schemas
│   ├── celery_app.py     # Celery configuration
│   ├── config.py         # Settings management
│   ├── database.py       # Database connection
│   └── tasks.py          # Celery tasks
├── services/             # Business logic
│   ├── grader.py         # Grading orchestration
│   ├── llm_validator.py  # LLM integration
│   └── sandbox.py        # Docker sandbox execution
├── tests/                # Test suite
├── main.py               # FastAPI application
├── Dockerfile.dev        # Development Dockerfile
├── Dockerfile.sandbox    # Sandbox image Dockerfile
└── pyproject.toml        # Dependencies (uv)
```

## Variáveis de Ambiente

Veja [CONFIG.md](./CONFIG.md) para documentação detalhada de todas as variáveis de ambiente.

Principais variáveis obrigatórias:

- `DATABASE_URL` - Connection string do PostgreSQL
- `REDIS_URL` - Connection string do Redis
- `JWT_SECRET_KEY` - Secret para assinatura de tokens JWT
- `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY` - API key do LLM provider

## Deploy em Produção

### Checklist

1. **Segurança**
   - [ ] Gerar `JWT_SECRET_KEY` forte e único
   - [ ] Configurar `CORS` com origins específicos (remover `allow_origins=["*"]`)
   - [ ] Configurar HTTPS/SSL
   - [ ] Usar senhas fortes para database e Redis
   - [ ] Habilitar autenticação no Redis

2. **Database**
   - [ ] Configurar backups automáticos
   - [ ] Setup replicação (se necessário)
   - [ ] Tuning de performance

3. **Sandbox**
   - [ ] Revisar limites de recursos (CPU, memória, timeout)
   - [ ] Considerar usar Docker Swarm ou Kubernetes para orchestration
   - [ ] Monitorar uso de recursos

4. **Monitoring**
   - [ ] Setup logs estruturados com request IDs
   - [ ] Configurar Prometheus/Grafana ou serviço managed
   - [ ] Alerting para queue depth, execution failures, LLM API errors

5. **Escalabilidade**
   - [ ] Adicionar mais workers Celery conforme carga
   - [ ] Configurar auto-scaling
   - [ ] Considerar cache de LLM responses (já implementado)

## Troubleshooting

### Docker não consegue criar containers

```bash
# Verificar se Docker daemon está rodando
docker ps

# Build a imagem sandbox novamente
docker build -f Dockerfile.sandbox -t autograder-sandbox:latest .
```

### Celery workers não processam tasks

```bash
# Verificar se Redis está acessível
redis-cli ping

# Verificar logs do worker
uv run celery -A app.celery_app worker --loglevel=debug
```

### Migrations falhando

```bash
# Verificar status das migrations
uv run alembic current

# Reset database (CUIDADO: deleta dados)
uv run alembic downgrade base
uv run alembic upgrade head
```

## Contribuindo

1. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
2. Faça commit das mudanças (`git commit -m 'Add nova feature'`)
3. Execute os testes (`uv run pytest`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

MIT License - veja LICENSE para detalhes.
