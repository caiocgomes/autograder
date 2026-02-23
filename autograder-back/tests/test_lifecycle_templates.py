"""Tests for lifecycle template resolution from database."""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone

from app.models.user import User, LifecycleStatus
from app.models.product import Product, ProductAccessRule
from app.models.message_template import MessageTemplate, TemplateEventType
from app.services.lifecycle import MSG_ONBOARDING, MSG_WELCOME, MSG_WELCOME_BACK, MSG_CHURN


def _make_user(whatsapp="5511999990001", lifecycle_status=None):
    user = Mock(spec=User)
    user.id = 10
    user.email = "aluno@test.com"
    user.whatsapp_number = whatsapp
    user.lifecycle_status = lifecycle_status
    user.onboarding_token = None
    user.onboarding_token_expires_at = None
    user.discord_id = None
    return user


def _make_product(name="Python Básico"):
    product = Mock(spec=Product)
    product.id = 1
    product.name = name
    return product


def _make_db_template(event_type, text):
    t = Mock(spec=MessageTemplate)
    t.event_type = event_type
    t.template_text = text
    return t


class TestLifecycleTemplateFromDB:
    """Lifecycle side-effects should read templates from DB with hardcoded fallback."""

    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_onboarding_uses_db_template_when_found(self, mock_send, mock_db):
        """GIVEN onboarding template in DB, WHEN transition to pending_onboarding, THEN uses DB template."""
        from app.services.lifecycle import _side_effects_for_pending_onboarding

        user = _make_user()
        product = _make_product()
        db_template = _make_db_template(
            TemplateEventType.ONBOARDING,
            "Fala {primeiro_nome}! Teu token: {token}. Produto: {product_name}"
        )

        mock_db.query.return_value.filter.return_value.first.return_value = db_template

        with patch("app.services.lifecycle.generate_onboarding_token", return_value="ABC12345"):
            _side_effects_for_pending_onboarding(mock_db, user, product, [])

        sent_text = mock_send.call_args[0][1]
        assert "Fala" in sent_text
        assert "ABC12345" in sent_text
        assert "Python Básico" in sent_text

    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_onboarding_uses_hardcoded_when_no_db_row(self, mock_send, mock_db):
        """GIVEN no template in DB, WHEN transition to pending_onboarding, THEN uses hardcoded MSG_ONBOARDING."""
        from app.services.lifecycle import _side_effects_for_pending_onboarding

        user = _make_user()
        product = _make_product()

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.lifecycle.generate_onboarding_token", return_value="XYZ99999"):
            _side_effects_for_pending_onboarding(mock_db, user, product, [])

        sent_text = mock_send.call_args[0][1]
        assert "XYZ99999" in sent_text
        assert "Python Básico" in sent_text

    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_onboarding_uses_hardcoded_on_db_error(self, mock_send, mock_db):
        """GIVEN DB query raises exception, WHEN transition to pending_onboarding, THEN falls back to hardcoded."""
        from app.services.lifecycle import _side_effects_for_pending_onboarding

        user = _make_user()
        product = _make_product()

        mock_db.query.return_value.filter.return_value.first.side_effect = Exception("DB down")

        with patch("app.services.lifecycle.generate_onboarding_token", return_value="ERR11111"):
            _side_effects_for_pending_onboarding(mock_db, user, product, [])

        sent_text = mock_send.call_args[0][1]
        assert "ERR11111" in sent_text

    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_welcome_uses_db_template(self, mock_send, mock_db):
        """GIVEN welcome template in DB, WHEN transition to active, THEN uses DB template."""
        from app.services.lifecycle import _side_effects_for_active

        user = _make_user()
        product = _make_product()
        db_template = _make_db_template(
            TemplateEventType.WELCOME,
            "Bora {primeiro_nome}! {product_name} te espera!"
        )

        mock_db.query.return_value.filter.return_value.first.return_value = db_template

        _side_effects_for_active(mock_db, user, product, [], is_reactivation=False)

        sent_text = mock_send.call_args[0][1]
        assert "Bora" in sent_text
        assert "Python Básico" in sent_text

    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_welcome_back_uses_db_template(self, mock_send, mock_db):
        """GIVEN welcome_back template in DB, WHEN reactivation, THEN uses DB template."""
        from app.services.lifecycle import _side_effects_for_active

        user = _make_user()
        product = _make_product()
        db_template = _make_db_template(
            TemplateEventType.WELCOME_BACK,
            "Voltou {primeiro_nome}! {product_name} de novo!"
        )

        mock_db.query.return_value.filter.return_value.first.return_value = db_template

        _side_effects_for_active(mock_db, user, product, [], is_reactivation=True)

        sent_text = mock_send.call_args[0][1]
        assert "Voltou" in sent_text

    @patch("app.integrations.evolution.send_message", return_value=True)
    def test_churn_uses_db_template(self, mock_send, mock_db):
        """GIVEN churn template in DB, WHEN transition to churned, THEN uses DB template."""
        from app.services.lifecycle import _side_effects_for_churned

        user = _make_user()
        product = _make_product()
        db_template = _make_db_template(
            TemplateEventType.CHURN,
            "Tchau {nome}. Acesso ao {product_name} encerrado."
        )

        mock_db.query.return_value.filter.return_value.first.return_value = db_template

        _side_effects_for_churned(mock_db, user, product, [])

        sent_text = mock_send.call_args[0][1]
        assert "Tchau" in sent_text
        assert "Python Básico" in sent_text
