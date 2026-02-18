# Backend - Autograder API

Python FastAPI backend for automated code grading with sandboxed execution and LLM feedback.

## Commands

```bash
uv sync --all-extras                                          # Install deps
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000   # Start API server
uv run pytest                                                 # Run all tests
uv run pytest tests/test_auth_router.py                       # Run test file
uv run pytest tests/test_grader.py -k "test_name"             # Run single test
uv run alembic upgrade head                                   # Apply migrations
uv run alembic revision --autogenerate -m "description"       # Create migration
docker build -f ../Dockerfile.sandbox -t autograder-sandbox .  # Build sandbox image
```

## Configuration

- Python 3.11+, package manager: uv
- Docker daemon must be running (sandbox execution uses Docker SDK)
- Config via Pydantic Settings in `app/config.py`, loaded from `.env` (see `.env.example`)
- Key env vars: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`, `LLM_PROVIDER`

## Architecture

Routers (`app/routers/`) -> Schemas (`app/schemas/`) -> Models (`app/models/`) -> Database (`app/database.py`).

Auth flow: JWT Bearer token extracted by `app/auth/dependencies.py:get_current_user()`, RBAC via `require_role()` factory. Rate limiting on login via Redis (`app/auth/rate_limiter.py`).

Async grading: Celery tasks in `app/tasks.py` handle sandbox execution and LLM evaluation. Worker config in `app/celery_app.py`.

### Docker Sandbox

Container isolation for student code execution:
- `network_mode: none` (no network)
- `read_only: true` (except /tmp)
- `user: nobody` (non-root)
- `mem_limit: 512m`, `timeout: 30s` (configurable)
- macOS fallback socket: `~/.docker/run/docker.sock`
