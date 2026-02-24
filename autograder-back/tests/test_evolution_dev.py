"""Tests for file-based Evolution dev sink (app/integrations/evolution_dev.py)"""
import os
import pytest
from unittest.mock import patch


@pytest.fixture
def output_dir(tmp_path):
    """Provide a temp dir and patch settings to use it."""
    with patch("app.integrations.evolution_dev.settings") as mock_settings:
        mock_settings.evolution_dev_output_dir = str(tmp_path)
        yield tmp_path, mock_settings


class TestDevSendMessage:
    def test_creates_file_with_send_id(self, output_dir):
        tmp_path, _ = output_dir
        from app.integrations.evolution_dev import send_message

        result = send_message("5511991747887", "Hello!", send_id="campaign_42")

        assert result is True
        file_path = tmp_path / "campaign_42" / "5511991747887.txt"
        assert file_path.exists()
        content = file_path.read_text()
        assert "TO: 5511991747887" in content
        assert "AT: " in content
        assert "---" in content
        assert "Hello!" in content

    def test_ungrouped_fallback_without_send_id(self, output_dir):
        tmp_path, _ = output_dir
        from app.integrations.evolution_dev import send_message

        result = send_message("5511991747887", "Hello!")

        assert result is True
        ungrouped = tmp_path / "_ungrouped"
        assert ungrouped.exists()
        files = list(ungrouped.iterdir())
        assert len(files) == 1
        assert files[0].name.startswith("5511991747887_")
        assert files[0].name.endswith(".txt")

    def test_append_on_duplicate_phone_same_send_id(self, output_dir):
        tmp_path, _ = output_dir
        from app.integrations.evolution_dev import send_message

        send_message("5511991747887", "First message", send_id="batch_1")
        send_message("5511991747887", "Second message", send_id="batch_1")

        file_path = tmp_path / "batch_1" / "5511991747887.txt"
        content = file_path.read_text()
        assert "First message" in content
        assert "Second message" in content
        assert content.count("TO: 5511991747887") == 2

    def test_different_phones_different_files(self, output_dir):
        tmp_path, _ = output_dir
        from app.integrations.evolution_dev import send_message

        send_message("5511991747887", "Msg A", send_id="test_batch")
        send_message("5511999998888", "Msg B", send_id="test_batch")

        assert (tmp_path / "test_batch" / "5511991747887.txt").exists()
        assert (tmp_path / "test_batch" / "5511999998888.txt").exists()

    def test_normalizes_phone_number(self, output_dir):
        tmp_path, _ = output_dir
        from app.integrations.evolution_dev import send_message

        send_message("+5511991747887", "Hello!", send_id="norm_test")

        # +55 stripped to digits, 13 digits → kept as-is
        file_path = tmp_path / "norm_test" / "5511991747887.txt"
        assert file_path.exists()

    def test_brazilian_short_number_gets_55_prefix(self, output_dir):
        tmp_path, _ = output_dir
        from app.integrations.evolution_dev import send_message

        send_message("11991747887", "Hello!", send_id="br_test")

        file_path = tmp_path / "br_test" / "5511991747887.txt"
        assert file_path.exists()
        content = file_path.read_text()
        assert "TO: 5511991747887" in content

    def test_empty_phone_returns_false(self, output_dir):
        from app.integrations.evolution_dev import send_message

        result = send_message("", "Hello!", send_id="test")
        assert result is False

    def test_creates_directories_automatically(self, output_dir):
        tmp_path, _ = output_dir
        from app.integrations.evolution_dev import send_message

        send_message("5511991747887", "Hello!", send_id="deep/nested/dir")

        file_path = tmp_path / "deep/nested/dir" / "5511991747887.txt"
        assert file_path.exists()


class TestDevModeRouting:
    def test_dev_mode_routes_to_file_sink(self):
        with patch("app.integrations.evolution.settings") as mock_settings:
            mock_settings.evolution_enabled = True
            mock_settings.evolution_dev_mode = True
            with patch("app.integrations.evolution_dev.send_message", return_value=True) as mock_dev:
                from app.integrations.evolution import send_message
                result = send_message("5511991747887", "Hello!", send_id="test")

        assert result is True
        mock_dev.assert_called_once_with("5511991747887", "Hello!", send_id="test")

    def test_production_mode_ignores_dev_sink(self):
        from unittest.mock import MagicMock, Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch("app.integrations.evolution.settings") as mock_settings:
            mock_settings.evolution_enabled = True
            mock_settings.evolution_dev_mode = False
            mock_settings.evolution_api_url = "https://evo.example.com"
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_instance = "test-instance"
            with patch("httpx.Client", return_value=mock_client):
                from app.integrations.evolution import send_message
                result = send_message("5511991747887", "Hello!", send_id="test")

        assert result is True
        mock_client.post.assert_called_once()
