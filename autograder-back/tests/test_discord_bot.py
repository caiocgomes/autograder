"""Unit tests for Discord bot /registrar command (app/discord_bot.py)"""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from app.models.user import User, UserRole, LifecycleStatus
from app.models.event import Event, EventStatus


def run(coro):
    """Helper to run an async coroutine synchronously in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_interaction(channel_id="777", user_id="9999"):
    interaction = Mock()
    interaction.channel_id = int(channel_id) if channel_id.isdigit() else channel_id
    interaction.user = Mock()
    interaction.user.id = int(user_id)
    interaction.response = Mock()
    interaction.response.send_message = AsyncMock()
    return interaction


def _make_user(id=1, discord_id=None, lifecycle_status=LifecycleStatus.PENDING_ONBOARDING,
               onboarding_token="VALIDTOK", expires_at=None):
    user = Mock(spec=User)
    user.id = id
    user.email = "student@test.com"
    user.discord_id = discord_id
    user.lifecycle_status = lifecycle_status
    user.onboarding_token = onboarding_token
    if expires_at is None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    user.onboarding_token_expires_at = expires_at
    return user


class TestRegistrarCommand:
    def test_valid_token_links_discord_and_transitions_lifecycle(self):
        interaction = _make_interaction(channel_id="", user_id="9999")
        user = _make_user(onboarding_token="VALIDTOK")

        db = MagicMock()
        # First query: check if discord_id already registered -> None
        # Second query: find user by token -> user
        db.query.return_value.filter.return_value.first.side_effect = [None, user]

        # The bot uses a local import: `from app.services.lifecycle import transition`
        # so we patch it at the source module.
        with patch("app.discord_bot.SessionLocal", return_value=db):
            with patch("app.discord_bot.settings") as mock_settings:
                mock_settings.discord_registration_channel_id = ""
                with patch("app.services.lifecycle.transition") as mock_transition:
                    mock_transition.return_value = LifecycleStatus.ACTIVE
                    from app.discord_bot import registrar
                    run(registrar.callback(interaction, codigo="VALIDTOK"))

        assert user.discord_id == "9999"
        assert user.onboarding_token is None
        assert user.onboarding_token_expires_at is None
        mock_transition.assert_called_once()
        interaction.response.send_message.assert_called_once()
        sent_message = interaction.response.send_message.call_args[0][0]
        assert "Registrado" in sent_message

    def test_invalid_token_sends_error_message(self):
        interaction = _make_interaction(channel_id="", user_id="9999")

        db = MagicMock()
        # First query: no existing registration; second: no user found for token
        db.query.return_value.filter.return_value.first.side_effect = [None, None]

        with patch("app.discord_bot.SessionLocal", return_value=db):
            with patch("app.discord_bot.settings") as mock_settings:
                mock_settings.discord_registration_channel_id = ""
                from app.discord_bot import registrar
                run(registrar.callback(interaction, codigo="BADTOKEN"))

        interaction.response.send_message.assert_called_once()
        sent_message = interaction.response.send_message.call_args[0][0]
        # The bot sends a message mentioning an invalid code
        assert any(word in sent_message for word in ["inválido", "Código", "invalido", "código"])

    def test_expired_token_sends_expiry_message(self):
        interaction = _make_interaction(channel_id="", user_id="9999")
        expired_time = datetime.now(timezone.utc) - timedelta(days=1)
        user = _make_user(onboarding_token="EXPTOKEN", expires_at=expired_time)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [None, user]

        with patch("app.discord_bot.SessionLocal", return_value=db):
            with patch("app.discord_bot.settings") as mock_settings:
                mock_settings.discord_registration_channel_id = ""
                from app.discord_bot import registrar
                run(registrar.callback(interaction, codigo="EXPTOKEN"))

        interaction.response.send_message.assert_called_once()
        sent_message = interaction.response.send_message.call_args[0][0]
        assert any(word in sent_message for word in ["expirado", "Expirado", "expirou"])

    def test_already_registered_sends_already_registered_message(self):
        interaction = _make_interaction(channel_id="", user_id="9999")
        existing_user = _make_user(discord_id="9999")

        db = MagicMock()
        # First query finds an existing user already linked to this discord_id
        db.query.return_value.filter.return_value.first.return_value = existing_user

        with patch("app.discord_bot.SessionLocal", return_value=db):
            with patch("app.discord_bot.settings") as mock_settings:
                mock_settings.discord_registration_channel_id = ""
                from app.discord_bot import registrar
                run(registrar.callback(interaction, codigo="ANYTOKEN"))

        interaction.response.send_message.assert_called_once()
        sent_message = interaction.response.send_message.call_args[0][0]
        assert any(word in sent_message for word in ["já", "registrado", "Registrado"])

    def test_wrong_channel_sends_redirect_message(self):
        # Channel 111 != registration channel 888
        interaction = _make_interaction(channel_id="111", user_id="9999")

        with patch("app.discord_bot.settings") as mock_settings:
            mock_settings.discord_registration_channel_id = "888"
            from app.discord_bot import registrar
            run(registrar.callback(interaction, codigo="VALIDTOK"))

        interaction.response.send_message.assert_called_once()
        sent_message = interaction.response.send_message.call_args[0][0]
        assert any(word in sent_message for word in ["canal", "registro", "#registro"])

    def test_no_channel_restriction_when_setting_is_empty(self):
        """When discord_registration_channel_id is empty, any channel is allowed."""
        interaction = _make_interaction(channel_id="111", user_id="9999")
        user = _make_user(onboarding_token="MYTOKEN")

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [None, user]

        with patch("app.discord_bot.SessionLocal", return_value=db):
            with patch("app.discord_bot.settings") as mock_settings:
                mock_settings.discord_registration_channel_id = ""
                with patch("app.services.lifecycle.transition") as mock_transition:
                    mock_transition.return_value = LifecycleStatus.ACTIVE
                    from app.discord_bot import registrar
                    run(registrar.callback(interaction, codigo="MYTOKEN"))

        sent_message = interaction.response.send_message.call_args[0][0]
        # Should reach success path, not the channel redirect
        assert "Registrado" in sent_message

    def test_db_closed_on_exception(self):
        """DB session must be closed even when an unhandled exception occurs."""
        interaction = _make_interaction(channel_id="", user_id="9999")

        db = MagicMock()
        db.query.side_effect = RuntimeError("DB failure")

        with patch("app.discord_bot.SessionLocal", return_value=db):
            with patch("app.discord_bot.settings") as mock_settings:
                mock_settings.discord_registration_channel_id = ""
                from app.discord_bot import registrar
                run(registrar.callback(interaction, codigo="VALIDTOK"))

        db.close.assert_called_once()
        db.rollback.assert_called_once()
