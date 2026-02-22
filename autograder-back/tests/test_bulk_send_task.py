"""Tests for send_bulk_messages Celery task."""
import pytest
from unittest.mock import patch, call
from app.tasks import send_bulk_messages, resolve_template


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


# ── send_bulk_messages task ──────────────────────────────────────────────


def _make_recipient(user_id, phone, name="user@test.com", email="user@test.com", class_name=""):
    return {"user_id": user_id, "phone": phone, "name": name, "email": email, "class_name": class_name}


@patch("app.integrations.evolution.send_message")
@patch("time.sleep")
def test_send_all_success(mock_sleep, mock_send):
    """GIVEN 3 recipients, all succeed, THEN sent=3, failed=0."""
    mock_send.return_value = True

    recipients = [
        _make_recipient(1, "5511999990001"),
        _make_recipient(2, "5511999990002"),
        _make_recipient(3, "5511999990003"),
    ]

    result = send_bulk_messages(recipients, "Hello!")
    assert result == {"sent": 3, "failed": 0, "total": 3}
    assert mock_send.call_count == 3


@patch("app.integrations.evolution.send_message")
@patch("time.sleep")
def test_send_with_failure(mock_sleep, mock_send):
    """GIVEN 3 recipients, 2nd fails, THEN sent=2, failed=1, all processed."""
    mock_send.side_effect = [True, False, True]

    recipients = [
        _make_recipient(1, "5511999990001"),
        _make_recipient(2, "5511999990002"),
        _make_recipient(3, "5511999990003"),
    ]

    result = send_bulk_messages(recipients, "Hello!")
    assert result == {"sent": 2, "failed": 1, "total": 3}
    assert mock_send.call_count == 3  # all 3 processed, not aborted


@patch("app.integrations.evolution.send_message")
@patch("random.uniform", return_value=15.0)
@patch("time.sleep")
def test_throttling_between_sends(mock_sleep, mock_uniform, mock_send):
    """GIVEN 3 recipients, THEN random delay 10-30s called between sends (2 times, not after last)."""
    mock_send.return_value = True

    recipients = [
        _make_recipient(1, "5511999990001"),
        _make_recipient(2, "5511999990002"),
        _make_recipient(3, "5511999990003"),
    ]

    send_bulk_messages(recipients, "Hello!")
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(15.0)
    mock_uniform.assert_called_with(10, 30)


@patch("app.integrations.evolution.send_message")
@patch("time.sleep")
def test_variable_resolution(mock_sleep, mock_send):
    """GIVEN template with {nome} and {turma}, THEN resolved per recipient."""
    mock_send.return_value = True

    recipients = [
        _make_recipient(1, "5511999990001", name="joao@test.com", email="joao@test.com", class_name="Python 101"),
    ]

    send_bulk_messages(recipients, "Olá {nome}, sua turma {turma}")

    mock_send.assert_called_once_with("5511999990001", "Olá joao@test.com, sua turma Python 101")


@patch("app.integrations.evolution.send_message")
@patch("time.sleep")
def test_primeiro_nome_resolution(mock_sleep, mock_send):
    """GIVEN template with {primeiro_nome}, THEN resolved to first part of name."""
    mock_send.return_value = True

    recipients = [
        _make_recipient(1, "5511999990001", name="joao.silva@test.com", email="joao.silva@test.com"),
    ]

    send_bulk_messages(recipients, "Oi {primeiro_nome}")

    # primeiro_nome = name.split("@")[0].split()[0] = "joao.silva"
    mock_send.assert_called_once_with("5511999990001", "Oi joao.silva")


@patch("app.integrations.evolution.send_message")
@patch("time.sleep")
def test_single_recipient_no_sleep(mock_sleep, mock_send):
    """GIVEN 1 recipient, THEN no throttle sleep."""
    mock_send.return_value = True
    recipients = [_make_recipient(1, "5511999990001")]
    send_bulk_messages(recipients, "Hello!")
    mock_sleep.assert_not_called()
