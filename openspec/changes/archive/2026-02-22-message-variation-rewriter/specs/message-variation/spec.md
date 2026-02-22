## ADDED Requirements

### Requirement: Gerar variações de mensagem via LLM
O sistema SHALL expor `POST /messaging/variations` que recebe um template de mensagem e número desejado de variações, chama Anthropic Haiku para gerar variações semanticamente equivalentes preservando placeholders, e retorna a lista de variações. Acessível apenas por admin.

#### Scenario: Geração bem-sucedida de variações
- **WHEN** admin faz `POST /messaging/variations` com `{"message_template": "Olá {nome}! Aula amanhã sobre regressão linear.", "num_variations": 6}`
- **THEN** retorna 200 com `{"variations": ["...", "...", ...], "original": "Olá {nome}! Aula amanhã sobre regressão linear."}`
- **AND** a lista contém exatamente 6 variações
- **AND** cada variação contém o placeholder `{nome}` preservado

#### Scenario: Preservação de todos os placeholders
- **GIVEN** template contém `{nome}`, `{turma}` e `{primeiro_nome}`
- **WHEN** admin faz `POST /messaging/variations` com esse template
- **THEN** cada variação retornada contém exatamente os mesmos placeholders `{nome}`, `{turma}` e `{primeiro_nome}`

#### Scenario: Variações com placeholders ausentes são descartadas e regeradas
- **GIVEN** LLM retorna 6 variações mas 2 perderam o placeholder `{nome}`
- **WHEN** sistema valida as variações
- **THEN** as 2 inválidas são descartadas
- **AND** sistema tenta gerar mais variações para completar o total solicitado (até 1 retry)
- **AND** se após retry ainda não atingir o total, retorna as variações válidas disponíveis com campo `warning`

#### Scenario: Número de variações dentro dos limites
- **WHEN** admin faz `POST /messaging/variations` com `num_variations` entre 3 e 10
- **THEN** sistema aceita e gera o número solicitado

#### Scenario: Número de variações fora dos limites
- **WHEN** admin faz `POST /messaging/variations` com `num_variations` menor que 3 ou maior que 10
- **THEN** retorna 422

#### Scenario: Template vazio é rejeitado
- **WHEN** admin faz `POST /messaging/variations` com `message_template: ""`
- **THEN** retorna 422

#### Scenario: Template com variáveis desconhecidas é rejeitado
- **GIVEN** template contém `{saldo_bancario}`
- **WHEN** admin faz `POST /messaging/variations`
- **THEN** retorna 422 com erro indicando variáveis inválidas

#### Scenario: Falha na API do Anthropic
- **WHEN** chamada ao Anthropic Haiku falha (timeout, rate limit, erro de API)
- **THEN** retorna 502 com `{"detail": "Falha ao gerar variações. Tente novamente."}`

#### Scenario: Acesso negado para não-admin
- **WHEN** usuário com role `professor` ou `student` faz `POST /messaging/variations`
- **THEN** retorna 403

### Requirement: Service de reescrita de mensagens
O sistema SHALL implementar `app/services/message_rewriter.py` com função `generate_variations(template: str, num_variations: int) -> list[str]` que encapsula a chamada ao Anthropic Haiku.

#### Scenario: Construção do prompt de reescrita
- **WHEN** `generate_variations` é chamado com template e num_variations
- **THEN** o prompt enviado ao Haiku instrui a gerar exatamente `num_variations` variações
- **AND** instrui preservação exata de placeholders entre chaves
- **AND** instrui variação de estrutura, abertura, tom e ordem de frases
- **AND** instrui manter comprimento aproximado e não adicionar informações novas
- **AND** solicita resposta em formato JSON array de strings

#### Scenario: Parse da resposta do Haiku
- **WHEN** Haiku retorna resposta com JSON array de strings
- **THEN** `generate_variations` faz parse e retorna a lista de strings
- **AND** remove espaços em branco extras de cada variação

#### Scenario: Resposta do Haiku em formato inesperado
- **WHEN** Haiku retorna texto que não é JSON array válido
- **THEN** `generate_variations` levanta exceção com mensagem descritiva
