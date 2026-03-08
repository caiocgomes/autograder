#!/bin/bash
# =============================================================================
# Autograder — Deploy Script (systemd)
# Uso: sudo ./deploy-systemd.sh
# =============================================================================

set -e

REPO_DIR="/opt/autograder"
ENV_FILE="$REPO_DIR/.env"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; exit 1; }
step()  { echo -e "\n${YELLOW}== $1 ==${NC}"; }

echo ""
echo "  Autograder Deploy (systemd)"
echo ""

# -----------------------------------------------------------------------------
step "1/6 Verificando pre-requisitos"
# -----------------------------------------------------------------------------
[ -f "$ENV_FILE" ] || error ".env nao encontrado em $ENV_FILE"
command -v uv >/dev/null 2>&1 || error "uv nao encontrado"
command -v node >/dev/null 2>&1 || error "Node.js nao encontrado"
systemctl is-active --quiet postgresql || error "PostgreSQL nao esta rodando"
systemctl is-active --quiet redis-server || error "Redis nao esta rodando"
info "Pre-requisitos ok"

# -----------------------------------------------------------------------------
step "2/6 Atualizando codigo"
# -----------------------------------------------------------------------------
cd "$REPO_DIR"
sudo -u autograder git pull origin main
info "Codigo atualizado"

# -----------------------------------------------------------------------------
step "3/6 Instalando dependencias backend"
# -----------------------------------------------------------------------------
cd "$REPO_DIR/autograder-back"
sudo -u autograder uv sync --all-extras
info "Dependencias Python ok"

# -----------------------------------------------------------------------------
step "4/6 Aplicando migrations"
# -----------------------------------------------------------------------------
sudo -u autograder -E uv run alembic upgrade head
info "Migrations ok"

# -----------------------------------------------------------------------------
step "5/6 Buildando frontend"
# -----------------------------------------------------------------------------
cd "$REPO_DIR/autograder-web"
sudo -u autograder npm ci --silent
sudo -u autograder npm run build
[ -d "dist" ] || error "Build do frontend falhou (dist/ nao existe)"
info "Frontend build ok"

# -----------------------------------------------------------------------------
step "6/6 Reiniciando servicos"
# -----------------------------------------------------------------------------
systemctl restart autograder-api autograder-worker autograder-worker-bulk autograder-discord
sleep 2

# Health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    info "API ok (health check HTTP $HTTP_STATUS)"
else
    warn "Health check retornou HTTP $HTTP_STATUS -- verifique: journalctl -u autograder-api -n 50"
fi

# Reload nginx (picks up new frontend build)
systemctl reload nginx 2>/dev/null || true

# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Deploy completo!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""
echo "  Logs:    journalctl -u autograder-api -f"
echo "  Status:  systemctl status autograder-api autograder-worker"
echo ""
