"""Tests for {token} variable support in bulk messaging."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from app.models.user import User
from app.models.message_campaign import MessageCampaign, MessageRecipient, RecipientStatus, CampaignStatus


class TestTokenVariableValidation:
    """Template validation should accept {token} as valid variable."""

    def test_token_is_accepted_in_template(self, client_with_admin):
        """GIVEN template with {token}, WHEN admin sends, THEN does not reject as invalid."""
        client, db, admin = client_with_admin

        users = [Mock(spec=User, id=1, email="u@t.com", whatsapp_number="5511999990001")]

        call_count = {"n": 0}
        def mock_query(*args):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                result.filter.return_value.all.return_value = users
            else:
                result.filter.return_value.all.return_value = []
            return result
        db.query = mock_query

        added = []
        db.add = lambda obj: added.append(obj)
        db.flush = Mock(side_effect=lambda: setattr(added[0], 'id', 42) if added else None)
        db.refresh = Mock()

        with patch("app.routers.messaging.celery_app") as mock_celery:
            mock_celery.send_task.return_value = Mock(id="task-123")
            resp = client.post("/messaging/send", json={
                "user_ids": [1],
                "message_template": "Seu token: {token}",
            })

        assert resp.status_code == 202

    def test_token_combined_with_other_vars(self, client_with_admin):
        """GIVEN template with {token} and {primeiro_nome}, WHEN admin sends, THEN accepted."""
        client, db, admin = client_with_admin

        users = [Mock(spec=User, id=1, email="u@t.com", whatsapp_number="5511999990001")]

        call_count = {"n": 0}
        def mock_query(*args):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                result.filter.return_value.all.return_value = users
            else:
                result.filter.return_value.all.return_value = []
            return result
        db.query = mock_query

        added = []
        db.add = lambda obj: added.append(obj)
        db.flush = Mock(side_effect=lambda: setattr(added[0], 'id', 42) if added else None)
        db.refresh = Mock()

        with patch("app.routers.messaging.celery_app") as mock_celery:
            mock_celery.send_task.return_value = Mock(id="task-123")
            resp = client.post("/messaging/send", json={
                "user_ids": [1],
                "message_template": "Oi {primeiro_nome}, token: {token}",
            })

        assert resp.status_code == 202


class TestTokenAutoManagement:
    """Celery task should auto-generate/regenerate tokens when template uses {token}."""

    def _make_db_mock(self, campaign, recipients, user):
        """Helper to build a mock DB for the send_bulk_messages task."""
        mock_db = MagicMock()
        call_count = {"n": 0}
        def mock_query(*args):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # db.query(MessageCampaign).filter(...).first()
                result.filter.return_value.first.return_value = campaign
            elif call_count["n"] == 2:
                # db.query(MessageRecipient).filter(..., ...).all()
                result.filter.return_value.filter.return_value.all.return_value = recipients
                # Also support single filter call
                result.filter.return_value.all.return_value = recipients
            else:
                # db.query(User).filter(...).first()
                result.filter.return_value.first.return_value = user
            return result
        mock_db.query = mock_query
        return mock_db

    @patch("time.sleep")
    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_generates_token_when_null(self, mock_send, mock_sleep):
        """GIVEN user with no token, WHEN task sends {token} template, THEN generates new token."""
        from app.tasks import send_bulk_messages

        user = Mock(spec=User)
        user.id = 1
        user.onboarding_token = None
        user.onboarding_token_expires_at = None

        recipient = Mock(spec=MessageRecipient)
        recipient.id = 1
        recipient.user_id = 1
        recipient.phone = "5511999990001"
        recipient.name = "João"
        recipient.status = RecipientStatus.PENDING

        campaign = Mock(spec=MessageCampaign)
        campaign.id = 42
        campaign.status = CampaignStatus.SENDING
        campaign.sent_count = 0
        campaign.failed_count = 0
        campaign.course_name = "Python"

        mock_db = self._make_db_mock(campaign, [recipient], user)

        with patch("app.database.SessionLocal", return_value=mock_db):
            send_bulk_messages(42, "Token: {token}")

        # User should have a token assigned
        assert user.onboarding_token is not None
        assert len(user.onboarding_token) == 8
        assert user.onboarding_token_expires_at is not None

        # Message should contain the generated token
        assert recipient.resolved_message is not None
        assert user.onboarding_token in recipient.resolved_message

    @patch("time.sleep")
    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_regenerates_expired_token(self, mock_send, mock_sleep):
        """GIVEN user with expired token, WHEN task sends {token} template, THEN regenerates."""
        from app.tasks import send_bulk_messages

        old_token = "OLDTOKEN1"
        user = Mock(spec=User)
        user.id = 1
        user.onboarding_token = old_token
        user.onboarding_token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        recipient = Mock(spec=MessageRecipient)
        recipient.id = 1
        recipient.user_id = 1
        recipient.phone = "5511999990001"
        recipient.name = "Maria"
        recipient.status = RecipientStatus.PENDING

        campaign = Mock(spec=MessageCampaign)
        campaign.id = 42
        campaign.status = CampaignStatus.SENDING
        campaign.sent_count = 0
        campaign.failed_count = 0
        campaign.course_name = "Python"

        mock_db = self._make_db_mock(campaign, [recipient], user)

        with patch("app.database.SessionLocal", return_value=mock_db):
            send_bulk_messages(42, "Token: {token}")

        assert user.onboarding_token != old_token
        assert len(user.onboarding_token) == 8
        assert user.onboarding_token_expires_at > datetime.now(timezone.utc)

    @patch("time.sleep")
    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_uses_existing_valid_token(self, mock_send, mock_sleep):
        """GIVEN user with valid token, WHEN task sends {token} template, THEN uses existing."""
        from app.tasks import send_bulk_messages

        existing_token = "VALID123"
        existing_expiry = datetime.now(timezone.utc) + timedelta(days=5)
        user = Mock(spec=User)
        user.id = 1
        user.onboarding_token = existing_token
        user.onboarding_token_expires_at = existing_expiry

        recipient = Mock(spec=MessageRecipient)
        recipient.id = 1
        recipient.user_id = 1
        recipient.phone = "5511999990001"
        recipient.name = "Carlos"
        recipient.status = RecipientStatus.PENDING

        campaign = Mock(spec=MessageCampaign)
        campaign.id = 42
        campaign.status = CampaignStatus.SENDING
        campaign.sent_count = 0
        campaign.failed_count = 0
        campaign.course_name = "Python"

        mock_db = self._make_db_mock(campaign, [recipient], user)

        with patch("app.database.SessionLocal", return_value=mock_db):
            send_bulk_messages(42, "Token: {token}")

        # Token should remain unchanged
        assert user.onboarding_token == existing_token
        assert user.onboarding_token_expires_at == existing_expiry
        assert "VALID123" in recipient.resolved_message
