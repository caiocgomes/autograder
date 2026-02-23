"""Tests for send_bulk_messages Celery task (V2 — campaign-based)."""
import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timezone
from app.tasks import send_bulk_messages, resolve_template
from app.models.message_campaign import (
    MessageCampaign,
    MessageRecipient,
    CampaignStatus,
    RecipientStatus,
)


# ── resolve_template ─────────────────────────────────────────────────────


def test_resolve_template_basic():
    result = resolve_template("Olá {nome}!", {"nome": "João", "email": "", "turma": "", "primeiro_nome": ""})
    assert result == "Olá João!"


def test_resolve_template_multiple_variables():
    result = resolve_template(
        "Olá {primeiro_nome}, sua turma {turma} começa amanhã",
        {"nome": "João Silva", "primeiro_nome": "João", "email": "joao@test.com", "turma": "Python 101"},
    )
    assert result == "Olá João, sua turma Python 101 começa amanhã"


def test_resolve_template_missing_variable_stays_empty():
    result = resolve_template("Turma: {turma}", {"nome": "", "primeiro_nome": "", "email": "", "turma": ""})
    assert result == "Turma: "


def test_resolve_template_no_variables():
    result = resolve_template("Mensagem sem variáveis", {"nome": "", "primeiro_nome": "", "email": "", "turma": ""})
    assert result == "Mensagem sem variáveis"


# ── send_bulk_messages task (V2) ─────────────────────────────────────────


def _make_mock_recipient(user_id, phone, name="User", status=RecipientStatus.PENDING):
    r = Mock(spec=MessageRecipient)
    r.user_id = user_id
    r.phone = phone
    r.name = name
    r.status = status
    r.resolved_message = None
    r.sent_at = None
    r.error_message = None
    return r


def _make_mock_campaign(id=42, total=3, sent=0, failed=0, course_name="Python"):
    c = Mock(spec=MessageCampaign)
    c.id = id
    c.status = CampaignStatus.SENDING
    c.total_recipients = total
    c.sent_count = sent
    c.failed_count = failed
    c.course_name = course_name
    c.completed_at = None
    return c


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_send_all_success(mock_session_cls, mock_send):
    """GIVEN 3 recipients, all succeed, THEN sent=3, campaign completed."""
    mock_send.return_value = True
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign()
    recipients = [
        _make_mock_recipient(1, "5511999990001", "João"),
        _make_mock_recipient(2, "5511999990002", "Maria"),
        _make_mock_recipient(3, "5511999990003", "Pedro"),
    ]

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = recipients
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep"), patch("random.uniform", return_value=15.0):
        result = send_bulk_messages(42, "Hello {nome}!")

    assert result["sent"] == 3
    assert result["failed"] == 0
    assert mock_send.call_count == 3

    # All recipients should be marked sent
    for r in recipients:
        assert r.status == RecipientStatus.SENT
        assert r.sent_at is not None
        assert r.resolved_message is not None

    # Campaign should be completed
    assert campaign.status == CampaignStatus.COMPLETED
    assert campaign.completed_at is not None


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_send_with_partial_failure(mock_session_cls, mock_send):
    """GIVEN 3 recipients, 2nd fails, THEN partial_failure status."""
    mock_send.side_effect = [True, False, True]
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign()
    recipients = [
        _make_mock_recipient(1, "5511999990001"),
        _make_mock_recipient(2, "5511999990002"),
        _make_mock_recipient(3, "5511999990003"),
    ]

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = recipients
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep"), patch("random.uniform", return_value=15.0):
        result = send_bulk_messages(42, "Hello!")

    assert result["sent"] == 2
    assert result["failed"] == 1

    assert recipients[0].status == RecipientStatus.SENT
    assert recipients[1].status == RecipientStatus.FAILED
    assert recipients[1].error_message is not None
    assert recipients[2].status == RecipientStatus.SENT

    assert campaign.status == CampaignStatus.PARTIAL_FAILURE


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_send_all_failed(mock_session_cls, mock_send):
    """GIVEN all sends fail, THEN campaign status is failed."""
    mock_send.return_value = False
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign(total=2)
    recipients = [
        _make_mock_recipient(1, "5511999990001"),
        _make_mock_recipient(2, "5511999990002"),
    ]

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = recipients
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep"), patch("random.uniform", return_value=15.0):
        result = send_bulk_messages(42, "Hello!")

    assert result["sent"] == 0
    assert result["failed"] == 2
    assert campaign.status == CampaignStatus.FAILED


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_throttling_between_sends(mock_session_cls, mock_send):
    """GIVEN 3 recipients, THEN sleep called between sends (2 times)."""
    mock_send.return_value = True
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign()
    recipients = [
        _make_mock_recipient(1, "5511999990001"),
        _make_mock_recipient(2, "5511999990002"),
        _make_mock_recipient(3, "5511999990003"),
    ]

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = recipients
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep") as mock_sleep, patch("random.uniform", return_value=15.0):
        send_bulk_messages(42, "Hello!")
        assert mock_sleep.call_count == 2


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_only_pending_processes_subset(mock_session_cls, mock_send):
    """GIVEN only_pending=True with 2 pending out of 5, THEN only 2 processed."""
    mock_send.return_value = True
    db = MagicMock()
    mock_session_cls.return_value = db

    # Campaign already has 3 sent from first run
    campaign = _make_mock_campaign(total=5, sent=3, failed=0)
    pending_recipients = [
        _make_mock_recipient(4, "5511999990004"),
        _make_mock_recipient(5, "5511999990005"),
    ]

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = pending_recipients
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep"), patch("random.uniform", return_value=15.0):
        result = send_bulk_messages(42, "Hello!", only_pending=True)

    assert result["sent"] == 2
    assert result["total"] == 2
    assert mock_send.call_count == 2


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_campaign_not_found(mock_session_cls, mock_send):
    """GIVEN campaign doesn't exist, THEN returns zeros."""
    db = MagicMock()
    mock_session_cls.return_value = db
    db.query.return_value.filter.return_value.first.return_value = None

    result = send_bulk_messages(999, "Hello!")
    assert result == {"sent": 0, "failed": 0, "total": 0}
    mock_send.assert_not_called()


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_resolved_message_persisted(mock_session_cls, mock_send):
    """GIVEN template with variables, THEN resolved_message is saved on recipient."""
    mock_send.return_value = True
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign(total=1, course_name="ML Avançado")
    recipient = _make_mock_recipient(1, "5511999990001", name="João Silva")

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = [recipient]
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep"):
        send_bulk_messages(42, "Olá {nome}, turma {turma}")

    assert recipient.resolved_message == "Olá João Silva, turma ML Avançado"


# ── send_bulk_messages with variations ───────────────────────────────────


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_send_with_variations_uses_random_choice(mock_session_cls, mock_send):
    """GIVEN variations provided, WHEN task runs, THEN each recipient gets a variation via random.choice."""
    mock_send.return_value = True
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign(total=3)
    recipients = [
        _make_mock_recipient(1, "5511999990001", "João"),
        _make_mock_recipient(2, "5511999990002", "Maria"),
        _make_mock_recipient(3, "5511999990003", "Pedro"),
    ]

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = recipients
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    variations = ["Oi {nome}!", "E aí {nome}!", "Fala {nome}!"]

    with patch("time.sleep"), patch("random.uniform", return_value=15.0):
        result = send_bulk_messages(42, "Olá {nome}!", variations=variations)

    assert result["sent"] == 3

    # Each recipient should have a resolved_message from one of the variations
    for r in recipients:
        assert r.resolved_message is not None
        # The resolved message should be from a variation, not the original template
        name = r.name
        possible = [f"Oi {name}!", f"E aí {name}!", f"Fala {name}!"]
        assert r.resolved_message in possible, f"Got '{r.resolved_message}', expected one of {possible}"


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_send_without_variations_uses_template(mock_session_cls, mock_send):
    """GIVEN no variations, WHEN task runs, THEN uses message_template (backwards compat)."""
    mock_send.return_value = True
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign(total=1, course_name="Python")
    recipient = _make_mock_recipient(1, "5511999990001", "João")

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = [recipient]
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep"):
        send_bulk_messages(42, "Olá {nome}!")

    assert recipient.resolved_message == "Olá João!"


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_send_with_empty_variations_uses_template(mock_session_cls, mock_send):
    """GIVEN empty variations list, WHEN task runs, THEN falls back to message_template."""
    mock_send.return_value = True
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign(total=1, course_name="Python")
    recipient = _make_mock_recipient(1, "5511999990001", "João")

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = [recipient]
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep"):
        send_bulk_messages(42, "Olá {nome}!", variations=[])

    assert recipient.resolved_message == "Olá João!"


# ── db commit behavior ──────────────────────────────────────────────────


@patch("app.integrations.evolution.send_message")
@patch("app.database.SessionLocal")
def test_db_commit_called_per_recipient(mock_session_cls, mock_send):
    """GIVEN 2 recipients, THEN db.commit() called at least 3 times (2 per-send + 1 final)."""
    mock_send.return_value = True
    db = MagicMock()
    mock_session_cls.return_value = db

    campaign = _make_mock_campaign(total=2)
    recipients = [
        _make_mock_recipient(1, "5511999990001"),
        _make_mock_recipient(2, "5511999990002"),
    ]

    call_count = {"n": 0}

    def mock_query(*args):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.filter.return_value.first.return_value = campaign
        elif call_count["n"] == 2:
            result.filter.return_value.all.return_value = recipients
        else:
            result.filter.return_value.first.return_value = campaign
        return result

    db.query = mock_query

    with patch("time.sleep"), patch("random.uniform", return_value=15.0):
        send_bulk_messages(42, "Hello!")

    # 2 commits (one per recipient) + 1 final commit for campaign status
    assert db.commit.call_count >= 3
