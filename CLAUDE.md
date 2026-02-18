# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Autograder is a monorepo for automated code grading with sandboxed execution and LLM feedback. Two components:

- **autograder-back/**: Python FastAPI backend (API, Celery workers, Docker sandbox, LLM integration)
- **autograder-web/**: React + TypeScript + Vite frontend

## Commands

### Backend (run from `autograder-back/`)

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
docker compose logs -f backend                                # Follow backend logs
docker compose logs -f worker                                 # Follow worker logs
docker build -f Dockerfile.sandbox -t autograder-sandbox .    # Build sandbox image (required for code execution)
```

Production: `docker compose -f docker-compose.prod.yml up -d` (adds nginx, db-backup, SSL)

### API Docs

Swagger UI at http://localhost:8000/docs when backend is running.

## Architecture

### Grading Pipeline (async via Celery)

Student submits code via `POST /submissions` -> submission stored with status "queued" -> Celery task picks it up:

1. **Test execution**: `app/tasks.py` generates a test harness script, runs it in a Docker container (`Dockerfile.sandbox`) with hard isolation (no network, read-only fs, non-root user, 30s timeout, 512MB memory limit). Docker SDK is used directly, not CLI.
2. **LLM evaluation** (optional, per-exercise toggle): Calls OpenAI or Anthropic API with exercise description + student code + grading criteria. Response cached by code hash.
3. **Scoring**: Composite score = `test_weight * test_score + llm_weight * llm_score`, with optional late penalty applied per day past deadline.

The sandbox Docker client has a macOS fallback socket path (`~/.docker/run/docker.sock`), relevant for local development.

### Backend Layers

- **Routers** (`app/routers/`): FastAPI endpoints. Auth, users, classes, exercises, exercise_lists, submissions, grades.
- **Models** (`app/models/`): SQLAlchemy ORM. Key entities: User (roles: admin/professor/student/ta), Class, ClassEnrollment, Group, Exercise, ExerciseList, Submission, TestResult, Grade, LLMEvaluation.
- **Schemas** (`app/schemas/`): Pydantic request/response models.
- **Auth** (`app/auth/`): JWT tokens (access 15min, refresh 7 days), bcrypt password hashing, RBAC via `require_role()` dependency, Redis-backed rate limiting on login.
- **Services** (`app/services/`): Extracted business logic (grading calculations). Legacy `services/` at repo root has grader/sandbox/llm_validator used by the original single-endpoint flow.
- **Tasks** (`app/tasks.py`): Celery async tasks for execution, grading, LLM evaluation.
- **Config** (`app/config.py`): Pydantic Settings loading from `.env`. All config via environment variables.

### Frontend Layers

- **API client** (`src/api/client.ts`): Axios instance with JWT Bearer token injection and automatic refresh. Failed requests during token refresh are queued and replayed (prevents race conditions). Base URL from `VITE_API_URL` env var (defaults to `http://localhost:8000`).
- **Auth state** (`src/store/authStore.ts`): Zustand store managing user session, tokens in localStorage.
- **Routing** (`src/App.tsx`): React Router v6 with `ProtectedRoute` component that checks auth + role. Professor routes under `/professor/*`, student routes under `/student/*`.
- **Layouts**: `ProfessorLayout` and `StudentLayout` provide sidebar navigation via `<Outlet />`.
- **Styling**: Inline styles throughout (no CSS framework). No component library.

### Database

PostgreSQL 16 via SQLAlchemy. Alembic migrations in `autograder-back/alembic/`. Connection pooling configured (pool_size=10, max_overflow=20, pre_ping=true).

`database.py` provides `get_db()` dependency for session injection into routers.

### Key Design Decisions

- **Exercise randomization**: Deterministic per-student shuffle using `Random(student_id * 31 + list_id)` seed, so order is consistent across page loads but different per student.
- **Test cases have a `hidden` flag**: Hidden tests run but details aren't shown to students.
- **ExerciseList scoping**: Lists can target specific groups within a class, not just the whole class.
- **Late penalties**: Configured per ExerciseList as percent-per-day after `closes_at`.
- **Two service layers coexist**: `services/` at repo root (original single-endpoint grader) and `app/services/` (extracted grading logic for the full platform). The Celery tasks in `app/tasks.py` implement their own execution flow.

## Testing

Backend tests use FastAPI's `TestClient` with dependency overrides. `conftest.py` provides fixtures that swap `get_db` and `get_current_user` with mocks, so tests run without a real database. Test files: `test_auth_router.py`, `test_class_router.py`, `test_exercise_router.py`, `test_sandbox_integration.py`, `test_grading_logic.py`.

No frontend tests exist yet.

## Environment Setup

1. Copy `autograder-back/.env.example` to `autograder-back/.env` and fill in secrets
2. `docker compose up -d` to start Postgres and Redis
3. `cd autograder-back && uv sync --all-extras && uv run alembic upgrade head`
4. Build sandbox: `docker build -f Dockerfile.sandbox -t autograder-sandbox .` (from repo root)
5. Backend: `cd autograder-back && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000`
6. Frontend: `cd autograder-web && npm install && npm run dev`
