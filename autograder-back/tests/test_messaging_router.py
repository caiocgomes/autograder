"""Tests for messaging router — bulk WhatsApp messaging endpoints."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from app.models.user import User, UserRole, LifecycleStatus
from app.models.product import Product
from app.models.hotmart_buyer import HotmartBuyer
from app.models.hotmart_product_mapping import HotmartProductMapping
from app.models.message_campaign import (
    MessageCampaign,
    MessageRecipient,
    CampaignStatus,
    RecipientStatus,
)


# ── GET /messaging/courses ───────────────────────────────────────────────


def test_list_courses(client_with_admin):
    """GIVEN courses exist as product mapping targets, WHEN admin GETs courses, THEN returns them."""
    client, db, admin = client_with_admin

    p1 = Mock(spec=Product)
    p1.id = 1
    p1.name = "O Senhor das LLMs"
    p2 = Mock(spec=Product)
    p2.id = 2
    p2.name = "De analista a CDO"

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.all.return_value = [(1,), (2,)]
        else:
            result.filter.return_value.order_by.return_value.all.return_value = [p1, p2]
        return result

    db.query = mock_query

    resp = client.get("/messaging/courses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "O Senhor das LLMs"


def test_list_courses_403_for_student(client_with_student):
    """GIVEN student user, WHEN GETs courses, THEN 403."""
    client, db, student = client_with_student
    resp = client.get("/messaging/courses")
    assert resp.status_code == 403


# ── GET /messaging/recipients ────────────────────────────────────────────


def test_list_recipients_by_course(client_with_admin):
    """GIVEN students bought course products, WHEN admin GETs recipients, THEN returns them."""
    client, db, admin = client_with_admin

    course = Mock(spec=Product)
    course.id = 1
    course.name = "LLMs"

    users_with_names = [
        (Mock(spec=User, id=10, email="joao@test.com", whatsapp_number="5511999990001"), "João Silva"),
        (Mock(spec=User, id=11, email="maria@test.com", whatsapp_number=None), "Maria Santos"),
    ]

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = course
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = [("4141338",), ("6626505",)]
        else:
            result.join.return_value.filter.return_value.order_by.return_value.all.return_value = users_with_names
        return result

    db.query = mock_query

    resp = client.get("/messaging/recipients?course_id=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "João Silva"
    assert data[0]["has_whatsapp"] is True
    assert data[1]["has_whatsapp"] is False


def test_list_recipients_403_for_student(client_with_student):
    """GIVEN student user, WHEN GETs recipients, THEN 403."""
    client, db, student = client_with_student
    resp = client.get("/messaging/recipients?course_id=1")
    assert resp.status_code == 403


def test_list_recipients_filtered_by_lifecycle_status(client_with_admin):
    """GIVEN students with different lifecycle_status, WHEN admin filters by pending_onboarding, THEN returns only matching."""
    client, db, admin = client_with_admin

    course = Mock(spec=Product)
    course.id = 1

    user_pending = Mock(spec=User, id=10, email="pending@test.com", whatsapp_number="5511999990001", lifecycle_status=LifecycleStatus.PENDING_ONBOARDING)

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = course
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = [("4141338",)]
        else:
            result.join.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
                (user_pending, "Pending User")
            ]
        return result

    db.query = mock_query

    resp = client.get("/messaging/recipients?course_id=1&lifecycle_status=pending_onboarding")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Pending User"


def test_list_recipients_invalid_lifecycle_status(client_with_admin):
    """GIVEN invalid lifecycle_status, WHEN admin filters, THEN 422."""
    client, db, admin = client_with_admin

    course = Mock(spec=Product)
    course.id = 1

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = course
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = [("4141338",)]
        return result

    db.query = mock_query

    resp = client.get("/messaging/recipients?course_id=1&lifecycle_status=banana")
    assert resp.status_code == 422


def test_list_recipients_403_for_professor(client_with_professor):
    """GIVEN professor user, WHEN GETs recipients, THEN 403."""
    client, db, prof = client_with_professor
    resp = client.get("/messaging/recipients?course_id=1")
    assert resp.status_code == 403


# ── POST /messaging/send ─────────────────────────────────────────────────


def _setup_send_mocks(db, users, buyer_names=None):
    """Helper: set up db.query mocks for send endpoint."""
    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            # db.query(User).filter(User.id.in_([...])).all()
            result.filter.return_value.all.return_value = users
        else:
            # db.query(HotmartBuyer...).filter(...).all()
            result.filter.return_value.all.return_value = buyer_names or []
        return result

    db.query = mock_query

    # Mock campaign ID assignment on flush
    added_objects = []
    original_add = db.add

    def track_add(obj):
        added_objects.append(obj)

    db.add = track_add

    def set_campaign_id():
        for obj in added_objects:
            if isinstance(obj, MessageCampaign) and obj.id is None:
                obj.id = 42

    db.flush = Mock(side_effect=lambda: set_campaign_id())

    def refresh_obj(obj):
        if isinstance(obj, MessageCampaign):
            if obj.id is None:
                obj.id = 42

    db.refresh = Mock(side_effect=refresh_obj)


def test_send_bulk_creates_campaign(client_with_admin):
    """GIVEN 3 users with whatsapp, WHEN admin sends, THEN 202 with campaign_id."""
    client, db, admin = client_with_admin

    users = []
    for i in range(3):
        u = Mock(spec=User)
        u.id = i + 1
        u.email = f"user{i}@test.com"
        u.whatsapp_number = f"551199999000{i}"
        users.append(u)

    _setup_send_mocks(db, users)

    with patch("app.routers.messaging.celery_app") as mock_celery:
        mock_task = Mock()
        mock_task.id = "task-abc-123"
        mock_celery.send_task.return_value = mock_task

        resp = client.post("/messaging/send", json={
            "user_ids": [1, 2, 3],
            "message_template": "Olá {nome}, tudo bem?",
        })

    assert resp.status_code == 202
    data = resp.json()
    assert data["campaign_id"] == 42
    assert data["task_id"] == "task-abc-123"
    assert data["total_recipients"] == 3
    assert data["skipped_no_phone"] == 0

    # Verify celery was called with campaign_id
    mock_celery.send_task.assert_called_once()
    call_args = mock_celery.send_task.call_args
    assert call_args[1]["args"] == [42, "Olá {nome}, tudo bem?"]


def test_send_bulk_skips_no_whatsapp(client_with_admin):
    """GIVEN 3 users, 1 without whatsapp, WHEN admin sends, THEN skipped reported."""
    client, db, admin = client_with_admin

    users = []
    for i, phone in enumerate(["5511999990001", None, "5511999990003"]):
        u = Mock(spec=User)
        u.id = i + 1
        u.email = f"user{i}@test.com"
        u.whatsapp_number = phone
        users.append(u)

    _setup_send_mocks(db, users)

    with patch("app.routers.messaging.celery_app") as mock_celery:
        mock_task = Mock()
        mock_task.id = "task-xyz"
        mock_celery.send_task.return_value = mock_task

        resp = client.post("/messaging/send", json={
            "user_ids": [1, 2, 3],
            "message_template": "Hello!",
        })

    assert resp.status_code == 202
    data = resp.json()
    assert data["campaign_id"] == 42
    assert data["total_recipients"] == 2
    assert data["skipped_no_phone"] == 1
    assert data["skipped_users"][0]["id"] == 2
    assert data["skipped_users"][0]["reason"] == "no_whatsapp"


def test_send_rejects_unknown_template_variable(client_with_admin):
    """GIVEN template with unknown variable, WHEN admin sends, THEN 422."""
    client, db, admin = client_with_admin

    resp = client.post("/messaging/send", json={
        "user_ids": [1],
        "message_template": "Olá {saldo_bancario}",
    })

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any("saldo_bancario" in str(e) for e in detail) if isinstance(detail, list) else "saldo_bancario" in str(detail)


def test_send_rejects_empty_user_ids(client_with_admin):
    """GIVEN empty user_ids, WHEN admin sends, THEN 422."""
    client, db, admin = client_with_admin

    resp = client.post("/messaging/send", json={
        "user_ids": [],
        "message_template": "Hello!",
    })

    assert resp.status_code == 422


def test_send_rejects_empty_template(client_with_admin):
    """GIVEN empty message_template, WHEN admin sends, THEN 422."""
    client, db, admin = client_with_admin

    resp = client.post("/messaging/send", json={
        "user_ids": [1],
        "message_template": "",
    })

    assert resp.status_code == 422


def test_send_403_for_student(client_with_student):
    """GIVEN student user, WHEN sends, THEN 403."""
    client, db, student = client_with_student

    resp = client.post("/messaging/send", json={
        "user_ids": [1],
        "message_template": "Hello!",
    })

    assert resp.status_code == 403


def test_send_403_for_professor(client_with_professor):
    """GIVEN professor user, WHEN sends, THEN 403."""
    client, db, prof = client_with_professor

    resp = client.post("/messaging/send", json={
        "user_ids": [1],
        "message_template": "Hello!",
    })

    assert resp.status_code == 403


# ── POST /messaging/send with variations ─────────────────────────────────


def test_send_bulk_with_variations(client_with_admin):
    """GIVEN variations provided, WHEN admin sends, THEN 202 and celery receives variations."""
    client, db, admin = client_with_admin

    users = []
    for i in range(3):
        u = Mock(spec=User)
        u.id = i + 1
        u.email = f"user{i}@test.com"
        u.whatsapp_number = f"551199999000{i}"
        users.append(u)

    _setup_send_mocks(db, users)

    with patch("app.routers.messaging.celery_app") as mock_celery:
        mock_task = Mock()
        mock_task.id = "task-var-123"
        mock_celery.send_task.return_value = mock_task

        resp = client.post("/messaging/send", json={
            "user_ids": [1, 2, 3],
            "message_template": "Olá {nome}!",
            "variations": ["Oi {nome}!", "E aí {nome}!", "Fala {nome}!"],
        })

    assert resp.status_code == 202
    data = resp.json()
    assert data["campaign_id"] == 42
    assert data["total_recipients"] == 3

    # Verify celery was called with variations in kwargs
    call_args = mock_celery.send_task.call_args
    assert call_args[1]["kwargs"]["variations"] == ["Oi {nome}!", "E aí {nome}!", "Fala {nome}!"]


def test_send_bulk_without_variations_backwards_compatible(client_with_admin):
    """GIVEN no variations, WHEN admin sends, THEN celery called without variations (backwards compat)."""
    client, db, admin = client_with_admin

    users = [Mock(spec=User, id=1, email="u@test.com", whatsapp_number="5511999990001")]
    _setup_send_mocks(db, users)

    with patch("app.routers.messaging.celery_app") as mock_celery:
        mock_task = Mock()
        mock_task.id = "task-no-var"
        mock_celery.send_task.return_value = mock_task

        resp = client.post("/messaging/send", json={
            "user_ids": [1],
            "message_template": "Hello!",
        })

    assert resp.status_code == 202

    call_args = mock_celery.send_task.call_args
    # variations should be None or not in kwargs
    variations = call_args[1].get("kwargs", {}).get("variations")
    assert variations is None


def test_send_rejects_variation_with_unknown_variable(client_with_admin):
    """GIVEN variation with unknown variable, WHEN admin sends, THEN 422."""
    client, db, admin = client_with_admin

    resp = client.post("/messaging/send", json={
        "user_ids": [1],
        "message_template": "Olá {nome}!",
        "variations": ["Oi {nome}!", "Saldo: {saldo}"],
    })

    assert resp.status_code == 422


# ── GET /messaging/campaigns ────────────────────────────────────────────


def _make_campaign(id, template="Hello", status=CampaignStatus.COMPLETED, total=10, sent=10, failed=0):
    """Helper: create a mock MessageCampaign."""
    from datetime import datetime, timezone
    c = Mock(spec=MessageCampaign)
    c.id = id
    c.message_template = template
    c.course_name = "Python"
    c.total_recipients = total
    c.sent_count = sent
    c.failed_count = failed
    c.status = status
    c.created_at = datetime(2026, 2, 22, tzinfo=timezone.utc)
    c.completed_at = datetime(2026, 2, 22, tzinfo=timezone.utc)
    return c


def test_list_campaigns(client_with_admin):
    """GIVEN campaigns exist, WHEN admin lists, THEN returns them ordered by created_at desc."""
    client, db, admin = client_with_admin

    campaigns = [_make_campaign(1), _make_campaign(2)]

    db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = campaigns

    resp = client.get("/messaging/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[0]["status"] == "completed"


def test_list_campaigns_with_status_filter(client_with_admin):
    """GIVEN campaigns exist, WHEN admin filters by status, THEN only matching returned."""
    client, db, admin = client_with_admin

    campaigns = [_make_campaign(1, status=CampaignStatus.FAILED)]

    db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = campaigns

    resp = client.get("/messaging/campaigns?status=failed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "failed"


def test_list_campaigns_403_for_professor(client_with_professor):
    """GIVEN professor user, WHEN lists campaigns, THEN 403."""
    client, db, prof = client_with_professor
    resp = client.get("/messaging/campaigns")
    assert resp.status_code == 403


# ── GET /messaging/campaigns/{id} ────────────────────────────────────────


def test_get_campaign_detail(client_with_admin):
    """GIVEN campaign with recipients, WHEN admin gets detail, THEN returns full info."""
    client, db, admin = client_with_admin
    from datetime import datetime, timezone

    campaign = _make_campaign(42, template="Olá {nome}")

    r1 = Mock(spec=MessageRecipient)
    r1.user_id = 1
    r1.name = "João"
    r1.phone = "5511999990001"
    r1.status = RecipientStatus.SENT
    r1.resolved_message = "Olá João"
    r1.sent_at = datetime(2026, 2, 22, tzinfo=timezone.utc)
    r1.error_message = None

    r2 = Mock(spec=MessageRecipient)
    r2.user_id = 2
    r2.name = "Maria"
    r2.phone = "5511999990002"
    r2.status = RecipientStatus.FAILED
    r2.resolved_message = "Olá Maria"
    r2.sent_at = None
    r2.error_message = "send_message returned False"

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        else:
            result.filter.return_value.order_by.return_value.all.return_value = [r1, r2]
        return result

    db.query = mock_query

    resp = client.get("/messaging/campaigns/42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 42
    assert data["message_template"] == "Olá {nome}"
    assert len(data["recipients"]) == 2
    assert data["recipients"][0]["status"] == "sent"
    assert data["recipients"][1]["status"] == "failed"
    assert data["recipients"][1]["error_message"] == "send_message returned False"


def test_get_campaign_404(client_with_admin):
    """GIVEN campaign doesn't exist, WHEN admin gets detail, THEN 404."""
    client, db, admin = client_with_admin

    db.query.return_value.filter.return_value.first.return_value = None

    resp = client.get("/messaging/campaigns/999")
    assert resp.status_code == 404


# ── POST /messaging/campaigns/{id}/retry ─────────────────────────────────


def test_retry_campaign_success(client_with_admin):
    """GIVEN campaign with failed recipients, WHEN admin retries, THEN 202."""
    client, db, admin = client_with_admin

    campaign = Mock(spec=MessageCampaign)
    campaign.id = 42
    campaign.status = CampaignStatus.PARTIAL_FAILURE
    campaign.message_template = "Hello {nome}"
    campaign.failed_count = 2
    campaign.throttle_min_seconds = 15.0
    campaign.throttle_max_seconds = 25.0

    r1 = Mock(spec=MessageRecipient)
    r1.status = RecipientStatus.FAILED
    r1.error_message = "some error"
    r2 = Mock(spec=MessageRecipient)
    r2.status = RecipientStatus.FAILED
    r2.error_message = "another error"

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        else:
            result.filter.return_value.all.return_value = [r1, r2]
        return result

    db.query = mock_query

    with patch("app.routers.messaging.celery_app") as mock_celery:
        resp = client.post("/messaging/campaigns/42/retry")

    assert resp.status_code == 202
    data = resp.json()
    assert data["retrying"] == 2
    assert data["campaign_id"] == 42

    # Recipients should be reset to pending
    assert r1.status == RecipientStatus.PENDING
    assert r1.error_message is None
    assert r2.status == RecipientStatus.PENDING

    # Campaign status should be sending
    assert campaign.status == CampaignStatus.SENDING
    assert campaign.failed_count == 0


def test_retry_campaign_no_failures(client_with_admin):
    """GIVEN campaign with no failed recipients, WHEN admin retries, THEN 400."""
    client, db, admin = client_with_admin

    campaign = Mock(spec=MessageCampaign)
    campaign.id = 42
    campaign.status = CampaignStatus.COMPLETED

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        else:
            result.filter.return_value.all.return_value = []
        return result

    db.query = mock_query

    resp = client.post("/messaging/campaigns/42/retry")
    assert resp.status_code == 400


def test_retry_campaign_still_sending(client_with_admin):
    """GIVEN campaign still sending, WHEN admin retries, THEN 409."""
    client, db, admin = client_with_admin

    campaign = Mock(spec=MessageCampaign)
    campaign.id = 42
    campaign.status = CampaignStatus.SENDING

    db.query.return_value.filter.return_value.first.return_value = campaign

    resp = client.post("/messaging/campaigns/42/retry")
    assert resp.status_code == 409


def test_retry_campaign_not_found(client_with_admin):
    """GIVEN campaign doesn't exist, WHEN admin retries, THEN 404."""
    client, db, admin = client_with_admin

    db.query.return_value.filter.return_value.first.return_value = None

    resp = client.post("/messaging/campaigns/999/retry")
    assert resp.status_code == 404
