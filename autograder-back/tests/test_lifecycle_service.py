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
        with patch("app.services.lifecycle._get_all_active_product_rules", return_value=[]):
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
        with patch("app.services.lifecycle._get_all_active_product_rules", return_value=[]):
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


class TestDiscordRegisteredMultiProduct:
    """Quando discord_registered dispara, roles devem vir de todos os HotmartBuyers ativos."""

    def _make_buyer(self, email, hotmart_product_id, status="Ativo"):
        from app.models.hotmart_buyer import HotmartBuyer
        buyer = Mock(spec=HotmartBuyer)
        buyer.email = email
        buyer.hotmart_product_id = hotmart_product_id
        buyer.status = status
        return buyer

    def _make_rule(self, rule_type_val, rule_value):
        from app.models.product import ProductAccessRule, AccessRuleType
        rule = Mock(spec=ProductAccessRule)
        rule.rule_type = rule_type_val
        rule.rule_value = rule_value
        return rule

    def _make_product(self, name, hotmart_product_id, rules=None):
        from app.models.product import Product
        product = Mock(spec=Product)
        product.id = 1
        product.name = name
        product.hotmart_product_id = hotmart_product_id
        product.is_active = True
        product.access_rules = rules or []
        return product

    def test_assigns_discord_roles_from_two_active_products(self, mock_db):
        from app.models.product import AccessRuleType
        user = make_user(
            lifecycle_status=LifecycleStatus.PENDING_ONBOARDING,
            discord_id="discord123",
        )
        role1 = self._make_rule(AccessRuleType.DISCORD_ROLE, "role_111")
        role2 = self._make_rule(AccessRuleType.DISCORD_ROLE, "role_222")
        product1 = self._make_product("Curso A", "hotmart_A", rules=[role1])
        product2 = self._make_product("Curso B", "hotmart_B", rules=[role2])

        with patch("app.services.lifecycle._get_all_active_product_rules",
                   return_value=[(product1, [role1]), (product2, [role2])]):
            with patch("app.integrations.discord.assign_role", return_value=True) as mock_assign:
                with patch("app.integrations.evolution.send_message", return_value=True):
                    from app.services.lifecycle import transition
                    result = transition(mock_db, user, trigger="discord_registered")

        assert result == LifecycleStatus.ACTIVE
        assigned_roles = {call.args[1] for call in mock_assign.call_args_list}
        assert assigned_roles == {"role_111", "role_222"}

    def test_skips_roles_from_cancelled_buyer(self, mock_db):
        """Compradores com status != Ativo não devem gerar roles na transição."""
        from app.models.product import AccessRuleType
        user = make_user(
            lifecycle_status=LifecycleStatus.PENDING_ONBOARDING,
            discord_id="discord123",
        )
        # Simula nenhum produto ativo (buyer cancelado não entra na query)
        with patch("app.services.lifecycle._get_all_active_product_rules",
                   return_value=[]):
            with patch("app.integrations.discord.assign_role", return_value=True) as mock_assign:
                with patch("app.integrations.evolution.send_message", return_value=True):
                    from app.services.lifecycle import transition
                    result = transition(mock_db, user, trigger="discord_registered")

        assert result == LifecycleStatus.ACTIVE
        mock_assign.assert_not_called()

    def test_transitions_to_active_even_with_no_buyers(self, mock_db):
        """Sem buyers, a transição de estado ainda deve acontecer."""
        user = make_user(lifecycle_status=LifecycleStatus.PENDING_ONBOARDING)
        with patch("app.services.lifecycle._get_all_active_product_rules", return_value=[]):
            with patch("app.integrations.evolution.send_message", return_value=True):
                from app.services.lifecycle import transition
                result = transition(mock_db, user, trigger="discord_registered")

        assert result == LifecycleStatus.ACTIVE

    def test_purchase_approved_still_uses_get_product_rules(self, mock_db):
        """Outros triggers não devem usar _get_all_active_product_rules."""
        user = make_user(lifecycle_status=None)
        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])) as mock_gpr:
            with patch("app.services.lifecycle._side_effects_for_pending_onboarding"):
                from app.services.lifecycle import transition
                transition(mock_db, user, trigger="purchase_approved", hotmart_product_id="hotmart_X")

        mock_gpr.assert_called_once_with(mock_db, "hotmart_X")


class TestGetAllActiveProductRules:
    """Testa a nova função _get_all_active_product_rules diretamente."""

    def test_returns_rules_for_active_buyers(self, mock_db):
        from app.models.hotmart_buyer import HotmartBuyer
        from app.models.product import Product, ProductAccessRule, AccessRuleType

        buyer = Mock(spec=HotmartBuyer)
        buyer.hotmart_product_id = "hp_001"

        product = Mock(spec=Product)
        product.hotmart_product_id = "hp_001"
        product.is_active = True
        product.access_rules = []

        mock_db.all.return_value = [buyer]

        with patch("app.services.lifecycle._get_product_rules", return_value=(product, [])):
            from app.services.lifecycle import _get_all_active_product_rules
            result = _get_all_active_product_rules(mock_db, "student@test.com")

        assert len(result) == 1
        assert result[0][0] is product

    def test_returns_empty_when_no_active_buyers(self, mock_db):
        mock_db.all.return_value = []
        from app.services.lifecycle import _get_all_active_product_rules
        result = _get_all_active_product_rules(mock_db, "student@test.com")
        assert result == []

    def test_skips_product_not_found_in_catalog(self, mock_db):
        from app.models.hotmart_buyer import HotmartBuyer

        buyer = Mock(spec=HotmartBuyer)
        buyer.hotmart_product_id = "hp_999"
        mock_db.all.return_value = [buyer]

        with patch("app.services.lifecycle._get_product_rules", return_value=(None, [])):
            from app.services.lifecycle import _get_all_active_product_rules
            result = _get_all_active_product_rules(mock_db, "student@test.com")

        assert result == []


class TestEvolutionAPISideEffects:
    """Verify that lifecycle side-effects call evolution.send_message, not manychat."""

    def test_pending_onboarding_sends_whatsapp_when_phone_set(self, mock_db):
        user = make_user(whatsapp_number="+5511999999999")
        product = Mock()
        product.name = "Curso LLMs"

        with patch("app.integrations.evolution.send_message", return_value=True) as mock_send:
            from app.services.lifecycle import _side_effects_for_pending_onboarding
            _side_effects_for_pending_onboarding(mock_db, user, product, [])

        mock_send.assert_called_once()
        call_phone = mock_send.call_args[0][0]
        assert call_phone == "+5511999999999"

    def test_pending_onboarding_skips_when_no_phone(self, mock_db):
        user = make_user(whatsapp_number=None)
        product = Mock()
        product.name = "Curso LLMs"

        with patch("app.integrations.evolution.send_message", return_value=True) as mock_send:
            from app.services.lifecycle import _side_effects_for_pending_onboarding
            _side_effects_for_pending_onboarding(mock_db, user, product, [])

        mock_send.assert_not_called()

    def test_active_sends_welcome_message(self, mock_db):
        user = make_user(whatsapp_number="+5511999999999")
        product = Mock()
        product.name = "Curso LLMs"

        with patch("app.integrations.evolution.send_message", return_value=True) as mock_send:
            from app.services.lifecycle import _side_effects_for_active
            _side_effects_for_active(mock_db, user, product, [], is_reactivation=False)

        mock_send.assert_called_once()
        call_text = mock_send.call_args[0][1]
        assert "Curso LLMs" in call_text

    def test_churned_sends_churn_message(self, mock_db):
        user = make_user(whatsapp_number="+5511999999999")
        product = Mock()
        product.name = "Curso LLMs"

        with patch("app.integrations.evolution.send_message", return_value=True) as mock_send:
            from app.services.lifecycle import _side_effects_for_churned
            _side_effects_for_churned(mock_db, user, product, [])

        mock_send.assert_called_once()
        call_phone = mock_send.call_args[0][0]
        assert call_phone == "+5511999999999"
