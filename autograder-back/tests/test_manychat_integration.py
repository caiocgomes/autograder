"""Tests for ManyChat integration module (app/integrations/manychat.py)"""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestAddTag:
    def test_successful_add_tag_returns_true(self):
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import add_tag
                result = add_tag("sub-123", "ACTIVE_STUDENT")

        assert result is True

    def test_api_error_returns_false(self):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import add_tag
                result = add_tag("sub-123", "ACTIVE_STUDENT")

        assert result is False

    def test_manychat_disabled_returns_true_without_http_call(self):
        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = False
            with patch("httpx.Client") as mock_client_cls:
                from app.integrations.manychat import add_tag
                result = add_tag("sub-123", "ACTIVE_STUDENT")

        assert result is True
        mock_client_cls.assert_not_called()

    def test_exception_returns_false(self):
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(side_effect=ConnectionError("Network down"))
        mock_client_instance.__exit__ = Mock(return_value=False)

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import add_tag
                result = add_tag("sub-123", "ACTIVE_STUDENT")

        assert result is False


class TestTriggerFlow:
    def test_successful_trigger_flow_returns_true(self):
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import trigger_flow
                result = trigger_flow("sub-123", "flow-ns-abc")

        assert result is True
        call_kwargs = mock_client_instance.post.call_args[1]
        payload = call_kwargs.get("json", {})
        assert payload["subscriber_id"] == "sub-123"
        assert payload["flow_ns"] == "flow-ns-abc"

    def test_trigger_flow_with_custom_fields_includes_them_in_request(self):
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        custom = {"student_name": "Ana", "onboarding_token": "ABC12345"}

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import trigger_flow
                result = trigger_flow("sub-123", "flow-ns-abc", custom_fields=custom)

        assert result is True
        call_kwargs = mock_client_instance.post.call_args[1]
        payload = call_kwargs.get("json", {})
        assert "custom_fields" in payload
        field_names = {f["field_name"] for f in payload["custom_fields"]}
        assert "student_name" in field_names
        assert "onboarding_token" in field_names

    def test_trigger_flow_without_custom_fields_has_no_custom_fields_key(self):
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import trigger_flow
                trigger_flow("sub-123", "flow-ns-abc")

        call_kwargs = mock_client_instance.post.call_args[1]
        payload = call_kwargs.get("json", {})
        assert "custom_fields" not in payload

    def test_manychat_disabled_returns_true_without_http_call(self):
        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = False
            with patch("httpx.Client") as mock_client_cls:
                from app.integrations.manychat import trigger_flow
                result = trigger_flow("sub-123", "flow-ns-abc")

        assert result is True
        mock_client_cls.assert_not_called()

    def test_api_error_returns_false(self):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import trigger_flow
                result = trigger_flow("sub-123", "flow-ns-abc")

        assert result is False


class TestFindSubscriber:
    def test_found_subscriber_returns_id(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": "sub-xyz"}}

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.get.return_value = mock_response

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import find_subscriber
                result = find_subscriber("+5511999999999")

        assert result == "sub-xyz"

    def test_subscriber_not_found_returns_none(self):
        mock_response = Mock()
        mock_response.status_code = 404

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.get.return_value = mock_response

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import find_subscriber
                result = find_subscriber("+5511999999999")

        assert result is None

    def test_manychat_disabled_returns_none_without_http_call(self):
        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = False
            with patch("httpx.Client") as mock_client_cls:
                from app.integrations.manychat import find_subscriber
                result = find_subscriber("+5511999999999")

        assert result is None
        mock_client_cls.assert_not_called()

    def test_api_error_returns_none(self):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_client_instance.get.return_value = mock_response

        with patch("app.integrations.manychat.settings") as mock_settings:
            mock_settings.manychat_enabled = True
            mock_settings.manychat_api_token = "test-token"
            with patch("httpx.Client", return_value=mock_client_instance):
                from app.integrations.manychat import find_subscriber
                result = find_subscriber("+5511999999999")

        assert result is None
