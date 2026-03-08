#!/bin/bash
# Autograder — Daily PostgreSQL backup
# Run via cron: 0 2 * * * /opt/autograder/scripts/backup-db.sh

set -e

BACKUP_DIR="/opt/autograder/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="$BACKUP_DIR/autograder_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

# Dump in custom format (fastest restore)
pg_dump -Fc -U autograder autograder > "$DUMP_FILE"

# Remove backups older than 7 days
find "$BACKUP_DIR" -name "*.dump" -mtime +7 -delete

echo "Backup complete: $DUMP_FILE"
