import pytest
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_anthropic_client():
    mock = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="VALID: true\nFEEDBACK: Code looks good")]
    mock.messages.create.return_value = mock_response
    return mock


@pytest.fixture
def mock_docker_client():
    mock = MagicMock()
    container = MagicMock()
    container.wait.return_value = {"StatusCode": 0}
    container.logs.return_value = b"3"
    mock.containers.run.return_value = container
    return mock


@pytest.fixture
def sample_code():
    return "def add(a, b):\n    return a + b"


@pytest.fixture
def sample_requirements():
    return "Write a function that adds two numbers"


@pytest.fixture
def sample_test_cases():
    return [
        {"input": "add(1, 2)", "expected": "3"},
        {"input": "add(-1, 1)", "expected": "0"},
    ]
