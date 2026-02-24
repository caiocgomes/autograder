"""
Evolution API client for WhatsApp message sending.

Addresses recipients by phone number (E.164 format) directly — no subscriber ID resolution needed.
"""
import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """
    Normalize a phone number to E.164-style digits only.

    Hotmart delivers Brazilian numbers without the country code (e.g. '11999999999').
    International numbers already include the country code and have 12+ digits.

    Rules (after stripping non-digits and leading zeros):
    - 10-11 digits → Brazilian number → prepend '55'
    - 12+ digits → already has country code → keep as-is
    - < 10 digits → too short, return as-is (will likely fail downstream)
    """
    digits = "".join(c for c in phone if c.isdigit()).lstrip("0")
    if len(digits) in (10, 11):
        return "55" + digits
    return digits


def send_message(phone: str, text: str, send_id: str | None = None) -> bool:
    """
    Send a WhatsApp text message via Evolution API.
    Phone numbers are normalized automatically (Brazilian numbers without country code
    get '55' prepended; international numbers with 12+ digits are kept as-is).
    Returns True on success, False on error.
    """
    if not settings.evolution_enabled:
        logger.info("Evolution API disabled. Skipping send_message to %s", phone)
        return True

    if settings.evolution_dev_mode:
        from app.integrations.evolution_dev import send_message as dev_send
        return dev_send(phone, text, send_id=send_id)

    if not phone:
        logger.warning("send_message called with empty phone number. Skipping.")
        return False

    phone = _normalize_phone(phone)

    url = f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance}"
    headers = {
        "apikey": settings.evolution_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "number": phone,
        "text": text,
    }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, headers=headers, json=payload)
        if resp.status_code == 200 or resp.status_code == 201:
            return True
        logger.error("send_message failed: %s %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("send_message exception: %s", e)
        return False
