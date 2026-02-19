"""Tests for Hotmart integration module (app/integrations/hotmart.py)"""
import pytest
from app.integrations.hotmart import (
    validate_hottok,
    parse_payload,
    is_supported_event,
    PURCHASE_APPROVED,
    SUBSCRIPTION_CANCELLATION,
)


VALID_PAYLOAD = {
    "event": "PURCHASE_APPROVED",
    "data": {
        "buyer": {"email": "student@test.com"},
        "product": {"id": "12345"},
        "purchase": {"transaction": "ABC123"},
    },
}

CANCELLATION_PAYLOAD = {
    "event": "SUBSCRIPTION_CANCELLATION",
    "data": {
        "buyer": {"email": "student@test.com"},
        "product": {"id": "12345"},
        "purchase": {"transaction": "XYZ789"},
    },
}


class TestValidateHottok:
    def test_valid_token_matches(self):
        assert validate_hottok("my-secret", "my-secret") is True

    def test_invalid_token_does_not_match(self):
        assert validate_hottok("wrong-token", "my-secret") is False

    def test_empty_header_returns_false(self):
        assert validate_hottok("", "my-secret") is False

    def test_none_header_returns_false(self):
        assert validate_hottok(None, "my-secret") is False

    def test_empty_expected_token_returns_false(self):
        assert validate_hottok("my-secret", "") is False

    def test_none_expected_token_returns_false(self):
        assert validate_hottok("my-secret", None) is False


class TestParsePayload:
    def test_valid_purchase_approved_payload(self):
        result = parse_payload(VALID_PAYLOAD)
        assert result is not None
        assert result.event_type == PURCHASE_APPROVED
        assert result.buyer_email == "student@test.com"
        assert result.hotmart_product_id == "12345"
        assert result.transaction_id == "ABC123"
        assert result.raw_payload == VALID_PAYLOAD

    def test_valid_subscription_cancellation(self):
        result = parse_payload(CANCELLATION_PAYLOAD)
        assert result is not None
        assert result.event_type == SUBSCRIPTION_CANCELLATION
        assert result.buyer_email == "student@test.com"
        assert result.transaction_id == "XYZ789"

    def test_missing_buyer_email_returns_none(self):
        payload = {
            "event": "PURCHASE_APPROVED",
            "data": {
                "buyer": {},
                "product": {"id": "12345"},
                "purchase": {"transaction": "ABC123"},
            },
        }
        result = parse_payload(payload)
        assert result is None

    def test_exception_during_parsing_returns_none(self):
        # Pass something that will cause an AttributeError when .get() is called on a non-dict
        result = parse_payload({"event": "PURCHASE_APPROVED", "data": "not-a-dict"})
        assert result is None

    def test_missing_transaction_id_is_none(self):
        payload = {
            "event": "PURCHASE_APPROVED",
            "data": {
                "buyer": {"email": "student@test.com"},
                "product": {"id": "12345"},
            },
        }
        result = parse_payload(payload)
        assert result is not None
        assert result.transaction_id is None

    def test_product_id_coerced_to_string(self):
        payload = {
            "event": "PURCHASE_APPROVED",
            "data": {
                "buyer": {"email": "student@test.com"},
                "product": {"id": 99999},
                "purchase": {"transaction": "T1"},
            },
        }
        result = parse_payload(payload)
        assert result is not None
        assert result.hotmart_product_id == "99999"


class TestIsSupportedEvent:
    @pytest.mark.parametrize("event_type", [
        "PURCHASE_APPROVED",
        "PURCHASE_DELAYED",
        "PURCHASE_REFUNDED",
        "SUBSCRIPTION_CANCELLATION",
    ])
    def test_supported_events_return_true(self, event_type):
        assert is_supported_event(event_type) is True

    @pytest.mark.parametrize("event_type", [
        "UNKNOWN_EVENT",
        "PURCHASE_PENDING",
        "",
        "purchase_approved",  # lowercase should not match
    ])
    def test_unsupported_events_return_false(self, event_type):
        assert is_supported_event(event_type) is False
