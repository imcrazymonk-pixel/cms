"""Bedolaga tariff analytics core.

Pure calculation layer for the Bedolaga revenue pages: name normalization,
payment-description parsing, price catalog (bot DB -> transactions -> unknown),
subscription selection, formulas F1-F15 from TASK.md, data collection with
pagination and a small TTL snapshot cache with single-flight.

No FastAPI imports here: the router in
`web/backend/api/v1/bedolaga/analytics.py` only validates input, maps errors
and returns these dicts. All money is kept in integer kopeks; business time is
Europe/Moscow (UTC+3, no DST).
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Optional

from web.backend.core import bot_db
from web.backend.core.bedolaga_client import bedolaga_client

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3), "MSK")
UNKNOWN_TARIFF_NAME = "Не определён"
UNKNOWN_TARIFF_KEY = "unknown"
BAD_SUB_STATUSES = {"expired", "disabled", "cancelled", "canceled", "deactivated"}
TRIAL_STATUSES = {"trial"}

PRICE_SOURCE_PRIORITY = ("manual", "bot_db", "transactions")
MIN_PRICE_KOPEPS = 100
MAX_PRICE_KOPEPS = 10_000_000
MAX_OBSERVATIONS_PER_PERIOD = 50

SNAPSHOT_TTL = 60.0

_DAY_SECONDS = 86_400
_PRICE_DAYS_RE = re.compile(r"(\d{1,4})\s*(?:дн[а-яё]*|день|дня|дней|days?|day)", re.IGNORECASE)
_PURCHASE_RE = re.compile(
    r"покупк[аи]\s+тариф[а]?\s+(?P<name>.+?)\s+на\s+"
    r"(?P<days>\d{1,4})\s*(?:дн[а-яё]*|день|дня|дней|days?|day)",
    re.IGNORECASE,
)
_RENEWAL_RE = re.compile(
    r"(?<!авто)продлени[ея]\s+подписки\s+на\s+"
    r"(?P<days>\d{1,4})\s*(?:дн[а-яё]*|день|дня|дней|days?|day)"
    r"(?:\s*\((?P<name>[^)]*)\))?",
    re.IGNORECASE,
)
_AUTORENEWAL_RE = re.compile(
    r"автопродлени[ея]\s+подписки\s+на\s+"
    r"(?P<days>\d{1,4})\s*(?:дн[а-яё]*|день|дня|дней|days?|day)",
    re.IGNORECASE,
)
_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")
_NON_NAME_RE = re.compile(r"[^0-9a-zA-Zа-яА-ЯёЁ]+")


# ── Time helpers ──────────────────────────────────────────────────────────


def now_msk() -> datetime:
    return datetime.now(tz=MSK)


def parse_ts(value: Any) -> Optional[datetime]:
    """Parse ISO/int/float into an aware MSK datetime; naive values are UTC."""
    if value is None or value == "":
        return None
    dt: Optional[datetime]
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 1e11:
            seconds /= 1000.0
        try:
            dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            try:
                dt = datetime.fromisoformat(text[:10])
            except ValueError:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MSK)


def iso(value: Any) -> Optional[str]:
    dt = parse_ts(value)
    return dt.isoformat() if dt else None


def date_str(value: Any) -> Optional[str]:
    dt = parse_ts(value)
    return dt.date().isoformat() if dt else None


def parse_month(month: str) -> tuple[datetime, datetime]:
    """Return `[start, end)` MSK bounds; raise ValueError on a bad `YYYY-MM`."""
    match = _MONTH_RE.match((month or "").strip())
    if not match:
        raise ValueError("month must be YYYY-MM")
    year, mon = int(match.group(1)), int(match.group(2))
    if not 1 <= mon <= 12:
        raise ValueError("month must be YYYY-MM")
    start = datetime(year, mon, 1, tzinfo=MSK)
    end = datetime(year + (1 if mon == 12 else 0), 1 if mon == 12 else mon + 1, 1, tzinfo=MSK)
    return start, end


def month_key(value: datetime) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def shift_month(month: str, delta: int) -> str:
    year, mon = (int(part) for part in month.split("-"))
    index = (year * 12 + (mon - 1)) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_days(month: str) -> list[str]:
    start, end = parse_month(month)
    days = (end - start).days
    return [(start + timedelta(days=i)).date().isoformat() for i in range(days)]


def _rubles(kopeks: Optional[int]) -> Optional[float]:
    if kopeks is None:
        return None
    value = Decimal(int(kopeks)) / Decimal(100)
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _pct(part: int, whole: int) -> float:
    if not whole:
        return 0.0
    return round(part * 100.0 / whole, 1)


def _to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None



# ── Names and payment descriptions ────────────────────────────────────────


def normalize_name(name: Any) -> str:
    """Strip emoji/punctuation, casefold, ё→е and collapse spaces."""
    if name is None:
        return ""
    text = str(name).replace("ё", "е").replace("Ё", "Е").casefold()
    text = _NON_NAME_RE.sub(" ", text)
    return " ".join(text.split())


def parse_days(value: Any) -> Optional[int]:
    if value is None:
        return None
    match = _PRICE_DAYS_RE.search(str(value))
    if not match:
        return None
    days = int(match.group(1))
    return days if 1 <= days <= 3650 else None


def _clean_tariff_name(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip().strip("«»\"'`[](){}").strip()
    return text or None


def parse_payment_description(description: Any, fallback_tariff_name: Optional[str] = None) -> dict:
    """Parse a `subscription_payment` description.

    Returns `{"name": str|None, "days": int|None, "kind": str|None}` where
    `kind` is `purchase`, `renewal` or `autorenewal`. A missing name falls back
    to `fallback_tariff_name` when the caller supplies one (the user's current
    subscription), which is used for personal totals, never for the catalog.
    """
    text = str(description or "").strip()
    if not text:
        return {"name": None, "days": None, "kind": None}

    match = _AUTORENEWAL_RE.search(text)
    if match:
        return {
            "name": _clean_tariff_name(fallback_tariff_name),
            "days": _valid_days(match.group("days")),
            "kind": "autorenewal",
        }

    match = _PURCHASE_RE.search(text)
    if match:
        return {
            "name": _clean_tariff_name(match.group("name")),
            "days": _valid_days(match.group("days")),
            "kind": "purchase",
        }

    match = _RENEWAL_RE.search(text)
    if match:
        name = _clean_tariff_name(match.group("name")) or _clean_tariff_name(fallback_tariff_name)
        return {
            "name": name,
            "days": _valid_days(match.group("days")),
            "kind": "renewal",
        }

    return {"name": _clean_tariff_name(fallback_tariff_name), "days": parse_days(text), "kind": None}


def _valid_days(raw: Any) -> Optional[int]:
    days = _to_int(raw)
    return days if days is not None and 1 <= days <= 3650 else None


def payment_kind(description: Any) -> Optional[str]:
    text = str(description or "").casefold()
    if "автопродлен" in text:
        return "autorenewal"
    if "продлен" in text:
        return "renewal"
    if "покупка тарифа" in text:
        return "purchase"
    return None


# ── Subscription helpers ──────────────────────────────────────────────────


def user_subscriptions(user: dict) -> list[dict]:
    """All subscriptions of a user, de-duplicated by id (order preserved)."""
    if not isinstance(user, dict):
        return []
    items: list[dict] = []
    seen: set[Any] = set()
    raw_list = user.get("subscriptions")
    for sub in raw_list if isinstance(raw_list, list) else []:
        if not isinstance(sub, dict):
            continue
        key = sub.get("id")
        if key is not None:
            if key in seen:
                continue
            seen.add(key)
        items.append(sub)
    single = user.get("subscription")
    if isinstance(single, dict):
        key = single.get("id")
        if key is None or key not in seen:
            items.append(single)
    return items


def sub_status(sub: dict) -> str:
    return str(sub.get("status") or "").strip().lower()


def sub_actual_status(sub: dict) -> str:
    return str(sub.get("actual_status") or "").strip().lower()


def sub_end(sub: dict) -> Optional[datetime]:
    return parse_ts(sub.get("end_date"))


def is_trial_sub(sub: dict) -> bool:
    if sub.get("is_trial") is True:
        return True
    return sub_status(sub) in TRIAL_STATUSES or sub_actual_status(sub) in TRIAL_STATUSES


def is_paid_active(sub: dict, now: Optional[datetime] = None) -> bool:
    """Paid active subscription (F3 §3.1); `limited` counts as paid active."""
    if not isinstance(sub, dict):
        return False
    current = now or now_msk()
    end = sub_end(sub)
    if end is None or end <= current:
        return False
    if sub.get("is_trial") is True or is_trial_sub(sub):
        return False
    effective_status = sub_actual_status(sub) or sub_status(sub)
    if effective_status in BAD_SUB_STATUSES:
        return False
    return True


def tariff_of(sub: dict) -> dict:
    tariff_id = _to_int(sub.get("tariff_id"))
    name = str(sub.get("tariff_name") or "").strip()
    if not name and tariff_id is not None:
        name = f"#{tariff_id}"
    if not name:
        name = UNKNOWN_TARIFF_NAME
    return {
        "tariff_id": tariff_id,
        "tariff_name": name,
        "tariff_key": tariff_key(tariff_id, name),
        "tariff_missing": tariff_id is None,
    }


def tariff_key(tariff_id: Optional[int], tariff_name: Optional[str]) -> str:
    if tariff_id is not None:
        return f"id:{tariff_id}"
    normalized = normalize_name(tariff_name)
    if not normalized or normalized == normalize_name(UNKNOWN_TARIFF_NAME):
        return UNKNOWN_TARIFF_KEY
    return f"name:{normalized}"


def primary_subscription(user: dict, now: Optional[datetime] = None) -> Optional[dict]:
    """Paid primary subscription, else the trial one (for the trial slice)."""
    current = now or now_msk()
    subs = user_subscriptions(user)
    paid = [sub for sub in subs if is_paid_active(sub, current)]
    if paid:
        def sort_key(sub: dict) -> tuple[datetime, int]:
            end = sub_end(sub) or datetime.min.replace(tzinfo=MSK)
            return end, _to_int(sub.get("tariff_id")) or 0

        return max(paid, key=sort_key)
    trials = [sub for sub in subs if is_trial_sub(sub) and (sub_end(sub) or current) > current]
    if trials:
        return max(trials, key=lambda sub: sub_end(sub) or current)
    return None


def period_days(sub: dict) -> int:
    explicit = _to_int(sub.get("autopay_period_days"))
    if explicit is not None and 1 <= explicit <= 3650:
        return explicit
    start = parse_ts(sub.get("start_date"))
    end = sub_end(sub)
    if start and end and end > start:
        days = math.floor((end - start).total_seconds() / _DAY_SECONDS)
        if 1 <= days <= 3650:
            return days
    return 30


def remaining_days(sub: dict, now: Optional[datetime] = None) -> int:
    current = now or now_msk()
    end = sub_end(sub)
    if end is None or end <= current:
        return 0
    return max(0, math.ceil((end - current).total_seconds() / _DAY_SECONDS))


def expected_charge_date(sub: dict) -> datetime:
    end = sub_end(sub) or now_msk()
    days_before = _to_int(sub.get("autopay_days_before")) or 0
    if sub.get("autopay_enabled") and days_before >= 0:
        return end - timedelta(days=days_before)
    return end


def user_tariff(user: dict, now: Optional[datetime] = None) -> dict:
    primary = primary_subscription(user, now)
    if primary is not None:
        return tariff_of(primary)
    return {
        "tariff_id": None,
        "tariff_name": UNKNOWN_TARIFF_NAME,
        "tariff_key": UNKNOWN_TARIFF_KEY,
        "tariff_missing": True,
    }


def normalize_user_subscription(user: dict, now: Optional[datetime] = None) -> dict:
    """Return a shallow copy of the user with `subscription` filled.

    The Bot Web API puts tariff fields inside `subscription` (or only inside
    `subscriptions[]` for some rows). Consumers get the same primary rule as
    analytics without mutating the upstream payload.
    """
    if not isinstance(user, dict):
        return {}
    copy = dict(user)
    single = copy.get("subscription")
    if isinstance(single, dict) and single:
        copy["subscription"] = single
    else:
        primary = primary_subscription(copy, now)
        if primary is not None:
            copy["subscription"] = primary
    tariff = user_tariff(copy, now)
    if tariff["tariff_id"] is not None:
        copy["tariff_id"] = tariff["tariff_id"]
        copy["tariff_name"] = tariff["tariff_name"]
    else:
        copy.setdefault("tariff_id", None)
        copy.setdefault("tariff_name", None)
    copy["tariff_missing"] = tariff["tariff_missing"]
    return copy


# ── Price catalog ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Observation:
    days: int
    price_kopeks: int
    created_at: Optional[datetime]


@dataclass(frozen=True)
class PricePart:
    kopeks: int
    source: str
    kind: str
    basis: str
    confidence: str


@dataclass(frozen=True)
class PriceQuote:
    tariff_id: Optional[int]
    tariff_name: str
    period_days: int
    monthly: Optional[PricePart]
    period: Optional[PricePart]
    price_per_day_kopeks: Optional[int]
    samples: int
    last_seen_at: Optional[str]

    @property
    def price_known(self) -> bool:
        return self.monthly is not None or self.period is not None

    @property
    def is_free(self) -> bool:
        return bool(
            (self.monthly is not None and self.monthly.kopeks == 0)
            or (self.period is not None and self.period.kopeks == 0)
        )

    @property
    def main(self) -> Optional[PricePart]:
        return self.monthly or self.period

    @property
    def price_source(self) -> str:
        part = self.main
        return part.source if part else "unknown"

    @property
    def price_kind(self) -> str:
        part = self.main
        return part.kind if part else "unknown"

    @property
    def confidence(self) -> str:
        part = self.main
        return part.confidence if part else "unknown"

    def to_dict(self, prefer: str = "monthly") -> dict:
        part = self.monthly if prefer == "monthly" else (self.period or self.monthly)
        return {
            "price_known": self.price_known,
            "price_source": part.source if part else "unknown",
            "price_kind": part.kind if part else "unknown",
            "price_basis": part.basis if part else "unknown",
            "confidence": part.confidence if part else "unknown",
            "is_free": self.is_free,
            "monthly_price_kopeks": self.monthly.kopeks if self.monthly else None,
            "monthly_price_rubles": _rubles(self.monthly.kopeks) if self.monthly else None,
            "monthly_basis": self.monthly.basis if self.monthly else "unknown",
            "monthly_source": self.monthly.source if self.monthly else "unknown",
            "period_price_kopeks": self.period.kopeks if self.period else None,
            "period_price_rubles": _rubles(self.period.kopeks) if self.period else None,
            "period_basis": self.period.basis if self.period else "unknown",
            "period_days": self.period_days,
            "price_per_day_kopeks": self.price_per_day_kopeks,
            "samples": self.samples,
            "last_seen_at": self.last_seen_at,
        }


def _period_map(row: dict) -> dict[int, int]:
    raw = row.get("period_prices")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            raw = None
    periods: dict[int, int] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            days = _to_int(key)
            price = _to_int(value)
            if days is not None and price is not None and days > 0:
                periods[days] = price
    if not periods and isinstance(row.get("period_prices_list"), list):
        for item in row["period_prices_list"]:
            if not isinstance(item, dict):
                continue
            days = _to_int(item.get("days"))
            price = _to_int(item.get("price_kopeks"))
            if days is not None and price is not None and days > 0:
                periods[days] = price
    return periods


def _confidence(samples: int, last_seen: Optional[datetime], now: datetime) -> str:
    if samples >= 5 and last_seen is not None and (now - last_seen) <= timedelta(days=30):
        return "high"
    if samples >= 2:
        return "medium"
    return "low"


def _lower(confidence: str) -> str:
    return {"high": "medium", "medium": "low", "low": "low"}.get(confidence, confidence)


class PriceCatalog:
    """Prices keyed by `tariff_id` (bot DB) with transaction observations."""

    def __init__(
        self,
        bot_tariffs: Iterable[dict],
        transactions: Iterable[dict],
        users: Iterable[dict],
        *,
        now: datetime,
        days_back: int = 365,
    ) -> None:
        self.now = now
        self.days_back = days_back
        self.bot: dict[int, dict] = {}
        self.display: dict[str, dict] = {}
        self.name_to_ids: dict[str, set[int]] = defaultdict(set)
        self.observations: dict[str, list[Observation]] = defaultdict(list)
        self.warnings: list[dict] = []
        self.named_price_samples = 0

        for row in bot_tariffs or []:
            if not isinstance(row, dict):
                continue
            tariff_id = _to_int(row.get("id"))
            if tariff_id is None:
                continue
            periods = _period_map(row)
            record = {
                "id": tariff_id,
                "name": str(row.get("name") or "").strip() or f"#{tariff_id}",
                "is_active": row.get("is_active") is not False,
                "periods": periods,
                "price_per_day_kopeks": _to_int(row.get("price_per_day_kopeks")),
                "daily_price_kopeks": _to_int(row.get("daily_price_kopeks")),
                "is_daily": bool(row.get("is_daily")),
            }
            self.bot[tariff_id] = record
            normalized = normalize_name(record["name"])
            self.name_to_ids[normalized].add(tariff_id)
            self.display[f"id:{tariff_id}"] = {
                "tariff_id": tariff_id,
                "tariff_name": record["name"],
                "is_active": record["is_active"],
            }

        for user in users or []:
            for sub in user_subscriptions(user):
                tariff = tariff_of(sub)
                tariff_id = tariff["tariff_id"]
                key = tariff["tariff_key"]
                if tariff_id is None and key == UNKNOWN_TARIFF_KEY:
                    continue
                self.display.setdefault(
                    key,
                    {"tariff_id": tariff_id, "tariff_name": tariff["tariff_name"], "is_active": True},
                )
                normalized = normalize_name(tariff["tariff_name"])
                if normalized and tariff_id is not None:
                    self.name_to_ids[normalized].add(tariff_id)

        self._collect_observations(transactions or [])
        self._collect_warnings()

    def _collect_observations(self, transactions: Iterable[dict]) -> None:
        cutoff = self.now - timedelta(days=max(1, int(self.days_back)))
        for tx in transactions:
            if not isinstance(tx, dict):
                continue
            if str(tx.get("type") or "") != "subscription_payment":
                continue
            if tx.get("is_completed") is False:
                continue
            created = parse_ts(tx.get("created_at"))
            if created is not None and created < cutoff:
                continue
            description = tx.get("description")
            info = parse_payment_description(description)
            name, days = info["name"], info["days"]
            if not name or not days:
                continue
            normalized = normalize_name(name)
            if not normalized:
                continue
            amount = tx.get("amount_kopeks")
            price = abs(_to_int(amount) or 0)
            if price == 0:
                # Zero-amount records (admin tariff change / mass action) are
                # not price evidence; a free tariff is recognized via bot DB.
                continue
            if not MIN_PRICE_KOPEPS <= price <= MAX_PRICE_KOPEPS:
                continue
            self.observations[normalized].append(Observation(days, price, created))
            self.named_price_samples += 1

        for normalized, items in list(self.observations.items()):
            items.sort(key=lambda obs: obs.created_at or datetime.min.replace(tzinfo=MSK), reverse=True)
            by_days: dict[int, list[Observation]] = defaultdict(list)
            for obs in items:
                by_days[obs.days].append(obs)
            self.observations[normalized] = [
                obs for bucket in by_days.values() for obs in bucket[:MAX_OBSERVATIONS_PER_PERIOD]
            ]

    def _collect_warnings(self) -> None:
        for normalized, ids in self.name_to_ids.items():
            if normalized and len(ids) > 1:
                self.warnings.append(
                    {
                        "code": "ambiguous_tariff_name",
                        "message": f"Несколько тарифов с одинаковым названием: {sorted(ids)}",
                        "tariff_ids": sorted(ids),
                    }
                )

        disagreeing: list[int] = []
        for tariff_id, record in self.bot.items():
            bot_monthly = self._bot_monthly(record)
            realized = self._realized_part(record["name"], 30)
            if not (bot_monthly and realized and bot_monthly.kopeks > 0 and realized.kopeks > 0):
                continue
            diff = abs(bot_monthly.kopeks - realized.kopeks) / max(bot_monthly.kopeks, realized.kopeks)
            if diff > 0.10:
                disagreeing.append(tariff_id)
        if disagreeing:
            self.warnings.append(
                {
                    "code": "price_sources_disagree",
                    "message": "Цена из БД бота расходится с фактическими платежами более чем на 10%",
                    "tariff_ids": sorted(disagreeing),
                }
            )

        changed: set[int] = set()
        for key, info in self.display.items():
            tariff_id = info["tariff_id"]
            record = self.bot.get(tariff_id)
            if record and normalize_name(record["name"]) != normalize_name(info["tariff_name"]):
                changed.add(tariff_id)
        if changed:
            self.warnings.append(
                {
                    "code": "tariff_name_changed",
                    "message": "Название тарифа в подписках отличается от каталога бота",
                    "tariff_ids": sorted(changed),
                }
            )

    # ── Lookups ──

    def _bot_monthly(self, record: dict) -> Optional[PricePart]:
        periods = record["periods"]
        if 30 in periods:
            return PricePart(periods[30], "bot_db", "list", "30_day", "high")
        per_day = record.get("price_per_day_kopeks")
        if per_day is not None:
            return PricePart(int(round(per_day * 30)), "bot_db", "list", "per_day", "high")
        return None


    def _name_stats(self, name: Optional[str]) -> dict:
        normalized = normalize_name(name)
        items = self.observations.get(normalized, [])
        by_days: dict[int, list[Observation]] = defaultdict(list)
        for obs in items:
            by_days[obs.days].append(obs)
        latest = max((obs.created_at for obs in items if obs.created_at), default=None)
        return {
            "items": items,
            "by_days": by_days,
            "latest": latest,
            "samples": len(items),
            "confidence": _confidence(len(items), latest, self.now),
        }

    def _transaction_period(self, name: Optional[str], days: int, stats: Optional[dict] = None) -> Optional[PricePart]:
        stats = stats or self._name_stats(name)
        bucket = stats["by_days"].get(days) or []
        if bucket:
            price = int(statistics.median(obs.price_kopeks for obs in bucket))
            return PricePart(price, "transactions", "realized", "exact_period", stats["confidence"])
        return None

    def _transaction_per_day(self, name: Optional[str], stats: Optional[dict] = None) -> Optional[PricePart]:
        stats = stats or self._name_stats(name)
        values = [
            obs.price_kopeks / obs.days
            for obs in stats["items"]
            if obs.days > 0 and obs.price_kopeks > 0
        ]
        if not values:
            return None
        price = int(round(statistics.median(values)))
        return PricePart(price, "transactions", "realized", "realized_per_day", _lower(stats["confidence"]))

    def _bot_period(self, record: dict, days: int) -> Optional[PricePart]:
        periods = record["periods"]
        if days in periods:
            return PricePart(periods[days], "bot_db", "list", "exact_period", "high")
        per_day = record.get("price_per_day_kopeks")
        if per_day is not None:
            return PricePart(int(round(per_day * days)), "bot_db", "list", "proportional", "medium")
        return None

    def _realized_part(self, name: Optional[str], days: int) -> Optional[PricePart]:
        stats = self._name_stats(name)
        part = self._transaction_period(name, days, stats)
        if part:
            return part
        per_day = self._transaction_per_day(name, stats)
        if per_day:
            return PricePart(int(round(per_day.kopeks * days)), "transactions", "realized", "realized_per_day", per_day.confidence)
        return None

    def _daily_part(self, record: dict, days: int) -> Optional[PricePart]:
        daily = record.get("daily_price_kopeks")
        if daily is None:
            return None
        return PricePart(int(round(daily * days)), "bot_db", "list", "proportional", "medium")

    @staticmethod
    def _free_record(record: dict) -> bool:
        """True when bot DB explicitly says the tariff costs nothing.

        A record with no price fields at all is "unknown", not free.
        """
        periods = record["periods"]
        per_day = record.get("price_per_day_kopeks")
        daily = record.get("daily_price_kopeks")
        if not periods and per_day is None and daily is None:
            return False
        if any(price > 0 for price in periods.values()):
            return False
        if per_day is not None and per_day > 0:
            return False
        if daily is not None and daily > 0:
            return False
        return True

    @staticmethod
    def _monthly_proportional(monthly: PricePart, days: int) -> PricePart:
        return PricePart(
            int(round(monthly.kopeks / 30 * days)),
            monthly.source,
            monthly.kind,
            "proportional",
            monthly.confidence,
        )

    # ── Public resolution ──

    def quote(self, tariff_id: Optional[int], tariff_name: Optional[str], days: int = 30) -> PriceQuote:
        safe_days = days if isinstance(days, int) and days > 0 else 30
        record = self.bot.get(tariff_id) if tariff_id is not None else None
        name = tariff_name or (record["name"] if record else UNKNOWN_TARIFF_NAME)
        stats = self._name_stats(name)

        period: Optional[PricePart] = None
        if record is not None:
            period = self._bot_period(record, safe_days)
        if period is None:
            period = self._realized_part(name, safe_days)
        if period is None and record is not None:
            period = self._daily_part(record, safe_days)

        monthly: Optional[PricePart] = None
        if record is not None:
            monthly = self._bot_monthly(record)
        if monthly is None:
            monthly = self._realized_part(name, 30)
            if monthly is not None and monthly.basis == "exact_period":
                monthly = PricePart(monthly.kopeks, monthly.source, monthly.kind, "30_day", monthly.confidence)
        if monthly is None and record is not None:
            daily = record.get("daily_price_kopeks")
            if daily is not None:
                monthly = PricePart(int(round(daily * 30)), "bot_db", "list", "daily", "high")

        # Explicitly free bot tariff: zero stays a valid known price, but only
        # when transactions do not hold positive observations for this tariff.
        if record is not None and not stats["items"] and self._free_record(record):
            if monthly is None:
                monthly = PricePart(0, "bot_db", "list", "30_day", "high")
            if period is None:
                basis = "exact_period" if safe_days in record["periods"] else "proportional"
                period = PricePart(0, "bot_db", "list", basis, "high")

        # No exact period price, but a valid monthly one: prorate by days.
        if period is None and monthly is not None:
            period = self._monthly_proportional(monthly, safe_days)
        elif (
            period is not None
            and period.kopeks == 0
            and monthly is not None
            and monthly.kopeks > 0
            and not (period.source == "bot_db" and period.basis == "exact_period")
        ):
            # A zero realized/proportional period must not beat a positive
            # monthly price from the bot DB.
            period = self._monthly_proportional(monthly, safe_days)

        per_day: Optional[int] = None
        if record is not None and record.get("price_per_day_kopeks") is not None:
            per_day = int(record["price_per_day_kopeks"])
        elif record is not None and record.get("daily_price_kopeks") is not None:
            per_day = int(record["daily_price_kopeks"])
        elif period is not None:
            per_day = int(round(period.kopeks / safe_days))
        elif monthly is not None:
            per_day = int(round(monthly.kopeks / 30))

        return PriceQuote(
            tariff_id=tariff_id,
            tariff_name=name,
            period_days=safe_days,
            monthly=monthly,
            period=period,
            price_per_day_kopeks=per_day,
            samples=stats["samples"],
            last_seen_at=stats["latest"].isoformat() if stats["latest"] else None,
        )

    def monthly(self, tariff_id: Optional[int], tariff_name: Optional[str]) -> Optional[PricePart]:
        return self.quote(tariff_id, tariff_name, 30).monthly


# ── Data collection ───────────────────────────────────────────────────────


@dataclass
class PageResult:
    items: list = field(default_factory=list)
    total: int = 0
    pages_loaded: int = 0
    partial: bool = False
    error: Optional[str] = None


@dataclass
class RawData:
    users: PageResult
    transactions: PageResult
    bot_db: dict
    full_stats: Optional[dict]
    fetched_at: datetime
    warnings: list[dict] = field(default_factory=list)

    @property
    def partial(self) -> bool:
        return bool(self.users.partial or self.transactions.partial)


def _warn(code: str, message: str, **extra: Any) -> dict:
    return {"code": code, "message": message, **extra}


def _dedupe(warnings: Iterable[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result: list[dict] = []
    for warning in warnings:
        key = (warning.get("code"), warning.get("message"))
        if key in seen:
            continue
        seen.add(key)
        result.append(warning)
    return result


def _error_text(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:300]


async def _call(client: Any, method: str, **kwargs: Any) -> dict:
    result = await getattr(client, method)(**kwargs)
    return result if isinstance(result, dict) else {}


async def fetch_all_users(
    client: Any = None,
    *,
    page_size: int = 200,
    max_pages: int = 100,
    timeout: float = 15.0,
) -> PageResult:
    """Load every `/users` page (200 per request); first-page errors raise."""
    api = client or bedolaga_client
    limit = max(1, min(int(page_size), 200))
    first = await asyncio.wait_for(_call(api, "list_users", limit=limit, offset=0), timeout=timeout)
    items = list(first.get("items") or [])
    total = _to_int(first.get("total")) or len(items)
    result = PageResult(items=items, total=total, pages_loaded=1)
    offset = len(items)
    pages = 1
    while items and len(result.items) < total and pages < max_pages:
        try:
            page = await asyncio.wait_for(
                _call(api, "list_users", limit=limit, offset=offset),
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 — partial data beats a failed page
            logger.warning("Bedolaga users page %s failed: %s", offset, _error_text(exc))
            result.partial = True
            result.error = _error_text(exc)
            break
        page_items = list(page.get("items") or [])
        if not page_items:
            break
        result.items.extend(page_items)
        offset += len(page_items)
        pages += 1
        if len(page_items) < limit:
            break
    result.pages_loaded = pages
    result.total = max(total, len(result.items))
    if len(result.items) < result.total:
        result.partial = True
    return result


async def fetch_all_transactions(
    client: Any = None,
    *,
    page_size: int = 100,
    concurrency: int = 4,
    max_pages: int = 200,
    timeout: float = 15.0,
    date_from: Optional[str] = None,
) -> PageResult:
    """Load `/transactions` pages with concurrency <= 4; partial on page errors."""
    api = client or bedolaga_client
    limit = max(1, min(int(page_size), 200))
    filters: dict[str, Any] = {}
    if date_from:
        filters["date_from"] = date_from
    first = await asyncio.wait_for(
        _call(api, "list_transactions", limit=limit, offset=0, **filters),
        timeout=timeout,
    )
    first_items = list(first.get("items") or [])
    total = _to_int(first.get("total")) or len(first_items)
    result = PageResult(items=list(first_items), total=total, pages_loaded=1)
    if not first_items or len(first_items) >= total:
        result.total = max(total, len(first_items))
        return result

    start_offset = len(first_items)
    offsets = list(
        range(start_offset, min(total, start_offset + limit * max_pages), limit)
    )
    semaphore = asyncio.Semaphore(max(1, min(int(concurrency), 4)))

    async def load(offset: int) -> tuple[int, Optional[list], Optional[str]]:
        async with semaphore:
            try:
                page = await asyncio.wait_for(
                    _call(api, "list_transactions", limit=limit, offset=offset, **filters),
                    timeout=timeout,
                )
                return offset, list(page.get("items") or []), None
            except Exception as exc:  # noqa: BLE001 — keep other pages
                logger.warning("Bedolaga transactions page %s failed: %s", offset, _error_text(exc))
                return offset, None, _error_text(exc)

    pages = await asyncio.gather(*(load(offset) for offset in offsets))
    errors: list[str] = []
    for offset, page_items, error in sorted(pages, key=lambda row: row[0]):
        if page_items is None:
            errors.append(error or "page failed")
            continue
        result.items.extend(page_items)
        result.pages_loaded += 1

    result.partial = bool(errors)
    result.error = errors[0] if errors else None
    result.total = max(total, len(result.items))
    if len(result.items) < result.total:
        result.partial = True
    return result


async def fetch_full_stats(client: Any = None, *, timeout: float = 10.0) -> Optional[dict]:
    api = client or bedolaga_client
    try:
        return await asyncio.wait_for(_call(api, "get_full_stats"), timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — analytics can live without aggregates
        logger.warning("Bedolaga /stats/full unavailable: %s", _error_text(exc))
        return None


async def _load_raw_data(days_back: int) -> RawData:
    fetched_at = now_msk()
    date_from = (fetched_at - timedelta(days=max(1, int(days_back)))).date().isoformat()

    tariffs_task = bot_db.get_tariffs_result(timeout=2.0)
    users_task = fetch_all_users()
    tx_task = fetch_all_transactions(date_from=date_from)
    stats_task = fetch_full_stats()

    bot_result, users, transactions, full_stats = await asyncio.gather(
        tariffs_task, users_task, tx_task, stats_task, return_exceptions=True
    )

    if isinstance(users, BaseException):
        raise users

    if isinstance(bot_result, BaseException):
        bot_result = {
            "status": "error",
            "tariffs": [],
            "error": _error_text(bot_result),
            "checked_at": fetched_at.isoformat(),
        }

    if isinstance(transactions, BaseException):
        transactions = PageResult(
            items=[], total=0, pages_loaded=0, partial=True, error=_error_text(transactions)
        )

    if isinstance(full_stats, BaseException):
        full_stats = None

    warnings: list[dict] = []
    if users.partial:
        warnings.append(
            _warn(
                "users_partial",
                f"Загружено {len(users.items)} из {users.total} пользователей",
                loaded=len(users.items),
                total=users.total,
            )
        )
    if transactions.partial:
        code = "transactions_unavailable" if not transactions.items else "transactions_partial"
        warnings.append(
            _warn(
                code,
                "Не все транзакции получены; суммы могут быть неполными",
                loaded=len(transactions.items),
                total=transactions.total,
            )
        )
    status = str((bot_result or {}).get("status") or "disabled")
    if status in ("disabled", "error", "timeout"):
        warnings.append(
            _warn(
                "bot_db_disabled" if status == "disabled" else "bot_db_error",
                "Каталог цен из БД бота недоступен; используется fallback по транзакциям",
                status=status,
            )
        )

    return RawData(
        users=users,
        transactions=transactions,
        bot_db=bot_result or {"status": "disabled", "tariffs": []},
        full_stats=full_stats if isinstance(full_stats, dict) else None,
        fetched_at=fetched_at,
        warnings=warnings,
    )


_raw_cache: dict[tuple[int], tuple[float, RawData]] = {}
_raw_locks: dict[tuple[int], asyncio.Lock] = {}


def invalidate_snapshot_cache() -> None:
    _raw_cache.clear()


async def load_raw_data(*, days_back: int = 365, refresh: bool = False) -> RawData:
    """TTL-cached source data with single-flight per `days_back`."""
    key = (max(1, int(days_back)),)
    now_mono = time.monotonic()
    if not refresh:
        cached = _raw_cache.get(key)
        if cached and now_mono - cached[0] < SNAPSHOT_TTL:
            return cached[1]

    started = time.monotonic()
    lock = _raw_locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _raw_cache.get(key)
        if cached and not refresh and time.monotonic() - cached[0] < SNAPSHOT_TTL:
            return cached[1]
        if cached and refresh and cached[0] >= started:
            # Another refresh finished while this call was waiting on the lock.
            return cached[1]
        raw = await _load_raw_data(key[0])
        _raw_cache[key] = (time.monotonic(), raw)
        return raw


# ── Engine: formulas F1–F15 ───────────────────────────────────────────────


class AnalyticsEngine:
    """Point-in-time view over one raw snapshot."""

    def __init__(self, raw: RawData, *, now: Optional[datetime] = None, price_days_back: int = 365) -> None:
        self.raw = raw
        self.now = now or raw.fetched_at or now_msk()
        self.users = [u for u in raw.users.items if isinstance(u, dict)]
        self.transactions = [t for t in raw.transactions.items if isinstance(t, dict)]
        self.catalog = PriceCatalog(
            raw.bot_db.get("tariffs") or [],
            self.transactions,
            self.users,
            now=self.now,
            days_back=price_days_back,
        )
        self._paid_subs: list[tuple[dict, dict]] = []
        self._trial_subs: list[tuple[dict, dict]] = []
        for user in self.users:
            for sub in user_subscriptions(user):
                if is_paid_active(sub, self.now):
                    self._paid_subs.append((user, sub))
                elif is_trial_sub(sub) and (sub_end(sub) or self.now) > self.now:
                    self._trial_subs.append((user, sub))

    # ── Shared helpers ──

    def _sources(self) -> dict:
        tx_status = "ok"
        if self.raw.transactions.partial:
            tx_status = "partial" if self.raw.transactions.items else "insufficient"
        return {
            "bot_db": {
                "status": self.raw.bot_db.get("status") or "disabled",
                "checked_at": self.raw.bot_db.get("checked_at"),
                "tariffs": len(self.raw.bot_db.get("tariffs") or []),
            },
            "transactions": {
                "status": tx_status,
                "scanned": len(self.transactions),
                "named_price_samples": self.catalog.named_price_samples,
                "total": self.raw.transactions.total,
            },
            "users": {
                "status": "partial" if self.raw.users.partial else "ok",
                "loaded": len(self.users),
                "total": self.raw.users.total,
            },
            "full_stats": {"status": "ok" if self.raw.full_stats else "unavailable"},
        }

    def _base_warnings(self) -> list[dict]:
        warnings = list(self.raw.warnings) + list(self.catalog.warnings)
        codes = {warning.get("code") for warning in warnings}
        if self.raw.users.partial and "users_partial" not in codes:
            warnings.append(
                _warn(
                    "users_partial",
                    f"Загружено {len(self.raw.users.items)} из {self.raw.users.total} пользователей",
                )
            )
        if self.raw.transactions.partial:
            derived = "transactions_unavailable" if not self.raw.transactions.items else "transactions_partial"
            if derived not in codes and "transactions_unavailable" not in codes:
                warnings.append(_warn(derived, "Не все транзакции получены; суммы могут быть неполными"))
        bot_status = str(self.raw.bot_db.get("status") or "")
        if bot_status in ("disabled", "error", "timeout"):
            derived = "bot_db_disabled" if bot_status == "disabled" else "bot_db_error"
            if derived not in codes:
                warnings.append(
                    _warn(
                        derived,
                        "Каталог цен из БД бота недоступен; используется fallback по транзакциям",
                        status=bot_status,
                    )
                )
        return warnings

    def _tariff_counts(self) -> tuple[Counter, Counter, int]:
        paid: Counter = Counter()
        trial: Counter = Counter()
        without = 0
        for user in self.users:
            primary = primary_subscription(user, self.now)
            if primary is not None and is_paid_active(primary, self.now):
                paid[tariff_of(primary)["tariff_key"]] += 1
            elif primary is not None and is_trial_sub(primary):
                trial[tariff_of(primary)["tariff_key"]] += 1
            else:
                without += 1
        return paid, trial, without

    def _coverage(self) -> dict:
        paid, trial, without = self._tariff_counts()
        known = unknown = 0
        for _user, sub in self._paid_subs:
            tariff = tariff_of(sub)
            quote = self.catalog.quote(tariff["tariff_id"], tariff["tariff_name"], 30)
            if quote.monthly is not None:
                known += 1
            else:
                unknown += 1
        total = len(self._paid_subs)
        return {
            "users_total": len(self.users),
            "clients_with_paid": sum(paid.values()),
            "active_paid_subscriptions": total,
            "trial_subscriptions": len(self._trial_subs),
            "clients_without_subscription": without,
            "price_known_subscriptions": known,
            "price_unknown_subscriptions": unknown,
            "price_coverage_pct": _pct(known, total) if total else 0.0,
        }

    def _sub_period_price(self, sub: dict) -> tuple[Optional[int], PriceQuote]:
        tariff = tariff_of(sub)
        days = period_days(sub)
        quote = self.catalog.quote(tariff["tariff_id"], tariff["tariff_name"], days)
        if quote.period is not None:
            return quote.period.kopeks, quote
        if quote.monthly is not None:
            return int(round(quote.monthly.kopeks / 30 * days)), quote
        return None, quote

    def _mrr(self) -> dict:
        total = 0
        unknown = 0
        sources: set[str] = set()
        for _user, sub in self._paid_subs:
            tariff = tariff_of(sub)
            part = self.catalog.monthly(tariff["tariff_id"], tariff["tariff_name"])
            if part is None:
                unknown += 1
                continue
            total += part.kopeks
            sources.add(part.source)
        if not sources:
            basis = "unknown"
        elif len(sources) == 1:
            basis = "list" if "bot_db" in sources else "realized"
        else:
            basis = "mixed"
        return {"kopeks": total, "unknown": unknown, "basis": basis, "is_lower_bound": unknown > 0}

    def _paid_forward(self) -> dict:
        total = 0
        unknown = 0
        by_key: Counter = Counter()
        for _user, sub in self._paid_subs:
            days = period_days(sub)
            price, _quote = self._sub_period_price(sub)
            if price is None or days <= 0:
                unknown += 1
                continue
            left = remaining_days(sub, self.now)
            amount = int(round(left * price / days))
            total += amount
            by_key[tariff_of(sub)["tariff_key"]] += amount
        return {"kopeks": total, "unknown": unknown, "by_tariff": by_key}

    def _monthly_transaction_stats(self, start: datetime, end: datetime) -> dict:
        received = 0
        count = 0
        users: set[Any] = set()
        renewals = 0
        purchases = 0
        for tx in self.transactions:
            if str(tx.get("type") or "") != "subscription_payment":
                continue
            if tx.get("is_completed") is False:
                continue
            created = parse_ts(tx.get("created_at"))
            if created is None or not (start <= created < end):
                continue
            amount = abs(_to_int(tx.get("amount_kopeks")) or 0)
            received += amount
            count += 1
            user_id = tx.get("user_id")
            if user_id is not None:
                users.add(user_id)
            kind = payment_kind(tx.get("description"))
            if kind in ("renewal", "autorenewal"):
                renewals += 1
            elif kind == "purchase":
                purchases += 1
        proxy = None
        if renewals + purchases:
            proxy = round(renewals / (renewals + purchases), 3)
        return {
            "cash_received_kopeks": received,
            "cash_received_rubles": _rubles(received),
            "payments_count": count,
            "unique_payers": len(users),
            "renewal_payments": renewals,
            "purchase_payments": purchases,
            "renewal_proxy": proxy,
            "avg_payment_kopeks": int(round(received / count)) if count else None,
        }

    def _accrual(self, start: datetime, end: datetime) -> tuple[Optional[int], int]:
        total = 0
        unknown = 0
        for _user, sub in self._paid_subs:
            sub_start = parse_ts(sub.get("start_date"))
            sub_end_at = sub_end(sub)
            if sub_start is None or sub_end_at is None:
                unknown += 1
                continue
            overlap_start = max(sub_start, start)
            overlap_end = min(sub_end_at, end)
            if overlap_end <= overlap_start:
                continue
            days = period_days(sub)
            price, _quote = self._sub_period_price(sub)
            if price is None or days <= 0:
                unknown += 1
                continue
            overlap_days = math.ceil((overlap_end - overlap_start).total_seconds() / _DAY_SECONDS)
            total += int(round(overlap_days * price / days))
        return (total if total or unknown == 0 else None), unknown

    def _forecast_month(self, month: str, basis: str = "cash") -> dict:
        start, end = parse_month(month)
        items: list[dict] = []
        by_day: dict[str, dict] = {day: {"date": day, "expected_kopeks": 0, "payments_count": 0} for day in month_days(month)}
        by_tariff: dict[str, dict] = {}
        expected = 0
        unknown = 0
        autopay = 0

        for user, sub in self._paid_subs:
            target = sub_end(sub) if basis == "renewal" else expected_charge_date(sub)
            if target is None or not (start <= target < end):
                continue
            tariff = tariff_of(sub)
            days = period_days(sub)
            price, quote = self._sub_period_price(sub)
            known = price is not None
            if known:
                expected += price
            else:
                unknown += 1
            autopay_enabled = bool(sub.get("autopay_enabled"))
            if autopay_enabled:
                autopay += 1
            day_key = target.date().isoformat()
            bucket = by_day.setdefault(day_key, {"date": day_key, "expected_kopeks": 0, "payments_count": 0})
            bucket["payments_count"] += 1
            bucket["expected_kopeks"] += price or 0
            tariff_bucket = by_tariff.setdefault(
                tariff["tariff_key"],
                {
                    "tariff_id": tariff["tariff_id"],
                    "tariff_name": tariff["tariff_name"],
                    "expected_kopeks": 0,
                    "payments_count": 0,
                    "unknown_count": 0,
                },
            )
            tariff_bucket["payments_count"] += 1
            tariff_bucket["expected_kopeks"] += price or 0
            if not known:
                tariff_bucket["unknown_count"] += 1
            items.append(
                {
                    "user_id": _to_int(user.get("id")),
                    "username": user.get("username") or user.get("first_name") or "",
                    "subscription_id": _to_int(sub.get("id")),
                    "tariff_id": tariff["tariff_id"],
                    "tariff_name": tariff["tariff_name"],
                    "period_days": days,
                    "period_price_kopeks": price,
                    "end_date": iso(sub.get("end_date")),
                    "expected_charge_date": target.date().isoformat(),
                    "autopay_enabled": autopay_enabled,
                    "autopay_days_before": _to_int(sub.get("autopay_days_before")),
                    "amount_kopeks": price,
                    "price_known": known,
                    "price_source": quote.price_source,
                }
            )

        items.sort(key=lambda row: (row["expected_charge_date"] or "", row["user_id"] or 0))
        warnings: list[dict] = []
        if autopay:
            warnings.append(
                _warn(
                    "autopay_balance_unaccounted",
                    "Часть автоплатежей может пройти с баланса клиента; прогноз валовый",
                    autopay_enabled_count=autopay,
                )
            )
        if unknown:
            warnings.append(
                _warn(
                    "price_unknown",
                    "Для части подписок цена периода не определена",
                    unknown_count=unknown,
                )
            )
        return {
            "month": month,
            "basis": basis,
            "totals": {
                "expected_kopeks": expected,
                "expected_rubles": _rubles(expected),
                "payments_count": len(items),
                "unknown_count": unknown,
                "autopay_enabled_count": autopay,
            },
            "by_day": [by_day[day] for day in sorted(by_day)],
            "by_tariff": sorted(
                by_tariff.values(),
                key=lambda row: (-row["expected_kopeks"], row["tariff_name"] or ""),
            ),
            "items": items[:500],
            "items_total": len(items),
            "warnings": warnings,
        }

    def _renewals_due(self, month: str) -> dict:
        start, end = parse_month(month)
        total = 0
        count = 0
        unknown = 0
        for _user, sub in self._paid_subs:
            target = sub_end(sub)
            if target is None or not (start <= target < end):
                continue
            price, _quote = self._sub_period_price(sub)
            if price is None:
                unknown += 1
                count += 1
                continue
            total += price
            count += 1
        return {"kopeks": total, "count": count, "unknown": unknown}

    def _tariff_row(self, key: str, info: dict, paid: Counter, trial: Counter, mrr_by: Counter, forward_by: Counter, next_by: dict, unknown_by: Counter) -> dict:
        tariff_id = info.get("tariff_id")
        name = info.get("tariff_name") or UNKNOWN_TARIFF_NAME
        quote = self.catalog.quote(tariff_id, name, 30)
        monthly = quote.monthly
        clients_paid = paid.get(key, 0)
        clients_trial = trial.get(key, 0)
        return {
            "tariff_id": tariff_id,
            "tariff_name": name,
            "normalized_name": normalize_name(name),
            "is_active": bool(info.get("is_active", True)),
            "is_free": quote.is_free,
            "price_known": monthly is not None,
            "price_source": monthly.source if monthly else "unknown",
            "price_kind": monthly.kind if monthly else "unknown",
            "confidence": quote.confidence,
            "period_prices": self._period_rows(tariff_id, name),
            "monthly_price_kopeks": monthly.kopeks if monthly else None,
            "monthly_price_rubles": _rubles(monthly.kopeks) if monthly else None,
            "price_per_day_kopeks": quote.price_per_day_kopeks,
            "price_basis": monthly.basis if monthly else "unknown",
            "clients_paid": clients_paid,
            "clients_trial": clients_trial,
            "clients_total": clients_paid + clients_trial,
            "share_pct": _pct(clients_paid, sum(paid.values())),
            "mrr_kopeks": mrr_by.get(key, 0),
            "paid_forward_kopeks": forward_by.get(key, 0),
            "next_month_expected_kopeks": next_by.get(key, 0),
            "unknown_price_clients": unknown_by.get(key, 0),
        }

    def _period_rows(self, tariff_id: Optional[int], name: str) -> list[dict]:
        record = self.catalog.bot.get(tariff_id) if tariff_id is not None else None
        if record and record["periods"]:
            return [
                {"days": days, "price_kopeks": price, "price_rubles": _rubles(price), "samples": None, "last_seen_at": None}
                for days, price in sorted(record["periods"].items())
            ]
        stats = self.catalog._name_stats(name)
        rows = []
        for days, samples in sorted(stats["by_days"].items()):
            price = int(statistics.median(obs.price_kopeks for obs in samples))
            latest = max((obs.created_at for obs in samples if obs.created_at), default=None)
            rows.append(
                {
                    "days": days,
                    "price_kopeks": price,
                    "price_rubles": _rubles(price),
                    "samples": len(samples),
                    "last_seen_at": latest.isoformat() if latest else None,
                }
            )
        return rows

    def _market(self, month: str) -> tuple[list[dict], dict]:
        paid, trial, without = self._tariff_counts()
        mrr = self._mrr()
        forward = self._paid_forward()
        next_month = shift_month(month, 1)
        forecast = self._forecast_month(next_month, "cash")

        mrr_by: Counter = Counter()
        unknown_by: Counter = Counter()
        for _user, sub in self._paid_subs:
            tariff = tariff_of(sub)
            part = self.catalog.monthly(tariff["tariff_id"], tariff["tariff_name"])
            if part is not None:
                mrr_by[tariff["tariff_key"]] += part.kopeks
        for user in self.users:
            primary = primary_subscription(user, self.now)
            if primary is None or not is_paid_active(primary, self.now):
                continue
            tariff = tariff_of(primary)
            if self.catalog.monthly(tariff["tariff_id"], tariff["tariff_name"]) is None:
                unknown_by[tariff["tariff_key"]] += 1
        next_by: Counter = Counter()
        for row in forecast["by_tariff"]:
            next_by[tariff_key(row["tariff_id"], row["tariff_name"])] += row["expected_kopeks"]

        known_keys = (
            set(paid)
            | set(trial)
            | set(mrr_by)
            | set(forward["by_tariff"])
            | {f"id:{tid}" for tid in self.catalog.bot}
        )
        rows = [
            self._tariff_row(key, self.catalog.display.get(key, {"tariff_id": None, "tariff_name": UNKNOWN_TARIFF_NAME}), paid, trial, mrr_by, forward["by_tariff"], next_by, unknown_by)
            for key in known_keys
        ]
        rows.sort(key=lambda row: (row["tariff_id"] is None, -(row["mrr_kopeks"] or 0), row["normalized_name"]))
        totals = {
            "clients_paid": sum(paid.values()),
            "clients_trial": sum(trial.values()),
            "clients_without_subscription": without,
            "mrr_kopeks": mrr["kopeks"],
            "mrr_basis": mrr["basis"],
            "mrr_is_lower_bound": mrr["is_lower_bound"],
            "mrr_unknown_subscriptions": mrr["unknown"],
            "paid_forward_kopeks": forward["kopeks"],
            "next_month_expected_kopeks": sum(next_by.values()),
            "unknown_price_clients": sum(unknown_by.values()),
        }
        return rows, totals

    def _price_unknown_warning(self) -> Optional[dict]:
        ids: set[int] = set()
        names: list[str] = []
        for _user, sub in self._paid_subs:
            tariff = tariff_of(sub)
            if self.catalog.monthly(tariff["tariff_id"], tariff["tariff_name"]) is None:
                if tariff["tariff_id"] is not None:
                    ids.add(tariff["tariff_id"])
                elif tariff["tariff_name"] not in names:
                    names.append(tariff["tariff_name"])
        if not ids and not names:
            return None
        label = ", ".join([f"#{i}" for i in sorted(ids)] + names)
        return _warn("price_unknown", f"Цена не определена для тарифов: {label}", tariff_ids=sorted(ids))

    def _multi_subscription_warning(self) -> Optional[dict]:
        counts = Counter()
        for user, _sub in self._paid_subs:
            counts[_to_int(user.get("id"))] += 1
        extra = sum(1 for value in counts.values() if value > 1)
        if not extra:
            return None
        return _warn(
            "multi_subscription_clients",
            "У части клиентов несколько активных платных подписок",
            clients=extra,
        )

    def _meta(self, warnings: Iterable[dict]) -> dict:
        return {
            "generated_at": self.now.isoformat(),
            "as_of": self.now.date().isoformat(),
            "partial": self.raw.partial,
            "warnings": _dedupe(warnings),
            "sources": self._sources(),
        }

    # ── Public views ──

    def tariffs(self, *, include_inactive: bool = True) -> dict:
        month = month_key(self.now)
        rows, totals = self._market(month)
        if not include_inactive:
            rows = [row for row in rows if row["is_active"] or row["clients_total"]]

        warnings: list[dict] = list(self._base_warnings())
        unknown_warning = self._price_unknown_warning()
        if unknown_warning:
            warnings.append(unknown_warning)
        multi = self._multi_subscription_warning()
        if multi:
            warnings.append(multi)

        coverage = self._coverage()
        payload = {
            "currency": "RUB",
            "price_source_priority": list(PRICE_SOURCE_PRIORITY),
            "coverage": coverage,
            "items": rows,
            "totals": totals,
        }
        payload.update(self._meta(warnings))
        return payload

    def overview(self, *, month: str, months: int = 6, basis: str = "cash") -> dict:
        start, end = parse_month(month)
        next_month = shift_month(month, 1)
        current_start, current_end = parse_month(month_key(self.now))
        mrr = self._mrr()
        forward = self._paid_forward()
        forecast = self._forecast_month(next_month, "cash")
        renewals = self._renewals_due(next_month)
        cash_month = self._monthly_transaction_stats(start, end)
        accrual_month, accrual_month_unknown = self._accrual(start, end)
        accrual_current, accrual_current_unknown = self._accrual(current_start, current_end)
        current_cash = self._monthly_transaction_stats(current_start, current_end)

        rows, _totals = self._market(month)
        by_tariff = [
            {
                "tariff_id": row["tariff_id"],
                "tariff_name": row["tariff_name"],
                "clients_paid": row["clients_paid"],
                "clients_trial": row["clients_trial"],
                "share_pct": row["share_pct"],
                "monthly_price_kopeks": row["monthly_price_kopeks"],
                "price_source": row["price_source"],
                "price_kind": row["price_kind"],
                "mrr_kopeks": row["mrr_kopeks"],
                "paid_forward_kopeks": row["paid_forward_kopeks"],
                "next_month_expected_kopeks": row["next_month_expected_kopeks"],
                "unknown_price_clients": row["unknown_price_clients"],
                "is_free": row["is_free"],
            }
            for row in rows
        ]

        monthly: list[dict] = []
        for offset in range(months - 1, -1, -1):
            key = shift_month(month, -offset)
            m_start, m_end = parse_month(key)
            stats = self._monthly_transaction_stats(m_start, m_end)
            accrual_value, _unknown = self._accrual(m_start, m_end)
            is_past = m_end <= current_start
            monthly.append(
                {
                    "month": key,
                    **stats,
                    "accrual_revenue_kopeks": None if is_past else accrual_value,
                    "accrual_is_estimate": True,
                }
            )

        warnings: list[dict] = list(self._base_warnings())
        unknown_warning = self._price_unknown_warning()
        if unknown_warning:
            warnings.append(unknown_warning)
        multi = self._multi_subscription_warning()
        if multi:
            warnings.append(multi)
        if forecast["totals"]["unknown_count"]:
            warnings.append(
                _warn(
                    "price_unknown",
                    "Для части подписок цена периода не определена",
                    unknown_count=forecast["totals"]["unknown_count"],
                )
            )

        autopay_count = sum(1 for _user, sub in self._paid_subs if sub.get("autopay_enabled"))
        coverage = self._coverage()
        payload = {
            "month": month,
            "next_month": next_month,
            "basis": basis,
            "coverage": coverage,
            "kpis": {
                "mrr_kopeks": mrr["kopeks"],
                "mrr_rubles": _rubles(mrr["kopeks"]),
                "mrr_basis": mrr["basis"],
                "mrr_is_lower_bound": mrr["is_lower_bound"],
                "mrr_unknown_subscriptions": mrr["unknown"],
                "cash_forecast_next_month_kopeks": forecast["totals"]["expected_kopeks"],
                "cash_forecast_unknown_count": forecast["totals"]["unknown_count"],
                "renewals_due_next_month_kopeks": renewals["kopeks"],
                "renewals_due_next_month_count": renewals["count"],
                "paid_forward_kopeks": forward["kopeks"],
                "accrual_revenue_current_month_kopeks": accrual_current,
                "accrual_unknown_subscriptions": accrual_current_unknown,
                "accrual_revenue_month_kopeks": accrual_month,
                "accrual_month_unknown_subscriptions": accrual_month_unknown,
                "cash_received_current_month_kopeks": current_cash["cash_received_kopeks"],
                "cash_received_month_kopeks": cash_month["cash_received_kopeks"],
                "payments_current_month": current_cash["payments_count"],
                "active_paid_clients": coverage["clients_with_paid"],
                "active_paid_subscriptions": len(self._paid_subs),
                "autopay_enabled_subscriptions": autopay_count,
            },
            "by_tariff": by_tariff,
            "monthly": monthly,
        }
        payload.update(self._meta(warnings))
        return payload

    def forecast(self, *, month: str, basis: str = "cash") -> dict:
        data = self._forecast_month(month, basis)
        warnings: list[dict] = list(self._base_warnings()) + data.pop("warnings")
        unknown_warning = self._price_unknown_warning()
        if unknown_warning:
            warnings.append(unknown_warning)
        data.update(self._meta(warnings))
        return data

    def customer(self, user_id: int, *, days_back: int = 3650) -> Optional[dict]:
        target: Optional[dict] = None
        for user in self.users:
            if _to_int(user.get("id")) == user_id:
                target = user
                break
        if target is None:
            return None

        user_txs = [tx for tx in self.transactions if _to_int(tx.get("user_id")) == user_id]
        primary = primary_subscription(target, self.now)
        tariff = tariff_of(primary) if primary is not None else None
        quote: Optional[PriceQuote] = None
        period_price: Optional[int] = None
        if primary is not None and tariff is not None:
            days = period_days(primary)
            quote = self.catalog.quote(tariff["tariff_id"], tariff["tariff_name"], days)
            period_price, quote = self._sub_period_price(primary)

        paid_total, paid_last_12m, paid_current = self._user_paid(user_txs)
        forward: Optional[int] = None
        next_date = None
        charge_date = None
        next_amount: Optional[int] = None
        if primary is not None and not is_trial_sub(primary):
            next_date = date_str(primary.get("end_date"))
            charge_date = expected_charge_date(primary).date().isoformat()
            if period_price is not None:
                days = period_days(primary)
                forward = int(round(remaining_days(primary, self.now) * period_price / days))
                next_amount = period_price

        subscriptions = []
        for sub in user_subscriptions(target):
            sub_tariff = tariff_of(sub)
            subscriptions.append(
                {
                    "id": _to_int(sub.get("id")),
                    "tariff_id": sub_tariff["tariff_id"],
                    "tariff_name": sub_tariff["tariff_name"],
                    "end_date": iso(sub.get("end_date")),
                    "is_trial": is_trial_sub(sub),
                    "status": sub.get("status"),
                    "actual_status": sub.get("actual_status"),
                }
            )
        subscriptions.sort(key=lambda row: row["end_date"] or "", reverse=True)

        payments = sorted(
            (
                {
                    "id": _to_int(tx.get("id")),
                    "created_at": iso(tx.get("created_at")),
                    "amount_kopeks": _to_int(tx.get("amount_kopeks")),
                    "description": tx.get("description"),
                    "type": tx.get("type"),
                }
                for tx in user_txs
                if str(tx.get("type") or "") in ("subscription_payment", "refund")
            ),
            key=lambda row: row["created_at"] or "",
            reverse=True,
        )[:50]

        warnings: list[dict] = list(self._base_warnings())
        if quote is not None and not quote.price_known:
            warnings.append(
                _warn("price_unknown", "Цена тарифа клиента не определена", tariff_ids=[quote.tariff_id] if quote.tariff_id else [])
            )
        multi = [sub for sub in user_subscriptions(target) if is_paid_active(sub, self.now)]
        if len(multi) > 1:
            warnings.append(
                _warn("multi_subscription_clients", "У клиента несколько активных платных подписок", count=len(multi))
            )

        payload = {
            "user": {
                "id": _to_int(target.get("id")),
                "username": target.get("username"),
                "telegram_id": _to_int(target.get("telegram_id")),
                "first_name": target.get("first_name"),
            },
            "primary_subscription": None if primary is None else {
                "id": _to_int(primary.get("id")),
                "status": primary.get("status"),
                "actual_status": primary.get("actual_status"),
                "is_trial": is_trial_sub(primary),
                "tariff_id": tariff["tariff_id"] if tariff else None,
                "tariff_name": tariff["tariff_name"] if tariff else UNKNOWN_TARIFF_NAME,
                "start_date": iso(primary.get("start_date")),
                "end_date": iso(primary.get("end_date")),
                "days_left": remaining_days(primary, self.now),
                "autopay_enabled": bool(primary.get("autopay_enabled")),
                "autopay_days_before": _to_int(primary.get("autopay_days_before")),
                "autopay_period_days": _to_int(primary.get("autopay_period_days")),
                "period_days": period_days(primary),
            },
            "tariff": None if quote is None else quote.to_dict(prefer="period"),
            "money": {
                "paid_total_kopeks": paid_total,
                "paid_last_12m_kopeks": paid_last_12m,
                "paid_current_month_kopeks": paid_current,
                "paid_forward_kopeks": forward if primary is not None and period_price is not None else None,
                "next_payment_date": next_date,
                "expected_charge_date": charge_date,
                "next_payment_kopeks": next_amount,
                "next_payment_known": next_amount is not None,
            },
            "subscriptions": subscriptions,
            "payments": payments,
        }
        payload.update(self._meta(warnings))
        return payload

    def _user_paid(self, transactions: Iterable[dict]) -> tuple[int, int, int]:
        total = 0
        last_12m = 0
        current_month = 0
        cutoff = self.now - timedelta(days=365)
        m_start, m_end = parse_month(month_key(self.now))
        for tx in transactions:
            if tx.get("is_completed") is False:
                continue
            tx_type = str(tx.get("type") or "")
            if tx_type not in ("subscription_payment", "refund"):
                continue
            amount = abs(_to_int(tx.get("amount_kopeks")) or 0)
            if tx_type == "refund":
                amount = -amount
            total += amount
            created = parse_ts(tx.get("created_at"))
            if created is None:
                continue
            if created >= cutoff:
                last_12m += amount
            if m_start <= created < m_end:
                current_month += amount
        return total, last_12m, current_month


