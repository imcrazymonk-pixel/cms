"""Customer card — Bedolaga data, 60s cache in support_customer_profile.meta (phase 1).

Resolves conversation → Bedolaga user (tg_user_id → /users/by-telegram-id, else
the ticket's user_id), then pulls subscriptions, ticket count and transactions.
Cache lives in the profile's meta jsonb (`customer_card` + `customer_card_at`);
`refresh` endpoints force a rebuild. Remnawave deep — phase 5 stub.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from web.backend.core.bedolaga_client import bedolaga_client, ensure_configured
from web.backend.core.support.channels.bedolaga import ticket_id_of

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60
_CARD_KEY = "customer_card"
_CARD_AT_KEY = "customer_card_at"


async def build_customer_card(service, conversation: dict[str, Any], *, force_refresh: bool = False) -> dict:
    """Customer card for a conversation — from cache when fresh, else Bedolaga."""
    profile = await _ensure_profile_linked(service, conversation)
    if profile is not None and not force_refresh:
        cached = profile.get("meta") or {}
        card = cached.get(_CARD_KEY)
        stamp = cached.get(_CARD_AT_KEY)
        if card and stamp and _cache_fresh(stamp):
            return card

    card = await _fetch_card(service, conversation)
    if profile is not None:
        meta = dict(profile.get("meta") or {})
        meta[_CARD_KEY] = card
        meta[_CARD_AT_KEY] = datetime.now(timezone.utc).isoformat()
        await service.store.update_customer_meta(profile["id"], meta)
    return card


def _cache_fresh(stamp: Any) -> bool:
    if not isinstance(stamp, str):
        return False
    try:
        stored = datetime.fromisoformat(stamp)
    except ValueError:
        return False
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - stored < timedelta(seconds=CACHE_TTL_SECONDS)


async def _ensure_profile_linked(service, conversation: dict[str, Any]) -> dict[str, Any] | None:
    """Return the conversation's profile, creating + linking one if missing."""
    profile_id = conversation.get("customer_profile_id")
    if profile_id:
        profile = await service.store.get_customer_profile(customer_id=int(profile_id))
        if profile is not None:
            return profile

    identity_key = f"bedolaga:{conversation.get('external_id')}"
    tg_user_id = conversation.get("tg_user_id")
    if tg_user_id:
        identity_key = f"tg:{tg_user_id}"
    try:
        new_id = await service.store.upsert_customer_profile(
            identity_key=identity_key,
            tg_user_id=tg_user_id or None,
            display_name=None,
        )
    except Exception as e:  # noqa: BLE001 — карточка без профиля всё равно строится
        logger.warning("Customer profile upsert failed: %s", e)
        return None
    try:
        await service.store.link_customer(int(conversation["id"]), new_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("Customer link failed: %s", e)
    return await service.store.get_customer_profile(customer_id=new_id)


def _bedolaga_client(service):
    """Bedolaga client: from the poller when wired, else the shared singleton."""
    poller = service.pollers.get("bedolaga") if service.pollers else None
    if poller is not None and getattr(poller, "client", None) is not None:
        return poller.client
    try:
        return bedolaga_client if ensure_configured() else None
    except Exception:  # noqa: BLE001
        return None


# ── Fetching ───────────────────────────────────────────────────────────────

async def _fetch_card(service, conversation: dict[str, Any]) -> dict[str, Any]:
    """Build the card from Bedolaga (best-effort; failures become empty sections)."""
    client = _bedolaga_client(service)
    user: dict | None = None
    user_id: int | None = None
    tg = conversation.get("tg_user_id")

    if client is not None:
        if tg:
            user = await _safe(client.get_user_by_telegram, tg)
        if not user:
            try:
                ticket = await _safe(client.get_ticket, ticket_id_of(conversation))
            except ValueError:
                ticket = None
            if ticket:
                uid = _num(ticket.get("user_id"))
                if uid:
                    user = await _safe(client.get_user, uid)
        if user:
            user_id = _num(user.get("id"))

    subscriptions: list[dict] = []
    tickets_total = 0
    transactions: list[dict] = []
    if client is not None and user_id:
        subscriptions = _items(await _safe(client.list_subscriptions, user_id=user_id, limit=5))
        page = await _safe(client.list_tickets, user_id=user_id, limit=1)
        tickets_total = _total(page, 0)
        transactions = _items(await _safe(client.list_transactions, user_id=user_id, limit=5))

    profile = user or {}
    kopeks = _num(profile.get("balance_kopeks"))
    return {
        "provider": "bedolaga",
        "id": user_id,
        "telegram_id": _num(_first(profile, "tg_id", "telegram_id", "telegramId")),
        "username": _first(profile, "username", "login") or "",
        "display_name": _display_name(profile) or "",
        "balance_kopeks": kopeks,
        "balance_rub": round(kopeks / 100, 2) if kopeks is not None else None,
        "subscription": _subscription_summary(subscriptions),
        "tickets_total": tickets_total,
        "last_activity": _first(profile, "last_activity", "last_seen"),
        "recent_transactions": len(transactions),
        "remnawave": {"available": False, "note": "Remnawave deep card — phase 5"},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _subscription_summary(subscriptions: list[dict]) -> dict[str, Any]:
    """First (most recent) subscription, condensed."""
    if not subscriptions:
        return {}
    sub = subscriptions[0]
    return {
        "status": _first(sub, "status", "subscription_status") or "unknown",
        "end_date": _first(sub, "end_date", "expires_at", "expire_at"),
        "is_trial": bool(_first(sub, "is_trial", "trial")),
        "traffic": {
            "used_bytes": _num(_first(sub, "traffic_used_bytes", "used_traffic")),
            "limit_bytes": _num(_first(sub, "traffic_limit_bytes", "traffic_limit")),
        },
    }


# ── Small helpers ──────────────────────────────────────────────────────────

async def _safe(fn, *args, **kwargs):
    """Run a client call; any failure becomes None (best-effort card)."""
    try:
        return await fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        logger.debug("Bedolaga card call %s failed: %s", getattr(fn, "__name__", "?"), e)
        return None


def _items(body: Any) -> list[dict]:
    if isinstance(body, list):
        return [b for b in body if isinstance(b, dict)]
    if isinstance(body, dict):
        for key in ("items", "subscriptions", "tickets", "transactions", "data"):
            value = body.get(key)
            if isinstance(value, list):
                return [v for v in value if isinstance(v, dict)]
    return []


def _total(body: Any, default: int = 0) -> int:
    if isinstance(body, dict):
        try:
            return int(body.get("total") or default)
        except (TypeError, ValueError):
            return default
    return default


def _num(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first(mapping: dict | None, *keys: str) -> Any:
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _display_name(profile: dict) -> str:
    first = str(_first(profile, "first_name", "firstName") or "").strip()
    last = str(_first(profile, "last_name", "lastName") or "").strip()
    return " ".join(part for part in (first, last) if part)

