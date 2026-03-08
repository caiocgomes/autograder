#!/bin/bash
# =============================================================================
# Autograder — Migrate data from Docker PostgreSQL to system PostgreSQL
# Run ONCE during migration. Requires both Docker and system PostgreSQL running.
# Uso: sudo ./scripts/migrate-from-docker.sh
# =============================================================================

set -e

BACKUP_FILE="/tmp/autograder_migration.dump"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; exit 1; }

echo ""
echo "  Autograder — Migracao Docker → System PostgreSQL"
echo ""

# Check Docker container is running
docker ps --format '{{.Names}}' | grep -q autograder-db || error "Container autograder-db nao esta rodando"

# Check system PostgreSQL is running
systemctl is-active --quiet postgresql || error "PostgreSQL do sistema nao esta rodando"

# Step 1: Dump from Docker
info "Fazendo dump do container Docker..."
docker exec autograder-db pg_dump -Fc -U autograder autograder > "$BACKUP_FILE"
info "Dump salvo em $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Step 2: Count tables in Docker for validation
DOCKER_TABLES=$(docker exec autograder-db psql -U autograder -d autograder -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
info "Tabelas no Docker: $DOCKER_TABLES"

# Step 3: Restore to system PostgreSQL
info "Restaurando no PostgreSQL do sistema..."
# Drop and recreate to ensure clean state
sudo -u postgres dropdb --if-exists autograder
sudo -u postgres createdb -O autograder autograder
pg_restore -U autograder -d autograder --no-owner --no-acl "$BACKUP_FILE" || warn "pg_restore teve warnings (normal para roles/grants)"

# Step 4: Validate
SYSTEM_TABLES=$(sudo -u postgres psql -d autograder -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
info "Tabelas no sistema: $SYSTEM_TABLES"

if [ "$DOCKER_TABLES" = "$SYSTEM_TABLES" ]; then
    info "Validacao OK: mesma quantidade de tabelas ($SYSTEM_TABLES)"
else
    warn "ATENCAO: Docker tem $DOCKER_TABLES tabelas, sistema tem $SYSTEM_TABLES"
    warn "Verifique manualmente antes de prosseguir"
fi

echo ""
info "Migracao concluida. Dump mantido em $BACKUP_FILE como backup."
info "Proximo passo: testar a aplicacao com o PostgreSQL do sistema."
info "Quando confirmar que tudo funciona, pode remover os containers Docker."
echo ""
