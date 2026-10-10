"""Bedolaga customers — users, subscriptions, transactions, events.

Adapted from remnawave-admin-main (511 lines). Simplified for CMS:
no RBAC, no audit, no shared.database, no shared.api_client.
"""
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from httpx import ConnectError, HTTPStatusError, TimeoutException
from pydantic import BaseModel, Field

from web.backend.api.deps import get_current_admin, AdminUser, get_client_ip
from web.backend.core.bedolaga_client import bedolaga_client

from . import ensure_configured, proxy_request

logger = logging.getLogger(__name__)
router = APIRouter()

# Full user list cache for local sort/filter: (time, list)
_list_cache: dict = {}
_LIST_CACHE_TTL = 60


def _invalidate_list() -> None:
    _list_cache.clear()


# ── Schemas ──

class BalanceModifyRequest(BaseModel):
    amount_kopeks: int = Field(..., ge=-100_000_000, le=100_000_000, description="Amount in kopeks (positive=add, negative=subtract)")
    reason: Optional[str] = Field(None, max_length=500)


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=255)


class SubscriptionCreateRequest(BaseModel):
    duration_days: int = Field(..., ge=1, le=36500)
    traffic_limit_gb: Optional[int] = Field(None, ge=0, le=1_000_000)
    device_limit: Optional[int] = Field(None, ge=1, le=10_000)
    is_trial: bool = False


class SubscriptionExtendRequest(BaseModel):
    days: int = Field(..., ge=1)


class TrafficAddRequest(BaseModel):
    traffic_gb: int = Field(..., ge=1, le=1_000_000)


class DevicesAddRequest(BaseModel):
    count: int = Field(..., ge=1, le=10_000)


# ══════════════════════════════════════════════════════
# IMPORTANT: All static paths MUST come BEFORE /{user_id}
# otherwise FastAPI will try to parse "transactions" etc
# as an integer and return 422.
# ══════════════════════════════════════════════════════


# ── Users (list) ──

@router.get("")
async def list_users(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    promo_group_id: Optional[int] = Query(None),
    subscription_status: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
):
    """Список клиентов Bedolaga Bot."""
    need_local = bool(subscription_status) or (sort and sort != "created_at") or (sort == "created_at" and order == "asc")

    if not need_local:
        return await proxy_request(lambda: bedolaga_client.list_users(
            limit=limit, offset=offset, status=status, search=search,
            promo_group_id=promo_group_id, sort=sort, order=order,
        ))

    cache_key = (status, search, promo_group_id)
    cached = _list_cache.get(cache_key)
    if cached and time.time() - cached[0] < _LIST_CACHE_TTL:
        all_items = list(cached[1])
    else:
        all_items = []
        batch_size = 200
        batch_offset = 0
        while True:
            resp = await proxy_request(lambda o=batch_offset: bedolaga_client.list_users(
                limit=batch_size, offset=o, status=status, search=search,
                promo_group_id=promo_group_id,
            ))
            items = resp.get("items", []) if isinstance(resp, dict) else []
            all_items.extend(items)
            if len(items) < batch_size:
                break
            batch_offset += batch_size
        if len(_list_cache) > 20:
            _list_cache.clear()
        _list_cache[cache_key] = (time.time(), list(all_items))

    if subscription_status:
        def match_sub(user: dict) -> bool:
            sub = user.get("subscription")
            if subscription_status == "trial":
                return isinstance(sub, dict) and sub.get("is_trial") is True
            if subscription_status == "active":
                return isinstance(sub, dict) and sub.get("status") == "active" and not sub.get("is_trial")
            if subscription_status == "expired":
                return isinstance(sub, dict) and sub.get("status") == "expired"
            if subscription_status == "none":
                return not sub or not isinstance(sub, dict) or not sub.get("status")
            return True
        all_items = [u for u in all_items if match_sub(u)]

    if sort:
        reverse = order == "desc"
        if sort == "last_activity":
            all_items.sort(key=lambda u: u.get("last_activity") or "", reverse=reverse)
        elif sort == "balance":
            all_items.sort(key=lambda u: u.get("balance_kopeks") or 0, reverse=reverse)
        elif sort == "username":
            all_items.sort(key=lambda u: (u.get("username") or u.get("first_name") or "").lower(), reverse=reverse)
        elif sort == "created_at":
            all_items.sort(key=lambda u: u.get("created_at") or "", reverse=reverse)

    return {"items": all_items[offset:offset + limit], "total": len(all_items)}


# ── Transactions (static path — before /{user_id}) ──

@router.get("/transactions")
async def list_transactions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: Optional[int] = Query(None),
    transaction_type: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    is_completed: Optional[bool] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
):
    """История транзакций."""
    return await proxy_request(lambda: bedolaga_client.list_transactions(
        limit=limit, offset=offset, user_id=user_id,
        type=transaction_type, payment_method=payment_method,
        is_completed=is_completed, date_from=date_from, date_to=date_to,
    ))


# ── Events feed (static path — before /{user_id}) ──

@router.get("/events")
async def list_events(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event_type: Optional[list[str]] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
):
    """Лента событий подписок по всем клиентам."""
    return await proxy_request(lambda: bedolaga_client.list_subscription_events(
        limit=limit, offset=offset, event_types=event_type,
    ))


# ── Subscriptions list (static path — before /{user_id}) ──

@router.get("/subscriptions/list")
async def list_subscriptions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
):
    """Список подписок."""
    return await proxy_request(lambda: bedolaga_client.list_subscriptions(
        limit=limit, offset=offset, status=status, user_id=user_id,
    ))


@router.get("/subscriptions/{sub_id}")
async def get_subscription(
    sub_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Детали подписки."""
    return await proxy_request(lambda: bedolaga_client.get_subscription(sub_id))


@router.post("/subscriptions/{sub_id}/extend")
async def extend_subscription(
    sub_id: int = Path(...),
    data: SubscriptionExtendRequest = ...,
    admin: AdminUser = Depends(get_current_admin),
):
    """Продлить подписку на N дней."""
    result = await proxy_request(lambda: bedolaga_client.extend_subscription(sub_id, data.model_dump()))
    _invalidate_list()
    return result


@router.post("/subscriptions/{sub_id}/traffic")
async def add_traffic(
    sub_id: int = Path(...),
    data: TrafficAddRequest = ...,
    admin: AdminUser = Depends(get_current_admin),
):
    """Добавить трафик к подписке."""
    result = await proxy_request(lambda: bedolaga_client.add_traffic(sub_id, {"gb": data.traffic_gb}))
    _invalidate_list()
    return result


@router.post("/subscriptions/{sub_id}/devices")
async def add_devices(
    sub_id: int = Path(...),
    data: DevicesAddRequest = ...,
    admin: AdminUser = Depends(get_current_admin),
):
    """Увеличить лимит устройств подписки."""
    result = await proxy_request(lambda: bedolaga_client.add_devices(sub_id, {"devices": data.count}))
    _invalidate_list()
    return result


@router.post("/subscriptions/{sub_id}/reset-devices")
async def reset_devices(
    sub_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Сбросить устройства подписки (CMS stub — requires panel DB access)."""
    raise HTTPException(
        status_code=501,
        detail={"success": False, "error": "Reset devices requires Remnawave panel integration — not available in CMS standalone mode."},
    )


# ── User by telegram (static path — before /{user_id}) ──

@router.get("/by-telegram/{telegram_id}")
async def get_user_by_telegram(
    telegram_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Найти клиента по Telegram ID."""
    return await proxy_request(lambda: bedolaga_client.get_user_by_telegram(telegram_id))


# ── User detail (dynamic /{user_id} — MUST be last) ──

@router.get("/{user_id}")
async def get_user(
    user_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Детальная информация о клиенте."""
    return await proxy_request(lambda: bedolaga_client.get_user(user_id))


@router.patch("/{user_id}")
async def update_user(
    user_id: int = Path(...),
    data: UserUpdateRequest = ...,
    admin: AdminUser = Depends(get_current_admin),
):
    """Обновить данные клиента: имя, фамилия, логин."""
    body = data.model_dump(exclude_unset=True)
    if not body:
        raise HTTPException(status_code=400, detail={"success": False, "error": "Nothing to update"})
    result = await proxy_request(lambda: bedolaga_client.update_user(user_id, body))
    _invalidate_list()
    return result


# ── Balance ──

@router.post("/{user_id}/balance")
async def modify_balance(
    user_id: int = Path(...),
    data: BalanceModifyRequest = ...,
    admin: AdminUser = Depends(get_current_admin),
):
    """Изменить баланс клиента."""
    payload = {"amount_kopeks": data.amount_kopeks}
    if data.reason:
        payload["description"] = data.reason
    result = await proxy_request(lambda: bedolaga_client.modify_balance(user_id, payload))
    _invalidate_list()
    return result


@router.post("/{user_id}/subscription")
async def create_subscription(
    user_id: int = Path(...),
    data: SubscriptionCreateRequest = ...,
    admin: AdminUser = Depends(get_current_admin),
):
    """Создать/заменить подписку клиента."""
    result = await proxy_request(lambda: bedolaga_client.create_subscription(user_id, data.model_dump()))
    _invalidate_list()
    return result


@router.delete("/{user_id}/subscription")
async def deactivate_subscription(
    user_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Деактивировать подписку клиента."""
    result = await proxy_request(lambda: bedolaga_client.deactivate_subscription(user_id))
    _invalidate_list()
    return result


# ── Activity timeline ──

_ACTIVITY_RECHECK_SECONDS = 300
_activity_support = {"supported": True, "checked_at": 0.0}


def _activity_unavailable(limit: int, offset: int) -> dict:
    return {"items": [], "total": 0, "limit": limit, "offset": offset, "available": False}


def _is_user_not_found(response) -> bool:
    try:
        detail = response.json().get("detail")
    except Exception:
        return False
    return isinstance(detail, str) and "user not found" in detail.lower()


@router.get("/{user_id}/activity")
async def user_activity(
    user_id: int = Path(..., ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    types: Optional[str] = Query(None, description="CSV-фильтр по типам записей"),
    admin: AdminUser = Depends(get_current_admin),
):
    """Лента активности клиента."""
    ensure_configured()

    now = time.monotonic()
    if not _activity_support["supported"]:
        if now - _activity_support["checked_at"] < _ACTIVITY_RECHECK_SECONDS:
            return _activity_unavailable(limit, offset)
        _activity_support["supported"] = True

    try:
        data = await bedolaga_client.get_user_activity(user_id, limit=limit, offset=offset, types=types)
    except HTTPStatusError as e:
        if e.response.status_code == 404 and not _is_user_not_found(e.response):
            logger.info("Bedolaga: activity endpoint not supported by this bot version — hiding section")
            _activity_support.update({"supported": False, "checked_at": now})
            return _activity_unavailable(limit, offset)
        logger.warning("Bedolaga activity error: %s %s", e.response.status_code, e.response.text[:200])
        from . import upstream_status
        raise HTTPException(
            status_code=upstream_status(e.response.status_code),
            detail={"success": False, "error": f"Bedolaga API error: {e.response.status_code}"},
        )
    except (ConnectError, TimeoutException) as e:
        logger.warning("Bedolaga activity connection error: %s", e)
        raise HTTPException(status_code=502, detail={"success": False, "error": "Cannot connect to Bedolaga API"})

    _activity_support.update({"supported": True, "checked_at": now})
    return {**data, "available": True}