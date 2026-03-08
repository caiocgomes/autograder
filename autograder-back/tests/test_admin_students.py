"""Tests for admin student listing and sync endpoints."""
import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.hotmart_buyer import HotmartBuyer


def _make_buyer(email, name=None, phone=None, hotmart_product_id="PROD1", status="Ativo"):
    buyer = Mock(spec=HotmartBuyer)
    buyer.email = email
    buyer.name = name
    buyer.phone = phone
    buyer.hotmart_product_id = hotmart_product_id
    buyer.status = status
    return buyer


def _make_user(id, email, discord_id=None):
    user = Mock(spec=User)
    user.id = id
    user.email = email
    user.discord_id = discord_id
    return user


def _setup_list_mock(mock_db, products, email_rows, total, buyers, users):
    """Configure mock_db for the list_students endpoint query chain."""
    call_count = {"n": 0}

    def query_side_effect(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            # db.query(Product).all() → product lookup
            result.all.return_value = products
        elif call_count["n"] == 2:
            # db.query(HotmartBuyer) → main buyer query chain
            emails_query = MagicMock()
            emails_query.count.return_value = total
            emails_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
                (e,) for e in email_rows
            ]
            result.filter.return_value = result  # status/product filters chain back
            result.with_entities.return_value.distinct.return_value = emails_query
        elif call_count["n"] == 3:
            # db.query(HotmartBuyer).filter(email.in_(...)).all() → batch load buyers
            result.filter.return_value.all.return_value = buyers
        elif call_count["n"] == 4:
            # db.query(User).filter(email.in_(...)).all() → load users
            result.filter.return_value.all.return_value = users
        return result

    mock_db.query.side_effect = query_side_effect


@pytest.fixture
def admin_user():
    user = Mock(spec=User)
    user.id = 99
    user.email = "admin@test.com"
    user.role = UserRole.ADMIN
    return user


@pytest.fixture
def student_user():
    user = Mock(spec=User)
    user.id = 2
    user.email = "student@test.com"
    user.role = UserRole.STUDENT
    return user


# ---------------------------------------------------------------------------
# Listing endpoint tests
# ---------------------------------------------------------------------------

class TestListStudents:
    def test_list_students_no_filters(self, admin_user):
        """Basic listing returns students with aggregated data."""
        product = Mock(spec=Product)
        product.hotmart_product_id = "PROD1"
        product.name = "Curso Python"

        buyers = [
            _make_buyer("alice@test.com", name="Alice", phone="+5511999", hotmart_product_id="PROD1"),
            _make_buyer("bob@test.com", name="Bob", hotmart_product_id="PROD1"),
        ]
        users = [
            _make_user(1, "alice@test.com", discord_id="123"),
        ]

        mock_db = MagicMock()
        _setup_list_mock(
            mock_db,
            products=[product],
            email_rows=["alice@test.com", "bob@test.com"],
            total=2,
            buyers=buyers,
            users=users,
        )

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        client = TestClient(app)

        response = client.get("/admin/students")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["email"] == "alice@test.com"
        assert data["items"][0]["discord_connected"] is True
        assert data["items"][0]["has_whatsapp"] is True
        assert data["items"][1]["email"] == "bob@test.com"
        assert data["items"][1]["discord_connected"] is False
        assert data["items"][1]["has_whatsapp"] is False

        app.dependency_overrides.clear()

    def test_list_students_non_admin_denied(self, student_user):
        """Non-admin users get 403."""
        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: student_user
        client = TestClient(app)

        response = client.get("/admin/students")
        assert response.status_code == 403

        app.dependency_overrides.clear()

    def test_list_students_empty(self, admin_user):
        """Empty result returns empty items and total=0."""
        mock_db = MagicMock()
        _setup_list_mock(
            mock_db,
            products=[],
            email_rows=[],
            total=0,
            buyers=[],
            users=[],
        )

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        client = TestClient(app)

        response = client.get("/admin/students")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

        app.dependency_overrides.clear()

    def test_list_students_pagination(self, admin_user):
        """Pagination params are passed through."""
        mock_db = MagicMock()
        _setup_list_mock(
            mock_db,
            products=[],
            email_rows=[],
            total=100,
            buyers=[],
            users=[],
        )

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        client = TestClient(app)

        response = client.get("/admin/students?limit=10&offset=20")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 100

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sync endpoint tests
# ---------------------------------------------------------------------------

class TestSyncEndpoints:
    @patch("app.redis_client.get_redis_client")
    def test_trigger_sync_success(self, mock_redis_fn, admin_user):
        """POST /admin/students/sync enqueues task and returns task_id."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # no lock
        mock_redis_fn.return_value = mock_redis

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        client = TestClient(app)

        with patch("app.tasks.sync_students_full") as mock_task:
            mock_task.delay.return_value = Mock(id="task-123")
            response = client.post("/admin/students/sync")

        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "task-123"

        app.dependency_overrides.clear()

    @patch("app.redis_client.get_redis_client")
    def test_trigger_sync_already_running(self, mock_redis_fn, admin_user):
        """POST /admin/students/sync returns 409 when lock exists."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = "existing-task"  # lock held
        mock_redis_fn.return_value = mock_redis

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        client = TestClient(app)

        response = client.post("/admin/students/sync")
        assert response.status_code == 409

        app.dependency_overrides.clear()

    @patch("app.redis_client.get_redis_client")
    def test_poll_sync_completed(self, mock_redis_fn, admin_user):
        """GET /admin/students/sync/{task_id} returns completed result."""
        result_data = {
            "status": "completed",
            "started_at": "2026-02-23T10:00:00+00:00",
            "completed_at": "2026-02-23T10:02:30+00:00",
            "summary": {
                "total_processed": 50,
                "new_students": 3,
                "status_changes": {
                    "to_ativo": 1,
                    "to_inadimplente": 1,
                    "to_cancelado": 1,
                    "to_reembolsado": 0,
                },
                "errors": 0,
            },
        }
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(result_data)
        mock_redis_fn.return_value = mock_redis

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        client = TestClient(app)

        response = client.get("/admin/students/sync/task-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["summary"]["new_students"] == 3

        app.dependency_overrides.clear()

    @patch("app.redis_client.get_redis_client")
    def test_poll_sync_running(self, mock_redis_fn, admin_user):
        """GET /admin/students/sync/{task_id} returns running status."""
        result_data = {
            "status": "running",
            "started_at": "2026-02-23T10:00:00+00:00",
        }
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(result_data)
        mock_redis_fn.return_value = mock_redis

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        client = TestClient(app)

        response = client.get("/admin/students/sync/task-123")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

        app.dependency_overrides.clear()

    @patch("app.redis_client.get_redis_client")
    def test_poll_sync_not_found(self, mock_redis_fn, admin_user):
        """GET /admin/students/sync/{task_id} returns 404 for unknown task."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis_fn.return_value = mock_redis

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        client = TestClient(app)

        response = client.get("/admin/students/sync/nonexistent")
        assert response.status_code == 404

        app.dependency_overrides.clear()
