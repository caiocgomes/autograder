## ADDED Requirements

### Requirement: API service unit
The system SHALL provide a systemd unit `autograder-api.service` that runs uvicorn with 4 workers, binding to `127.0.0.1:8000`. The unit SHALL start after `postgresql.service` and `redis-server.service`, run as user `autograder`, and load environment from `/opt/autograder/.env`.

#### Scenario: Service starts on boot
- **WHEN** the server boots
- **THEN** `autograder-api.service` starts automatically after PostgreSQL and Redis are ready

#### Scenario: Service restarts on crash
- **WHEN** the uvicorn process crashes
- **THEN** systemd restarts it within 5 seconds

#### Scenario: Graceful stop
- **WHEN** `systemctl stop autograder-api` is executed
- **THEN** uvicorn receives SIGTERM and shuts down gracefully

### Requirement: Celery worker service unit
The system SHALL provide a systemd unit `autograder-worker.service` that runs a Celery worker consuming queues `celery` and `whatsapp_rt` with concurrency 4.

#### Scenario: Worker starts with correct queues
- **WHEN** `autograder-worker.service` starts
- **THEN** the Celery worker consumes from `celery` and `whatsapp_rt` queues

#### Scenario: Worker restarts on crash
- **WHEN** the Celery worker process crashes
- **THEN** systemd restarts it within 5 seconds

### Requirement: Celery bulk worker service unit
The system SHALL provide a systemd unit `autograder-worker-bulk.service` that runs a Celery worker consuming queue `whatsapp_bulk` with concurrency 1.

#### Scenario: Bulk worker runs with concurrency 1
- **WHEN** `autograder-worker-bulk.service` starts
- **THEN** the Celery worker runs with concurrency 1 on queue `whatsapp_bulk`

### Requirement: Discord bot service unit
The system SHALL provide a systemd unit `autograder-discord.service` that runs the Discord bot as `python -m app.discord_bot`.

#### Scenario: Discord bot starts
- **WHEN** `autograder-discord.service` starts
- **THEN** the Discord bot connects to the configured guild

### Requirement: Dedicated system user
The system SHALL use a dedicated `autograder` system user (no login shell) to run all application services. This user SHALL be a member of the `docker` group to access the Docker socket for sandbox execution.

#### Scenario: User has Docker access
- **WHEN** the `autograder` user runs a Docker command
- **THEN** the command executes successfully via `/var/run/docker.sock`

### Requirement: Centralized environment file
All service units SHALL load environment variables from `/opt/autograder/.env` via `EnvironmentFile=`. The `.env` SHALL use `localhost` for database and Redis URLs instead of Docker service names.

#### Scenario: Database URL uses localhost
- **WHEN** services start
- **THEN** `DATABASE_URL` resolves to `postgresql://autograder:<password>@localhost:5432/autograder`
