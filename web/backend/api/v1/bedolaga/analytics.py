"""Bedolaga revenue analytics — tariff prices, MRR, forecast, customer finance.

Read-only endpoints over the Bot Web API plus the read-only bot PostgreSQL
price catalog. All calculation lives in `core/bedolaga_analytics`; this module
validates query parameters, maps upstream failures to 502/503 and returns the
same flat JSON style as the rest of the `bedolaga` package.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from httpx import ConnectError, HTTPStatusError, TimeoutException

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core import bedolaga_analytics as core

from . import ensure_configured

logger = logging.getLogger(__name__)
router = APIRouter()

_BASIS_OVERVIEW = ("cash", "accrual")
_BASIS_FORECAST = ("cash", "renewal")


def _error(status_code: int, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"success": False, "error": message})


def _month(value: Optional[str]) -> str:
    month = (value or "").strip() or core.month_key(core.now_msk())
    try:
        core.parse_month(month)
    except ValueError:
        raise _error(400, "month must be YYYY-MM")
    return month


def _load_error(exc: BaseException) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, HTTPStatusError):
        code = exc.response.status_code if exc.response is not None else 0
        logger.warning("Bedolaga analytics upstream error: %s", code)
        return _error(502, f"Bedolaga API error: {code}")
    if isinstance(exc, (ConnectError, TimeoutException, asyncio.TimeoutError)):
        logger.warning("Bedolaga analytics connection error: %s", type(exc).__name__)
        return _error(502, "Cannot connect to Bedolaga API")
    logger.warning("Bedolaga analytics data load failed: %s", type(exc).__name__)
    return _error(502, "Bedolaga data is temporarily unavailable")


async def _load(days_back: int, refresh: bool):
    await ensure_configured()
    try:
        return await core.load_raw_data(days_back=days_back, refresh=refresh)
    except Exception as exc:  # noqa: BLE001 — mapped to HTTP below
        raise _load_error(exc)


@router.get("/tariffs")
async def analytics_tariffs(
    days_back: int = Query(365, ge=30, le=3650),
    refresh: bool = Query(False),
    include_inactive: bool = Query(True),
    admin: AdminUser = Depends(get_current_admin),
):
    """Tariff catalog with prices, client counts and money per tariff."""
    raw = await _load(days_back, refresh)
    engine = core.AnalyticsEngine(raw, price_days_back=days_back)
    return engine.tariffs(include_inactive=include_inactive)


@router.get("/overview")
async def analytics_overview(
    month: Optional[str] = Query(None),
    months: int = Query(6, ge=1, le=24),
    days_back: int = Query(365, ge=30, le=3650),
    basis: str = Query("cash"),
    refresh: bool = Query(False),
    admin: AdminUser = Depends(get_current_admin),
):
    """KPI, distribution, coverage and monthly dynamics."""
    report_month = _month(month)
    normalized_basis = (basis or "cash").strip().lower()
    if normalized_basis not in _BASIS_OVERVIEW:
        raise _error(400, "basis must be cash or accrual")
    history_days = max(days_back, months * 31)
    raw = await _load(history_days, refresh)
    engine = core.AnalyticsEngine(raw, price_days_back=days_back)
    return engine.overview(month=report_month, months=months, basis=normalized_basis)


@router.get("/forecast")
async def analytics_forecast(
    month: Optional[str] = Query(None),
    basis: str = Query("cash"),
    refresh: bool = Query(False),
    admin: AdminUser = Depends(get_current_admin),
):
    """Expected payments for a calendar month (charge date or renewal date)."""
    current = core.month_key(core.now_msk())
    target_month = _month(month) if month else core.shift_month(current, 1)
    normalized_basis = (basis or "cash").strip().lower()
    if normalized_basis not in _BASIS_FORECAST:
        raise _error(400, "basis must be cash or renewal")
    raw = await _load(365, refresh)
    engine = core.AnalyticsEngine(raw, price_days_back=365)
    return engine.forecast(month=target_month, basis=normalized_basis)


@router.get("/customers/{user_id}")
async def analytics_customer(
    user_id: int = Path(..., ge=1),
    days_back: int = Query(3650, ge=1, le=3650),
    refresh: bool = Query(False),
    admin: AdminUser = Depends(get_current_admin),
):
    """Financial profile of one customer for the detail page."""
    raw = await _load(days_back, refresh)
    engine = core.AnalyticsEngine(raw, price_days_back=days_back)
    data = engine.customer(user_id)
    if data is None:
        raise _error(404, "Customer not found")
    return data
