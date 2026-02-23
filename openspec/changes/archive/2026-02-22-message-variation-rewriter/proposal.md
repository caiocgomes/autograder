## Why

Mensagens em massa enviadas via WhatsApp (campanhas bulk) têm conteúdo idêntico para todos os destinatários. O Meta detecta esse padrão de repetição e bloqueia a linha, independente do throttling entre envios. A frequência atual é semanal (~1 campanha/semana para eventos e atualizações de aulas), mas o risco de bloqueio cresce com o número de alunos, e o custo de perder a linha é alto.

## What Changes

- Novo endpoint `POST /messaging/variations` que recebe um template de mensagem e gera N variações via Anthropic Haiku, mantendo placeholders (`{nome}`, `{turma}`) intactos
- `POST /messaging/send` estendido para aceitar um campo opcional `variations[]` com as variações aprovadas pelo admin
- Celery task `send_bulk_messages` estendido: quando recebe variações, sorteia uma por destinatário em vez de usar template único
- Frontend: botão "Gerar variações" na tela de envio de campanha, com lista editável (checkboxes + edição inline) para revisar e selecionar variações antes do disparo
- Novo service `app/services/message_rewriter.py` encapsulando a chamada ao Anthropic Haiku

## Capabilities

### New Capabilities
- `message-variation`: Geração de variações de mensagem via LLM para campanhas bulk, incluindo endpoint de geração, integração com Haiku, e lógica de sorteio no envio

### Modified Capabilities
- `bulk-messaging-api`: POST /messaging/send aceita campo opcional `variations[]`; Celery task sorteia variação por destinatário quando fornecidas
- `message-campaigns`: `MessageRecipient.resolved_message` passa a armazenar a variação específica usada (comportamento já existente, sem mudança de schema)

## Impact

- **Backend**: novo service (`message_rewriter.py`), novo endpoint no router de messaging, extensão do schema `BulkSendRequest`, extensão do Celery task
- **Frontend**: nova UI de variações na tela de campanha (componente de lista editável)
- **Dependências**: Anthropic SDK (já instalado para grading com LLM)
- **Config**: reutiliza `ANTHROPIC_API_KEY` existente, sem nova variável de ambiente
- **Backwards compatibility**: sem `variations[]` no request, comportamento idêntico ao atual
