"""
Discord REST API client for role management and messaging.

Uses httpx for HTTP requests (sync for Celery tasks, async for the bot itself).
The bot token is used for all API calls.
"""
import logging
from typing import List
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"


def _headers() -> dict:
    return {"Authorization": f"Bot {settings.discord_bot_token}"}


def assign_role(discord_id: str, role_id: str) -> bool:
    """Add a role to a guild member. Returns True on success."""
    if not settings.discord_enabled:
        logger.info("Discord disabled. Skipping assign_role for %s", discord_id)
        return True

    url = f"{DISCORD_API_BASE}/guilds/{settings.discord_guild_id}/members/{discord_id}/roles/{role_id}"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.put(url, headers=_headers())
        if resp.status_code in (200, 204):
            return True
        logger.error("assign_role failed: %s %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("assign_role exception: %s", e)
        return False


def revoke_role(discord_id: str, role_id: str) -> bool:
    """Remove a role from a guild member. Returns True on success."""
    if not settings.discord_enabled:
        logger.info("Discord disabled. Skipping revoke_role for %s", discord_id)
        return True

    url = f"{DISCORD_API_BASE}/guilds/{settings.discord_guild_id}/members/{discord_id}/roles/{role_id}"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.delete(url, headers=_headers())
        if resp.status_code in (200, 204):
            return True
        logger.error("revoke_role failed: %s %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("revoke_role exception: %s", e)
        return False


def send_channel_message(channel_id: str, content: str) -> bool:
    """Post a message to a Discord channel. Returns True on success."""
    if not settings.discord_enabled:
        logger.info("Discord disabled. Skipping send_channel_message to %s", channel_id)
        return True

    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, headers=_headers(), json={"content": content})
        if resp.status_code in (200, 201):
            return True
        logger.error("send_channel_message failed: %s %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("send_channel_message exception: %s", e)
        return False


def send_dm(discord_id: str, content: str) -> bool:
    """Send a DM to a user via Discord. Returns True on success."""
    if not settings.discord_enabled:
        logger.info("Discord disabled. Skipping send_dm to %s", discord_id)
        return True

    try:
        with httpx.Client(timeout=10) as client:
            # First, create a DM channel
            dm_resp = client.post(
                f"{DISCORD_API_BASE}/users/@me/channels",
                headers=_headers(),
                json={"recipient_id": discord_id},
            )
            if dm_resp.status_code not in (200, 201):
                logger.error("create DM channel failed: %s", dm_resp.text)
                return False
            channel_id = dm_resp.json()["id"]
            return send_channel_message(channel_id, content)
    except Exception as e:
        logger.error("send_dm exception: %s", e)
        return False


def is_member(discord_id: str) -> bool:
    """Check if a user is a member of the configured guild."""
    if not settings.discord_enabled:
        return True

    url = f"{DISCORD_API_BASE}/guilds/{settings.discord_guild_id}/members/{discord_id}"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=_headers())
        return resp.status_code == 200
    except Exception as e:
        logger.error("is_member exception: %s", e)
        return False
