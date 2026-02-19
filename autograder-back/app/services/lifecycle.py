"""
Student lifecycle state machine.

States: pending_payment → pending_onboarding → active → churned
       churned → active (reactivation)

Each transition has associated side-effects executed in order.
Failed side-effects are retried once; persistent failures are logged and admin alerted.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Callable, Tuple

from sqlalchemy.orm import Session

from app.models.user import User, LifecycleStatus
from app.models.product import Product, ProductAccessRule, AccessRuleType
from app.models.event import Event, EventStatus
from app import integrations

logger = logging.getLogger(__name__)

# State machine: maps (from_state, trigger) → to_state
# None from_state means "create new"
TRANSITIONS: Dict[Tuple[Optional[str], str], str] = {
    (None, "purchase_approved"): LifecycleStatus.PENDING_ONBOARDING,
    (None, "purchase_delayed"): LifecycleStatus.PENDING_PAYMENT,
    (LifecycleStatus.PENDING_PAYMENT, "purchase_approved"): LifecycleStatus.PENDING_ONBOARDING,
    (LifecycleStatus.PENDING_ONBOARDING, "discord_registered"): LifecycleStatus.ACTIVE,
    (LifecycleStatus.ACTIVE, "subscription_cancelled"): LifecycleStatus.CHURNED,
    (LifecycleStatus.ACTIVE, "purchase_refunded"): LifecycleStatus.CHURNED,
    (LifecycleStatus.CHURNED, "purchase_approved"): LifecycleStatus.ACTIVE,
}


def _log_event(
    db: Session,
    event_type: str,
    target_id: Optional[int],
    payload: Dict[str, Any],
    status: EventStatus = EventStatus.PROCESSED,
    error_message: Optional[str] = None,
    actor_id: Optional[int] = None,
) -> Event:
    event = Event(
        type=event_type,
        actor_id=actor_id,
        target_id=target_id,
        payload=payload,
        status=status,
        error_message=error_message,
    )
    db.add(event)
    db.flush()
    return event


def _execute_side_effect(
    name: str,
    fn: Callable,
    db: Session,
    user: User,
    payload: Dict[str, Any],
) -> bool:
    """Execute a side-effect with 1 retry on failure. Returns True on success."""
    for attempt in range(2):
        try:
            result = fn()
            if result is not False:
                _log_event(db, name, user.id, {**payload, "attempt": attempt + 1})
                return True
        except Exception as e:
            logger.warning("Side-effect %s attempt %d failed: %s", name, attempt + 1, e)
            if attempt == 1:
                _log_event(
                    db, name, user.id, payload,
                    status=EventStatus.FAILED,
                    error_message=str(e),
                )
                _alert_admin_failure(name, user, str(e))
                return False
    # Both attempts returned False
    _log_event(
        db, name, user.id, payload,
        status=EventStatus.FAILED,
        error_message="Side-effect returned False after 2 attempts",
    )
    _alert_admin_failure(name, user, "Returned False after 2 attempts")
    return False


def _alert_admin_failure(side_effect_name: str, user: User, error: str) -> None:
    """Send an alert when a side-effect fails persistently."""
    logger.error(
        "ADMIN ALERT: side-effect '%s' failed for user %s (%s). Error: %s",
        side_effect_name, user.id, user.email, error,
    )
    # Discord DM alert to admin - if admin discord_id configured
    # This intentionally does NOT raise - alerting failures must not cascade


def generate_onboarding_token(db: Session, user: User) -> str:
    """Generate and store a unique 8-char onboarding token (valid 7 days)."""
    token = secrets.token_urlsafe(6)[:8].upper()
    user.onboarding_token = token
    user.onboarding_token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    return token


def _get_product_rules(db: Session, hotmart_product_id: str) -> Tuple[Optional[Product], List[ProductAccessRule]]:
    product = db.query(Product).filter(
        Product.hotmart_product_id == hotmart_product_id,
        Product.is_active == True,
    ).first()
    if not product:
        return None, []
    return product, product.access_rules


def _side_effects_for_pending_onboarding(
    db: Session, user: User, product: Optional[Product], rules: List[ProductAccessRule]
) -> None:
    """Side-effects when transitioning to pending_onboarding"""
    from app.integrations import manychat

    token = generate_onboarding_token(db, user)

    for rule in rules:
        if rule.rule_type == AccessRuleType.MANYCHAT_TAG and user.manychat_subscriber_id:
            _execute_side_effect(
                "manychat.tag_added",
                lambda sid=user.manychat_subscriber_id, tag=rule.rule_value: manychat.add_tag(sid, tag),
                db, user, {"tag": rule.rule_value},
            )

    if user.manychat_subscriber_id and user.whatsapp_number:
        from app.config import settings
        _execute_side_effect(
            "manychat.flow_triggered",
            lambda: manychat.trigger_flow(
                user.manychat_subscriber_id,
                settings.manychat_onboarding_flow_id,
                {
                    "student_name": user.email,
                    "onboarding_token": token,
                    "product_name": product.name if product else "",
                },
            ),
            db, user, {"flow": "onboarding", "token": token},
        )


def _side_effects_for_active(
    db: Session, user: User, product: Optional[Product], rules: List[ProductAccessRule],
    is_reactivation: bool = False,
) -> None:
    """Side-effects when transitioning to active"""
    from app.integrations import discord as discord_client, manychat
    from app.services.enrollment import auto_enroll_by_product
    from app.config import settings

    for rule in rules:
        if rule.rule_type == AccessRuleType.DISCORD_ROLE and user.discord_id:
            _execute_side_effect(
                "discord.role_assigned",
                lambda rid=rule.rule_value: discord_client.assign_role(user.discord_id, rid),
                db, user, {"role_id": rule.rule_value},
            )
        elif rule.rule_type == AccessRuleType.CLASS_ENROLLMENT:
            try:
                auto_enroll_by_product(db, user, int(rule.rule_value), product.id if product else None)
                _log_event(db, "enrollment.enrolled", user.id, {"class_id": rule.rule_value})
            except Exception as e:
                _log_event(db, "enrollment.enrolled", user.id, {"class_id": rule.rule_value},
                           status=EventStatus.FAILED, error_message=str(e))
        elif rule.rule_type == AccessRuleType.MANYCHAT_TAG and user.manychat_subscriber_id:
            _execute_side_effect(
                "manychat.tag_added",
                lambda sid=user.manychat_subscriber_id, tag=rule.rule_value: manychat.add_tag(sid, tag),
                db, user, {"tag": rule.rule_value},
            )

    if user.manychat_subscriber_id:
        flow_id = settings.manychat_welcome_back_flow_id if is_reactivation else settings.manychat_welcome_flow_id
        flow_name = "welcome-back" if is_reactivation else "welcome-confirmed"
        _execute_side_effect(
            "manychat.flow_triggered",
            lambda: manychat.trigger_flow(user.manychat_subscriber_id, flow_id),
            db, user, {"flow": flow_name},
        )


def _side_effects_for_churned(
    db: Session, user: User, product: Optional[Product], rules: List[ProductAccessRule]
) -> None:
    """Side-effects when transitioning to churned"""
    from app.integrations import discord as discord_client, manychat
    from app.services.enrollment import auto_unenroll_by_product
    from app.config import settings

    for rule in rules:
        if rule.rule_type == AccessRuleType.DISCORD_ROLE and user.discord_id:
            _execute_side_effect(
                "discord.role_revoked",
                lambda rid=rule.rule_value: discord_client.revoke_role(user.discord_id, rid),
                db, user, {"role_id": rule.rule_value},
            )
        elif rule.rule_type == AccessRuleType.CLASS_ENROLLMENT:
            try:
                auto_unenroll_by_product(db, user, int(rule.rule_value))
                _log_event(db, "enrollment.unenrolled", user.id, {"class_id": rule.rule_value})
            except Exception as e:
                _log_event(db, "enrollment.unenrolled", user.id, {"class_id": rule.rule_value},
                           status=EventStatus.FAILED, error_message=str(e))
        elif rule.rule_type == AccessRuleType.MANYCHAT_TAG and user.manychat_subscriber_id:
            _execute_side_effect(
                "manychat.tag_removed",
                lambda sid=user.manychat_subscriber_id, tag=rule.rule_value: manychat.remove_tag(sid, tag),
                db, user, {"tag": rule.rule_value},
            )

    if user.manychat_subscriber_id:
        _execute_side_effect(
            "manychat.flow_triggered",
            lambda: manychat.trigger_flow(user.manychat_subscriber_id, settings.manychat_churn_flow_id),
            db, user, {"flow": "churn-notification"},
        )


def transition(
    db: Session,
    user: User,
    trigger: str,
    hotmart_product_id: Optional[str] = None,
    actor_id: Optional[int] = None,
) -> Optional[LifecycleStatus]:
    """
    Execute a lifecycle transition for a user.
    Returns the new status on success, None if transition is not valid.
    """
    from_state = user.lifecycle_status
    key = (from_state, trigger)

    to_state = TRANSITIONS.get(key)
    if to_state is None:
        logger.warning("No transition for (%s, %s)", from_state, trigger)
        return None

    is_reactivation = from_state == LifecycleStatus.CHURNED and to_state == LifecycleStatus.ACTIVE

    product, rules = _get_product_rules(db, hotmart_product_id) if hotmart_product_id else (None, [])

    # Execute transition
    user.lifecycle_status = to_state
    db.flush()

    _log_event(
        db, "lifecycle.transition", user.id,
        {"from_state": str(from_state), "to_state": str(to_state), "trigger": trigger},
        actor_id=actor_id,
    )

    # Execute side-effects
    if to_state == LifecycleStatus.PENDING_ONBOARDING:
        _side_effects_for_pending_onboarding(db, user, product, rules)
    elif to_state == LifecycleStatus.ACTIVE:
        _side_effects_for_active(db, user, product, rules, is_reactivation=is_reactivation)
    elif to_state == LifecycleStatus.CHURNED:
        _side_effects_for_churned(db, user, product, rules)

    db.commit()
    return to_state
