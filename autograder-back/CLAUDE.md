# Backend - Autograder API

Python FastAPI para correção automática de código.

## Commands

```bash
uv sync --all-extras                                         # Install dependencies
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000  # Start API
uv run pytest                                                # Run tests
uv run pytest tests/test_grader.py -k "test_name"            # Run single test
docker build -f Dockerfile.sandbox -t autograder-sandbox .   # Build sandbox image
```

## Architecture

### Grading Flow

1. `POST /grade` receives code, requirements, and test cases
2. `services/llm_validator.py` uses Claude Sonnet 4 to validate syntax and alignment with requirements
3. If valid, `services/sandbox.py` executes test cases in Docker container (30s timeout, 256MB RAM, no network, read-only fs)
4. `services/grader.py` orchestrates the flow and returns score, LLM feedback, and test results

### Docker Sandbox

Container isolado com:
- `network_mode: none` (sem rede)
- `read_only: true`
- `user: nobody` (non-root)
- `mem_limit: 256m`
- `timeout: 30s`

## Configuration

- Python 3.11+
- Docker daemon must be running
- `ANTHROPIC_API_KEY` environment variable required
- Package manager: [uv](https://github.com/astral-sh/uv)

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
