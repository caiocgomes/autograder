"""Tests for messaging schemas — VariationRequest, VariationResponse, extended BulkSendRequest."""
import pytest
from pydantic import ValidationError


# ── VariationRequest ─────────────────────────────────────────────────────


def test_variation_request_valid():
    from app.schemas.messaging import VariationRequest

    req = VariationRequest(message_template="Olá {nome}!", num_variations=6)
    assert req.message_template == "Olá {nome}!"
    assert req.num_variations == 6


def test_variation_request_default_num_variations():
    from app.schemas.messaging import VariationRequest

    req = VariationRequest(message_template="Olá {nome}!")
    assert req.num_variations == 6


def test_variation_request_rejects_num_below_3():
    from app.schemas.messaging import VariationRequest

    with pytest.raises(ValidationError):
        VariationRequest(message_template="Olá!", num_variations=2)


def test_variation_request_rejects_num_above_10():
    from app.schemas.messaging import VariationRequest

    with pytest.raises(ValidationError):
        VariationRequest(message_template="Olá!", num_variations=11)


def test_variation_request_rejects_empty_template():
    from app.schemas.messaging import VariationRequest

    with pytest.raises(ValidationError):
        VariationRequest(message_template="", num_variations=6)


def test_variation_request_rejects_unknown_variables():
    from app.schemas.messaging import VariationRequest

    with pytest.raises(ValidationError, match="saldo_bancario"):
        VariationRequest(message_template="Olá {saldo_bancario}!", num_variations=6)


def test_variation_request_accepts_known_variables():
    from app.schemas.messaging import VariationRequest

    req = VariationRequest(
        message_template="{nome}, turma {turma}, email {email}, oi {primeiro_nome}!",
        num_variations=3,
    )
    assert "{nome}" in req.message_template


# ── VariationResponse ────────────────────────────────────────────────────


def test_variation_response_valid():
    from app.schemas.messaging import VariationResponse

    resp = VariationResponse(
        variations=["Oi {nome}!", "E aí {nome}!"],
        original="Olá {nome}!",
    )
    assert len(resp.variations) == 2
    assert resp.original == "Olá {nome}!"
    assert resp.warning is None


def test_variation_response_with_warning():
    from app.schemas.messaging import VariationResponse

    resp = VariationResponse(
        variations=["Oi {nome}!"],
        original="Olá {nome}!",
        warning="Apenas 1 variação válida gerada (solicitadas 3).",
    )
    assert resp.warning is not None


# ── BulkSendRequest with variations ──────────────────────────────────────


def test_bulk_send_request_without_variations():
    from app.schemas.messaging import BulkSendRequest

    req = BulkSendRequest(
        user_ids=[1, 2, 3],
        message_template="Olá {nome}!",
    )
    assert req.variations is None


def test_bulk_send_request_with_variations():
    from app.schemas.messaging import BulkSendRequest

    req = BulkSendRequest(
        user_ids=[1, 2, 3],
        message_template="Olá {nome}!",
        variations=["Oi {nome}!", "E aí {nome}!"],
    )
    assert len(req.variations) == 2


def test_bulk_send_request_rejects_variation_with_unknown_variable():
    from app.schemas.messaging import BulkSendRequest

    with pytest.raises(ValidationError, match="saldo"):
        BulkSendRequest(
            user_ids=[1, 2, 3],
            message_template="Olá {nome}!",
            variations=["Oi {nome}!", "Saldo: {saldo}"],
        )


def test_bulk_send_request_accepts_variation_with_known_variables():
    from app.schemas.messaging import BulkSendRequest

    req = BulkSendRequest(
        user_ids=[1, 2, 3],
        message_template="Olá {nome}!",
        variations=["{nome}, turma {turma}!", "Oi {primeiro_nome}!"],
    )
    assert len(req.variations) == 2
