## Context

O autograder hoje executa um pipeline único: código entra, roda em sandbox Docker, testes automatizados geram score, LLM opcionalmente complementa com feedback qualitativo. Todo o modelo de dados e toda a lógica de tasks assume que a submissão é código Python executável. Os campos `code` (NOT NULL) e `code_hash` (NOT NULL) em `Submission`, a validação de sintaxe Python no router, a construção do test harness em `tasks.py`, e o prompt do LLM que referencia "student code" refletem essa premissa.

A mudança proposta desacopla formato de submissão e modo de correção, permitindo que exercícios aceitem arquivos (PDF, XLSX, imagens) e que a correção aconteça exclusivamente via LLM com rubrica estruturada, sem sandbox. Isso exige intervenção em quatro camadas: modelo de dados, pipeline de processamento (Celery tasks), API (routers + schemas), e frontend.

O backend já tem config via Pydantic Settings com `max_submission_file_size_mb` definido (1MB default), o que indica que upload de arquivo já estava previsto como extensão. O router de submissions já aceita `UploadFile` via multipart, mas hoje converte o arquivo em texto de código Python.

## Goals / Non-Goals

**Goals:**

- Permitir que exercícios definam `submission_type` (code ou file-upload) e `grading_mode` (test-first ou llm-first) de forma independente.
- Implementar upload de arquivos com armazenamento em disco local e referência por path no banco.
- Criar pipeline LLM-first que avalia submissões contra rubrica definida pelo professor, gerando nota por dimensão e feedback consolidado.
- Manter o pipeline test-first inalterado para exercícios existentes (backward compatible).
- Expor no frontend a seleção de tipo de submissão, editor de rubrica, componente de upload, e visualização de nota por dimensão.

**Non-Goals:**

- Object storage (S3/GCS) nesta fase. O design permite migração futura, mas não implementa.
- Validação programática de planilhas no modo test-first (a arquitetura não impede, mas está fora do escopo).
- Chunking de documentos longos para múltiplas chamadas LLM. A primeira versão assume que o conteúdo extraído cabe em uma chamada. Se não couber, trunca com aviso.
- Suporte a outros formatos além de PDF, XLSX e imagens (PNG, JPG).
- Anti-plágio ou detecção de similaridade entre submissões.

## Decisions

### 1. Dois enums no model Exercise, sem herança de tipo

Adicionar `submission_type` (enum: `code`, `file_upload`) e `grading_mode` (enum: `test_first`, `llm_first`) como colunas em `exercises`. Defaults: `code` e `test_first`, preservando o comportamento atual para exercícios existentes.

Alternativa descartada: criar subclasses de Exercise via Single Table Inheritance (STI). A combinação de dois eixos ortogonais com STI geraria quatro subclasses para duas flags. A complexidade no ORM e nas queries não compensa quando o que muda é fluxo de processamento, não estrutura de dados.

Alternativa descartada: tabela separada `exercise_config`. Fragmentaria a configuração do exercício em dois lugares sem ganho de normalização, já que cada exercício tem exatamente uma configuração.

### 2. Armazenamento de arquivos em disco local com path relativo no banco

Novo campo `file_path` (nullable) em `Submission`, armazenando path relativo ao `UPLOAD_BASE_DIR` (nova variável de config, default `./uploads`). Estrutura: `{exercise_id}/{submission_id}/{filename_original}`. O `content_hash` (renomeação de `code_hash`) é calculado como SHA256 do conteúdo do arquivo, mantendo a semântica de cache.

O `UPLOAD_BASE_DIR` em produção aponta para um volume montado no Docker. O path relativo no banco permite trocar o backend de storage depois sem migração de dados: basta implementar um resolver que traduz path relativo para URL assinada de S3.

Novos campos em `Submission`: `file_path` (String, nullable), `file_name` (String, nullable), `file_size` (Integer, nullable), `content_type` (String, nullable). O campo `code` passa a nullable. O campo `code_hash` é renomeado para `content_hash` na migration (mantém o índice para cache de LLM).

Alternativa descartada: armazenar arquivo como blob no PostgreSQL. Funciona para arquivos pequenos mas degrada backup, replication e queries de listagem. Disco local com referência no banco é o padrão pragmático para volume baixo.

### 3. Extração de conteúdo como etapa isolada no pipeline

Uma função `extract_content(file_path, content_type) -> str` converte o artefato em texto antes de montar o prompt para o LLM. Implementações por tipo:

- **PDF**: `pdfplumber` (melhor que pymupdf para tabelas e layout estruturado). Extrai texto página a página, preservando tabelas como texto formatado.
- **XLSX**: `openpyxl`. Serializa cada sheet como tabela markdown (cabeçalhos + linhas).
- **Imagens** (PNG, JPG): não extrai texto. Passa o arquivo diretamente como input multimodal para o LLM (Claude vision ou GPT-4V). O prompt recebe a imagem como attachment em vez de texto extraído.

A separação da extração permite testar e cachear o conteúdo extraído independentemente da chamada ao LLM. Se o mesmo arquivo for resubmetido (mesmo `content_hash`), o texto extraído já existe.

Alternativa descartada: usar OCR (Tesseract) para imagens em vez de vision model. OCR perde contexto de diagramas, gráficos e formatação que o vision model captura nativamente. Para o caso de uso (avaliação de trabalhos acadêmicos), o vision model é mais adequado.

### 4. Nova task Celery `grade_llm_first` separada de `execute_submission`

O pipeline LLM-first não tem sandbox, não tem Docker, não tem test harness. Compartilhar a task existente adicionaria branches condicionais em código que já tem complexidade considerável (tratamento de timeout, container lifecycle, parsing de JSON de resultados).

A nova task `grade_llm_first(submission_id)`:
1. Carrega submission + exercise + rubric dimensions do banco.
2. Se `submission_type == file_upload`: chama `extract_content()` para obter texto. Se imagem: prepara input multimodal.
3. Se `submission_type == code`: usa o campo `code` diretamente (cenário de exercício de código com `grading_mode == llm_first`).
4. Monta prompt com: descrição do exercício, dimensões da rubrica com pesos, conteúdo extraído.
5. Chama LLM (Anthropic ou OpenAI, conforme `settings.llm_provider`).
6. Faz parse da resposta JSON estruturada: `{ dimensions: [{ name, score, feedback }], overall_feedback }`.
7. Persiste `RubricScore` por dimensão e calcula `final_score` como média ponderada.
8. Cria `Grade` e marca submission como `COMPLETED`.

Cache: antes do passo 5, verifica se já existe `LLMEvaluation` com mesmo `content_hash` E mesmo `exercise_id` (importante: o hash sozinho não basta, porque a rubrica pode mudar entre exercícios). Se cache hit, copia scores e pula a chamada.

O dispatcher no router decide qual task enfileirar baseado no `grading_mode` do exercício: `execute_submission.delay()` para test-first, `grade_llm_first.delay()` para llm-first.

### 5. Modelo de rubrica: duas tabelas novas

`RubricDimension`: (id, exercise_id, name, description, weight, position). O professor define dimensões ao criar o exercício com `grading_mode == llm_first`. Validação: soma dos weights deve ser 1.0 (mesma lógica que `test_weight + llm_weight` já existente).

`RubricScore`: (id, submission_id, dimension_id, score 0-100, feedback). Uma linha por dimensão por submissão. O `final_score` na tabela `Grade` é calculado como `sum(dimension.weight * rubric_score.score)`.

A relação `Exercise -> RubricDimension` é 1:N. A relação `Submission -> RubricScore` é 1:N (via dimension). `RubricScore` tem FK para `RubricDimension` e para `Submission`, com unique constraint em `(submission_id, dimension_id)`.

### 6. Endpoint de submissão: bifurcação por submission_type

O endpoint `POST /submissions` já aceita multipart/form-data. A mudança:

- Se `submission_type == code`: valida Python syntax (comportamento atual), calcula `content_hash` sobre o código, salva `code` no banco.
- Se `submission_type == file_upload`: valida extensão (pdf, xlsx, png, jpg), valida tamanho (`max_submission_file_size_mb`), salva arquivo em disco, calcula `content_hash` sobre o binário, salva metadados de arquivo no banco, `code` fica NULL.

A validação de sintaxe Python só acontece quando `submission_type == code`. Hoje ela é incondicional e bloquearia uploads de arquivo.

### 7. Prompt engineering para rubrica

O prompt segue uma estrutura fixa que o LLM preenche:

```
Você está avaliando uma submissão de aluno.

**Exercício:** {title}
**Descrição:** {description}

**Rubrica de avaliação:**
{for dim in dimensions}
- {dim.name} (peso: {dim.weight}): {dim.description}
{endfor}

**Submissão do aluno:**
{extracted_content ou code}

Avalie a submissão em cada dimensão da rubrica.
Responda SOMENTE com JSON no formato:
{
  "dimensions": [
    {"name": "...", "score": 0-100, "feedback": "..."},
    ...
  ],
  "overall_feedback": "..."
}
```

Para imagens, o conteúdo vai como attachment multimodal e o prompt referencia "a imagem anexada" em vez de texto.

O modelo default para LLM-first é o mesmo configurado em `settings.llm_provider`. A escolha de modelo mais barato para triagem (mencionada no proposal) fica como otimização futura, não no escopo desta implementação.

## Risks / Trade-offs

**Custo de LLM por submissão** → Cache por `(content_hash, exercise_id)`. Rate limiting existente por aluno se aplica. Para a primeira versão, o professor precisa estar ciente de que cada submissão gera uma chamada. Monitoramento de custo pode ser adicionado depois via contagem de tokens nas LLMEvaluation.

**Qualidade da extração de PDF/XLSX** → PDFs com layout complexo (duas colunas, tabelas aninhadas) podem perder estrutura na extração por `pdfplumber`. Mitigação: para esses casos, o professor pode configurar `submission_type == file_upload` com imagem, que vai direto para vision model sem extração de texto. Documentar a limitação na UI.

**Parsing do JSON estruturado do LLM** → O LLM pode retornar JSON malformado ou com dimensões que não correspondem à rubrica. Mitigação: validação strict do response (verificar que todos os nomes de dimensão existem, scores estão em 0-100). Em caso de falha de parsing, retry com prompt corrigido (1 tentativa). Se falhar de novo, marca submission como FAILED com mensagem de erro interna (não expõe ao aluno).

**Migration breaking: `code` e `code_hash` passam a nullable** → Exercícios existentes não são afetados porque todos têm `submission_type == code` (default). A migration precisa:
1. Adicionar novos campos com default/nullable.
2. Renomear `code_hash` para `content_hash` (preservar índice).
3. Alterar `code` para nullable.
4. Preencher `submission_type` e `grading_mode` com defaults para exercícios existentes.
Rollback: reverter a migration restaura NOT NULL em `code` (seguro porque nenhuma linha terá NULL nesse ponto).

**Tamanho do conteúdo extraído vs. context window do LLM** → Um PDF de 50 páginas pode gerar texto que excede o context window. Na primeira versão, truncar a 50k caracteres com warning no feedback ("Avaliação parcial: conteúdo truncado"). Otimização futura: chunking + múltiplas chamadas + aggregation de scores.

## Open Questions

- Limite de tamanho de arquivo para upload. O config atual tem `max_submission_file_size_mb = 1`. Para PDFs e planilhas acadêmicas, 5-10MB parece mais razoável. Precisa de input do professor sobre o que é típico.
- O professor deve poder editar a rubrica depois que já existem submissões avaliadas? Se sim, as notas antigas ficam com a rubrica anterior (snapshot) ou são reavaliadas? Sugestão: rubrica é imutável após a primeira submissão. Se o professor quiser mudar, cria um novo exercício.
