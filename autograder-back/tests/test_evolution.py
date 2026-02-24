"""Tests for Evolution API integration (app/integrations/evolution.py)"""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestSendMessage:
    def test_successful_send_returns_true(self):
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch("app.integrations.evolution.settings") as mock_settings:
            mock_settings.evolution_enabled = True
            mock_settings.evolution_dev_mode = False
            mock_settings.evolution_api_url = "https://evo.example.com"
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_instance = "test-instance"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.evolution import send_message
                result = send_message("+5511999999999", "Hello!")

        assert result is True
        call_kwargs = mock_client_instance.post.call_args
        assert "test-instance" in call_kwargs[0][0]
        payload = call_kwargs[1]["json"]
        assert payload["number"] == "5511999999999"
        assert payload["text"] == "Hello!"

    def test_status_201_returns_true(self):
        mock_response = Mock()
        mock_response.status_code = 201

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch("app.integrations.evolution.settings") as mock_settings:
            mock_settings.evolution_enabled = True
            mock_settings.evolution_dev_mode = False
            mock_settings.evolution_api_url = "https://evo.example.com"
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_instance = "test-instance"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.evolution import send_message
                result = send_message("+5511999999999", "Hello!")

        assert result is True

    def test_api_error_returns_false(self):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch("app.integrations.evolution.settings") as mock_settings:
            mock_settings.evolution_enabled = True
            mock_settings.evolution_dev_mode = False
            mock_settings.evolution_api_url = "https://evo.example.com"
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_instance = "test-instance"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.evolution import send_message
                result = send_message("+5511999999999", "Hello!")

        assert result is False

    def test_network_exception_returns_false(self):
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(side_effect=ConnectionError("Network down"))
        mock_client_instance.__exit__ = Mock(return_value=False)

        with patch("app.integrations.evolution.settings") as mock_settings:
            mock_settings.evolution_enabled = True
            mock_settings.evolution_dev_mode = False
            mock_settings.evolution_api_url = "https://evo.example.com"
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_instance = "test-instance"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.evolution import send_message
                result = send_message("+5511999999999", "Hello!")

        assert result is False

    def test_evolution_disabled_returns_true_without_http_call(self):
        with patch("app.integrations.evolution.settings") as mock_settings:
            mock_settings.evolution_enabled = False
            with patch("httpx.Client") as mock_client_cls:
                from app.integrations.evolution import send_message
                result = send_message("+5511999999999", "Hello!")

        assert result is True
        mock_client_cls.assert_not_called()

    def test_empty_phone_returns_false_without_http_call(self):
        with patch("app.integrations.evolution.settings") as mock_settings:
            mock_settings.evolution_enabled = True
            with patch("httpx.Client") as mock_client_cls:
                from app.integrations.evolution import send_message
                result = send_message("", "Hello!")

        assert result is False
        mock_client_cls.assert_not_called()
