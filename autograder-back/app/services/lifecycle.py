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
from app.models.message_template import MessageTemplate, TemplateEventType
from app import integrations

logger = logging.getLogger(__name__)

# WhatsApp message templates for lifecycle events
MSG_ONBOARDING = (
    "Olá! Seu acesso ao {product_name} foi confirmado.\n\n"
    "Para liberar seu acesso ao Discord, use o comando /registrar com o token abaixo:\n\n"
    "Token: {onboarding_token}\n\n"
    "O token expira em 7 dias."
)
MSG_WELCOME = (
    "Tudo pronto! Seu acesso ao {product_name} está ativo. "
    "Você já pode acessar o Discord e a plataforma. Bons estudos!"
)
MSG_WELCOME_BACK = (
    "Bem-vindo de volta ao {product_name}! "
    "Seu acesso foi reativado. Bons estudos!"
)
MSG_CHURN = (
    "Seu acesso ao {product_name} foi encerrado. "
    "Se tiver dúvidas, responda esta mensagem."
)

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


def _get_template(db: Session, event_type: TemplateEventType, fallback: str) -> str:
    """Read template from DB, fallback to hardcoded constant on miss or error."""
    try:
        row = db.query(MessageTemplate).filter(MessageTemplate.event_type == event_type).first()
        if row:
            return row.template_text
    except Exception:
        logger.warning("Failed to read template %s from DB, using fallback", event_type.value)
    return fallback


def _resolve_lifecycle_template(template: str, variables: Dict[str, Any]) -> str:
    """Resolve {variable} placeholders in a lifecycle template."""
    result = template
    for key, value in variables.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def generate_onboarding_token(db: Session, user: User) -> str:
    """Generate and store a unique 8-char onboarding token (valid 7 days)."""
    token = secrets.token_hex(4).upper()
    user.onboarding_token = token
    user.onboarding_token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    return token


def _get_all_active_product_rules(
    db: Session, email: str
) -> List[Tuple[Optional[Product], List[ProductAccessRule]]]:
    """Get all products and their rules for a buyer email, based on active HotmartBuyer records."""
    from app.models.hotmart_buyer import HotmartBuyer

    buyers = (
        db.query(HotmartBuyer)
        .filter(HotmartBuyer.email == email, HotmartBuyer.status == "Ativo")
        .all()
    )
    result = []
    for buyer in buyers:
        product, rules = _get_product_rules(db, buyer.hotmart_product_id)
        if product:
            result.append((product, rules))
    return result


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
    from app.integrations import evolution

    token = generate_onboarding_token(db, user)

    if user.whatsapp_number:
        product_name = product.name if product else ""
        template = _get_template(db, TemplateEventType.ONBOARDING, MSG_ONBOARDING)
        nome = user.email.split("@")[0]
        variables = {
            "product_name": product_name,
            "onboarding_token": token,
            "token": token,
            "nome": nome,
            "primeiro_nome": nome.split()[0] if nome else "",
        }
        text = _resolve_lifecycle_template(template, variables)
        sid = f"onboarding_{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')}"
        _execute_side_effect(
            "evolution.message_sent",
            lambda: evolution.send_message(user.whatsapp_number, text, send_id=sid),
            db, user, {"event": "onboarding", "token": token},
        )


def _side_effects_for_active(
    db: Session, user: User, product: Optional[Product], rules: List[ProductAccessRule],
    is_reactivation: bool = False,
) -> None:
    """Side-effects when transitioning to active"""
    from app.integrations import discord as discord_client, evolution
    from app.services.enrollment import auto_enroll_by_product

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

    if user.whatsapp_number:
        product_name = product.name if product else ""
        nome = user.email.split("@")[0]
        variables = {
            "product_name": product_name,
            "nome": nome,
            "primeiro_nome": nome.split()[0] if nome else "",
        }
        if is_reactivation:
            template = _get_template(db, TemplateEventType.WELCOME_BACK, MSG_WELCOME_BACK)
            event_name = "welcome-back"
        else:
            template = _get_template(db, TemplateEventType.WELCOME, MSG_WELCOME)
            event_name = "welcome-confirmed"
        text = _resolve_lifecycle_template(template, variables)
        sid = f"{event_name}_{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')}"
        _execute_side_effect(
            "evolution.message_sent",
            lambda: evolution.send_message(user.whatsapp_number, text, send_id=sid),
            db, user, {"event": event_name},
        )


def _side_effects_for_churned(
    db: Session, user: User, product: Optional[Product], rules: List[ProductAccessRule]
) -> None:
    """Side-effects when transitioning to churned"""
    from app.integrations import discord as discord_client, evolution
    from app.services.enrollment import auto_unenroll_by_product

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

    if user.whatsapp_number:
        product_name = product.name if product else ""
        nome = user.email.split("@")[0]
        template = _get_template(db, TemplateEventType.CHURN, MSG_CHURN)
        variables = {
            "product_name": product_name,
            "nome": nome,
            "primeiro_nome": nome.split()[0] if nome else "",
        }
        text = _resolve_lifecycle_template(template, variables)
        sid = f"churn_{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')}"
        _execute_side_effect(
            "evolution.message_sent",
            lambda: evolution.send_message(user.whatsapp_number, text, send_id=sid),
            db, user, {"event": "churn-notification"},
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

    if hotmart_product_id:
        product, rules = _get_product_rules(db, hotmart_product_id)
    elif trigger == "discord_registered":
        all_pr = _get_all_active_product_rules(db, user.email)
        rules = [rule for _, pr in all_pr for rule in pr]
        product = all_pr[0][0] if all_pr else None
    else:
        product, rules = None, []

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
