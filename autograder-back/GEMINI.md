# Autograder Backend

## Project Overview

This project is a Python backend API designed for grading Python code submissions. It leverages FastAPI for the API interface, an LLM (Anthropic Claude) for code validation, and Docker containers for secure sandboxed execution of user-submitted code against predefined test cases.

The core functionality involves:
1.  Receiving Python code and requirements via an API endpoint.
2.  Validating the code against requirements using an LLM to provide feedback.
3.  Executing the validated code within an isolated Docker sandbox environment.
4.  Running provided test cases against the executed code.
5.  Returning detailed results including LLM validation status, test outcomes, and a final score.

## Key Technologies

*   **Backend Framework:** FastAPI
*   **Web Server:** Uvicorn
*   **Language:** Python 3.11+
*   **LLM Integration:** Anthropic Claude API (via `anthropic` library)
*   **Sandboxing:** Docker (for isolated code execution)
*   **Dependency Management:** `uv` (inferred from `uv.lock` and general Python best practices)

## Architecture

The application is structured as follows:
*   `main.py`: The main FastAPI application entry point, defining API routes (`/health`, `/grade`).
*   `services/grader.py`: Orchestrates the grading process, integrating LLM validation and sandbox execution.
*   `services/llm_validator.py`: Handles interaction with the Anthropic Claude API for code validation and feedback.
*   `services/sandbox.py`: Manages Docker containers for safe and isolated execution of submitted code.
*   `Dockerfile.sandbox`: Defines the Docker image used for the sandbox environment.
*   `tests/`: Contains `pytest` tests for the API endpoints and service logic.

## Building and Running

### Prerequisites

*   Python 3.11+
*   Docker Desktop or Docker Engine installed and running
*   An Anthropic API key, set as the `ANTHROPIC_API_KEY` environment variable.

### Setup

1.  **Install `uv` (if not already installed):**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

3.  **Build the Docker sandbox image:**
    The `services/sandbox.py` relies on a custom Docker image.
    ```bash
    docker build -f Dockerfile.sandbox -t autograder-sandbox .
    ```

### Running the API

To start the FastAPI application:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://0.0.0.0:8000`. You can access the interactive API documentation at `http://0.0.0.0:8000/docs`.

### Running Tests

To run the unit and integration tests:

```bash
uv run pytest
```

## Development Conventions

*   **LLM API Key:** Ensure the `ANTHROPIC_API_KEY` environment variable is set for LLM validation functionality.
*   **Testing:** New features and bug fixes should include corresponding `pytest` tests.
*   **Code Style:** Follow standard Python coding conventions (e.g., PEP 8).

