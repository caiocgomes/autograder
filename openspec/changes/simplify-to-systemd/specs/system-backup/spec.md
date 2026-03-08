## ADDED Requirements

### Requirement: Automated daily backup
The system SHALL configure a cron job that runs `pg_dump` daily and stores the dump in `/opt/autograder/backups/` with filename `autograder_YYYYMMDD_HHMMSS.dump` in custom format (`-Fc`).

#### Scenario: Daily backup executes
- **WHEN** the cron job triggers (daily at 02:00 UTC)
- **THEN** a new dump file is created in `/opt/autograder/backups/`

### Requirement: Backup retention
The cron job SHALL delete backup files older than 7 days after each successful dump.

#### Scenario: Old backups cleaned
- **WHEN** a backup completes
- **THEN** dump files older than 7 days are deleted from the backups directory
