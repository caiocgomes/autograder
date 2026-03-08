## ADDED Requirements

### Requirement: Deploy script
The system SHALL provide a `deploy.sh` script at the repo root that performs: git pull, dependency sync (uv sync), database migration (alembic upgrade head), frontend build (npm run build), and service restart.

#### Scenario: Full deploy
- **WHEN** `./deploy.sh` is executed on the server
- **THEN** code is updated, deps synced, migrations applied, frontend rebuilt, and all autograder services restarted

#### Scenario: Deploy with migration failure
- **WHEN** `alembic upgrade head` fails during deploy
- **THEN** the script stops and does NOT restart services, preserving the running version

### Requirement: nginx configuration
The system SHALL provide an nginx site config that serves the frontend from `/opt/autograder/autograder-web/dist` and proxies `/api/` to `127.0.0.1:8000`. SSL configuration SHALL reuse existing certificates.

#### Scenario: Frontend served as static files
- **WHEN** a user accesses the root URL
- **THEN** nginx serves the React SPA from dist/ with fallback to index.html

#### Scenario: API requests proxied
- **WHEN** a request hits `/api/*`
- **THEN** nginx proxies to the uvicorn backend on port 8000

### Requirement: Infrastructure setup script
The system SHALL provide a `setup-server.sh` script that installs PostgreSQL 16, Redis 7, nginx, Python 3.12, and uv on Ubuntu. The script SHALL create the `autograder` system user, database, and install systemd unit files.

#### Scenario: Fresh server setup
- **WHEN** `setup-server.sh` is executed on a fresh Ubuntu server
- **THEN** all system dependencies are installed and configured
