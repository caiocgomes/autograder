#!/bin/bash
# =============================================================================
# Autograder — Server Setup (Ubuntu 22.04/24.04)
# Instala todas as dependencias e configura os servicos.
# Uso: sudo ./scripts/setup-server.sh
# =============================================================================

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; exit 1; }
step()  { echo -e "\n${YELLOW}== $1 ==${NC}"; }

[ "$(id -u)" -eq 0 ] || error "Execute como root: sudo $0"

REPO_DIR="/opt/autograder"

echo ""
echo "  Autograder — Server Setup"
echo ""

# -----------------------------------------------------------------------------
step "1/8 Instalando PostgreSQL 16"
# -----------------------------------------------------------------------------
if command -v psql >/dev/null 2>&1 && psql --version | grep -q "16"; then
    info "PostgreSQL 16 ja instalado"
else
    apt-get update -qq
    apt-get install -y -qq postgresql-common
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
    apt-get install -y -qq postgresql-16
    info "PostgreSQL 16 instalado"
fi
systemctl enable --now postgresql

# -----------------------------------------------------------------------------
step "2/8 Instalando Redis 7"
# -----------------------------------------------------------------------------
if command -v redis-server >/dev/null 2>&1; then
    info "Redis ja instalado"
else
    apt-get install -y -qq redis-server
    info "Redis instalado"
fi
systemctl enable --now redis-server

# -----------------------------------------------------------------------------
step "3/8 Instalando nginx"
# -----------------------------------------------------------------------------
if command -v nginx >/dev/null 2>&1; then
    info "nginx ja instalado"
else
    apt-get install -y -qq nginx
    info "nginx instalado"
fi
systemctl enable --now nginx

# -----------------------------------------------------------------------------
step "4/8 Instalando Python 3.12 + uv"
# -----------------------------------------------------------------------------
if python3.12 --version >/dev/null 2>&1; then
    info "Python 3.12 ja instalado"
else
    apt-get install -y -qq software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y -qq python3.12 python3.12-venv python3.12-dev
    info "Python 3.12 instalado"
fi

if command -v uv >/dev/null 2>&1; then
    info "uv ja instalado"
else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    info "uv instalado"
fi

# -----------------------------------------------------------------------------
step "5/8 Instalando Node.js"
# -----------------------------------------------------------------------------
if command -v node >/dev/null 2>&1; then
    info "Node.js ja instalado ($(node --version))"
else
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
    info "Node.js instalado"
fi

# -----------------------------------------------------------------------------
step "6/8 Criando usuario e database"
# -----------------------------------------------------------------------------
if id autograder >/dev/null 2>&1; then
    info "Usuario autograder ja existe"
else
    useradd --system --shell /usr/sbin/nologin --home-dir /opt/autograder autograder
    info "Usuario autograder criado"
fi

# Add to docker group (for sandbox execution)
if getent group docker >/dev/null 2>&1; then
    usermod -aG docker autograder
    info "Usuario autograder adicionado ao grupo docker"
else
    warn "Grupo docker nao existe. Instale Docker para sandbox execution."
fi

# Create PostgreSQL role and database
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='autograder'" | grep -q 1 || {
    sudo -u postgres createuser autograder
    info "Role PostgreSQL autograder criada"
}
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='autograder'" | grep -q 1 || {
    sudo -u postgres createdb -O autograder autograder
    info "Database autograder criada"
}

# Set password from .env if available
if [ -f "$REPO_DIR/.env" ]; then
    PG_PASS=$(grep '^POSTGRES_PASSWORD=' "$REPO_DIR/.env" | cut -d= -f2-)
    if [ -n "$PG_PASS" ]; then
        sudo -u postgres psql -c "ALTER USER autograder PASSWORD '$PG_PASS';"
        info "Senha PostgreSQL configurada"
    fi
fi

# Configure pg_hba.conf for password auth
PG_HBA=$(find /etc/postgresql -name pg_hba.conf | head -1)
if [ -n "$PG_HBA" ] && ! grep -q "autograder" "$PG_HBA"; then
    echo "local   autograder   autograder   md5" >> "$PG_HBA"
    echo "host    autograder   autograder   127.0.0.1/32   md5" >> "$PG_HBA"
    systemctl reload postgresql
    info "pg_hba.conf configurado"
fi

# Configure Redis password
if [ -f "$REPO_DIR/.env" ]; then
    REDIS_PASS=$(grep '^REDIS_PASSWORD=' "$REPO_DIR/.env" | cut -d= -f2-)
    if [ -n "$REDIS_PASS" ]; then
        sed -i "s/^# *requirepass .*/requirepass $REDIS_PASS/" /etc/redis/redis.conf
        sed -i "s/^requirepass .*/requirepass $REDIS_PASS/" /etc/redis/redis.conf
        systemctl restart redis-server
        info "Senha Redis configurada"
    fi
fi

# Create directories
mkdir -p "$REPO_DIR/backups" "$REPO_DIR/autograder-back/uploads"
chown -R autograder:autograder "$REPO_DIR"

# -----------------------------------------------------------------------------
step "7/8 Instalando systemd unit files"
# -----------------------------------------------------------------------------
cp "$REPO_DIR/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable autograder-api autograder-worker autograder-worker-bulk autograder-discord
info "Servicos systemd instalados e habilitados"

# -----------------------------------------------------------------------------
step "8/8 Configurando nginx e cron"
# -----------------------------------------------------------------------------
# nginx site
cp "$REPO_DIR/nginx/autograder.conf" /etc/nginx/sites-available/autograder
ln -sf /etc/nginx/sites-available/autograder /etc/nginx/sites-enabled/autograder
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
info "nginx configurado"

# Backup cron
chmod +x "$REPO_DIR/scripts/backup-db.sh"
crontab -u autograder "$REPO_DIR/scripts/crontab.txt"
info "Cron de backup instalado"

# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Setup completo!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""
echo "  Proximos passos:"
echo ""
echo "  1. Copiar .env.production.example para /opt/autograder/.env e preencher"
echo "  2. Instalar deps:  cd $REPO_DIR/autograder-back && sudo -u autograder uv sync --all-extras"
echo "  3. Migrations:     sudo -u autograder -E uv run alembic upgrade head"
echo "  4. Build frontend: cd $REPO_DIR/autograder-web && sudo -u autograder npm ci && sudo -u autograder npm run build"
echo "  5. Iniciar:        systemctl start autograder-api autograder-worker autograder-worker-bulk autograder-discord"
echo "  6. Verificar:      systemctl status autograder-api"
echo "  7. Logs:           journalctl -u autograder-api -f"
echo ""
echo "  Se migrando de Docker, rode primeiro: ./scripts/migrate-from-docker.sh"
echo ""
