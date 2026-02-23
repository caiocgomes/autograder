"""Tests for admin templates router — lifecycle message template CRUD."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from app.models.message_template import MessageTemplate, TemplateEventType


def _make_template(event_type=TemplateEventType.ONBOARDING, text="Oi {primeiro_nome}! Token: {token}"):
    from datetime import datetime, timezone
    t = Mock(spec=MessageTemplate)
    t.id = 1
    t.event_type = event_type
    t.template_text = text
    t.updated_at = datetime(2026, 2, 22, tzinfo=timezone.utc)
    t.updated_by = 3
    return t


# --- GET /admin/templates ---

class TestListTemplates:
    def test_returns_all_4_templates_with_defaults(self, client_with_admin):
        """GIVEN no templates in DB, WHEN admin GETs /admin/templates, THEN returns 4 defaults."""
        client, db, admin = client_with_admin
        db.query.return_value.all.return_value = []

        resp = client.get("/admin/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        event_types = {t["event_type"] for t in data}
        assert event_types == {"onboarding", "welcome", "welcome_back", "churn"}
        assert all(t["is_default"] for t in data)

    def test_returns_db_template_overriding_default(self, client_with_admin):
        """GIVEN onboarding template in DB, WHEN admin GETs, THEN that one is not default."""
        client, db, admin = client_with_admin
        db_template = _make_template()
        db.query.return_value.all.return_value = [db_template]

        resp = client.get("/admin/templates")
        assert resp.status_code == 200
        data = resp.json()
        onboarding = next(t for t in data if t["event_type"] == "onboarding")
        assert onboarding["is_default"] is False
        assert onboarding["template_text"] == "Oi {primeiro_nome}! Token: {token}"
        # Other 3 should still be defaults
        others = [t for t in data if t["event_type"] != "onboarding"]
        assert all(t["is_default"] for t in others)

    def test_403_for_student(self, client_with_student):
        """GIVEN student user, WHEN GETs /admin/templates, THEN 403."""
        client, db, student = client_with_student
        resp = client.get("/admin/templates")
        assert resp.status_code == 403


# --- PATCH /admin/templates/{event_type} ---

class TestUpdateTemplate:
    def test_upsert_creates_new_template(self, client_with_admin):
        """GIVEN no existing template, WHEN admin PATCHes, THEN creates new row."""
        client, db, admin = client_with_admin
        db.query.return_value.filter.return_value.first.return_value = None

        resp = client.patch(
            "/admin/templates/onboarding",
            json={"template_text": "Novo template: {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "onboarding"
        assert data["template_text"] == "Novo template: {token}"
        assert data["is_default"] is False
        db.add.assert_called_once()
        db.commit.assert_called()

    def test_upsert_updates_existing_template(self, client_with_admin):
        """GIVEN existing template, WHEN admin PATCHes, THEN updates it."""
        client, db, admin = client_with_admin
        existing = _make_template()
        db.query.return_value.filter.return_value.first.return_value = existing

        resp = client.patch(
            "/admin/templates/onboarding",
            json={"template_text": "Atualizado: {nome}"},
        )
        assert resp.status_code == 200
        assert existing.template_text == "Atualizado: {nome}"
        db.commit.assert_called()

    def test_rejects_invalid_variable(self, client_with_admin):
        """GIVEN template with unknown variable, WHEN admin PATCHes, THEN 422."""
        client, db, admin = client_with_admin
        resp = client.patch(
            "/admin/templates/onboarding",
            json={"template_text": "Olá {saldo_bancario}"},
        )
        assert resp.status_code == 422

    def test_rejects_token_variable_for_non_onboarding(self, client_with_admin):
        """GIVEN welcome template with {token}, WHEN admin PATCHes, THEN 422."""
        client, db, admin = client_with_admin
        resp = client.patch(
            "/admin/templates/welcome",
            json={"template_text": "Bem-vindo! Token: {token}"},
        )
        assert resp.status_code == 422

    def test_rejects_invalid_event_type(self, client_with_admin):
        """GIVEN invalid event type, WHEN admin PATCHes, THEN 422."""
        client, db, admin = client_with_admin
        resp = client.patch(
            "/admin/templates/invalid_type",
            json={"template_text": "test"},
        )
        assert resp.status_code == 422

    def test_403_for_student(self, client_with_student):
        """GIVEN student user, WHEN PATCHes template, THEN 403."""
        client, db, student = client_with_student
        resp = client.patch(
            "/admin/templates/onboarding",
            json={"template_text": "test"},
        )
        assert resp.status_code == 403


# --- DELETE /admin/templates/{event_type} ---

class TestDeleteTemplate:
    def test_deletes_existing_template(self, client_with_admin):
        """GIVEN existing template, WHEN admin DELETEs, THEN removes row."""
        client, db, admin = client_with_admin
        existing = _make_template()
        db.query.return_value.filter.return_value.first.return_value = existing

        resp = client.delete("/admin/templates/onboarding")
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "onboarding"
        assert data["is_default"] is True
        db.delete.assert_called_once_with(existing)
        db.commit.assert_called()

    def test_delete_nonexistent_returns_default(self, client_with_admin):
        """GIVEN no template in DB, WHEN admin DELETEs, THEN returns default (no error)."""
        client, db, admin = client_with_admin
        db.query.return_value.filter.return_value.first.return_value = None

        resp = client.delete("/admin/templates/onboarding")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_default"] is True

    def test_rejects_invalid_event_type(self, client_with_admin):
        """GIVEN invalid event type, WHEN admin DELETEs, THEN 422."""
        client, db, admin = client_with_admin
        resp = client.delete("/admin/templates/invalid_type")
        assert resp.status_code == 422

    def test_403_for_student(self, client_with_student):
        """GIVEN student user, WHEN DELETEs template, THEN 403."""
        client, db, student = client_with_student
        resp = client.delete("/admin/templates/onboarding")
        assert resp.status_code == 403
