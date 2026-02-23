## Context

O sistema de bulk messaging já envia campanhas WhatsApp via Evolution API com throttling (10-30s entre envios). O problema é que mensagens idênticas para muitos destinatários disparam detecção de spam do Meta. O Anthropic SDK já está instalado e configurado (`anthropic_api_key` em settings, usado no grading pipeline).

O fluxo atual é: admin escreve template → `POST /messaging/send` cria campanha + despacha Celery task → task resolve variáveis e envia via Evolution API.

## Goals / Non-Goals

**Goals:**
- Permitir que o admin gere variações de uma mensagem via Haiku antes de enviar
- Manter o admin no controle: ele revisa, edita e seleciona quais variações usar
- Sorteio transparente de variações por destinatário no envio
- Backwards-compatible: sem variações, comportamento atual intacto

**Non-Goals:**
- Reescrita automática sem revisão humana
- Variação de mensagens de lifecycle (onboarding, welcome, churn) — são individuais e transacionais
- Persistência das variações como entidade separada no banco — vivem no frontend até o envio
- Interface de prompt engineering para o admin — o prompt de reescrita é fixo no backend

## Decisions

### 1. Endpoint de geração stateless

Novo `POST /messaging/variations` recebe o template e retorna lista de variações. Não persiste nada. O frontend guarda as variações em state local até o admin confirmar e enviar.

**Alternativa considerada**: salvar variações em tabela intermediária e retornar IDs. Rejeitada porque adiciona complexidade sem benefício — as variações são efêmeras e descartáveis até o momento do envio.

### 2. Anthropic Haiku como modelo de reescrita

`claude-haiku-4-5-20251001` via SDK que já está instalado. Rápido (<1s), barato, suficiente para reescrita de mensagens curtas.

**Alternativa considerada**: GPT-4o-mini. Rejeitada por preferência do stakeholder e porque a SDK da Anthropic já está integrada.

### 3. Variações passadas no BulkSendRequest

`POST /messaging/send` ganha campo opcional `variations: List[str]`. Quando presente, o Celery task sorteia uma variação por destinatário em vez de usar o `message_template` diretamente. O `message_template` continua obrigatório (é o template original, armazenado na campanha para referência).

**Alternativa considerada**: campo booleano `use_variations` + buscar variações de algum lugar. Rejeitada porque é mais simples e explícito passar as variações diretamente.

### 4. Prompt de reescrita fixo com instruções de preservação

O prompt instrui o Haiku a:
- Gerar N variações semânticamente equivalentes
- Preservar todos os placeholders (`{nome}`, `{turma}`, etc.) exatamente como estão
- Variar estrutura, abertura, tom e ordem das frases
- Manter o mesmo comprimento aproximado
- Não adicionar informações que não estejam no original
- Responder em formato JSON array de strings

### 5. Sorteio com distribuição uniforme

Na Celery task, `random.choice(variations)` para cada destinatário. Não precisa de seed determinístico aqui (diferente da randomização de exercícios) porque não há necessidade de reprodutibilidade.

### 6. Validação de variações no schema

Cada variação na lista `variations[]` passa pela mesma validação de template que `message_template` (verificação de variáveis permitidas). Isso garante que variações editadas pelo admin não introduzam variáveis inválidas.

## Risks / Trade-offs

- **Haiku pode não preservar placeholders**: o prompt instrui preservação, mas LLMs podem falhar. → Validação pós-geração: backend verifica que cada variação contém os mesmos placeholders do original. Variações que perdem placeholders são descartadas e regeradas (ou retornadas com flag de warning).

- **Custo por chamada LLM**: para 6 variações de mensagem curta, ~500 tokens de entrada + ~1000 de saída. Custo < $0.01 por campanha. → Irrelevante na escala atual.

- **Latência da geração**: Haiku responde em <2s para esse volume. → Aceitável porque é uma operação one-shot antes do envio, não no hot path.

- **Meta pode evoluir detecção**: variações textuais podem não ser suficientes se o Meta passar a usar fingerprinting semântico. → Risco aceito. Se acontecer, o prompt pode ser ajustado ou a abordagem reavaliada.
