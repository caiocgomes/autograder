## 1. Model e Migration

- [x] 1.1 Adicionar campos `throttle_min_seconds` (Float, nullable, server_default=15.0) e `throttle_max_seconds` (Float, nullable, server_default=25.0) ao modelo `MessageCampaign`
- [x] 1.2 Criar migration Alembic para adicionar as duas colunas

## 2. Schema e Validação

- [x] 2.1 Adicionar `throttle_min_seconds` (Optional[float], default=15.0) e `throttle_max_seconds` (Optional[float], default=25.0) ao schema `BulkSendRequest`
- [x] 2.2 Adicionar validação: `throttle_min_seconds >= 3` e `throttle_max_seconds >= throttle_min_seconds`

## 3. Router e Dispatch

- [x] 3.1 Atualizar `POST /messaging/send` para gravar throttle na `MessageCampaign` e propagar para o task
- [x] 3.2 Implementar cálculo dinâmico de `soft_time_limit` e `time_limit` no dispatch do `apply_async`
- [x] 3.3 Atualizar `POST /messaging/campaigns/{id}/retry` para ler throttle do modelo e recalcular time limits com base nos pendentes restantes

## 4. Celery Task

- [x] 4.1 Adicionar parâmetros `throttle_min` e `throttle_max` ao task `send_bulk_messages`
- [x] 4.2 Substituir `random.uniform(10, 30)` hardcoded por `random.uniform(throttle_min, throttle_max)` com fallback para defaults (15, 25)

## 5. Separação de Filas

- [x] 5.1 Configurar `task_routes` no Celery para rotear `send_bulk_messages` para queue `whatsapp_bulk` e `execute_side_effect` para queue `whatsapp_rt`
- [x] 5.2 Atualizar docker-compose para iniciar workers com routing de queues (`-Q whatsapp_bulk`, `-Q whatsapp_rt`, `-Q celery`)

## 6. Testes

- [x] 6.1 Atualizar `test_bulk_send_task.py`: testar throttle custom, throttle default (fallback), e validar que `time.sleep` recebe valores do range configurado
- [x] 6.2 Adicionar testes para validação de piso mínimo e max >= min no schema
- [x] 6.3 Adicionar teste para cálculo dinâmico de time limits (campanha grande, campanha pequena com piso 120s)
- [x] 6.4 Adicionar teste para retry reutilizando throttle da campanha e recalculando time limits
