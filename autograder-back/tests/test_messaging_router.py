"""Tests for messaging router — bulk WhatsApp messaging endpoints."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.hotmart_buyer import HotmartBuyer
from app.models.hotmart_product_mapping import HotmartProductMapping


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

    # Router queries:
    # 1. db.query(distinct(...)).all() -> [(1,), (2,)]
    # 2. db.query(Product).filter(Product.id.in_([1,2])).order_by(...).all() -> [p1, p2]
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

    # Router queries:
    # 1. db.query(Product).filter(Product.id == 1).first() -> course
    # 2. db.query(HotmartProductMapping.source_hotmart_product_id).filter(...).all() -> source IDs
    # 3. db.query(User, ...).join(...).filter(...).order_by(...).all() -> users_with_names
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


def test_list_recipients_403_for_professor(client_with_professor):
    """GIVEN professor user, WHEN GETs recipients, THEN 403."""
    client, db, prof = client_with_professor
    resp = client.get("/messaging/recipients?course_id=1")
    assert resp.status_code == 403


# ── POST /messaging/send ─────────────────────────────────────────────────


def test_send_bulk_success(client_with_admin):
    """GIVEN 3 users with whatsapp, WHEN admin sends, THEN 202 with task_id."""
    client, db, admin = client_with_admin

    users = []
    for i in range(3):
        u = Mock(spec=User)
        u.id = i + 1
        u.email = f"user{i}@test.com"
        u.whatsapp_number = f"551199999000{i}"
        users.append(u)

    # Router queries (no course_id):
    # 1. db.query(User).filter(User.id.in_([1,2,3])).all() -> users
    # 2. db.query(HotmartBuyer.user_id, HotmartBuyer.name).filter(...).all() -> []
    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.all.return_value = users
        else:
            result.filter.return_value.all.return_value = []
        return result

    db.query = mock_query

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
    assert data["task_id"] == "task-abc-123"
    assert data["total_recipients"] == 3
    assert data["skipped_no_phone"] == 0


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

    # Router queries (no course_id):
    # 1. db.query(User).filter(...).all() -> users
    # 2. db.query(HotmartBuyer.user_id, HotmartBuyer.name).filter(...).all() -> []
    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.all.return_value = users
        else:
            result.filter.return_value.all.return_value = []
        return result

    db.query = mock_query

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
