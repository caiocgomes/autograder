"""Tests for lifecycle state machine (app/services/lifecycle.py)"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch

from app.models.user import User, UserRole, LifecycleStatus


def make_user(lifecycle_status=None, **kwargs):
    """Create a lightweight User-like object without DB round-trips."""
    user = Mock(spec=User)
    user.id = kwargs.get("id", 1)
    user.email = kwargs.get("email", "student@test.com")
    user.role = UserRole.STUDENT
    user.lifecycle_status = lifecycle_status
    user.discord_id = kwargs.get("discord_id", None)
    user.manychat_subscriber_id = kwargs.get("manychat_subscriber_id", None)
    user.whatsapp_number = kwargs.get("whatsapp_number", None)
    user.onboarding_token = None
    user.onboarding_token_expires_at = None
    return user


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    return db


class TestTransitionValidPaths:
    def test_none_to_pending_onboarding_on_purchase_approved(self, mock_db):
        user = make_user(lifecycle_status=None)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_pending_onboarding"):
                from app.services.lifecycle import transition
                result = transition(mock_db, user, trigger="purchase_approved")

        assert result == LifecycleStatus.PENDING_ONBOARDING
        assert user.lifecycle_status == LifecycleStatus.PENDING_ONBOARDING

    def test_pending_onboarding_to_active_on_discord_registered(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.PENDING_ONBOARDING)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_active"):
                from app.services.lifecycle import transition
                result = transition(mock_db, user, trigger="discord_registered")

        assert result == LifecycleStatus.ACTIVE
        assert user.lifecycle_status == LifecycleStatus.ACTIVE

    def test_active_to_churned_on_subscription_cancelled(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.ACTIVE)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_churned"):
                from app.services.lifecycle import transition
                result = transition(mock_db, user, trigger="subscription_cancelled")

        assert result == LifecycleStatus.CHURNED
        assert user.lifecycle_status == LifecycleStatus.CHURNED

    def test_churned_to_active_on_purchase_approved_is_reactivation(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.CHURNED)
        captured = {}

        def capture_active(db, u, product, rules, is_reactivation=False):
            captured["is_reactivation"] = is_reactivation

        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_active", side_effect=capture_active):
                from app.services.lifecycle import transition
                result = transition(mock_db, user, trigger="purchase_approved")

        assert result == LifecycleStatus.ACTIVE
        assert captured["is_reactivation"] is True

    def test_pending_payment_to_pending_onboarding(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.PENDING_PAYMENT)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_pending_onboarding"):
                from app.services.lifecycle import transition
                result = transition(mock_db, user, trigger="purchase_approved")

        assert result == LifecycleStatus.PENDING_ONBOARDING


class TestTransitionInvalidPaths:
    def test_invalid_transition_returns_none(self, mock_db):
        # active → pending_payment has no defined transition
        user = make_user(lifecycle_status=LifecycleStatus.ACTIVE)
        from app.services.lifecycle import transition
        result = transition(mock_db, user, trigger="purchase_delayed")
        assert result is None

    def test_churned_to_churned_returns_none(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.CHURNED)
        from app.services.lifecycle import transition
        result = transition(mock_db, user, trigger="subscription_cancelled")
        assert result is None

    def test_unknown_trigger_returns_none(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.ACTIVE)
        from app.services.lifecycle import transition
        result = transition(mock_db, user, trigger="totally_unknown_event")
        assert result is None

    def test_state_not_mutated_on_invalid_transition(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.ACTIVE)
        original_status = user.lifecycle_status
        from app.services.lifecycle import transition
        transition(mock_db, user, trigger="totally_unknown_event")
        assert user.lifecycle_status == original_status


class TestTransitionSideEffects:
    def test_side_effects_called_for_pending_onboarding(self, mock_db):
        user = make_user(lifecycle_status=None)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_pending_onboarding") as mock_se:
                from app.services.lifecycle import transition
                transition(mock_db, user, trigger="purchase_approved")
                mock_se.assert_called_once()

    def test_side_effects_called_for_active(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.PENDING_ONBOARDING)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_active") as mock_se:
                from app.services.lifecycle import transition
                transition(mock_db, user, trigger="discord_registered")
                mock_se.assert_called_once()

    def test_side_effects_called_for_churned(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.ACTIVE)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_churned") as mock_se:
                from app.services.lifecycle import transition
                transition(mock_db, user, trigger="subscription_cancelled")
                mock_se.assert_called_once()

    def test_db_commit_called_on_valid_transition(self, mock_db):
        user = make_user(lifecycle_status=None)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            with patch("app.services.lifecycle._side_effects_for_pending_onboarding"):
                from app.services.lifecycle import transition
                transition(mock_db, user, trigger="purchase_approved")
                mock_db.commit.assert_called_once()

    def test_db_commit_not_called_on_invalid_transition(self, mock_db):
        user = make_user(lifecycle_status=LifecycleStatus.ACTIVE)
        from app.services.lifecycle import transition
        transition(mock_db, user, trigger="totally_unknown_event")
        mock_db.commit.assert_not_called()


class TestGenerateOnboardingToken:
    def test_token_is_8_chars(self, mock_db):
        user = make_user()
        from app.services.lifecycle import generate_onboarding_token
        token = generate_onboarding_token(mock_db, user)
        assert len(token) == 8

    def test_token_is_uppercase(self, mock_db):
        user = make_user()
        from app.services.lifecycle import generate_onboarding_token
        token = generate_onboarding_token(mock_db, user)
        assert token == token.upper()

    def test_token_stored_on_user(self, mock_db):
        user = make_user()
        from app.services.lifecycle import generate_onboarding_token
        token = generate_onboarding_token(mock_db, user)
        assert user.onboarding_token == token

    def test_expiry_set_on_user(self, mock_db):
        user = make_user()
        from app.services.lifecycle import generate_onboarding_token
        generate_onboarding_token(mock_db, user)
        assert user.onboarding_token_expires_at is not None
        assert user.onboarding_token_expires_at > datetime.now(timezone.utc)

    def test_tokens_are_not_deterministic(self, mock_db):
        user = make_user()
        from app.services.lifecycle import generate_onboarding_token
        tokens = {generate_onboarding_token(mock_db, user) for _ in range(10)}
        # Probabilistically: at least 2 distinct tokens across 10 calls
        assert len(tokens) > 1
