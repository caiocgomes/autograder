# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Autograder is a monorepo for automated code grading with sandboxed execution and LLM feedback. Two components:

- **autograder-back/**: Python FastAPI backend (API, Celery workers, Docker sandbox, LLM integration)
- **autograder-web/**: React + TypeScript + Vite frontend

## Commands

### Backend (run from `autograder-back/` — all `uv run` commands require this cwd)

```bash
uv sync --all-extras                                          # Install deps
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000   # Start API server
uv run pytest                                                 # Run all tests
uv run pytest tests/test_auth_router.py                       # Run test file
uv run pytest tests/test_grader.py -k "test_name"             # Run single test
uv run alembic upgrade head                                   # Apply migrations
uv run alembic revision --autogenerate -m "description"       # Create migration
```

### Frontend (run from `autograder-web/`)

```bash
npm install        # Install deps
npm run dev        # Vite dev server (port 5173)
npm run build      # TypeScript check + Vite production build
npm run lint       # ESLint
```

### Infrastructure (run from repo root)

```bash
docker compose up -d                                          # Start Postgres + Redis + backend + worker
docker compose --profile discord up -d                        # Also start Discord bot
docker compose logs -f backend                                # Follow backend logs
docker compose logs -f worker                                 # Follow worker logs
docker build -f Dockerfile.sandbox -t autograder-sandbox .    # Build sandbox image (required for code execution)
```

### Discord bot (run from `autograder-back/`)

```bash
uv run python -m app.discord_bot                              # Start Discord bot locally
```

Production: `docker compose -f docker-compose.prod.yml up -d` (adds nginx, db-backup, SSL)

### API Docs

Swagger UI at http://localhost:8000/docs when backend is running.

## Architecture

### Grading Pipeline (async via Celery)

Student submits code via `POST /submissions` → submission stored with status "queued" → Celery task picks it up:

1. **Test execution**: `app/tasks.py` generates a test harness script, runs it in a Docker container (`Dockerfile.sandbox`) with hard isolation (no network, read-only fs, non-root user, 30s timeout, 512MB memory limit). Docker SDK is used directly, not CLI.
2. **LLM evaluation** (optional, per-exercise toggle): Calls OpenAI or Anthropic API with exercise description + student code + grading criteria. Response cached by code hash.
3. **Scoring**: Composite score = `test_weight * test_score + llm_weight * llm_score`, with optional late penalty applied per day past deadline.

The sandbox Docker client has a macOS fallback socket path (`~/.docker/run/docker.sock`), relevant for local development.

### Backend Layers

- **Routers** (`app/routers/`): FastAPI endpoints. Auth, users, classes, exercises, exercise_lists, submissions, grades, webhooks, products, admin_events.
- **Models** (`app/models/`): SQLAlchemy ORM. Key entities: User (roles: admin/professor/student/ta; lifecycle_status: pending_payment/pending_onboarding/active/churned), Class, ClassEnrollment (enrollment_source: manual/product), Group, Exercise, ExerciseList, Submission, TestResult, Grade, LLMEvaluation, Product, ProductAccessRule (types: discord_role, class_enrollment), Event, StudentCourseStatus.
- **Schemas** (`app/schemas/`): Pydantic request/response models.
- **Auth** (`app/auth/`): JWT tokens (access 15min, refresh 7 days), bcrypt password hashing, RBAC via `require_role()` dependency, Redis-backed rate limiting on login.
- **Services** (`app/services/`): Extracted business logic. `lifecycle.py`: state machine (pending_payment→pending_onboarding→active→churned) with side-effects (Discord roles, class enrollment, WhatsApp via Evolution API). `enrollment.py`: auto-enroll/unenroll by product, preserving manual enrollments. `notifications.py`: Discord DM + WhatsApp (Evolution API).
- **Integrations** (`app/integrations/`): `hotmart.py` (HMAC validation, payload parsing, buyer status sync), `discord.py` (role management via REST), `evolution.py` (WhatsApp messages via Evolution API — `send_message(phone, text)`).
- **Tasks** (`app/tasks.py`): Celery async tasks for execution, grading, LLM evaluation, `process_hotmart_event`, `execute_side_effect`, `sync_student_course_status` (daily batch that syncs Hotmart buyer statuses to `student_course_status` SCD Type 2 table).
- **Discord bot** (`app/discord_bot.py`): Separate worker. `/registrar` slash command, `on_member_join` handler. Run as standalone process.
- **Config** (`app/config.py`): Pydantic Settings loading from `.env`. All config via environment variables. Feature flags: `HOTMART_WEBHOOK_ENABLED`, `DISCORD_ENABLED`, `EVOLUTION_ENABLED`.

### WhatsApp Messaging

Evolution API sends WhatsApp messages directly by phone number (E.164 format) — no subscriber resolution step. Chatwoot connects to the same Evolution API instance externally to provide an inbox for incoming replies. No Chatwoot code in the autograder backend.

### Student Lifecycle

`lifecycle.py` implements a state machine with side-effects per transition:

| Trigger | Transition | Side-effects |
|---------|-----------|--------------|
| purchase_approved | → pending_onboarding | generate token, WhatsApp onboarding message |
| discord_registered | → active | assign Discord roles, enroll in classes, WhatsApp welcome |
| subscription_cancelled / purchase_refunded | → churned | revoke Discord roles, unenroll, WhatsApp churn notification |
| purchase_approved (from churned) | → active | assign roles, enroll, WhatsApp welcome-back |

Side-effect failures retry once; persistent failures log to `Event` table and alert admin via Discord DM.

### Student Course Status (SCD Type 2)

`student_course_status` table tracks `(user, product)` status history with `valid_from`, `valid_to`, `is_current` columns. Updated by the `sync_student_course_status` Celery task (daily at 02:00 UTC) reading from Hotmart API. Powers segmentation queries without relying on external tag state.

### Frontend Layers

- **API client** (`src/api/client.ts`): Axios instance with JWT Bearer token injection and automatic refresh. Failed requests during token refresh are queued and replayed (prevents race conditions). Base URL from `VITE_API_URL` env var (defaults to `http://localhost:8000`).
- **Auth state** (`src/store/authStore.ts`): Zustand store managing user session, tokens in localStorage.
- **Routing** (`src/App.tsx`): React Router v6 with `ProtectedRoute` component that checks auth + role. Professor routes under `/professor/*`, student routes under `/student/*`.
- **Layouts**: `ProfessorLayout` and `StudentLayout` provide sidebar navigation via `<Outlet />`.
- **Styling**: Inline styles throughout (no CSS framework). No component library.

### Database

PostgreSQL 16 via SQLAlchemy. Alembic migrations in `autograder-back/alembic/`. Connection pooling configured (pool_size=10, max_overflow=20, pre_ping=true).

`database.py` provides `get_db()` dependency for session injection into routers.

**Alembic gotcha**: SQLAlchemy uses enum member *names* (uppercase: `DISCORD_ROLE`) for PostgreSQL enum types, not values (`discord_role`). When writing raw SQL in migrations that filters on enum columns, use the uppercase name.

### Key Design Decisions

- **Exercise randomization**: Deterministic per-student shuffle using `Random(student_id * 31 + list_id)` seed — consistent across page loads, different per student.
- **Test cases have a `hidden` flag**: Hidden tests run but details aren't shown to students.
- **ExerciseList scoping**: Lists can target specific groups within a class, not just the whole class.
- **Late penalties**: Configured per ExerciseList as percent-per-day after `closes_at`.
- **Two service layers coexist**: `services/` at repo root (original single-endpoint grader) and `app/services/` (extracted grading logic for the full platform). The Celery tasks in `app/tasks.py` implement their own execution flow.

## Testing

Backend tests use FastAPI's `TestClient` with dependency overrides. `conftest.py` provides fixtures that swap `get_db` and `get_current_user` with mocks, so tests run without a real database. 23 test files covering routers, services, and integrations.

### Mock DB chain pattern

The `mock_db` fixture chains all calls back to itself (`query.return_value = db`, `filter.return_value = db`), so `.query(...).filter(...).first()` flows through the same object. Two critical gotchas:

1. **Multiple `.first()` calls in one endpoint**: `mock_db.query.return_value.filter.return_value.first.return_value = x` makes every `.first()` return `x`. If an endpoint calls `.first()` twice, use `side_effect=[x, None]` instead.

2. **SQLAlchemy server-side defaults**: Fields with `server_default` (e.g., `created_at`) stay `None` in-memory after mock INSERT. Set them explicitly in the `db.refresh` mock via `side_effect=lambda obj: setattr(obj, 'created_at', datetime(...))`.

No frontend tests exist yet.

## Environment Setup

1. Copy `autograder-back/.env.example` to `autograder-back/.env` and fill in secrets
2. `docker compose up -d` to start Postgres and Redis
3. `cd autograder-back && uv sync --all-extras && uv run alembic upgrade head`
4. Build sandbox: `docker build -f Dockerfile.sandbox -t autograder-sandbox .` (from repo root)
5. Backend: `cd autograder-back && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000`
6. Frontend: `cd autograder-web && npm install && npm run dev`
