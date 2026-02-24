"""Tests for admin student listing and sync endpoints."""
import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, LifecycleStatus


def _make_student(id, email, discord_id=None, whatsapp=None, lifecycle_status=None):
    user = Mock(spec=User)
    user.id = id
    user.email = email
    user.role = UserRole.STUDENT
    user.discord_id = discord_id
    user.whatsapp_number = whatsapp
    user.lifecycle_status = lifecycle_status
    return user


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
        students = [
            _make_student(1, "alice@test.com", discord_id="123", whatsapp="+5511999"),
            _make_student(2, "bob@test.com"),
        ]

        mock_db = MagicMock()

        # Main query chain: filter(role=student) → count/order_by/offset/limit
        student_query = MagicMock()
        student_query.count.return_value = 2
        student_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = students

        # Subqueries for status/product filters won't be called
        mock_db.query.return_value.filter.return_value = student_query

        # Course statuses query: empty
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []

        # HotmartBuyer names: empty
        # Override the second query().filter() call to return empty list
        # This is tricky with MagicMock chains, so we use side_effect

        call_count = {"n": 0}
        original_query = mock_db.query

        def query_side_effect(*args):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # User query
                result.filter.return_value = student_query
            elif call_count["n"] == 2:
                # StudentCourseStatus + Product join
                result.join.return_value.filter.return_value.all.return_value = []
            elif call_count["n"] == 3:
                # HotmartBuyer names
                result.filter.return_value.all.return_value = []
            return result

        mock_db.query.side_effect = query_side_effect

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

        student_query = MagicMock()
        student_query.count.return_value = 0
        student_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        mock_db.query.return_value.filter.return_value = student_query

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

        student_query = MagicMock()
        student_query.count.return_value = 100
        student_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        mock_db.query.return_value.filter.return_value = student_query

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
