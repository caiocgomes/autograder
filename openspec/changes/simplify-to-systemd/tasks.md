## 1. Systemd Unit Files

- [x] 1.1 Criar `systemd/autograder-api.service` (uvicorn, 4 workers, bind 127.0.0.1:8000, User=autograder, EnvironmentFile=/opt/autograder/.env, After=postgresql.service redis-server.service, Restart=on-failure RestartSec=5)
- [x] 1.2 Criar `systemd/autograder-worker.service` (celery worker, queues celery+whatsapp_rt, concurrency 4, mesmas dependências)
- [x] 1.3 Criar `systemd/autograder-worker-bulk.service` (celery worker, queue whatsapp_bulk, concurrency 1)
- [x] 1.4 Criar `systemd/autograder-discord.service` (python -m app.discord_bot)

## 2. nginx Configuration

- [x] 2.1 Criar `nginx/autograder.conf` com: reverse proxy /api/ → 127.0.0.1:8000, static files de /opt/autograder/autograder-web/dist, SSL com certs existentes, rate limiting, security headers, gzip

## 3. Backup Cron

- [x] 3.1 Criar `scripts/backup-db.sh` (pg_dump -Fc para /opt/autograder/backups/, cleanup de dumps > 7 dias)
- [x] 3.2 Criar `scripts/crontab.txt` com a entrada de cron (diário 02:00 UTC)

## 4. Deploy Script

- [x] 4.1 Criar `deploy.sh` na raiz do repo (git pull, uv sync, alembic upgrade head, npm install + build, systemctl restart de todos os serviços, com exit on error)

## 5. Server Setup Script

- [x] 5.1 Criar `setup-server.sh` que instala PostgreSQL 16, Redis 7, nginx, Python 3.12, uv, Node.js
- [x] 5.2 No mesmo script: criar usuário de sistema `autograder`, adicionar ao grupo `docker`, criar database e role PostgreSQL
- [x] 5.3 No mesmo script: copiar unit files para /etc/systemd/system/, habilitar serviços, copiar nginx config, instalar cron

## 6. Configuração da Aplicação

- [x] 6.1 Criar `.env.production.example` com URLs usando localhost em vez de nomes de container Docker (DATABASE_URL=postgresql://...@localhost:5432/..., REDIS_URL=redis://...@localhost:6379/0)

## 7. Migração de Dados

- [x] 7.1 Criar `scripts/migrate-from-docker.sh` (pg_dump do container, pg_restore no PostgreSQL do sistema, validação de contagem de tabelas)

## 8. Cleanup

- [x] 8.1 Marcar `docker-compose.prod.yml` como deprecated (adicionar comentário no topo direcionando para systemd)
- [x] 8.2 Atualizar CLAUDE.md com novos comandos de infra (systemctl, journalctl, deploy.sh)
