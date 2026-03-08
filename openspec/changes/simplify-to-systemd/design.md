## Context

O autograder roda num VPS Ubuntu com 7-8 containers Docker Compose. A escala é ~100-200 alunos, um único servidor, sem necessidade de orquestração ou scaling horizontal. O Docker está sendo usado como gerenciador de processos, papel que o systemd faz melhor no Linux. O único uso legítimo de Docker é o sandbox de execução de código de aluno, que precisa de isolamento real (no network, read-only fs, non-root, memory limit).

Estado atual no servidor:
- PostgreSQL 16 (container, volume nomeado `postgres_data`)
- Redis 7 (container, volume nomeado `redis_data`)
- Backend FastAPI (container, 4 workers uvicorn)
- Celery worker (container, concurrency 4, queues: celery + whatsapp_rt)
- Celery worker-bulk (container, concurrency 1, queue: whatsapp_bulk)
- Discord bot (container)
- db-backup (container, loop com pg_dump + sleep 86400)
- Frontend: `npm exec serve` como processo solto (fora do Compose)
- nginx: não está rodando no servidor atual

## Goals / Non-Goals

**Goals:**
- Processos da aplicação gerenciados por systemd com restart automático e boot startup
- PostgreSQL e Redis como serviços do sistema (apt install)
- Deploy com um comando: `./deploy.sh`
- Logs centralizados via journalctl
- Backup via cron do sistema
- Frontend servido por nginx como static files
- Manter Docker apenas para sandbox execution
- Migração de dados sem perda

**Non-Goals:**
- Mudar a lógica da aplicação (routers, tasks, models)
- Adicionar CI/CD automatizado
- Mudar para managed database (RDS, etc.)
- Containerizar o frontend build (continua buildando local ou no deploy)
- Mudar a estrutura de filas do Celery

## Decisions

### 1. PostgreSQL via apt em vez de container

Instalar `postgresql-16` via apt. O PostgreSQL do sistema já vem com systemd integration, pg_hba.conf, e tooling padrão. Upgrade de versão é `apt upgrade`. Backup é `pg_dump` via cron.

Alternativa considerada: manter PostgreSQL em container. Rejeitada porque é exatamente o tipo de container que causa os problemas relatados (porta travada, volume órfão, restart não funciona).

### 2. Redis via apt em vez de container

Instalar `redis-server` via apt. Configuração de senha no `/etc/redis/redis.conf`. Mesmo raciocínio do PostgreSQL.

### 3. Um systemd unit file por processo

```
autograder-api.service      → uvicorn (4 workers)
autograder-worker.service   → celery worker (default + whatsapp_rt)
autograder-worker-bulk.service → celery worker (whatsapp_bulk, concurrency=1)
autograder-discord.service  → discord bot
```

Cada um com:
- `Restart=on-failure`, `RestartSec=5`
- `After=postgresql.service redis-server.service`
- `User=autograder` (usuário de sistema dedicado)
- `WorkingDirectory=/opt/autograder/autograder-back`
- `EnvironmentFile=/opt/autograder/.env`
- Logs via stdout/stderr → journalctl

Alternativa considerada: um único serviço com supervisord dentro. Rejeitada porque perde a granularidade de restart/status por processo.

### 4. nginx como reverse proxy + static server

```nginx
server {
    listen 443 ssl;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
    }

    location / {
        root /opt/autograder/autograder-web/dist;
        try_files $file $file/ /index.html;
    }
}
```

Substitui o `npm exec serve` atual. Reusa a config de SSL/HSTS que já existe em `nginx/nginx.conf`.

### 5. Variáveis de ambiente em arquivo único

Um `.env` em `/opt/autograder/.env` referenciado por `EnvironmentFile=` em todos os unit files. Mesmo formato do `.env` atual. O `DATABASE_URL` muda de `@db:5432` para `@localhost:5432`.

### 6. Deploy script

```bash
#!/bin/bash
cd /opt/autograder
git pull origin main
cd autograder-back && uv sync --all-extras
uv run alembic upgrade head
cd ../autograder-web && npm install && npm run build
sudo systemctl restart autograder-api autograder-worker autograder-worker-bulk autograder-discord
```

### 7. Docker socket para sandbox

O backend e o worker acessam `/var/run/docker.sock` diretamente (já estão no host). O usuário `autograder` precisa estar no grupo `docker`. Mais simples que o mount entre containers atual.

## Risks / Trade-offs

**[Migração de dados do PostgreSQL]** → Fazer pg_dump do container atual, restaurar no PostgreSQL do sistema. Testar em staging primeiro. Manter o container antigo parado (não removido) até confirmar que tudo funciona.

**[Downtime durante migração]** → Inevitável. Estimar 30-60 minutos. Fazer fora de horário de aula.

**[Permissões do Docker socket]** → O usuário `autograder` no grupo `docker` tem acesso root equivalente via Docker. Mitigação: é o mesmo nível de acesso que o container tinha antes (montava o socket).

**[Upgrade de PostgreSQL]** → Sem container, upgrade major (16→17) requer `pg_upgrade` manual ou dump/restore. Na prática, isso acontece uma vez por ano e é bem documentado.

**[Python no host]** → Precisa manter Python 3.12 + uv no host. Com uv, o gerenciamento de deps é trivial (`uv sync`). Não usar pyenv, instalar via deadsnakes PPA ou similar.

## Migration Plan

### Fase 1: Preparar o host
1. Instalar PostgreSQL 16, Redis 7, nginx, Python 3.12, uv
2. Configurar PostgreSQL (criar user + database `autograder`)
3. Configurar Redis (senha, bind localhost)
4. Criar usuário de sistema `autograder`
5. Clonar repo em `/opt/autograder`, instalar deps com uv

### Fase 2: Migrar dados
1. `docker compose exec db pg_dump -Fc -U autograder autograder > /tmp/autograder.dump`
2. `pg_restore -U autograder -d autograder /tmp/autograder.dump`
3. Validar dados (contagem de tabelas, spot check)

### Fase 3: Instalar serviços
1. Copiar unit files para `/etc/systemd/system/`
2. Copiar nginx config para `/etc/nginx/sites-available/`
3. Copiar `.env` para `/opt/autograder/.env`
4. `systemctl daemon-reload && systemctl enable --now autograder-api autograder-worker autograder-worker-bulk autograder-discord`
5. Build do frontend: `cd autograder-web && npm run build`
6. Enable nginx site

### Fase 4: Validar e cleanup
1. Testar todos os endpoints (API, frontend, WebSocket, Discord bot)
2. Testar sync Hotmart, envio WhatsApp, sandbox execution
3. Parar containers antigos: `docker compose down`
4. NÃO remover volumes Docker ainda (manter como backup por 1 semana)
5. Após 1 semana: `docker volume prune`

### Rollback
Se algo der errado:
1. `systemctl stop autograder-*`
2. `docker compose up -d` (containers antigos ainda existem)
3. Investigar o problema com calma

## Open Questions

- O servidor tem SSL via Let's Encrypt (certbot)? Se sim, o nginx config precisa apontar para os certs existentes.
- Existe algum processo rodando que depende dos containers Docker além do autograder? (outros projetos no mesmo VPS?)
