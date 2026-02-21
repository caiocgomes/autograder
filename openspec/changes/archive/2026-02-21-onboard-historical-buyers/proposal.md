## Why

Compradores históricos ativos na Hotmart (276 registros em `hotmart_buyers`) nunca passaram pelo webhook de `purchase_approved` — seja porque compraram antes do sistema existir ou porque o evento foi perdido. Essas pessoas precisam receber um token de cadastro via WhatsApp para conseguir se registrar no Discord e ter seus acessos ativados.

## What Changes

- Nova Celery task `onboard_historical_buyers` que processa compradores ativos em `hotmart_buyers` sem `user_id`
- Criação proativa de `User` para cada comprador elegível (email, name, whatsapp_number populados a partir de `hotmart_buyers`)
- Disparo do fluxo `lifecycle.transition("purchase_approved")` → gera `onboarding_token` + envia WhatsApp com código para `/registrar` no Discord
- Vinculação de `hotmart_buyers.user_id` após criação do User

## Capabilities

### New Capabilities
- `historical-buyer-onboarding`: Task para onboarding em lote de compradores ativos sem conta na plataforma. Reutiliza lifecycle state machine existente sem alteração.

### Modified Capabilities
- `student-lifecycle`: Nenhuma mudança nos requisitos — apenas consumo do fluxo existente por um novo caller (batch task).

## Impact

- `app/tasks.py`: nova task `onboard_historical_buyers`
- `app/models/user.py`: leitura de campos existentes — sem mudança
- `app/services/lifecycle.py`: sem mudança
- `app/integrations/evolution.py`: sem mudança (chamado indiretamente via lifecycle)
- Banco: cria rows em `users` e atualiza `hotmart_buyers.user_id`
- Efeito colateral: envia WhatsApp para cada buyer com `whatsapp_number` populado
