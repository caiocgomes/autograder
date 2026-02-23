"""Tests for admin settings router."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from app.models.system_settings import SystemSettings


class TestGetSettings:
    def test_get_settings_empty(self, client_with_admin):
        client, mock_db, _ = client_with_admin
        mock_db.query.return_value.first.return_value = None

        response = client.get("/admin/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["openai_configured"] is False
        assert data["anthropic_configured"] is False
        assert data["openai_api_key_masked"] == ""
        assert data["anthropic_api_key_masked"] == ""

    @patch("app.routers.admin_settings.decrypt_value")
    def test_get_settings_with_tokens(self, mock_decrypt, client_with_admin):
        client, mock_db, _ = client_with_admin

        row = Mock(spec=SystemSettings)
        row.openai_api_key_encrypted = "encrypted-openai"
        row.anthropic_api_key_encrypted = "encrypted-anthropic"
        mock_db.query.return_value.first.return_value = row

        mock_decrypt.side_effect = lambda x: {
            "encrypted-openai": "sk-proj-abc123456789",
            "encrypted-anthropic": "sk-ant-xyz987654321",
            "": "",
        }.get(x, "")

        response = client.get("/admin/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["openai_configured"] is True
        assert data["anthropic_configured"] is True
        assert data["openai_api_key_masked"] == "sk-proj-ab****"
        assert data["anthropic_api_key_masked"] == "sk-ant-xyz****"

    def test_get_settings_forbidden_for_professor(self, client_with_professor):
        client, _, _ = client_with_professor
        response = client.get("/admin/settings")
        assert response.status_code == 403


class TestUpdateSettings:
    @patch("app.routers.admin_settings.decrypt_value")
    @patch("app.routers.admin_settings.encrypt_value")
    def test_update_creates_row_if_missing(self, mock_encrypt, mock_decrypt, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.first.return_value = None
        mock_encrypt.return_value = "encrypted-new"
        mock_decrypt.return_value = "sk-proj-newkey1234"

        def fake_refresh(obj):
            obj.openai_api_key_encrypted = "encrypted-new"
            obj.anthropic_api_key_encrypted = None
            obj.updated_at = datetime.now()

        mock_db.refresh.side_effect = fake_refresh

        response = client.put("/admin/settings", json={"openai_api_key": "sk-proj-newkey1234"})
        assert response.status_code == 200
        mock_db.add.assert_called_once()

    @patch("app.routers.admin_settings.decrypt_value")
    @patch("app.routers.admin_settings.encrypt_value")
    def test_partial_update(self, mock_encrypt, mock_decrypt, client_with_admin):
        client, mock_db, _ = client_with_admin

        row = Mock(spec=SystemSettings)
        row.openai_api_key_encrypted = "old-encrypted"
        row.anthropic_api_key_encrypted = "existing-encrypted"
        mock_db.query.return_value.first.return_value = row

        mock_encrypt.return_value = "new-encrypted"
        mock_decrypt.side_effect = lambda x: {
            "new-encrypted": "sk-proj-updated123",
            "existing-encrypted": "sk-ant-existing123",
            "": "",
        }.get(x, "")

        response = client.put("/admin/settings", json={"openai_api_key": "sk-proj-updated123"})
        assert response.status_code == 200
        assert row.openai_api_key_encrypted == "new-encrypted"
        assert row.anthropic_api_key_encrypted == "existing-encrypted"

    @patch("app.routers.admin_settings.decrypt_value")
    def test_clear_token(self, mock_decrypt, client_with_admin):
        client, mock_db, _ = client_with_admin

        row = Mock(spec=SystemSettings)
        row.openai_api_key_encrypted = "old-encrypted"
        row.anthropic_api_key_encrypted = None
        mock_db.query.return_value.first.return_value = row
        mock_decrypt.return_value = ""

        response = client.put("/admin/settings", json={"openai_api_key": ""})
        assert response.status_code == 200
        assert row.openai_api_key_encrypted is None

    def test_update_forbidden_for_professor(self, client_with_professor):
        client, _, _ = client_with_professor
        response = client.put("/admin/settings", json={"openai_api_key": "sk-test"})
        assert response.status_code == 403

    def test_update_forbidden_for_student(self, client_with_student):
        client, _, _ = client_with_student
        response = client.put("/admin/settings", json={"openai_api_key": "sk-test"})
        assert response.status_code == 403
