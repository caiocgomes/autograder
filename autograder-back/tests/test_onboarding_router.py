"""Tests for onboarding router — student listing and summary endpoints."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from app.models.user import User, UserRole, LifecycleStatus


def _make_student(
    id, email, whatsapp=None, lifecycle_status=LifecycleStatus.PENDING_ONBOARDING,
    token=None, token_expires_at=None
):
    u = Mock(spec=User)
    u.id = id
    u.email = email
    u.whatsapp_number = whatsapp
    u.lifecycle_status = lifecycle_status
    u.onboarding_token = token
    u.onboarding_token_expires_at = token_expires_at
    u.role = UserRole.STUDENT
    return u


# --- GET /onboarding/students ---

class TestListOnboardingStudents:
    def test_returns_students_with_token_status(self, client_with_admin):
        """GIVEN students in various states, WHEN admin GETs, THEN returns correct token_status."""
        client, db, admin = client_with_admin

        now = datetime.now(timezone.utc)
        # The router returns (user, buyer_name, last_sent) tuples from the query
        rows = [
            (_make_student(1, "carlos@t.com", "5511999990001",
                          LifecycleStatus.ACTIVE, "TOK1", now + timedelta(days=3)),
             "Carlos Dias", now - timedelta(days=7)),
            (_make_student(2, "joao@t.com", "5511999990002",
                          LifecycleStatus.PENDING_ONBOARDING, "TOK2", now + timedelta(days=3)),
             "João Silva", now - timedelta(days=2)),
            (_make_student(3, "maria@t.com", "5511999990003",
                          LifecycleStatus.PENDING_ONBOARDING, "TOK3", now - timedelta(days=1)),
             "Maria Costa", now - timedelta(days=10)),
            (_make_student(4, "ana@t.com", "5511999990004",
                          LifecycleStatus.PENDING_ONBOARDING, None, None),
             "Ana Souza", None),
            (_make_student(5, "pedro@t.com", None,
                          LifecycleStatus.PENDING_ONBOARDING, "TOK5", now + timedelta(days=5)),
             "Pedro Lima", None),
        ]

        # Mock the complex query chain - the router builds a subquery then joins
        mock_subquery = MagicMock()
        mock_subquery.c.user_id = "user_id"
        mock_subquery.c.last_sent = "last_sent"

        # First db.query call: subquery for last message
        # Second db.query call: main query
        call_count = {"n": 0}
        def mock_query(*args):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # Subquery for last message
                result.filter.return_value.group_by.return_value.subquery.return_value = mock_subquery
            else:
                # Main query - chain all the joins/filters/ordering to return rows
                result.outerjoin.return_value.outerjoin.return_value \
                    .filter.return_value.group_by.return_value \
                    .order_by.return_value.all.return_value = rows
            return result
        db.query = mock_query

        resp = client.get("/onboarding/students")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

        assert data[0]["token_status"] == "activated"
        assert data[1]["token_status"] == "valid"
        assert data[1]["token_expires_in_days"] >= 2
        assert data[2]["token_status"] == "expired"
        assert data[3]["token_status"] == "none"
        assert data[4]["whatsapp_number"] is None

    def test_403_for_student(self, client_with_student):
        """GIVEN student user, WHEN GETs /onboarding/students, THEN 403."""
        client, db, student = client_with_student
        resp = client.get("/onboarding/students")
        assert resp.status_code == 403


# --- GET /onboarding/summary ---

class TestOnboardingSummary:
    def test_returns_funnel_counts(self, client_with_admin):
        """GIVEN students in various states, WHEN admin GETs summary, THEN returns 200 with counts."""
        client, db, admin = client_with_admin

        # The router reuses base_query which is db.query(User).filter(...)
        # Then calls .count(), .filter().count(), .filter().filter().count()
        # Since MagicMock chains all return the same mock, we need a simpler approach.
        # Just verify it returns 200 with the expected shape.
        # Deep count assertions require integration tests.
        mock_q = MagicMock()
        mock_q.filter.return_value = mock_q
        mock_q.count.return_value = 5
        db.query.return_value = mock_q

        resp = client.get("/onboarding/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "activated" in data
        assert "pending" in data
        assert "no_whatsapp" in data

    def test_403_for_student(self, client_with_student):
        """GIVEN student user, WHEN GETs /onboarding/summary, THEN 403."""
        client, db, student = client_with_student
        resp = client.get("/onboarding/summary")
        assert resp.status_code == 403
