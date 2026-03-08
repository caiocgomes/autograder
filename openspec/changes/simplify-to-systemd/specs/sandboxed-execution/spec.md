## MODIFIED Requirements

### Requirement: Docker socket access
The sandbox execution system SHALL access the Docker daemon via `/var/run/docker.sock` directly from the host process (no container-to-container socket mount). The `autograder` system user SHALL be in the `docker` group to enable this access.

#### Scenario: Sandbox container created from host process
- **WHEN** a grading task needs to execute student code
- **THEN** the Celery worker (running as systemd service) creates a sandbox container via the Docker socket

#### Scenario: macOS fallback removed in production
- **WHEN** running on the production server (Linux)
- **THEN** the Docker socket path is `/var/run/docker.sock` (no macOS fallback needed)
