## 1. Service de reescrita (TDD)

- [x] 1.1 Escrever testes para `generate_variations`: prompt construction, parse de resposta JSON, preservação de placeholders, descarte de variações inválidas, tratamento de erro da API Anthropic, resposta em formato inesperado
- [x] 1.2 Implementar `app/services/message_rewriter.py` com `generate_variations(template, num_variations)` até todos os testes passarem

## 2. Schemas e validação (TDD)

- [x] 2.1 Escrever testes para novos schemas: `VariationRequest` (validação de template, limites de num_variations), `VariationResponse`, extensão de `BulkSendRequest` com campo `variations` opcional (validação de variáveis em cada variação)
- [x] 2.2 Implementar schemas em `app/schemas/messaging.py` até todos os testes passarem

## 3. Endpoint de variações (TDD)

- [x] 3.1 Escrever testes para `POST /messaging/variations`: geração bem-sucedida, template inválido, variáveis desconhecidas, num_variations fora dos limites, falha da API Anthropic (502), acesso negado para não-admin
- [x] 3.2 Implementar endpoint em `app/routers/messaging.py` até todos os testes passarem

## 4. Extensão do envio bulk (TDD)

- [x] 4.1 Escrever testes para `POST /messaging/send` com variações: envio com variations[], variações com variáveis inválidas rejeitadas, envio sem variações mantém comportamento atual
- [x] 4.2 Escrever testes para Celery task `send_bulk_messages` com variações: sorteio de variação por destinatário, fallback para message_template sem variações, resolved_message armazena variação usada
- [x] 4.3 Implementar extensão do endpoint `/send` e do Celery task até todos os testes passarem

## 5. Frontend

- [x] 5.1 Adicionar botão "Gerar variações" na tela de envio de campanha com toggle on/off
- [x] 5.2 Implementar chamada à API `POST /messaging/variations` e exibir lista de variações com checkboxes e edição inline
- [x] 5.3 Integrar variações selecionadas no `POST /messaging/send` (passar campo `variations[]` quando presente)
