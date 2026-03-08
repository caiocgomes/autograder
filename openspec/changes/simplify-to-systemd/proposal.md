## Why

O deploy atual usa 7-8 containers Docker Compose num VPS único para ~100-200 alunos. Containers morrem e não voltam após reboot, processos órfãos travam portas, o frontend roda fora do Compose como processo solto. A complexidade operacional é desproporcional à escala. Cada incidente de infra exige debug de Docker (kill de docker-proxy, remove orphans, rebuild de images) quando o problema real é gerenciamento de processos, que o systemd resolve nativamente.

## What Changes

- **BREAKING**: Remove todos os containers Docker da aplicação (backend, workers, discord-bot, db-backup, nginx)
- **BREAKING**: Remove containers de infraestrutura (PostgreSQL, Redis) em favor de serviços do sistema (`apt install`)
- Cria systemd unit files para: API (uvicorn), Celery worker, Celery worker-bulk, Discord bot
- Configura nginx como serviço do sistema (reverse proxy + serve frontend estático)
- Configura PostgreSQL 16 e Redis 7 como serviços do sistema
- Substitui o container db-backup por cron job do sistema
- Mantém Docker **apenas** para sandbox execution (containers on-demand para código de aluno)
- Cria script de deploy simplificado (`git pull && uv sync && systemctl restart`)
- Migra dados do volume Docker do PostgreSQL para o PostgreSQL do sistema

## Capabilities

### New Capabilities
- `systemd-services`: Unit files para todos os processos da aplicação (API, workers, discord bot) com restart automático, logging via journalctl, e dependências corretas
- `system-deploy`: Script de deploy que faz git pull, sync de dependências, aplica migrations e restart dos serviços
- `system-backup`: Cron job para pg_dump diário com retenção de 7 dias

### Modified Capabilities
- `sandboxed-execution`: Continua usando Docker, mas agora o daemon é acessado diretamente pelo host em vez de via Docker socket mount entre containers
- `discord-bot`: Muda de container para processo systemd (sem mudança funcional)

## Impact

- **Infra do servidor**: Precisa instalar PostgreSQL 16, Redis 7, nginx, Python 3.12, uv no host via apt/instalação direta
- **Docker**: Mantém apenas o daemon para sandbox. Remove todos os docker-compose files de produção
- **Deploy**: Muda completamente. De `docker compose build && up` para `git pull && uv sync && systemctl restart`
- **Monitoramento**: Logs migram de `docker compose logs` para `journalctl -u <service>`
- **Dados**: Migração única do volume Docker PostgreSQL para o PostgreSQL do sistema
- **Arquivos removidos/obsoletos**: `docker-compose.prod.yml`, `Dockerfile`, `Dockerfile.dev`, `Dockerfile.worker`, `autograder-back/docker-compose.yml`
- **Arquivos novos**: systemd units, deploy script, cron backup, nginx site config
