#!/bin/bash
# =============================================================================
# Autograder — First Deploy Script
# Roda UMA vez no servidor depois de clonar o repo e preencher o .env
# Uso: ./deploy.sh [APP_PORT]  (default: 8000)
# =============================================================================

set -e

APP_PORT=${1:-${APP_PORT:-8000}}
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$REPO_DIR/autograder-back/.env"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()  { echo -e "\n${YELLOW}══ $1 ══${NC}"; }

echo ""
echo "  Autograder Deploy"
echo "  Porta: $APP_PORT"
echo ""

# -----------------------------------------------------------------------------
step "1/7 Verificando pré-requisitos"
# -----------------------------------------------------------------------------
command -v docker >/dev/null 2>&1 || error "Docker não encontrado"
docker compose version >/dev/null 2>&1 || error "Docker Compose não encontrado"
info "Docker ok"

[ -f "$ENV_FILE" ] || error ".env não encontrado em $ENV_FILE — copie .env.example e preencha"

# Verificar se ainda tem placeholders críticos
for placeholder in "your-secret-key-here" "your-hotmart-webhook-secret" "your-discord-bot-token" "your-evolution-api-host"; do
    if grep -q "$placeholder" "$ENV_FILE" 2>/dev/null; then
        error ".env ainda tem placeholder: '$placeholder' — preencha antes de continuar"
    fi
done
info ".env ok"

# Corrigir DATABASE_URL e REDIS_URL para apontar para os containers
sed -i 's|DATABASE_URL=postgresql://.*@localhost|DATABASE_URL=postgresql://autograder:'"$(grep POSTGRES_PASSWORD "$ENV_FILE" | cut -d= -f2)"'@db|' "$ENV_FILE" 2>/dev/null || true
sed -i 's|REDIS_URL=redis://\(:.*@\)\?localhost|REDIS_URL=redis://:'"$(grep ^REDIS_PASSWORD "$ENV_FILE" | cut -d= -f2)"'@redis|' "$ENV_FILE" 2>/dev/null || true

# -----------------------------------------------------------------------------
step "2/7 Construindo imagem sandbox"
# -----------------------------------------------------------------------------
docker build -f "$REPO_DIR/Dockerfile.sandbox" -t autograder-sandbox:latest "$REPO_DIR"
info "Sandbox ok"

# -----------------------------------------------------------------------------
step "3/7 Subindo banco e redis"
# -----------------------------------------------------------------------------
cd "$REPO_DIR"
APP_PORT=$APP_PORT docker compose -f docker-compose.prod.yml up -d db redis
info "Aguardando db ficar saudável..."
sleep 5
docker compose -f docker-compose.prod.yml ps db redis
info "DB e Redis ok"

# -----------------------------------------------------------------------------
step "4/7 Rodando migrations"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT docker compose -f docker-compose.prod.yml run --rm \
    --entrypoint "python -m alembic upgrade head" backend
info "Migrations ok"

# -----------------------------------------------------------------------------
step "5/7 Subindo backend e worker"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT docker compose -f docker-compose.prod.yml up -d backend worker
info "Backend e worker ok"
sleep 3

# Health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$APP_PORT/health" 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    info "Health check ok (HTTP $HTTP_STATUS)"
else
    warn "Health check retornou HTTP $HTTP_STATUS — verifique logs: docker compose -f docker-compose.prod.yml logs backend"
fi

# -----------------------------------------------------------------------------
step "6/7 Setup de dados (produtos e access rules)"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT docker compose -f docker-compose.prod.yml exec backend \
    python scripts/setup_product_access_rules.py
info "ProductAccessRules configuradas"

# -----------------------------------------------------------------------------
step "7/7 Subindo Discord bot"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT docker compose -f docker-compose.prod.yml --profile discord up -d discord-bot
info "Discord bot ok"

# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  Deploy concluído!${NC}"
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo ""
echo "  API:         http://$(curl -s ifconfig.me 2>/dev/null || echo 'IP'):$APP_PORT"
echo "  Docs:        http://$(curl -s ifconfig.me 2>/dev/null || echo 'IP'):$APP_PORT/docs"
echo "  Logs:        docker compose -f docker-compose.prod.yml logs -f backend"
echo ""
echo -e "${YELLOW}Próximos passos:${NC}"
echo "  1. Configure o webhook Hotmart:"
echo "     URL: http://IP:$APP_PORT/webhooks/hotmart"
echo ""
echo "  2. Onboard dos compradores históricos (envia WhatsApp para todos):"
echo "     docker compose -f docker-compose.prod.yml exec backend \\"
echo "       uv run python -c \"from app.tasks import sync_hotmart_buyers, onboard_historical_buyers; sync_hotmart_buyers.run(); print(onboard_historical_buyers.run())\""
echo ""
echo "  3. Verificar Discord bot:"
echo "     docker compose -f docker-compose.prod.yml logs discord-bot"
echo ""
