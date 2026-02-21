## ADDED Requirements

### Requirement: Onboarding em lote de compradores históricos
O sistema SHALL processar compradores ativos em `hotmart_buyers` sem `user_id` e criar contas de usuário com fluxo de onboarding completo.

#### Scenario: Comprador ativo sem conta recebe onboarding
- **WHEN** a task `onboard_historical_buyers` é executada e existe um `hotmart_buyer` com `status='Ativo'` e `user_id=NULL`
- **THEN** o sistema cria um `User` com `email`, `name` e `whatsapp_number` do buyer, dispara `lifecycle.transition("purchase_approved")`, e atualiza `hotmart_buyers.user_id`

#### Scenario: WhatsApp enviado quando phone disponível
- **WHEN** o comprador tem `phone` preenchido em `hotmart_buyers`
- **THEN** o User é criado com `whatsapp_number` preenchido e o WhatsApp de onboarding é enviado com o token

#### Scenario: Onboarding sem WhatsApp quando phone ausente
- **WHEN** o comprador não tem `phone` em `hotmart_buyers`
- **THEN** o User é criado sem `whatsapp_number` e o onboarding prossegue sem envio de WhatsApp

### Requirement: Deduplicação por email para compradores multi-produto
O sistema SHALL criar apenas um `User` por email, mesmo que o comprador tenha múltiplos produtos em `hotmart_buyers`.

#### Scenario: Comprador com dois produtos recebe um único User
- **WHEN** um email aparece em dois rows de `hotmart_buyers` (produtos diferentes) ambos com `user_id=NULL`
- **THEN** apenas um `User` é criado e ambos os rows recebem o mesmo `user_id`

#### Scenario: WhatsApp enviado uma única vez por comprador
- **WHEN** o comprador tem múltiplos produtos ativos
- **THEN** o WhatsApp de onboarding é enviado apenas uma vez

### Requirement: Idempotência da task
O sistema SHALL ser seguro para re-execução sem criar duplicatas ou reenviar WhatsApp.

#### Scenario: Re-execução não afeta buyers já processados
- **WHEN** `onboard_historical_buyers` é executada novamente após processamento bem-sucedido
- **THEN** buyers que já têm `user_id` preenchido são ignorados e nenhuma nova mensagem é enviada

#### Scenario: Email já existente em users não gera erro fatal
- **WHEN** já existe um `User` com o mesmo email do buyer
- **THEN** o sistema vincula `hotmart_buyers.user_id` ao User existente sem criar duplicata e sem abortar o processamento dos demais

### Requirement: Resiliência a falhas individuais
O sistema SHALL continuar processando os demais compradores quando um falhar.

#### Scenario: Falha em um buyer não aborta o lote
- **WHEN** o processamento de um buyer levanta exceção (ex: Evolution API timeout)
- **THEN** o erro é logado, o contador de erros é incrementado, e o próximo buyer é processado

### Requirement: Counters de resultado
A task SHALL retornar um dict com os resultados do processamento.

#### Scenario: Task retorna métricas ao final
- **WHEN** a task conclui
- **THEN** retorna `{"created": N, "skipped": N, "errors": N, "total": N}` e registra um `Event` do tipo `hotmart_buyers.historical_onboarding_completed`
