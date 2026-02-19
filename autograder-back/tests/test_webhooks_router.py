"""Integration tests for /webhooks/hotmart endpoint (app/routers/webhooks.py)"""
import pytest
from unittest.mock import Mock, MagicMock, patch

from app.models.event import Event, EventStatus


VALID_HOTTOK = "test-secret-token"

PURCHASE_APPROVED_PAYLOAD = {
    "event": "PURCHASE_APPROVED",
    "data": {
        "buyer": {"email": "student@test.com"},
        "product": {"id": "12345"},
        "purchase": {"transaction": "TXN-001"},
    },
}

UNKNOWN_EVENT_PAYLOAD = {
    "event": "SOME_UNKNOWN_EVENT",
    "data": {
        "buyer": {"email": "student@test.com"},
        "product": {"id": "12345"},
    },
}


def _mock_event(id=1, status=EventStatus.PROCESSED):
    ev = Mock(spec=Event)
    ev.id = id
    ev.status = status
    ev.type = "hotmart.purchase_approved"
    ev.payload = {}
    return ev


class TestHotmartWebhookAuth:
    def test_valid_hottok_returns_200(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_db.query.return_value.filter.return_value.first.return_value = None
        persisted_event = _mock_event()
        mock_db.refresh = Mock(side_effect=lambda ev: setattr(ev, "id", 1))

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.hotmart_hottok = VALID_HOTTOK
            mock_settings.hotmart_webhook_enabled = False
            response = client.post(
                "/webhooks/hotmart",
                json=PURCHASE_APPROVED_PAYLOAD,
                headers={"X-Hotmart-Hottok": VALID_HOTTOK},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True

    def test_invalid_hottok_returns_401(self, unauthenticated_client):
        client, mock_db = unauthenticated_client

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.hotmart_hottok = VALID_HOTTOK
            mock_settings.hotmart_webhook_enabled = False
            response = client.post(
                "/webhooks/hotmart",
                json=PURCHASE_APPROVED_PAYLOAD,
                headers={"X-Hotmart-Hottok": "wrong-token"},
            )

        assert response.status_code == 401

    def test_missing_hottok_header_returns_401(self, unauthenticated_client):
        client, mock_db = unauthenticated_client

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.hotmart_hottok = VALID_HOTTOK
            mock_settings.hotmart_webhook_enabled = False
            response = client.post(
                "/webhooks/hotmart",
                json=PURCHASE_APPROVED_PAYLOAD,
            )

        assert response.status_code == 401


class TestHotmartWebhookEventHandling:
    def test_unknown_event_type_returns_200_with_ignored_status(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.refresh = Mock(side_effect=lambda ev: setattr(ev, "id", 2))

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.hotmart_hottok = VALID_HOTTOK
            mock_settings.hotmart_webhook_enabled = False
            response = client.post(
                "/webhooks/hotmart",
                json=UNKNOWN_EVENT_PAYLOAD,
                headers={"X-Hotmart-Hottok": VALID_HOTTOK},
            )

        assert response.status_code == 200
        # The event is persisted but with IGNORED status - no Celery task fired
        mock_db.add.assert_called_once()
        added_event = mock_db.add.call_args[0][0]
        assert added_event.status == EventStatus.IGNORED

    def test_duplicate_transaction_id_skips_processing(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        existing_event = _mock_event(id=99)
        mock_db.query.return_value.filter.return_value.first.return_value = existing_event

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.hotmart_hottok = VALID_HOTTOK
            mock_settings.hotmart_webhook_enabled = True
            response = client.post(
                "/webhooks/hotmart",
                json=PURCHASE_APPROVED_PAYLOAD,
                headers={"X-Hotmart-Hottok": VALID_HOTTOK},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True
        # Should not add a new event record
        mock_db.add.assert_not_called()

    def test_event_persisted_to_db_on_new_event(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.refresh = Mock(side_effect=lambda ev: setattr(ev, "id", 5))

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.hotmart_hottok = VALID_HOTTOK
            mock_settings.hotmart_webhook_enabled = False
            client.post(
                "/webhooks/hotmart",
                json=PURCHASE_APPROVED_PAYLOAD,
                headers={"X-Hotmart-Hottok": VALID_HOTTOK},
            )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestHotmartWebhookCeleryDispatch:
    def test_webhook_enabled_fires_celery_task(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.refresh = Mock(side_effect=lambda ev: setattr(ev, "id", 10))

        # The router does a local import: `from app.tasks import process_hotmart_event`
        # so we patch it on the app.tasks module where it is defined.
        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.hotmart_hottok = VALID_HOTTOK
            mock_settings.hotmart_webhook_enabled = True
            with patch("app.tasks.process_hotmart_event") as mock_task:
                mock_task.delay = Mock()
                response = client.post(
                    "/webhooks/hotmart",
                    json=PURCHASE_APPROVED_PAYLOAD,
                    headers={"X-Hotmart-Hottok": VALID_HOTTOK},
                )

        assert response.status_code == 200

    def test_webhook_disabled_does_not_fire_celery_task(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.refresh = Mock(side_effect=lambda ev: setattr(ev, "id", 11))

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.hotmart_hottok = VALID_HOTTOK
            mock_settings.hotmart_webhook_enabled = False
            with patch("app.tasks.process_hotmart_event") as mock_task:
                mock_task.delay = Mock()
                response = client.post(
                    "/webhooks/hotmart",
                    json=PURCHASE_APPROVED_PAYLOAD,
                    headers={"X-Hotmart-Hottok": VALID_HOTTOK},
                )

        mock_task.delay.assert_not_called()
        assert response.status_code == 200
