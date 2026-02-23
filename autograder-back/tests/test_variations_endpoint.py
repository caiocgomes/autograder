"""Tests for POST /messaging/variations endpoint."""
import pytest
from unittest.mock import patch, Mock


# ── POST /messaging/variations ──────────────────────────────────────────


@patch("app.routers.messaging.generate_variations")
def test_variations_success(mock_gen, client_with_admin):
    """GIVEN valid template, WHEN admin requests variations, THEN 200 with variations list."""
    client, db, admin = client_with_admin

    mock_gen.return_value = [
        "Oi {nome}! Aula amanhã.",
        "E aí {nome}! Amanhã tem aula.",
        "{nome}, lembrete: aula amanhã.",
    ]

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {nome}! Aula amanhã.",
        "num_variations": 3,
    })

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["variations"]) == 3
    assert data["original"] == "Olá {nome}! Aula amanhã."
    assert data["warning"] is None
    mock_gen.assert_called_once()
    args = mock_gen.call_args[0]
    assert args[0] == "Olá {nome}! Aula amanhã."
    assert args[1] == 3


@patch("app.routers.messaging.generate_variations")
def test_variations_default_count(mock_gen, client_with_admin):
    """GIVEN no num_variations, WHEN admin requests, THEN defaults to 6."""
    client, db, admin = client_with_admin

    mock_gen.return_value = [f"Variação {i} {{nome}}" for i in range(6)]

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {nome}!",
    })

    assert resp.status_code == 200
    mock_gen.assert_called_once()
    args = mock_gen.call_args[0]
    assert args[0] == "Olá {nome}!"
    assert args[1] == 6


def test_variations_rejects_empty_template(client_with_admin):
    """GIVEN empty template, WHEN admin requests, THEN 422."""
    client, db, admin = client_with_admin

    resp = client.post("/messaging/variations", json={
        "message_template": "",
        "num_variations": 3,
    })

    assert resp.status_code == 422


def test_variations_rejects_unknown_variables(client_with_admin):
    """GIVEN template with unknown variable, WHEN admin requests, THEN 422."""
    client, db, admin = client_with_admin

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {saldo_bancario}!",
        "num_variations": 3,
    })

    assert resp.status_code == 422


def test_variations_rejects_num_below_3(client_with_admin):
    """GIVEN num_variations=2, WHEN admin requests, THEN 422."""
    client, db, admin = client_with_admin

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {nome}!",
        "num_variations": 2,
    })

    assert resp.status_code == 422


def test_variations_rejects_num_above_10(client_with_admin):
    """GIVEN num_variations=11, WHEN admin requests, THEN 422."""
    client, db, admin = client_with_admin

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {nome}!",
        "num_variations": 11,
    })

    assert resp.status_code == 422


@patch("app.routers.messaging.generate_variations")
def test_variations_api_error_returns_502(mock_gen, client_with_admin):
    """GIVEN Anthropic API fails, WHEN admin requests, THEN 502."""
    client, db, admin = client_with_admin

    mock_gen.side_effect = Exception("API connection error")

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {nome}!",
        "num_variations": 3,
    })

    assert resp.status_code == 502
    assert "Falha ao gerar variações" in resp.json()["detail"]


@patch("app.routers.messaging.generate_variations")
def test_variations_partial_result_includes_warning(mock_gen, client_with_admin):
    """GIVEN LLM returns fewer valid variations than requested, WHEN processed, THEN warning included."""
    client, db, admin = client_with_admin

    # Requested 5 but only got 3 valid
    mock_gen.return_value = [
        "Oi {nome}!",
        "E aí {nome}!",
        "{nome}, oi!",
    ]

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {nome}!",
        "num_variations": 5,
    })

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["variations"]) == 3
    assert data["warning"] is not None


def test_variations_403_for_student(client_with_student):
    """GIVEN student user, WHEN requests variations, THEN 403."""
    client, db, student = client_with_student

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {nome}!",
        "num_variations": 3,
    })

    assert resp.status_code == 403


def test_variations_403_for_professor(client_with_professor):
    """GIVEN professor user, WHEN requests variations, THEN 403."""
    client, db, prof = client_with_professor

    resp = client.post("/messaging/variations", json={
        "message_template": "Olá {nome}!",
        "num_variations": 3,
    })

    assert resp.status_code == 403
