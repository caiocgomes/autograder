## Context

O sistema de bulk messaging usa um delay hardcoded de `random.uniform(10, 30)` entre envios WhatsApp via Evolution API. Todas as campanhas compartilham o mesmo comportamento, e o Celery task tem `soft_time_limit=7200` (2h) fixo. Mensagens transacionais (lifecycle: onboarding, welcome, churn) e campanhas bulk usam a mesma fila Celery default, o que significa que uma campanha longa pode competir com mensagens transacionais por workers.

Stack relevante: Celery + Redis como broker, Evolution API para envio, PostgreSQL para persistência de campanhas.

## Goals / Non-Goals

**Goals:**
- Permitir configuração de throttle (min/max delay) por campanha no momento da criação
- Calcular time limits do Celery task dinamicamente com base no volume e throttle
- Separar filas Celery para mensagens transacionais e bulk
- Manter compatibilidade com retry (reutiliza throttle da campanha original)

**Non-Goals:**
- Semáforo global entre filas (colisão pontual entre transacional e bulk é aceitável)
- Chunking de campanhas em múltiplos tasks (recovery por retry é suficiente)
- UI para configuração de throttle (será via API, UI pode vir depois)
- Rate limiting por instância Evolution API (uma instância por deploy)

## Decisions

### 1. Throttle como campos no modelo MessageCampaign

Dois campos Float: `throttle_min_seconds` e `throttle_max_seconds`, com defaults 15 e 25. Gravar no modelo garante que o retry usa a mesma configuração, e permite auditoria de qual throttle foi usado em cada campanha.

Alternativa descartada: config via environment variable. Não permite variação por campanha.

### 2. Piso mínimo de 3 segundos

Validação no schema: `throttle_min_seconds >= 3`. Protege contra configuração acidental que bloquearia a linha WhatsApp. O valor de 3s é conservador o suficiente para evitar rajadas sem ser restritivo para envios pequenos.

### 3. Cálculo dinâmico de time limits

Na hora do `apply_async`, calcular:

```
avg_delay = (throttle_min + throttle_max) / 2
api_overhead = 2  # segundos por mensagem (latência Evolution API + commit DB)
estimated = n_recipients * (avg_delay + api_overhead)
soft_limit = max(estimated * 1.3, 120)  # buffer de 30%, piso de 2 min
hard_limit = soft_limit + 300  # 5 min de grace period
```

O buffer de 1.3x absorve variação do random e latência variável. O piso de 120s evita time limits absurdamente curtos para envios pequenos. O retry recalcula com base nos recipients pendentes restantes.

### 4. Duas Celery queues sem semáforo compartilhado

Queue `whatsapp_rt` para side-effects do lifecycle (transacionais). Queue `whatsapp_bulk` para `send_bulk_messages`. Workers separados. Sem lock compartilhado entre as filas.

Justificativa: colisão pontual (transacional e bulk mandando no mesmo segundo) é improvável e inofensiva (são 2 msgs com ~0-2s de gap, WhatsApp não bloqueia por isso). Semáforo global adicionaria complexidade e latência na fila transacional sem benefício prático.

Alternativa descartada: semáforo Redis com bypass para transacional. Complexidade desnecessária para o volume atual.

### 5. Routing de tasks por nome

Usar `task_routes` na config Celery para rotear `send_bulk_messages` para `whatsapp_bulk` e `execute_side_effect` para `whatsapp_rt`. Tasks que não envolvem WhatsApp continuam na fila default.

## Risks / Trade-offs

**[Worker bulk morrer no meio de campanha longa]** → O mecanismo de recovery já existe: commit por recipient + retry processa apenas pendentes. Perda máxima: 1 mensagem duplicada (enviada mas não commitada).

**[Duas campanhas simultâneas na mesma linha]** → Cada uma roda em seu próprio ritmo. O intervalo efetivo na linha é menor que o throttle individual. Aceitável: mesmo com 2 campanhas de 15s, o intervalo real (~7-8s) ainda é seguro. Para 3+ campanhas simultâneas, considerar semáforo no futuro.

**[Deploy requer mudança na inicialização dos workers]** → Workers precisam ser iniciados com `-Q` específico. Documentar no docker-compose e no CLAUDE.md.

**[Default de 15-25s difere do código atual (10-30s)]** → Campanhas existentes (antes da migration) terão NULL nos campos de throttle. O task usa os defaults 15-25 quando os valores são None. Migration adiciona os campos como nullable com server_default.
