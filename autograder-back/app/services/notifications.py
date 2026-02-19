"""
Notification service - abstracts over Discord and ManyChat channels.

This is intentionally thin. The lifecycle service drives the when;
this service handles the how.
"""
import logging

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


def notify_admin_failure(side_effect_name: str, user: User, error: str) -> None:
    """
    Alert admin about a persistent side-effect failure.
    Tries Discord DM first, then logs as fallback.
    """
    message = (
        f"⚠️ Side-effect failure\n"
        f"Action: {side_effect_name}\n"
        f"Student: {user.email} (id={user.id})\n"
        f"Error: {error}"
    )

    if settings.discord_enabled:
        try:
            from app.integrations.discord import send_dm
            # Admin discord_id would come from config - placeholder for now
            admin_discord_id = getattr(settings, "discord_admin_id", None)
            if admin_discord_id:
                send_dm(admin_discord_id, message)
                return
        except Exception as e:
            logger.error("Failed to send admin Discord DM: %s", e)

    logger.error("ADMIN NOTIFICATION: %s", message)


def notify_student_welcome(user: User, product_name: str) -> None:
    """Send a welcome notification when student becomes active."""
    if settings.manychat_enabled and user.manychat_subscriber_id:
        try:
            from app.integrations.manychat import trigger_flow
            trigger_flow(
                user.manychat_subscriber_id,
                settings.manychat_welcome_flow_id,
                {"product_name": product_name},
            )
        except Exception as e:
            logger.error("notify_student_welcome failed: %s", e)
    else:
        logger.info("Welcome notification skipped for %s (ManyChat disabled or no subscriber_id)", user.email)
