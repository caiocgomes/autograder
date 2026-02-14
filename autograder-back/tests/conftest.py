import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    db.count.return_value = 0
    return db


@pytest.fixture
def mock_professor():
    """Mock professor user"""
    user = Mock(spec=User)
    user.id = 1
    user.email = "professor@test.com"
    user.role = UserRole.PROFESSOR
    user.password_hash = "$2b$12$test_hash"
    return user


@pytest.fixture
def mock_student():
    """Mock student user"""
    user = Mock(spec=User)
    user.id = 2
    user.email = "student@test.com"
    user.role = UserRole.STUDENT
    user.password_hash = "$2b$12$test_hash"
    return user


@pytest.fixture
def mock_admin():
    """Mock admin user"""
    user = Mock(spec=User)
    user.id = 3
    user.email = "admin@test.com"
    user.role = UserRole.ADMIN
    user.password_hash = "$2b$12$test_hash"
    return user


@pytest.fixture
def client_with_professor(mock_db, mock_professor):
    """TestClient with professor auth and mocked DB"""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_professor
    client = TestClient(app)
    yield client, mock_db, mock_professor
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_student(mock_db, mock_student):
    """TestClient with student auth and mocked DB"""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_student
    client = TestClient(app)
    yield client, mock_db, mock_student
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_admin(mock_db, mock_admin):
    """TestClient with admin auth and mocked DB"""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    client = TestClient(app)
    yield client, mock_db, mock_admin
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(mock_db):
    """TestClient with mocked DB but no auth"""
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client, mock_db
    app.dependency_overrides.clear()


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
