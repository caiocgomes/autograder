## ADDED Requirements

### Requirement: Isolated execution environment
The system SHALL execute student code in isolated Docker containers.

#### Scenario: Network isolation
- **WHEN** student code attempts network request
- **THEN** container blocks access (network mode: none)

#### Scenario: Filesystem isolation
- **WHEN** student code attempts to read host filesystem
- **THEN** container only sees mounted code/data, not host files

#### Scenario: Process isolation
- **WHEN** student code spawns processes
- **THEN** processes are confined to container namespace

### Requirement: Resource limits
The system SHALL enforce CPU and memory limits per execution.

#### Scenario: Memory limit enforcement
- **WHEN** student code exceeds memory limit (e.g., 512MB)
- **THEN** container is killed and submission fails with "Memory limit exceeded"

#### Scenario: CPU limit enforcement
- **WHEN** student code is allocated 1 CPU core
- **THEN** container cannot use more than 1 core

#### Scenario: PID limit
- **WHEN** student code attempts fork bomb
- **THEN** container PID limit (e.g., 256) prevents excessive process creation

### Requirement: Execution timeout
The system SHALL terminate code execution after configured timeout.

#### Scenario: Within timeout
- **WHEN** student code completes in 5 seconds with 30s timeout
- **THEN** execution succeeds and results are captured

#### Scenario: Timeout exceeded
- **WHEN** student code runs beyond timeout
- **THEN** container is killed and submission fails with "Execution timed out"

### Requirement: Capture execution output
The system SHALL capture stdout, stderr, and exit code from student code.

#### Scenario: Successful execution
- **WHEN** student code prints to stdout and exits with code 0
- **THEN** system captures stdout and records success

#### Scenario: Runtime error
- **WHEN** student code raises exception
- **THEN** system captures stderr with full traceback and exit code

#### Scenario: Output size limit
- **WHEN** student code prints > 100KB to stdout
- **THEN** system truncates output and notes "Output truncated"

### Requirement: Ephemeral containers
The system SHALL create fresh containers per execution and destroy after completion.

#### Scenario: Container lifecycle
- **WHEN** execution task starts
- **THEN** system creates new container, runs code, captures output, destroys container

#### Scenario: No state persistence
- **WHEN** student submits second attempt
- **THEN** execution runs in new container, not reusing first container's state

### Requirement: Test harness execution
The system SHALL mount test cases and execute them against student code.

#### Scenario: Run unit tests
- **WHEN** exercise has test cases
- **THEN** system mounts tests into container, imports student code, runs tests, captures results

#### Scenario: Test case isolation
- **WHEN** multiple test cases exist
- **THEN** each test runs independently and failures don't block subsequent tests

### Requirement: Dataset availability
The system SHALL mount exercise datasets into container for student code access.

#### Scenario: CSV dataset mounted
- **WHEN** exercise includes train.csv
- **THEN** container mounts file at /data/train.csv readable by student code

#### Scenario: Multiple datasets
- **WHEN** exercise has multiple files
- **THEN** all files are mounted under /data/ directory

### Requirement: Security hardening
The system SHALL apply security measures to prevent container escape.

#### Scenario: Drop Linux capabilities
- **WHEN** container starts
- **THEN** all capabilities are dropped (no CAP_SYS_ADMIN, CAP_NET_RAW, etc.)

#### Scenario: Read-only filesystem
- **WHEN** student code attempts to write outside /tmp
- **THEN** write fails (filesystem read-only except /tmp)

#### Scenario: Non-root user
- **WHEN** code executes in container
- **THEN** runs as non-root user (UID 1000) via user namespace mapping

### Requirement: Async task queue
The system SHALL process submissions via async worker queue.

#### Scenario: Enqueue submission
- **WHEN** student submits code
- **THEN** system creates task in queue and returns "queued" status

#### Scenario: Worker picks up task
- **WHEN** Celery worker is idle
- **THEN** worker dequeues task, updates status to "running", executes code

#### Scenario: Concurrent executions
- **WHEN** 50 submissions arrive simultaneously
- **THEN** multiple workers process tasks in parallel (auto-scaling)

### Requirement: Retry on infrastructure failure
The system SHALL retry execution if container fails due to infrastructure issues.

#### Scenario: Docker daemon error
- **WHEN** container creation fails due to daemon error
- **THEN** system retries up to 3 times before marking as failed

#### Scenario: Permanent failure
- **WHEN** 3 retries fail
- **THEN** submission marked as failed with error "Infrastructure error, contact support"

### Requirement: Execution logs accessibility
The system SHALL make execution logs accessible to students for debugging.

#### Scenario: View logs
- **WHEN** student views completed submission
- **THEN** system displays stdout, stderr, and execution time

#### Scenario: Hidden test output
- **WHEN** test case is marked hidden
- **THEN** logs show "Test failed" without revealing input/output
