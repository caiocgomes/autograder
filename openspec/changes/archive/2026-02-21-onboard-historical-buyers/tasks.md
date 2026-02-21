## 1. Task Celery

- [x] 1.1 Criar task `onboard_historical_buyers` em `app/tasks.py` com estrutura base (decorator, imports, db session, counters)
- [x] 1.2 Implementar query de elegíveis: `hotmart_buyers WHERE status='Ativo' AND user_id IS NULL`, deduplicada por email
- [x] 1.3 Para cada email: checar se `User` já existe pelo email; se sim, vincular `user_id` e marcar como `skipped`
- [x] 1.4 Para cada email novo: criar `User(email, whatsapp_number, password_hash=bcrypt(token_hex(32)))`
- [x] 1.5 Chamar `lifecycle.transition(db, user, "purchase_approved", hotmart_product_id=<produto_primário>)` para Users novos
- [x] 1.6 Atualizar `hotmart_buyers.user_id` para todos os rows do email (incluindo múltiplos produtos)
- [x] 1.7 Envolver cada buyer em try/except com rollback e incremento de `errors`
- [x] 1.8 Registrar `Event(type="hotmart_buyers.historical_onboarding_completed", payload=counters)` ao final
- [x] 1.9 Retornar dict `{"created": N, "skipped": N, "errors": N, "total": N}`

## 2. Testes

- [x] 2.1 Teste: buyer ativo sem conta → User criado com campos corretos (email, name, whatsapp_number)
- [x] 2.2 Teste: buyer com phone → `lifecycle.transition` chamado → WhatsApp enviado (mock Evolution)
- [x] 2.3 Teste: buyer sem phone → User criado, `transition` chamado, sem envio WhatsApp
- [x] 2.4 Teste: comprador com dois produtos → um único User criado, dois `hotmart_buyers.user_id` atualizados
- [x] 2.5 Teste: re-execução com `user_id` já preenchido → skipped, sem duplicata
- [x] 2.6 Teste: email já existe em `users` → vincula `user_id`, sem criar duplicata
- [x] 2.7 Teste: falha em um buyer não aborta os demais, `errors` incrementado
- [x] 2.8 Teste: counters corretos no retorno e Event registrado

## 3. Verificação manual

- [x] 3.1 Executar task em produção: `SSL_CERT_FILE=... uv run python -c "from app.tasks import onboard_historical_buyers; print(onboard_historical_buyers.run())"`
- [x] 3.2 Validar no banco: 1445 users criados com lifecycle=PENDING_ONBOARDING
- [x] 3.3 Validar vínculo: `hotmart_buyers WHERE status='Ativo' AND user_id IS NULL` = 0
- [x] 3.4 Validar eventos: `{"total": 1445, "errors": 0, "created": 1445, "skipped": 0}`
