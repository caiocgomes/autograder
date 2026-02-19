"""
Hotmart webhook parsing/validation and REST API client.

Webhook auth: simple shared-secret via X-Hotmart-Hottok header.
API auth: OAuth2 client_credentials flow, token cached in Redis.
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Iterator, Dict
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

# Supported Hotmart event types
PURCHASE_APPROVED = "PURCHASE_APPROVED"
PURCHASE_DELAYED = "PURCHASE_DELAYED"
PURCHASE_REFUNDED = "PURCHASE_REFUNDED"
SUBSCRIPTION_CANCELLATION = "SUBSCRIPTION_CANCELLATION"

SUPPORTED_EVENTS = {
    PURCHASE_APPROVED,
    PURCHASE_DELAYED,
    PURCHASE_REFUNDED,
    SUBSCRIPTION_CANCELLATION,
}


@dataclass
class HotmartEventData:
    """Parsed Hotmart event with the fields we care about"""
    event_type: str
    buyer_email: str
    hotmart_product_id: str
    transaction_id: Optional[str]
    raw_payload: dict


def validate_hottok(header_value: Optional[str], expected_token: str) -> bool:
    """Validate the X-Hotmart-Hottok header against the configured secret"""
    if not header_value or not expected_token:
        return False
    return header_value == expected_token


def parse_payload(payload: dict) -> Optional[HotmartEventData]:
    """
    Parse a Hotmart webhook payload into structured data.

    Hotmart sends different shapes depending on event type.
    We extract the fields we need and log what we can't parse.
    """
    event_type = payload.get("event", "")

    try:
        data = payload.get("data", {})

        # Buyer email: nested under buyer or product
        buyer = data.get("buyer", {})
        buyer_email = buyer.get("email", "")

        # Product ID
        product_info = data.get("product", {})
        hotmart_product_id = str(product_info.get("id", ""))

        # Transaction ID (present on purchase events)
        purchase = data.get("purchase", {})
        transaction_id = purchase.get("transaction", None)

        if not buyer_email:
            logger.warning("Hotmart payload missing buyer email: %s", payload)
            return None

        return HotmartEventData(
            event_type=event_type,
            buyer_email=buyer_email,
            hotmart_product_id=hotmart_product_id,
            transaction_id=transaction_id,
            raw_payload=payload,
        )
    except Exception as e:
        logger.error("Failed to parse Hotmart payload: %s. Error: %s", payload, e)
        return None


def is_supported_event(event_type: str) -> bool:
    return event_type in SUPPORTED_EVENTS


# ---------------------------------------------------------------------------
# Hotmart REST API client
# ---------------------------------------------------------------------------

_TOKEN_CACHE_KEY = "hotmart:access_token"


def get_access_token() -> str:
    """
    Get a valid Hotmart OAuth2 access token, cached in Redis.

    Returns empty string if credentials are not configured or Redis unavailable.
    Token is cached with TTL = expires_in - 300s to allow a safety margin.
    """
    if not settings.hotmart_client_id or not settings.hotmart_client_secret:
        logger.warning("Hotmart API credentials not configured; skipping token fetch")
        return ""

    try:
        from app.redis_client import get_redis_client
        redis = get_redis_client()
        cached = redis.get(_TOKEN_CACHE_KEY)
        if cached:
            return cached
    except Exception as e:
        logger.warning("Redis unavailable for token cache: %s", e)
        redis = None

    try:
        import base64
        credentials = base64.b64encode(
            f"{settings.hotmart_client_id}:{settings.hotmart_client_secret}".encode()
        ).decode()
        resp = requests.post(
            settings.hotmart_token_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data="grant_type=client_credentials",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token", "")
        expires_in = int(data.get("expires_in", 3600))

        if token and redis is not None:
            try:
                ttl = max(expires_in - 300, 60)
                redis.setex(_TOKEN_CACHE_KEY, ttl, token)
            except Exception as e:
                logger.warning("Failed to cache Hotmart token in Redis: %s", e)

        return token
    except Exception as e:
        logger.error("Failed to fetch Hotmart access token: %s", e)
        return ""


def _paginate(url: str, params: dict) -> Iterator[dict]:
    """
    Generic cursor-based paginator for Hotmart API list endpoints.
    Yields individual items from each page.
    """
    token = get_access_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    page_token = None
    _retried = False

    while True:
        page_params = dict(params)
        if page_token:
            page_params["page_token"] = page_token

        try:
            resp = requests.get(url, headers=headers, params=page_params, timeout=30)
        except Exception as e:
            logger.error("Hotmart API request failed for %s: %s", url, e)
            return

        if resp.status_code == 401 and not _retried:
            logger.warning("Hotmart token rejected (401) — invalidating cache and retrying")
            try:
                from app.redis_client import get_redis_client
                get_redis_client().delete(_TOKEN_CACHE_KEY)
            except Exception:
                pass
            token = get_access_token()
            if not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            _retried = True
            continue

        try:
            resp.raise_for_status()
            body = resp.json()
        except Exception as e:
            logger.error("Hotmart API request failed for %s: %s", url, e)
            return

        items = body.get("items", [])
        for item in items:
            yield item

        page_info = body.get("page_info", {})
        page_token = page_info.get("next_page_token")
        if not page_token:
            break


def list_active_subscriptions(product_id: Optional[str] = None) -> Iterator[dict]:
    """
    Yield all active subscriptions from Hotmart.

    Each yielded dict: {"email", "name", "hotmart_product_id", "source": "subscription"}
    """
    url = f"{settings.hotmart_api_base}/subscriptions"
    params = {"status": "ACTIVE", "max_results": 500}
    if product_id:
        params["product_id"] = product_id

    for item in _paginate(url, params):
        try:
            subscriber = item.get("subscriber", {})
            email = subscriber.get("email", "")
            name = subscriber.get("name", "")
            product = item.get("product", {})
            pid = str(product.get("id", ""))
            if email:
                yield {"email": email, "name": name, "hotmart_product_id": pid, "source": "subscription"}
        except Exception as e:
            logger.warning("Failed to parse subscription item: %s — %s", item, e)


def list_active_sales(product_id: Optional[str] = None) -> Iterator[dict]:
    """
    Yield approved/completed one-time sales from Hotmart.

    Each yielded dict: {"email", "name", "hotmart_product_id", "source": "sale"}
    """
    url = f"{settings.hotmart_api_base}/sales/history"
    params = {"max_results": 500}
    if product_id:
        params["product_id"] = product_id

    for item in _paginate(url, params):
        try:
            buyer = item.get("buyer", {})
            email = buyer.get("email", "")
            name = buyer.get("name", "")
            product = item.get("product", {})
            pid = str(product.get("id", ""))
            if email:
                yield {"email": email, "name": name, "hotmart_product_id": pid, "source": "sale"}
        except Exception as e:
            logger.warning("Failed to parse sale item: %s — %s", item, e)


def list_buyers_with_phone(product_id: Optional[str] = None) -> Iterator[dict]:
    """
    Yield buyers from GET /sales/users with phone numbers.

    Each yielded dict: {"email", "name", "phone", "hotmart_product_id"}
    Phone prefers cellphone over phone field (raw value, no country code prefix).
    """
    url = f"{settings.hotmart_api_base}/sales/users"
    params = {"max_results": 500}
    if product_id:
        params["product_id"] = product_id

    seen_emails: set = set()
    for item in _paginate(url, params):
        try:
            pid = str(item.get("product", {}).get("id", ""))
            for u in item.get("users", []):
                if u.get("role") != "BUYER":
                    continue
                user = u.get("user", {})
                email = user.get("email", "").lower().strip()
                if not email or email in seen_emails:
                    continue
                seen_emails.add(email)
                phone = user.get("cellphone", "") or user.get("phone", "")
                yield {
                    "email": email,
                    "name": user.get("name", ""),
                    "phone": phone,
                    "hotmart_product_id": pid,
                }
        except Exception as e:
            logger.warning("Failed to parse sales/users item: %s — %s", item, e)


# Hotmart → business status mapping
_STATUS_MAP: Dict[str, str] = {
    "APPROVED": "Ativo",
    "COMPLETE": "Ativo",
    "OVERDUE": "Inadimplente",
    "CANCELLED": "Cancelado",
    "EXPIRED": "Cancelado",
    "REFUNDED": "Reembolsado",
    "CHARGEBACK": "Reembolsado",
    "PARTIALLY_REFUNDED": "Reembolsado",
}

# Priority: higher = takes precedence when multiple statuses exist for same buyer
_STATUS_PRIORITY: Dict[str, int] = {
    "Ativo": 4,
    "Inadimplente": 3,
    "Cancelado": 2,
    "Reembolsado": 1,
}


def get_buyer_statuses(product_id: str, years: int = 6) -> Dict[str, str]:
    """
    Return a dict mapping buyer email -> business status for a given product.

    Scans up to `years` of Hotmart sales history in 30-day windows.
    When a buyer has multiple transaction statuses, the highest-priority wins:
    Ativo > Inadimplente > Cancelado > Reembolsado.
    """
    url = f"{settings.hotmart_api_base}/sales/history"
    buyer_statuses: Dict[str, str] = {}

    now = datetime.now()
    end = now
    start = end - timedelta(days=30)
    cutoff = now - timedelta(days=years * 365)

    all_hotmart_statuses = list(_STATUS_MAP.keys())

    while end > cutoff:
        for hotmart_status in all_hotmart_statuses:
            page_token = None
            while True:
                params: Dict = {
                    "max_results": 500,
                    "product_id": product_id,
                    "transaction_status": hotmart_status,
                    "start_date": int(start.timestamp() * 1000),
                    "end_date": int(end.timestamp() * 1000),
                }
                if page_token:
                    params["page_token"] = page_token

                try:
                    token = get_access_token()
                    if not token:
                        break
                    resp = requests.get(
                        url,
                        headers={"Authorization": f"Bearer {token}"},
                        params=params,
                        timeout=30,
                    )
                    if resp.status_code == 401:
                        try:
                            from app.redis_client import get_redis_client
                            get_redis_client().delete(_TOKEN_CACHE_KEY)
                        except Exception:
                            pass
                        break
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                except Exception as e:
                    logger.error("get_buyer_statuses request failed: %s", e)
                    break

                for item in data.get("items", []):
                    email = item.get("buyer", {}).get("email", "").lower().strip()
                    if not email:
                        continue
                    biz_status = _STATUS_MAP.get(hotmart_status, "")
                    if not biz_status:
                        continue
                    existing = buyer_statuses.get(email)
                    if existing is None or (
                        _STATUS_PRIORITY.get(biz_status, 0) > _STATUS_PRIORITY.get(existing, 0)
                    ):
                        buyer_statuses[email] = biz_status

                page_token = data.get("page_info", {}).get("next_page_token")
                if not page_token:
                    break

        end = start
        start = end - timedelta(days=30)

    return buyer_statuses
