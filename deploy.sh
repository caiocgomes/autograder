#!/bin/bash
# =============================================================================
# Autograder — Deploy Script
# Sobe tudo: DB, Redis, Backend, Workers, Discord Bot, Frontend (via Nginx)
# Uso: ./deploy.sh [APP_PORT]  (default: 8000)
# =============================================================================

set -e

APP_PORT=${1:-${APP_PORT:-8000}}
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$REPO_DIR/autograder-back/.env"
COMPOSE="docker compose -f docker-compose.prod.yml"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; exit 1; }
step()  { echo -e "\n${YELLOW}== $1 ==${NC}"; }

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo 'SEU_IP')

echo ""
echo "  Autograder Deploy"
echo "  Porta: $APP_PORT"
echo ""

# -----------------------------------------------------------------------------
step "1/9 Verificando pre-requisitos"
# -----------------------------------------------------------------------------
command -v docker >/dev/null 2>&1 || error "Docker nao encontrado"
docker compose version >/dev/null 2>&1 || error "Docker Compose nao encontrado"
command -v node >/dev/null 2>&1 || error "Node.js nao encontrado (necessario para build do frontend)"
info "Docker + Node ok"

[ -f "$ENV_FILE" ] || error ".env nao encontrado em $ENV_FILE -- copie .env.example e preencha"

# Verificar se ainda tem placeholders criticos
for placeholder in "your-secret-key-here" "your-hotmart-webhook-secret" "your-discord-bot-token" "your-evolution-api-host"; do
    if grep -q "$placeholder" "$ENV_FILE" 2>/dev/null; then
        error ".env ainda tem placeholder: '$placeholder' -- preencha antes de continuar"
    fi
done
info ".env ok"

# Validar que DATABASE_URL e REDIS_URL apontam para os containers Docker
if grep -q "@localhost" "$ENV_FILE" || grep -q "@127.0.0.1" "$ENV_FILE"; then
    warn "ATENCAO: DATABASE_URL ou REDIS_URL aponta para localhost."
    warn "Em producao deve apontar para os containers: @db e @redis"
    warn "Corrija o .env antes de continuar."
    exit 1
fi

# -----------------------------------------------------------------------------
step "2/9 Buildando frontend"
# -----------------------------------------------------------------------------
cd "$REPO_DIR/autograder-web"
npm ci --silent
npm run build
cd "$REPO_DIR"
[ -d "autograder-web/dist" ] || error "Build do frontend falhou (dist/ nao existe)"
info "Frontend build ok"

# -----------------------------------------------------------------------------
step "3/9 Construindo imagem sandbox"
# -----------------------------------------------------------------------------
docker build -f "$REPO_DIR/Dockerfile.sandbox" -t autograder-sandbox:latest "$REPO_DIR"
info "Sandbox ok"

# -----------------------------------------------------------------------------
step "4/9 Subindo banco e redis"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT $COMPOSE up -d db redis
info "Aguardando DB e Redis ficarem healthy..."
for i in $(seq 1 30); do
    db_ok=$(docker inspect --format='{{.State.Health.Status}}' autograder-db 2>/dev/null || echo "starting")
    redis_ok=$(docker inspect --format='{{.State.Health.Status}}' autograder-redis 2>/dev/null || echo "starting")
    if [ "$db_ok" = "healthy" ] && [ "$redis_ok" = "healthy" ]; then
        break
    fi
    if [ "$i" -eq 30 ]; then
        error "Timeout esperando DB/Redis ficarem healthy"
    fi
    sleep 2
done
info "DB e Redis ok"

# -----------------------------------------------------------------------------
step "5/9 Buildando imagens e rodando migrations"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT $COMPOSE build backend worker worker-bulk
APP_PORT=$APP_PORT $COMPOSE --profile discord build discord-bot
APP_PORT=$APP_PORT $COMPOSE run --rm --entrypoint "python -m alembic upgrade head" backend
info "Migrations ok"

# -----------------------------------------------------------------------------
step "6/9 Subindo backend"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT $COMPOSE up -d backend
sleep 3

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$APP_PORT/health" 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    info "Backend ok (health check HTTP $HTTP_STATUS)"
else
    warn "Health check retornou HTTP $HTTP_STATUS -- verifique logs: $COMPOSE logs backend"
fi

# -----------------------------------------------------------------------------
step "7/9 Subindo workers (celery + celery-bulk)"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT $COMPOSE up -d worker worker-bulk
info "Workers ok (celery,whatsapp_rt + whatsapp_bulk)"

# -----------------------------------------------------------------------------
step "8/9 Subindo Discord bot + DB backup"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT $COMPOSE --profile discord up -d discord-bot
APP_PORT=$APP_PORT $COMPOSE up -d db-backup
info "Discord bot + backup ok"

# -----------------------------------------------------------------------------
step "9/9 Deployando frontend"
# -----------------------------------------------------------------------------
FRONT_PORT=${FRONT_PORT:-5173}
NGINX_CONTAINER="autograder-nginx"
if [ -d "nginx/certs" ] && [ -f "nginx/certs/fullchain.pem" ]; then
    APP_PORT=$APP_PORT $COMPOSE --profile ssl up -d nginx
    sleep 2
    if docker ps --format '{{.Names}}' | grep -q "$NGINX_CONTAINER"; then
        docker cp "autograder-web/dist/." "$NGINX_CONTAINER:/usr/share/nginx/html/"
        docker exec "$NGINX_CONTAINER" nginx -s reload 2>/dev/null || true
        info "Nginx + frontend ok (HTTPS)"
        FRONT_URL="https://$SERVER_IP"
    else
        warn "Nginx nao subiu. Verifique certs em nginx/certs/"
    fi
fi

if [ -z "${FRONT_URL:-}" ]; then
    # Sem Nginx: servir o build com npx serve na porta 5173
    # Matar instancia anterior se existir
    pkill -f "serve.*autograder-web/dist" 2>/dev/null || true
    sleep 1
    cd "$REPO_DIR"
    nohup npx -y serve -s autograder-web/dist -l "$FRONT_PORT" > /tmp/autograder-frontend.log 2>&1 &
    FRONT_PID=$!
    sleep 2
    if kill -0 "$FRONT_PID" 2>/dev/null; then
        info "Frontend servindo na porta $FRONT_PORT (pid $FRONT_PID)"
        FRONT_URL="http://$SERVER_IP:$FRONT_PORT"
    else
        warn "Frontend nao subiu. Log: /tmp/autograder-frontend.log"
        FRONT_URL="(nao iniciado)"
    fi
fi

# -----------------------------------------------------------------------------
step "Setup de dados"
# -----------------------------------------------------------------------------
APP_PORT=$APP_PORT $COMPOSE exec -T backend python scripts/setup_product_access_rules.py 2>/dev/null && \
    info "ProductAccessRules configuradas" || \
    warn "Script de setup nao encontrado ou falhou (pode rodar depois)"

# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Deploy completo!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

APP_PORT=$APP_PORT $COMPOSE --profile discord ps 2>/dev/null || $COMPOSE ps

echo ""
echo "  API:       http://$SERVER_IP:$APP_PORT"
echo "  Docs:      http://$SERVER_IP:$APP_PORT/docs"
echo "  Frontend:  $FRONT_URL"
echo "  Logs:      $COMPOSE logs -f backend worker worker-bulk"
echo ""
echo -e "${YELLOW}Criar usuario admin:${NC}"
echo ""
echo "  # 1. Gerar hash da senha"
echo "  docker exec autograder-backend python -c \\"
echo "    \"from app.auth.security import hash_password; print(hash_password('SUA_SENHA'))\""
echo ""
echo "  # 2. Inserir no banco"
echo "  docker exec autograder-db psql -U autograder -d autograder -c \\"
echo "    \"INSERT INTO users (email, password_hash, role, whatsapp_number, lifecycle_status)"
echo "     VALUES ('caio@caiogomes.com.br', 'HASH_DO_PASSO_1', 'ADMIN', '+5511991747887', 'ACTIVE');\""
echo ""
