"""
ManyChat API client for subscriber state management and flow triggers.

ManyChat subscribers are resolved by phone number (E.164 format).
subscriber_id is cached on the User record after first lookup.
"""
import logging
from typing import Optional, Dict, Any
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

MANYCHAT_API_BASE = "https://api.manychat.com"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.manychat_api_token}",
        "Content-Type": "application/json",
    }


def find_subscriber(phone_number: str) -> Optional[str]:
    """
    Find ManyChat subscriber ID by phone number.
    Phone should be in E.164 format (e.g. +5511999999999).
    Returns subscriber_id or None if not found.
    """
    if not settings.manychat_enabled:
        logger.info("ManyChat disabled. Skipping find_subscriber")
        return None

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{MANYCHAT_API_BASE}/fb/subscriber/findByPhone",
                headers=_headers(),
                params={"phone": phone_number},
            )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            return data.get("id")
        if resp.status_code == 404:
            logger.warning("ManyChat subscriber not found for phone %s", phone_number)
            return None
        logger.error("find_subscriber failed: %s %s", resp.status_code, resp.text)
        return None
    except Exception as e:
        logger.error("find_subscriber exception: %s", e)
        return None


def add_tag(subscriber_id: str, tag_name: str) -> bool:
    """Add a tag to a ManyChat subscriber. Returns True on success."""
    if not settings.manychat_enabled:
        logger.info("ManyChat disabled. Skipping add_tag")
        return True

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{MANYCHAT_API_BASE}/fb/subscriber/addTag",
                headers=_headers(),
                json={"subscriber_id": subscriber_id, "tag_name": tag_name},
            )
        if resp.status_code == 200:
            return True
        logger.error("add_tag failed: %s %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("add_tag exception: %s", e)
        return False


def remove_tag(subscriber_id: str, tag_name: str) -> bool:
    """Remove a tag from a ManyChat subscriber. Returns True on success."""
    if not settings.manychat_enabled:
        logger.info("ManyChat disabled. Skipping remove_tag")
        return True

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{MANYCHAT_API_BASE}/fb/subscriber/removeTag",
                headers=_headers(),
                json={"subscriber_id": subscriber_id, "tag_name": tag_name},
            )
        if resp.status_code == 200:
            return True
        logger.error("remove_tag failed: %s %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("remove_tag exception: %s", e)
        return False


def set_custom_fields(subscriber_id: str, fields: Dict[str, Any]) -> bool:
    """Set custom fields on a ManyChat subscriber. Returns True on success."""
    if not settings.manychat_enabled:
        logger.info("ManyChat disabled. Skipping set_custom_fields")
        return True

    field_list = [{"field_name": k, "field_value": v} for k, v in fields.items()]
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{MANYCHAT_API_BASE}/fb/subscriber/setCustomFields",
                headers=_headers(),
                json={"subscriber_id": subscriber_id, "fields": field_list},
            )
        if resp.status_code == 200:
            return True
        logger.error("set_custom_fields failed: %s %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("set_custom_fields exception: %s", e)
        return False


def trigger_flow(subscriber_id: str, flow_ns: str, custom_fields: Optional[Dict[str, Any]] = None) -> bool:
    """
    Trigger a ManyChat flow for a subscriber.
    flow_ns is the flow namespace (ID).
    Returns True on success.
    """
    if not settings.manychat_enabled:
        logger.info("ManyChat disabled. Skipping trigger_flow")
        return True

    payload: Dict[str, Any] = {
        "subscriber_id": subscriber_id,
        "flow_ns": flow_ns,
    }
    if custom_fields:
        payload["custom_fields"] = [
            {"field_name": k, "field_value": v} for k, v in custom_fields.items()
        ]

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{MANYCHAT_API_BASE}/fb/sending/sendFlow",
                headers=_headers(),
                json=payload,
            )
        if resp.status_code == 200:
            return True
        logger.error("trigger_flow failed: %s %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("trigger_flow exception: %s", e)
        return False
