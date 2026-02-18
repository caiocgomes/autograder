## Why

Professores de cursos técnicos (ML, data science, programação) precisam avaliar submissões de código de forma escalável e consistente. Avaliação manual não escala além de 20-30 alunos e gera feedback inconsistente. Sistemas LMS tradicionais não suportam execução sandboxed de código nem avaliação qualitativa automatizada via LLM.

## What Changes

- Gestão completa de usuários com três perfis: Admin/Professor, Aluno, e Monitor/TA
- Sistema de autenticação com email/senha, recuperação de senha, e proteção contra brute force
- Criação e gestão de turmas com atribuição de alunos (manual, convite, ou importação CSV)
- Suporte a grupos dentro de turmas para atribuir listas diferentes
- Criação de exercícios com enunciado Markdown/LaTeX, datasets auxiliares, e template de código
- Configuração de avaliação por testes automatizados (unit tests) e/ou LLM qualitativo
- Submissão de código via upload ou editor in-browser
- Execução sandboxed em containers Docker com fila assíncrona
- Feedback detalhado por submissão: resultado de testes, score parcial, feedback LLM, e nota final

## Capabilities

### New Capabilities

- `user-authentication`: Sistema de autenticação e autorização com perfis de acesso (Admin/Professor, Aluno, Monitor), cadastro, login, recuperação de senha, e rate limiting
- `class-management`: Gestão de turmas, atribuição de alunos, criação de grupos dentro de turmas, e arquivamento
- `exercise-creation`: Criação e edição de exercícios com enunciado rico (Markdown/LaTeX), upload de datasets, template de código, e configuração de avaliação (testes + LLM)
- `exercise-lists`: Agrupamento de exercícios em listas, atribuição a turmas/grupos, e controle de datas de abertura/fechamento
- `code-submission`: Submissão de código via upload ou editor in-browser, validação básica, e histórico de submissões
- `sandboxed-execution`: Execução de código em containers Docker isolados com fila assíncrona, timeout configurável, e logs acessíveis
- `automated-grading`: Avaliação automática via testes unitários (casos de teste) e análise qualitativa via LLM, com score parcial e feedback detalhado

### Modified Capabilities

<!-- No existing capabilities to modify - this is the initial implementation -->

## Impact

**New Components:**
- Backend API (FastAPI) para gerenciar usuários, turmas, exercícios, submissões
- Database schema para users, classes, exercises, submissions, grades
- Docker-based sandbox execution service
- Async task queue (Celery + Redis ou similar) para execução de código
- LLM integration service para avaliação qualitativa

**Infrastructure:**
- Docker compose setup para dev environment
- Database migrations system
- Container orchestration para sandboxed execution
- Redis/queue service para async tasks

**Frontend (autograder-web):**
- Telas de login, cadastro, recuperação de senha
- Dashboard professor: criação de turmas, exercícios, listas
- Dashboard aluno: visualização de exercícios, submissão de código, feedback
- Editor de código in-browser com syntax highlighting
