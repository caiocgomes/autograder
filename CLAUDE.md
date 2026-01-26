# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Autograder is a monorepo with two components:
- **autograder-back**: Python FastAPI backend for automated code grading
- **autograder-web**: React + TypeScript + Vite frontend

## Commands

### Backend (autograder-back/)

```bash
uv sync --all-extras                                    # Install dependencies
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000  # Start API
uv run pytest                                           # Run tests
uv run pytest tests/test_grader.py -k "test_name"       # Run single test
docker build -f Dockerfile.sandbox -t autograder-sandbox .  # Build sandbox image
```

### Frontend (autograder-web/)

```bash
npm install          # Install dependencies
npm run dev          # Start Vite dev server
npm run build        # TypeScript + Vite production build
npm run lint         # ESLint check
```

## Architecture

### Backend Grading Flow

1. `POST /grade` receives code, requirements, and test cases
2. `services/llm_validator.py` uses Claude Sonnet 4 to validate syntax and alignment with requirements
3. If valid, `services/sandbox.py` executes test cases in Docker container (30s timeout, 256MB RAM, no network, read-only fs)
4. `services/grader.py` orchestrates the flow and returns score, LLM feedback, and test results

### Frontend Structure

- `src/App.tsx` - Main component with form state management
- `src/api/grader.ts` - HTTP client for `/grade` endpoint (uses `VITE_API_URL` env var)
- `src/components/` - CodeEditor, TestCases, Results components

## Configuration

### Backend
- Python 3.11+
- Docker daemon must be running
- `ANTHROPIC_API_KEY` environment variable required
- Package manager: [uv](https://github.com/astral-sh/uv)

### Frontend
- Node.js with npm
- `VITE_API_URL` to override API endpoint (defaults to relative `/grade`)

## API Endpoints

- `GET /health` - Health check
- `POST /grade` - Submit code for grading

### Grade Request Example

```json
{
  "code": "def add(a, b):\n    return a + b",
  "requirements": "Write a function that adds two numbers",
  "test_cases": [
    {"input": "add(1, 2)", "expected": "3"},
    {"input": "add(-1, 1)", "expected": "0"}
  ]
}
```
