## Why

O autograder foi construído em torno de exercícios de programação: o aluno submete código, que roda em sandbox, passa por testes automatizados e opcionalmente recebe feedback de LLM. Isso cobre bem disciplinas de computação, mas exclui disciplinas como Álgebra Linear, Machine Learning e Data Analytics, onde os exercícios são resoluções matemáticas, relatórios analíticos e planilhas com resultados. Essas disciplinas já estão sendo ministradas e precisam do mesmo fluxo de submissão e correção, sem que o professor precise de outra ferramenta.

## What Changes

A mudança separa dois conceitos que hoje estão acoplados: **formato de submissão** e **modo de correção**.

**Formato de submissão** (`submission_type`): determina o que o aluno envia.
- `code`: texto de código, como funciona hoje.
- `file-upload`: arquivo (PDF, XLSX, imagem). O aluno faz upload em vez de colar código.

**Modo de correção** (`grading_mode`): determina como a nota é calculada. Configurado por exercício, independente do formato.
- `test-first`: testes automatizados são o validador principal. LLM é opcional e complementar (comportamento atual).
- `llm-first`: LLM é o avaliador principal, usando rubrica definida pelo professor. Sem sandbox, sem test harness.

Os dois eixos são ortogonais. Um exercício de código pode usar `llm-first` quando o que importa é qualidade da solução e não se passa em testes específicos. Uma planilha pode ter validações programáticas no modo `test-first` no futuro (fora do escopo agora, mas a arquitetura não impede).

**Demais mudanças:**
- Submissões passam a aceitar **upload de arquivos**. Os arquivos são armazenados em disco local (com caminho para migração futura para object storage) e referenciados por path na tabela de submissions.
- Um novo **pipeline de correção LLM-first** processa submissões: extrai conteúdo do artefato (texto de PDF, dados de planilha, imagem via vision model), monta o prompt com a rubrica do professor, chama o LLM e persiste feedback + nota.
- O modelo de **rubrica** permite ao professor definir dimensões de avaliação com pesos (ex: "Corretude matemática: 40%, Clareza da explicação: 30%, Apresentação dos resultados: 30%"), que o LLM usa para estruturar a avaliação e retornar nota por dimensão.
- O frontend ganha um componente de **upload de arquivo** na tela de submissão (condicionado ao `submission_type`) e o formulário de criação de exercício expõe seletor de `grading_mode` e editor de rubrica.
- **BREAKING**: O campo `code` em `Submission` passa a ser nullable, já que submissões de arquivo não têm código. A coluna `code_hash` também passa a ser nullable (o hash será calculado sobre o arquivo quando aplicável).

## Capabilities

### New Capabilities
- `file-submission`: Upload, armazenamento e referência de arquivos submetidos por alunos (PDF, XLSX, imagens). Inclui validação de formato, limite de tamanho e extração de conteúdo para processamento pelo LLM.
- `rubric-grading`: Definição de rubrica estruturada por exercício (dimensões + pesos) e pipeline de correção LLM-first que avalia o artefato submetido contra a rubrica, gerando nota por dimensão e feedback consolidado. Ativado quando o exercício usa `grading_mode = llm-first`.

### Modified Capabilities
- `exercise`: Adição dos campos `submission_type` e `grading_mode`. Campos existentes (`template_code`, `language`, `timeout_seconds`, `test_cases`) continuam válidos para exercícios com `submission_type = code` e `grading_mode = test-first`. Exercícios com `grading_mode = llm-first` usam rubrica em vez de test cases.
- `submission`: Campo `code` passa a nullable, adição de referência a arquivo (`file_path`, `file_name`, `file_size`, `content_type`), suporte a submissão de arquivo via multipart upload.

## Impact

**Backend:**
- Models: `Exercise` (novos campos `submission_type`, `grading_mode`, relação com rubrica), `Submission` (nullable `code`, campos de arquivo), nova tabela `RubricDimension`, nova tabela `RubricScore` (nota por dimensão por submission).
- Tasks: Nova task Celery `grade_with_llm` para o pipeline LLM-first (extração de conteúdo + prompt com rubrica + chamada LLM + parsing de notas por dimensão). A task existente `execute_submission` continua inalterada para `grading_mode = test-first`.
- Routers: Endpoint de submissão precisa aceitar multipart/form-data quando `submission_type = file-upload`. Endpoint de criação de exercício precisa dos novos campos.
- Dependências: `pymupdf` ou `pdfplumber` para extração de texto de PDF, `openpyxl` para planilhas. Para imagens, o LLM vision (Claude ou GPT-4V) processa direto.
- Storage: Diretório local configurável para arquivos, com path persistido no banco.

**Frontend:**
- Tela de submissão: componente de upload de arquivo quando `submission_type == "file-upload"`, editor de código quando `submission_type == "code"`.
- Tela de criação de exercício: seletor de `submission_type`, seletor de `grading_mode`, formulário de rubrica com dimensões e pesos (visível quando `grading_mode == "llm-first"`).
- Tela de visualização de grade: quando `grading_mode == "llm-first"`, exibir nota por dimensão da rubrica além da nota final.

**Migrations:**
- Alterar tabela `exercises` (novos campos `submission_type`, `grading_mode`).
- Alterar tabela `submissions` (nullable `code` e `code_hash`, novos campos de arquivo).
- Nova tabela `rubric_dimensions` (exercise_id, name, weight, description).
- Nova tabela `rubric_scores` (submission_id, dimension_id, score, feedback).

**Risco principal:** Custo de LLM por submissão. No modo `llm-first`, cada submissão gera pelo menos uma chamada de LLM (duas se o artefato for grande e precisar de chunking). Mitigações: cache por hash de arquivo, rate limiting por aluno, modelo mais barato (Haiku/GPT-4o-mini) para primeira passada com escalation para modelo melhor quando a nota está na fronteira.
