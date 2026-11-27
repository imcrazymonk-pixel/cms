"""Unit tests for `core/bedolaga_analytics.py`.

Covers normalization, description parsing, price catalog priority/quality,
subscription selection, formulas F1-F15 and the paginated data collectors with
partial-page behaviour. No network or FastAPI is involved.
"""
import asyncio
from datetime import timedelta

import pytest

from web.backend.core import bedolaga_analytics as core
from web.backend.core import bot_db

NOW = core.parse_ts("2026-11-20T12:00:00+03:00")


def sub(
    sub_id: int,
    *,
    tariff_id=2,
    tariff_name="Optimal",
    days=30,
    end_days=10,
    status="active",
    actual_status=None,
    is_trial=False,
    start_days=-20,
    autopay=False,
    autopay_days_before=0,
):
    return {
        "id": sub_id,
        "status": status,
        "actual_status": actual_status or status,
        "is_trial": is_trial,
        "tariff_id": tariff_id,
        "tariff_name": tariff_name,
        "start_date": (NOW + timedelta(days=start_days)).isoformat(),
        "end_date": (NOW + timedelta(days=end_days)).isoformat(),
        "autopay_enabled": autopay,
        "autopay_days_before": autopay_days_before,
        "autopay_period_days": days,
    }


def user(user_id: int, subs=None, single=None, **extra):
    data = {"id": user_id, "username": f"user{user_id}", **extra}
    if subs is not None:
        data["subscriptions"] = subs
    if single is not None:
        data["subscription"] = single
    return data


def payment(user_id: int, price: int, description: str, created_at=None, **extra):
    return {
        "id": extra.pop("id", abs(price)),
        "user_id": user_id,
        "type": extra.pop("type", "subscription_payment"),
        "amount_kopeks": -price,
        "description": description,
        "created_at": (created_at or NOW - timedelta(days=1)).isoformat(),
        "is_completed": True,
        **extra,
    }


def bot_tariff(tariff_id, name, periods, *, is_active=True, **extra):
    return {
        "id": tariff_id,
        "name": name,
        "is_active": is_active,
        "period_prices": {str(days): price for days, price in periods.items()},
        **extra,
    }


def make_raw(
    users,
    transactions=None,
    tariffs=None,
    *,
    users_total=None,
    tx_total=None,
    users_partial=False,
    tx_partial=False,
    bot_status="ok",
):
    transactions = transactions or []
    return core.RawData(
        users=core.PageResult(
            items=list(users),
            total=users_total if users_total is not None else len(users),
            pages_loaded=1,
            partial=users_partial,
        ),
        transactions=core.PageResult(
            items=list(transactions),
            total=tx_total if tx_total is not None else len(transactions),
            pages_loaded=1,
            partial=tx_partial,
        ),
        bot_db={"status": bot_status, "tariffs": list(tariffs or []), "checked_at": NOW.isoformat()},
        full_stats=None,
        fetched_at=NOW,
    )


def engine(raw, days_back=365):
    return core.AnalyticsEngine(raw, now=NOW, price_days_back=days_back)


# ── Names and descriptions ────────────────────────────────────────────────


def test_normalize_name_strips_emoji_and_spaces():
    assert core.normalize_name("  👤  Optimal  ") == "optimal"
    assert core.normalize_name("ЁЖИК ✨") == "ежик"
    assert core.normalize_name(None) == ""


def test_parse_purchase_description():
    parsed = core.parse_payment_description("Покупка тарифа 👤 Optimal на 30 дней")
    assert parsed == {"name": "👤 Optimal", "days": 30, "kind": "purchase"}


def test_parse_renewal_description_with_name():
    parsed = core.parse_payment_description("Продление подписки на 90 дней (Optimal)")
    assert parsed["name"] == "Optimal"
    assert parsed["days"] == 90
    assert parsed["kind"] == "renewal"


def test_parse_autorenewal_falls_back_to_user_tariff():
    parsed = core.parse_payment_description("Автопродление подписки на 30 дней")
    assert parsed["name"] is None
    assert parsed["days"] == 30
    assert parsed["kind"] == "autorenewal"

    with_fallback = core.parse_payment_description(
        "Автопродление подписки на 30 дней", fallback_tariff_name="Optimal"
    )
    assert with_fallback["name"] == "Optimal"


# ── Price catalog ─────────────────────────────────────────────────────────


def test_transaction_median_and_confidence_high():
    prices = [10000, 11000, 15000, 15000, 15000]
    users = [user(1, single=sub(10, tariff_id=None, tariff_name="Base"))]
    transactions = [
        payment(1, price, "Покупка тарифа Base на 30 дней", NOW - timedelta(days=i + 1))
        for i, price in enumerate(prices)
    ]
    data = engine(make_raw(users, transactions)).tariffs()
    row = next(item for item in data["items"] if item["tariff_name"] == "Base")
    assert row["monthly_price_kopeks"] == 15000
    assert row["price_source"] == "transactions"
    assert row["price_kind"] == "realized"
    assert row["confidence"] == "high"
    assert row["price_basis"] == "30_day"


def test_ambiguous_tariff_names_apply_price_to_all_and_warn():
    users = [user(1, single=sub(10, tariff_id=1, tariff_name="Same"))]
    tariffs = [bot_tariff(1, "Same", {}), bot_tariff(2, "Same", {})]
    transactions = [payment(1, 12000, "Покупка тарифа Same на 30 дней")]
    data = engine(make_raw(users, transactions, tariffs)).tariffs()
    rows = [item for item in data["items"] if item["tariff_id"] in (1, 2)]
    assert len(rows) == 2
    assert all(row["monthly_price_kopeks"] == 12000 for row in rows)
    assert any(w["code"] == "ambiguous_tariff_name" for w in data["warnings"])


def test_bot_db_price_wins_over_transactions():
    users = [user(1, single=sub(10))]
    tariffs = [bot_tariff(2, "Optimal", {30: 15000})]
    transactions = [payment(1, 5000, "Покупка тарифа Optimal на 30 дней")]
    row = next(item for item in engine(make_raw(users, transactions, tariffs)).tariffs()["items"] if item["tariff_id"] == 2)
    assert row["monthly_price_kopeks"] == 15000
    assert row["price_source"] == "bot_db"
    assert row["price_kind"] == "list"
    assert any(w["code"] == "price_sources_disagree" for w in engine(make_raw(users, transactions, tariffs)).tariffs()["warnings"])


def test_zero_price_is_valid_and_inactive_tariff_included():
    users = [user(1, single=sub(10, tariff_id=7, tariff_name="Free"))]
    tariffs = [bot_tariff(7, "Free", {30: 0}, is_active=False)]
    data = engine(make_raw(users, [], tariffs)).tariffs()
    row = next(item for item in data["items"] if item["tariff_id"] == 7)
    assert row["is_active"] is False
    assert row["is_free"] is True
    assert row["price_known"] is True
    assert row["monthly_price_kopeks"] == 0
    assert data["coverage"]["price_unknown_subscriptions"] == 0


def test_unknown_price_is_not_zero():
    users = [user(1, single=sub(10, tariff_id=99, tariff_name="Mystery"))]
    data = engine(make_raw(users, [], [])).tariffs()
    row = next(item for item in data["items"] if item["tariff_id"] == 99)
    assert row["price_known"] is False
    assert row["monthly_price_kopeks"] is None
    assert row["price_source"] == "unknown"
    assert any(w["code"] == "price_unknown" for w in data["warnings"])


def test_zero_amount_transactions_do_not_zero_arbitrary_period_price():
    users = [user(1, single=sub(10, days=41, end_days=41))]
    tariffs = [bot_tariff(2, "Optimal", {30: 15000})]
    transactions = [
        # Admin tariff change / mass action is recorded with zero amount and
        # must not drag the realized price down to zero.
        payment(1, 0, "Продление подписки на 41 дней (Optimal)"),
        payment(1, 15000, "Автопродление подписки на 30 дней", NOW - timedelta(days=20)),
        payment(1, 15000, "Автопродление подписки на 30 дней", NOW - timedelta(days=50)),
    ]
    eng = engine(make_raw(users, transactions, tariffs))
    quote = eng.catalog.quote(2, "Optimal", 41)
    assert quote.period is not None
    assert quote.period.kopeks == 20500
    assert quote.period.kopeks != 0
    assert quote.price_known is True
    assert quote.is_free is False
    assert quote.monthly is not None and quote.monthly.kopeks == 15000

    data = eng.forecast(month="2026-12")
    assert data["totals"]["expected_kopeks"] == 20500
    item = data["items"][0]
    assert item["period_price_kopeks"] == 20500
    assert item["price_known"] is True


def test_arbitrary_period_falls_back_to_monthly_proportional():
    users = [user(1, single=sub(10, days=41, end_days=41))]
    tariffs = [bot_tariff(2, "Optimal", {30: 15000})]
    eng = engine(make_raw(users, [], tariffs))
    quote = eng.catalog.quote(2, "Optimal", 41)
    assert quote.period is not None
    assert quote.period.kopeks == 20500
    assert quote.period.basis == "proportional"
    assert quote.price_known is True
    assert eng.forecast(month="2026-12")["totals"]["expected_kopeks"] == 20500


def test_free_tariff_with_zero_observations_stays_known_zero():
    users = [user(1, single=sub(10, tariff_id=7, tariff_name="Free", days=41, end_days=41))]
    tariffs = [bot_tariff(7, "Free", {30: 0})]
    transactions = [payment(1, 0, "Продление подписки на 41 дней (Free)")]
    eng = engine(make_raw(users, transactions, tariffs))
    quote = eng.catalog.quote(7, "Free", 41)
    assert quote.period is not None
    assert quote.period.kopeks == 0
    assert quote.price_known is True
    assert quote.is_free is True
    data = eng.forecast(month="2026-12")
    assert data["totals"]["expected_kopeks"] == 0
    assert data["items"][0]["price_known"] is True
    assert data["items"][0]["period_price_kopeks"] == 0


def test_unknown_price_without_bot_db_or_positive_observations():
    users = [user(1, single=sub(10, tariff_id=99, tariff_name="Mystery", days=41, end_days=41))]
    transactions = [payment(1, 0, "Продление подписки на 41 дней (Mystery)")]
    eng = engine(make_raw(users, transactions, []))
    quote = eng.catalog.quote(99, "Mystery", 41)
    assert quote.period is None
    assert quote.monthly is None
    assert quote.price_known is False
    data = eng.forecast(month="2026-12")
    assert data["items"][0]["price_known"] is False
    assert data["items"][0]["period_price_kopeks"] is None
    assert data["totals"]["unknown_count"] == 1



# ── Subscription selection and distribution ───────────────────────────────


def test_primary_subscription_prefers_latest_end_and_counts_user_once():
    subs = [
        sub(10, tariff_id=1, tariff_name="Old", end_days=5),
        sub(11, tariff_id=2, tariff_name="Optimal", end_days=40),
    ]
    users = [user(1, subs=subs)]
    data = engine(make_raw(users, [], [bot_tariff(1, "Old", {30: 1000}), bot_tariff(2, "Optimal", {30: 15000})])).tariffs()
    assert data["totals"]["clients_paid"] == 1
    assert data["coverage"]["active_paid_subscriptions"] == 2
    row = next(item for item in data["items"] if item["tariff_id"] == 2)
    assert row["clients_paid"] == 1
    assert any(w["code"] == "multi_subscription_clients" for w in data["warnings"])


def test_actual_status_has_priority_over_status():
    expired_actual = sub(10, status="active", actual_status="expired", end_days=30)
    assert core.is_paid_active(expired_actual, NOW) is False
    revived = sub(11, status="expired", actual_status="active", end_days=30)
    assert core.is_paid_active(revived, NOW) is True


def test_limited_subscription_is_paid_active():
    sub_data = sub(10, status="limited", end_days=30)
    assert core.is_paid_active(sub_data, NOW) is True


def test_trial_and_missing_tariff_are_counted_separately():
    users = [
        user(1, single=sub(10, status="trial", is_trial=True, tariff_id=5, tariff_name="Trial")),
        user(2, single=sub(11, tariff_id=None, tariff_name=None)),
        user(3),
    ]
    data = engine(make_raw(users, [], [bot_tariff(5, "Trial", {30: 100})])).tariffs()
    assert data["totals"]["clients_trial"] == 1
    assert data["totals"]["clients_paid"] == 1
    assert data["totals"]["clients_without_subscription"] == 1
    unknown = next(item for item in data["items"] if item["tariff_id"] is None)
    assert unknown["clients_paid"] == 1
    assert unknown["price_known"] is False


# ── Money formulas ────────────────────────────────────────────────────────


def test_mrr_known_unknown_and_free():
    users = [
        user(1, single=sub(10, tariff_id=1, tariff_name="Paid")),
        user(2, single=sub(11, tariff_id=2, tariff_name="Free")),
        user(3, single=sub(12, tariff_id=3, tariff_name="Mystery")),
    ]
    tariffs = [bot_tariff(1, "Paid", {30: 15000}), bot_tariff(2, "Free", {30: 0})]
    data = engine(make_raw(users, [], tariffs)).tariffs()
    totals = data["totals"]
    assert totals["mrr_kopeks"] == 15000
    assert totals["mrr_unknown_subscriptions"] == 1
    assert totals["mrr_is_lower_bound"] is True
    assert totals["mrr_basis"] == "list"
    assert data["coverage"]["price_coverage_pct"] == 66.7


def test_forecast_uses_charge_date_and_msk_month_boundary():
    users = [
        user(1, single=sub(10, end_days=11, autopay=False)),
        user(2, single=sub(11, tariff_id=3, tariff_name="Late", end_days=10, autopay=False)),
    ]
    users[0]["subscription"]["end_date"] = "2026-12-01T00:30:00+03:00"
    users[1]["subscription"]["end_date"] = "2026-11-30T23:30:00+03:00"
    tariffs = [bot_tariff(2, "Optimal", {30: 15000}), bot_tariff(3, "Late", {30: 7000})]
    data = engine(make_raw(users, [], tariffs)).forecast(month="2026-12")
    assert data["totals"]["expected_kopeks"] == 15000
    assert data["totals"]["payments_count"] == 1
    assert data["by_day"][0]["date"] == "2026-12-01"


def test_forecast_autopay_charge_date_moves_to_previous_month():
    users = [user(1, single=sub(10, end_days=11, autopay=True, autopay_days_before=3))]
    tariffs = [bot_tariff(2, "Optimal", {30: 15000})]
    cash = engine(make_raw(users, [], tariffs)).forecast(month="2026-12", basis="cash")
    renewal = engine(make_raw(users, [], tariffs)).forecast(month="2026-12", basis="renewal")
    assert cash["totals"]["expected_kopeks"] == 0
    assert cash["totals"]["autopay_enabled_count"] == 0
    assert renewal["totals"]["expected_kopeks"] == 15000


def test_accrual_prorates_within_month_boundaries():
    months = [
        user(
            1,
            single=sub(
                10,
                tariff_id=1,
                tariff_name="TwoDays",
                start_days=0,
                end_days=2,
                days=2,
            ),
        )
    ]
    months[0]["subscription"]["start_date"] = "2026-11-30T12:00:00+03:00"
    months[0]["subscription"]["end_date"] = "2026-12-02T12:00:00+03:00"
    eng = engine(make_raw(months, [], [bot_tariff(1, "TwoDays", {2: 20000})]))
    start, end = core.parse_month("2026-11")
    nov_total, _ = eng._accrual(start, end)
    start, end = core.parse_month("2026-12")
    dec_total, _ = eng._accrual(start, end)
    assert nov_total == 10000
    assert dec_total == 20000


def test_paid_forward_uses_period_price_not_monthly():
    users = [
        user(1, single=sub(10, tariff_id=1, tariff_name="Month", end_days=15, days=30)),
        user(2, single=sub(11, tariff_id=2, tariff_name="Quarter", end_days=45, days=90)),
    ]
    tariffs = [bot_tariff(1, "Month", {30: 30000}), bot_tariff(2, "Quarter", {90: 90000})]
    forward = engine(make_raw(users, [], tariffs))._paid_forward()
    assert forward["kopeks"] == 60000
    assert forward["unknown"] == 0


def test_paid_total_excludes_gift_and_withdrawal_and_subtracts_refund():
    transactions = [
        payment(1, 15000, "Покупка тарифа Optimal на 30 дней"),
        payment(1, 5000, "Продление подписки на 30 дней (Optimal)"),
        {"id": 3, "user_id": 1, "type": "refund", "amount_kopeks": -2000, "created_at": NOW.isoformat()},
        {"id": 4, "user_id": 1, "type": "gift_payment", "amount_kopeks": -7000, "created_at": NOW.isoformat()},
        {"id": 5, "user_id": 1, "type": "withdrawal", "amount_kopeks": -3000, "created_at": NOW.isoformat()},
        {"id": 6, "user_id": 1, "type": "subscription_payment", "amount_kopeks": -9000, "created_at": NOW.isoformat(), "is_completed": False},
    ]
    eng = engine(make_raw([user(1, single=sub(10))], transactions, [bot_tariff(2, "Optimal", {30: 15000})]))
    total, last_12m, current = eng._user_paid(transactions)
    assert total == 18000
    assert last_12m == 18000
    assert current == 18000


def test_customer_profile_money_and_tariff():
    users = [user(1, single=sub(10, tariff_id=2, end_days=12, autopay=True, autopay_days_before=3))]
    transactions = [payment(1, 15000, "Покупка тарифа Optimal на 30 дней")]
    data = engine(make_raw(users, transactions, [bot_tariff(2, "Optimal", {30: 15000})])).customer(1)
    assert data["tariff"]["price_basis"] == "exact_period"
    assert data["money"]["paid_total_kopeks"] == 15000
    assert data["money"]["next_payment_kopeks"] == 15000
    assert data["money"]["next_payment_known"] is True
    assert data["primary_subscription"]["days_left"] == 12
    assert data["tariff"]["monthly_price_kopeks"] == 15000


# ── Partial data and collectors ───────────────────────────────────────────


def test_partial_data_marks_response_and_adds_warnings():
    users = [user(1, single=sub(10))]
    raw = make_raw(users, [], [bot_tariff(2, "Optimal", {30: 15000})], users_partial=True, tx_partial=True)
    data = engine(raw).tariffs()
    assert data["partial"] is True
    codes = {w["code"] for w in data["warnings"]}
    assert "users_partial" in codes
    assert "transactions_unavailable" in codes


@pytest.mark.asyncio
async def test_fetch_all_users_paginates_277():
    class Fake:
        async def list_users(self, limit=200, offset=0, **filters):
            total = 277
            start = min(offset, total)
            end = min(start + limit, total)
            return {"items": [{"id": i} for i in range(start, end)], "total": total}

    result = await core.fetch_all_users(Fake())
    assert result.total == 277
    assert len(result.items) == 277
    assert result.pages_loaded == 2
    assert result.partial is False


@pytest.mark.asyncio
async def test_fetch_all_transactions_partial_page():
    class Fake:
        async def list_transactions(self, limit=100, offset=0, **filters):
            total = 300
            if offset == 100:
                raise RuntimeError("page failed")
            start = min(offset, total)
            end = min(start + limit, total)
            return {"items": [{"id": i} for i in range(start, end)], "total": total}

    result = await core.fetch_all_transactions(Fake())
    assert result.total == 300
    assert len(result.items) == 200
    assert result.partial is True
    assert result.pages_loaded == 2


@pytest.mark.asyncio
async def test_snapshot_single_flight(monkeypatch):
    core.invalidate_snapshot_cache()
    calls = 0

    async def fake_load(days_back):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return make_raw([user(1, single=sub(10))])

    monkeypatch.setattr(core, "_load_raw_data", fake_load)
    first, second = await asyncio.gather(
        core.load_raw_data(days_back=123, refresh=True),
        core.load_raw_data(days_back=123, refresh=True),
    )
    assert calls == 1
    assert first is second
    core.invalidate_snapshot_cache()


@pytest.mark.asyncio
async def test_bot_db_error_is_distinguished_and_cached(monkeypatch):
    async def no_config():
        return False

    monkeypatch.setattr(bot_db, "ensure_config", no_config)
    monkeypatch.setattr(bot_db, "_config", None)
    monkeypatch.setattr(bot_db, "_get_engine", lambda: object())
    bot_db.clear_cache()
    monkeypatch.setattr(bot_db, "_circuit_until", 0.0)

    async def boom(engine):
        raise RuntimeError("db down")

    monkeypatch.setattr(bot_db, "_read_tariffs", boom)
    first = await bot_db.get_tariffs_result()
    second = await bot_db.get_tariffs_result()
    assert first["status"] == "error"
    assert first["tariffs"] == []
    assert second["status"] == "error"
    assert second["cached"] is True
    assert await bot_db.get_tariffs() == []
    bot_db.clear_cache()
    monkeypatch.setattr(bot_db, "_circuit_until", 0.0)
