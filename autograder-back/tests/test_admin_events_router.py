"""Integration tests for /admin/events endpoints (app/routers/admin_events.py)"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from app.models.event import Event, EventStatus


def _mock_event(id=1, status=EventStatus.PROCESSED, event_type="lifecycle.transition", target_id=None):
    ev = Mock(spec=Event)
    ev.id = id
    ev.type = event_type
    ev.status = status
    ev.target_id = target_id
    ev.actor_id = None
    ev.payload = {}
    ev.error_message = None
    ev.created_at = datetime(2024, 1, 1, 0, 0, 0)
    return ev


class TestListEvents:
    def test_admin_gets_event_list_returns_200(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        events = [_mock_event(id=1), _mock_event(id=2)]
        mock_db.query.return_value.count.return_value = 2
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = events

        response = client.get("/admin/events")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_non_admin_cannot_list_events(self, client_with_student):
        client, mock_db, student = client_with_student

        response = client.get("/admin/events")

        assert response.status_code == 403

    def test_professor_cannot_list_events(self, client_with_professor):
        client, mock_db, professor = client_with_professor

        response = client.get("/admin/events")

        assert response.status_code == 403

    def test_filter_by_status_failed(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        failed_events = [_mock_event(id=3, status=EventStatus.FAILED)]
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        (mock_db.query.return_value.filter.return_value
            .order_by.return_value.offset.return_value.limit.return_value
            .all.return_value) = failed_events

        response = client.get("/admin/events?status=failed")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_filter_by_invalid_status_returns_400(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.count.return_value = 0
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        response = client.get("/admin/events?status=not_a_real_status")

        assert response.status_code == 400

    def test_filter_by_target_id(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        events = [_mock_event(id=4, target_id=7)]
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        (mock_db.query.return_value.filter.return_value
            .order_by.return_value.offset.return_value.limit.return_value
            .all.return_value) = events

        response = client.get("/admin/events?target_id=7")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_empty_list_returns_200(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.count.return_value = 0
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        response = client.get("/admin/events")

        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestRetryEvent:
    def test_retry_failed_event_returns_200(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        failed_event = _mock_event(id=5, status=EventStatus.FAILED)
        mock_db.query.return_value.filter.return_value.first.return_value = failed_event
        mock_db.refresh = Mock()

        # The router does a local import: `from app.tasks import execute_side_effect`
        # so we patch it on the app.tasks module where it lives.
        with patch("app.tasks.execute_side_effect") as mock_task:
            mock_task.delay = Mock()
            response = client.post("/admin/events/5/retry")

        assert response.status_code == 200
        mock_task.delay.assert_called_once_with(5)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_retry_non_failed_event_returns_400(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        processed_event = _mock_event(id=6, status=EventStatus.PROCESSED)
        mock_db.query.return_value.filter.return_value.first.return_value = processed_event

        with patch("app.tasks.execute_side_effect") as mock_task:
            mock_task.delay = Mock()
            response = client.post("/admin/events/6/retry")

        assert response.status_code == 400
        mock_task.delay.assert_not_called()

    def test_retry_ignored_event_returns_400(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        ignored_event = _mock_event(id=7, status=EventStatus.IGNORED)
        mock_db.query.return_value.filter.return_value.first.return_value = ignored_event

        with patch("app.tasks.execute_side_effect") as mock_task:
            mock_task.delay = Mock()
            response = client.post("/admin/events/7/retry")

        assert response.status_code == 400

    def test_retry_nonexistent_event_returns_404(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.tasks.execute_side_effect") as mock_task:
            mock_task.delay = Mock()
            response = client.post("/admin/events/999/retry")

        assert response.status_code == 404
        mock_task.delay.assert_not_called()

    def test_retry_logs_admin_manual_retry_event(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        failed_event = _mock_event(id=8, status=EventStatus.FAILED)
        mock_db.query.return_value.filter.return_value.first.return_value = failed_event
        mock_db.refresh = Mock()

        with patch("app.tasks.execute_side_effect") as mock_task:
            mock_task.delay = Mock()
            client.post("/admin/events/8/retry")

        added_events = [call[0][0] for call in mock_db.add.call_args_list]
        retry_log = added_events[0]
        assert retry_log.type == "admin.manual_retry"
        assert retry_log.actor_id == admin.id
