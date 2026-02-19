"""
Tests for ManyChat tag sync: _update_scd2, _apply_manychat_tags, admin endpoint.
"""
import datetime
from unittest.mock import MagicMock, patch, call
import pytest
from fastapi.testclient import TestClient

from main import app
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user():
    u = User()
    u.id = 1
    u.email = "admin@test.com"
    u.role = UserRole.ADMIN
    return u


@pytest.fixture
def client(admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_role(UserRole.ADMIN)] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# _update_scd2
# ---------------------------------------------------------------------------

class TestUpdateScd2:
    def _make_db(self):
        db = MagicMock()
        db.query.return_value = db
        db.filter.return_value = db
        db.first.return_value = None
        return db

    def test_initial_insert(self):
        from app.tasks import _update_scd2
        db = self._make_db()
        db.first.return_value = None  # no existing row

        result = _update_scd2(user_id=1, product_id=2, new_status="Ativo",
                               source="test", db=db)

        assert result is True
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert added.status == "Ativo"
        assert added.is_current is True
        assert added.valid_to is None

    def test_noop_same_status(self):
        from app.tasks import _update_scd2
        from app.models.student_course_status import StudentCourseStatus

        db = self._make_db()
        existing = StudentCourseStatus()
        existing.status = "Ativo"
        existing.is_current = True
        db.first.return_value = existing

        result = _update_scd2(user_id=1, product_id=2, new_status="Ativo",
                               source="test", db=db)

        assert result is False
        db.add.assert_not_called()

    def test_status_change_closes_old_row(self):
        from app.tasks import _update_scd2
        from app.models.student_course_status import StudentCourseStatus

        db = self._make_db()
        existing = StudentCourseStatus()
        existing.status = "Ativo"
        existing.is_current = True
        existing.valid_to = None
        db.first.return_value = existing

        result = _update_scd2(user_id=1, product_id=2, new_status="Cancelado",
                               source="test", db=db)

        assert result is True
        assert existing.is_current is False
        assert existing.valid_to is not None
        db.add.assert_called_once()
        new_row = db.add.call_args[0][0]
        assert new_row.status == "Cancelado"
        assert new_row.is_current is True


# ---------------------------------------------------------------------------
# _apply_manychat_tags
# ---------------------------------------------------------------------------

class TestApplyManychatTags:
    def test_removes_all_statuses_then_adds(self):
        from app.tasks import _apply_manychat_tags, _MANYCHAT_STATUSES

        with patch("app.integrations.manychat.remove_tag") as mock_remove, \
             patch("app.integrations.manychat.add_tag") as mock_add:
            _apply_manychat_tags("sub123", "Senhor das LLMs", "Ativo")

        # Should remove all possible status tags
        remove_calls = [c[0] for c in mock_remove.call_args_list]
        for status in _MANYCHAT_STATUSES:
            assert ("sub123", f"Senhor das LLMs, {status}") in remove_calls

        # Should add course tag + current status tag
        add_calls = [c[0] for c in mock_add.call_args_list]
        assert ("sub123", "Senhor das LLMs") in add_calls
        assert ("sub123", "Senhor das LLMs, Ativo") in add_calls

    def test_brute_force_regardless_of_current(self):
        from app.tasks import _apply_manychat_tags, _MANYCHAT_STATUSES

        with patch("app.integrations.manychat.remove_tag") as mock_remove, \
             patch("app.integrations.manychat.add_tag"):
            _apply_manychat_tags("sub123", "De analista a CDO", "Cancelado")

        # All 4 status tags should be removed (even those not current)
        assert mock_remove.call_count == len(_MANYCHAT_STATUSES)


# ---------------------------------------------------------------------------
# Admin endpoint
# ---------------------------------------------------------------------------

class TestManychatSyncEndpoint:
    def test_enqueue_without_product(self, client):
        with patch("app.tasks.sync_manychat_tags") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "task-abc-123"
            mock_task.delay.return_value = mock_result

            resp = client.post("/admin/events/manychat-sync")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc-123"
        assert "enqueued" in data["message"].lower()
        mock_task.delay.assert_called_once_with(None)

    def test_enqueue_with_product_id(self, client):
        with patch("app.tasks.sync_manychat_tags") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "task-xyz"
            mock_task.delay.return_value = mock_result

            resp = client.post("/admin/events/manychat-sync",
                               json={"product_id": 42})

        assert resp.status_code == 200
        mock_task.delay.assert_called_once_with(42)
