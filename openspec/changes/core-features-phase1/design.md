## Context

Autograder é um monorepo com backend FastAPI (autograder-back) e frontend React+Vite (autograder-web). O sistema precisa executar código arbitrário submetido por alunos de forma segura, avaliar automaticamente via testes e LLM, e escalar para centenas de alunos submetendo próximo a deadlines.

Fase 1 foca em funcionalidades core: usuários, turmas, exercícios, submissão e avaliação automatizada. Integrações avançadas (LMS, GitHub Classroom, plágio) ficam para fases posteriores.

Constraints:
- Segurança é crítica: código do aluno não pode comprometer o sistema
- Escalabilidade: suportar picos de 200+ submissões em 30 minutos
- Custo de LLM: avaliar estratégias de cache e batch processing

## Goals / Non-Goals

**Goals:**
- Sistema de autenticação robusto com RBAC (Admin/Professor, Aluno, Monitor)
- Gestão completa de turmas e exercícios com listas atribuíveis
- Execução sandboxed de código Python em containers isolados
- Avaliação automática via unit tests + feedback qualitativo via LLM
- Feedback detalhado por submissão acessível ao aluno
- Interface web responsiva para professor e aluno

**Non-Goals:**
- Suporte a múltiplas linguagens (apenas Python na Fase 1)
- Detecção de plágio / similaridade entre submissões
- Integração com LMS externos (Moodle, Google Classroom)
- GitHub Classroom integration
- Analytics avançados de turma (ficam para Fase 2)
- SSO / OAuth (email/senha apenas na Fase 1)

## Decisions

### 1. Stack Tecnológico

**Backend:**
- FastAPI + SQLAlchemy (ORM) + Alembic (migrations)
- PostgreSQL como database principal
- Redis para cache e fila de tarefas
- Celery para async task processing
- Docker para sandboxed execution

**Rationale:** FastAPI oferece performance, type safety, e async nativo. PostgreSQL é robusto para dados relacionais (users, classes, submissions). Celery + Redis é padrão maduro para filas assíncronas com retry e monitoring.

**Alternatives considered:**
- RabbitMQ: mais complexo, Redis suficiente para Fase 1
- SQLite: não escala para concorrência de múltiplos workers

### 2. Autenticação e Autorização

**Decision:** JWT tokens com refresh/access pattern + bcrypt para senhas

**Rationale:** JWT permite stateless auth, facilita escalabilidade horizontal. Access token curto (15min) + refresh token longo (7 dias) balanceia segurança e UX. Bcrypt é padrão seguro para hashing de senhas.

**RBAC implementation:**
- Tabela `users` com campo `role` (enum: admin, professor, student, ta)
- Middleware FastAPI verifica role em rotas protegidas
- Professors podem criar turmas/exercícios, Students apenas submitam

**Alternatives considered:**
- Session-based auth: requer state server-side, dificulta horizontal scaling
- OAuth/SSO: adiciona complexidade, fica para Fase 2

### 3. Sandboxed Execution Architecture

**Decision:** Docker containers efêmeros com resource limits + network isolation

**Implementation:**
1. Celery worker recebe submission task
2. Worker cria container Docker com:
   - Base image Python slim
   - Network mode: none (sem acesso à rede)
   - CPU limit: 1 core
   - Memory limit: 512MB
   - Timeout: configurável por exercício (default 30s)
3. Worker monta código do aluno + datasets + test harness no container
4. Executa tests dentro do container
5. Captura stdout/stderr/exit code
6. Container é destruído após execução
7. Worker salva resultado no database

**Rationale:** Docker fornece isolamento de processo, filesystem, e rede. Resource limits previnem DoS. Containers efêmeros garantem estado limpo por execução.

**Security measures:**
- No network access (evita exfiltração de dados)
- Read-only filesystem exceto /tmp
- Drop all Linux capabilities
- User namespace remapping (non-root inside container)

**Alternatives considered:**
- VMs: overhead alto, latência de startup
- Process sandboxing (systemd-nspawn, firejail): menos isolamento que Docker
- Cloud functions (Lambda, Cloud Run): vendor lock-in, cold start latency

### 4. LLM Integration for Qualitative Grading

**Decision:** Async LLM calls via API (OpenAI/Anthropic) com cache de resultados

**Implementation:**
1. Após execução de tests, se exercício tem `llm_grading_enabled=True`:
2. Celery task envia código + prompt template para LLM API
3. Prompt inclui: código do aluno, enunciado do exercício, critérios de avaliação
4. LLM retorna feedback textual + score sugerido (0-100)
5. Professor pode revisar/ajustar feedback LLM antes de publicar nota final

**Cost optimization:**
- Cache LLM responses por hash de código (evita re-avaliação de código idêntico)
- Batch processing de múltiplas submissões quando possível
- Rate limiting por aluno (max 5 submissões/exercício para evitar abuse)

**Alternatives considered:**
- Self-hosted LLM: custo de infra > custo de API para Fase 1
- Synchronous LLM calls: latência alta bloquearia submission flow

### 5. Database Schema

**Core tables:**

```
users:
  id (PK), email (unique), password_hash, role (enum), created_at

classes:
  id (PK), name, professor_id (FK users), archived (bool), created_at

class_enrollments:
  id (PK), class_id (FK), student_id (FK users), enrolled_at

groups:
  id (PK), class_id (FK), name

group_memberships:
  id (PK), group_id (FK), student_id (FK users)

exercises:
  id (PK), title, description (text), template_code, language (enum),
  max_submissions (int), timeout_seconds, memory_limit_mb,
  has_tests (bool), llm_grading_enabled (bool), created_by (FK users)

exercise_lists:
  id (PK), title, class_id (FK), opens_at, closes_at

exercise_list_items:
  id (PK), list_id (FK), exercise_id (FK), position (int), weight (float)

submissions:
  id (PK), exercise_id (FK), student_id (FK users), code (text),
  status (enum: queued, running, completed, failed), submitted_at

test_results:
  id (PK), submission_id (FK), test_name, passed (bool), message (text)

llm_evaluations:
  id (PK), submission_id (FK), feedback (text), score (float),
  cached (bool), created_at

grades:
  id (PK), submission_id (FK unique), test_score (float), llm_score (float),
  final_score (float), published (bool)
```

**Indexes:**
- `class_enrollments(class_id, student_id)` - unique composite
- `submissions(exercise_id, student_id, submitted_at)` - latest submission queries
- `llm_evaluations(code_hash)` - cache lookups

### 6. API Design Patterns

**RESTful endpoints:**

```
/auth:
  POST /register, /login, /refresh, /password-reset

/users:
  GET /me, PATCH /me
  GET /users (admin only)

/classes:
  GET /classes (list user's classes)
  POST /classes (professor)
  GET /classes/{id}
  POST /classes/{id}/enroll (student with invite code)
  POST /classes/{id}/students (professor: bulk import CSV)

/exercises:
  GET /exercises
  POST /exercises (professor)
  GET /exercises/{id}
  PATCH /exercises/{id}

/exercise-lists:
  POST /exercise-lists
  GET /classes/{class_id}/lists

/submissions:
  POST /submissions (student)
  GET /submissions?exercise_id=X&student_id=Y
  GET /submissions/{id}/results

/grades:
  GET /grades?class_id=X (professor)
  GET /grades/me (student)
```

**Pagination:** Query params `?page=1&limit=20` com Link headers
**Filtering:** Query params `?status=completed&student_id=123`
**Response format:** `{"data": [...], "meta": {"total": X, "page": Y}}`

## Risks / Trade-offs

**[Risk] Docker execution latency on cold start**
→ Mitigation: Pre-pull Python base images nos workers. Considerar warm pool de containers se latência > 2s se tornar problema.

**[Risk] LLM API rate limits / downtime**
→ Mitigation: Retry logic com exponential backoff. Fallback: professor pode avaliar manualmente se LLM falhar.

**[Risk] Picos de submissão próximo a deadlines sobrecarregam fila**
→ Mitigation: Horizontal scaling de Celery workers. Configurar alertas em queue depth > 100. Considerar priority queue se necessário.

**[Risk] Código malicioso do aluno tenta fork bomb ou preencher disco**
→ Mitigation: Docker resource limits (CPU, memory, PIDs). Read-only filesystem. Timeout agressivo.

**[Trade-off] Cache de LLM pode mascarar mudanças em prompt template**
→ Aceitável: invalidar cache quando prompt muda (versionar prompts).

**[Trade-off] Apenas Python suportado na Fase 1**
→ Aceitável: 90% dos use cases são Python. Adicionar outras linguagens na Fase 2.

## Migration Plan

**N/A** - Fase 1 é implementação inicial, sem migração de dados.

**Deployment:**
1. Database setup via Alembic migrations
2. Docker compose para dev environment (app, db, redis, celery worker)
3. Backend + worker deployment em produção
4. Frontend build + deploy (Vercel / Netlify)

**Rollback strategy:**
- Backend: reverter para commit anterior via Docker tag
- Database: Alembic downgrade migration
- Frontend: rollback deploy no host

## Open Questions

1. **LLM provider:** OpenAI GPT-4 vs Anthropic Claude? Precisa avaliar custo/token e qualidade de feedback.
2. **File upload limits:** Qual tamanho máximo para código + datasets? Proposta: 10MB por exercício.
3. **Monitoring stack:** Prometheus + Grafana ou usar serviço managed (DataDog, New Relic)?
