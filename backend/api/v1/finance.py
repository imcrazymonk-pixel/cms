"""Finance API — core endpoints migrated from PHP AdminFinanceController.

Covers (React Finance page usage):
  GET  /data, POST /add, /edit, /delete, /delete-bulk
  POST /bulk/{type,category,participant,description}
  POST /export/selected, GET /export/csv, POST /import
  GET+POST /settings

Platega/YooKassa sync/preview endpoints are NOT migrated here (kept on PHP via nginx).
Mount prefix: /admin/finance/api
"""
import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.crypto import decrypt, encrypt
from backend.core.database import get_db
from backend.core.errors import E, api_error
from backend.core.request_utils import json_body

router = APIRouter()

_SORT_COLS = {"date", "amount", "category", "participant", "type"}
_JSON_ARRAY_KEYS = {
    "avg_exclude_categories", "avg_exclude_income_keywords", "avg_exclude_expense_keywords",
    "quick_categories", "quick_participants",
}
_SECRET_KEYS = {"platega_secret", "yookassa_secret_key"}
_SETTINGS_ALLOWED = [
    "currency", "decimals", "auto_refresh", "avg_period",
    "avg_exclude_categories", "avg_exclude_income_keywords", "avg_exclude_expense_keywords",
    "quick_categories", "quick_participants",
    "platega_merchant_id", "platega_secret", "platega_days_back", "platega_auto_sync",
    "yookassa_shop_id", "yookassa_secret_key", "yookassa_days_back", "yookassa_auto_sync",
]


# ── helpers ───────────────────────────────────────────────────────────

def _as_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _dstr(v: Any) -> str:
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _build_filters(f: Dict[str, str]) -> Tuple[str, Dict[str, Any]]:
    where: List[str] = []
    params: Dict[str, Any] = {}
    if f.get("month") and len(f["month"]) == 7 and f["month"][4] == "-":
        where.append("TO_CHAR(\"date\", 'YYYY-MM') = :month")
        params["month"] = f["month"]
    if f.get("since"):
        where.append("date >= :since")
        params["since"] = f["since"]
    if f.get("until"):
        where.append("date <= :until")
        params["until"] = f["until"]
    if f.get("type") in ("income", "expense"):
        where.append("type = :ftype")
        params["ftype"] = f["type"]
    if f.get("category"):
        where.append("category = :fcategory")
        params["fcategory"] = f["category"]
    if f.get("participant"):
        where.append("participant = :fparticipant")
        params["fparticipant"] = f["participant"]
    if f.get("q"):
        where.append("(category LIKE :fq OR participant LIKE :fq OR description LIKE :fq)")
        params["fq"] = f"%{f['q']}%"
    return ((" WHERE " + " AND ".join(where)) if where else ""), params


def _parse_filters(request: Request) -> Dict[str, str]:
    qp = request.query_params
    return {
        "month": qp.get("month", "") or "",
        "since": qp.get("since", "") or "",
        "until": qp.get("until", "") or "",
        "type": qp.get("type", "") or "",
        "category": qp.get("category", "") or "",
        "participant": qp.get("participant", "") or "",
        "q": qp.get("q", "") or "",
    }


def _keywords_from(raw: Any) -> List[str]:
    import json
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for kw in data:
        s = str(kw).strip().lower()
        if s:
            out.append(s)
    return out


def _is_excluded(row: Dict[str, Any], keywords: List[str]) -> bool:
    if not keywords:
        return False
    vals = [str(row.get("category") or "").lower(),
            str(row.get("participant") or "").lower(),
            str(row.get("description") or "").lower()]
    for kw in keywords:
        for v in vals:
            if v and kw in v:
                return True
    return False


async def _fin_settings(db: AsyncSession) -> Dict[str, str]:
    rows = (await db.execute(text("SELECT setting_key, setting_value FROM fin_settings"))).fetchall()
    return {r.setting_key: r.setting_value for r in rows}


async def _upsert_fin_setting(db: AsyncSession, key: str, value: str) -> None:
    await db.execute(
        text("INSERT INTO fin_settings (setting_key, setting_value) VALUES (:k, :v) "
             "ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value"),
        {"k": key, "v": value},
    )


def _group(rows: List[dict], scale: str) -> List[dict]:
    buckets: Dict[str, Dict[str, float]] = {}
    labels: Dict[str, str] = {}
    for r in rows:
        d = r["date"]
        if scale == "month":
            key = d[:7]
            label = d[5:7] + "." + d[0:4]
        elif scale == "year":
            key = d[:4]
            label = key
        elif scale == "week":
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            iso = dt.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            monday = dt - timedelta(days=dt.isoweekday() - 1)
            label = monday.strftime("%d.%m") + " w" + key.split("W")[1]
        else:  # day
            key = d
            label = datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.%Y")
        b = buckets.setdefault(key, {"income": 0.0, "expense": 0.0})
        labels[key] = label
        b["income" if r["type"] == "income" else "expense"] += r["amount"]
    out = []
    for key in sorted(buckets.keys()):
        v = buckets[key]
        out.append({"key": key, "label": labels[key],
                    "income": round(v["income"], 2), "expense": round(v["expense"], 2)})
    return out


def _attach_balances(daily, monthly, weekly, yearly):
    cum = 0.0
    cum_by_date: Dict[str, float] = {}
    for d in daily:
        cum += d["income"] - d["expense"]
        d["balance"] = round(cum, 2)
        cum_by_date[d["key"]] = round(cum, 2)

    def end_bal(scale):
        out = {}
        for dstr, bal in cum_by_date.items():
            if scale == "month":
                out[dstr[:7]] = bal
            elif scale == "year":
                out[dstr[:4]] = bal
            elif scale == "week":
                dt = datetime.strptime(dstr, "%Y-%m-%d").date().isocalendar()
                out[f"{dt[0]}-W{dt[1]:02d}"] = bal
            else:
                out[dstr] = bal
        return out

    for items, scale in ((monthly, "month"), (weekly, "week"), (yearly, "year")):
        eb = end_bal(scale)
        for it in items:
            it["balance"] = eb.get(it["key"])


def _format_row(r) -> dict:
    d = _dstr(r.date)
    return {
        "id": int(r.id),
        "date": d,
        "date_display": datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.%Y"),
        "month": d[:7],
        "type": r.type,
        "participant": r.participant or "",
        "category": r.category,
        "amount": _as_float(r.amount),
        "description": r.description or "",
    }


async def _summary(db: AsyncSession) -> dict:
    settings = await _fin_settings(db)
    gen_excl = _keywords_from(settings.get("avg_exclude_categories", "[]"))
    rows = (await db.execute(text(
        "SELECT type, category, participant, description, amount FROM fin_transactions"))).fetchall()
    income = expense = 0.0
    count = 0
    for r in rows:
        row = {"category": r.category, "participant": r.participant, "description": r.description}
        if _is_excluded(row, gen_excl):
            continue
        count += 1
        if r.type == "income":
            income += _as_float(r.amount)
        else:
            expense += _as_float(r.amount)
    income, expense = round(income, 2), round(expense, 2)
    return {"income": income, "expense": expense, "balance": round(income - expense, 2), "count": count}


async def _averages(db: AsyncSession) -> dict:
    settings = await _fin_settings(db)
    gen_excl = _keywords_from(settings.get("avg_exclude_categories", "[]"))
    inc_excl = _keywords_from(settings.get("avg_exclude_income_keywords", "[]"))
    exp_excl = _keywords_from(settings.get("avg_exclude_expense_keywords", "[]"))

    rows = (await db.execute(text(
        "SELECT date, type, category, participant, description, amount FROM fin_transactions"))).fetchall()

    income = expense = avg_income = avg_expense = 0.0
    dates = set()
    for r in rows:
        row = {"category": r.category, "participant": r.participant, "description": r.description}
        ds = _dstr(r.date)
        dates.add(ds)
        is_income = r.type == "income"
        if not _is_excluded(row, gen_excl):
            if is_income:
                income += _as_float(r.amount)
            else:
                expense += _as_float(r.amount)
        if is_income:
            if not _is_excluded(row, gen_excl) and not _is_excluded(row, inc_excl):
                avg_income += _as_float(r.amount)
        else:
            if not _is_excluded(row, gen_excl) and not _is_excluded(row, exp_excl):
                avg_expense += _as_float(r.amount)

    date_list = sorted(dates)
    n = len(date_list)
    days = 0
    if n > 1:
        days = (datetime.strptime(date_list[-1], "%Y-%m-%d").date()
                - datetime.strptime(date_list[0], "%Y-%m-%d").date()).days + 1
    elif n == 1:
        days = 1
    weeks = max(1, -(-days // 7)) if days else 1
    months = len({d[:7] for d in date_list}) or 1
    years = len({d[:4] for d in date_list}) or 1

    def avg(x):
        return {
            "day": round(x / days, 2) if days else 0,
            "week": round(x / weeks, 2) if weeks else 0,
            "month": round(x / months, 2) if months else 0,
            "year": round(x / years, 2) if years else 0,
        }

    return {
        "income": round(income, 2), "expense": round(expense, 2),
        "balance": round(income - expense, 2), "total": len(rows),
        "avg_days": days, "avg_weeks": weeks, "avg_months": months, "avg_years": years,
        "avg_income": avg(avg_income), "avg_expense": avg(avg_expense),
    }


async def _chart(db: AsyncSession, filters: dict) -> dict:
    where, params = _build_filters(filters)
    rows = (await db.execute(text(
        "SELECT date, type, amount FROM fin_transactions" + where + " ORDER BY date ASC"), params)).fetchall()
    rr = [{"date": _dstr(r.date), "type": r.type, "amount": _as_float(r.amount)} for r in rows]
    daily = _group(rr, "day")
    monthly = _group(rr, "month")
    weekly = _group(rr, "week")
    yearly = _group(rr, "year")
    _attach_balances(daily, monthly, weekly, yearly)
    return {"monthly": monthly, "daily": daily, "weekly": weekly, "yearly": yearly}


async def _categories(db: AsyncSession, filters: dict) -> list:
    where, params = _build_filters(filters)
    rows = (await db.execute(text(
        "SELECT type, category, amount FROM fin_transactions" + where), params)).fetchall()
    agg: Dict[str, dict] = {}
    for r in rows:
        key = f"{r.category}|{r.type}"
        if key not in agg:
            agg[key] = {"category": r.category, "type": r.type, "amount": 0.0}
        agg[key]["amount"] += _as_float(r.amount)
    out = sorted(agg.values(), key=lambda x: x["amount"], reverse=True)
    for o in out:
        o["amount"] = round(o["amount"], 2)
    return out


async def _anomalies(db: AsyncSession, filters: dict, threshold: float = 2.0) -> list:
    where, params = _build_filters(filters)
    rows = (await db.execute(text(
        "SELECT id, type, amount FROM fin_transactions" + where), params)).fetchall()
    s: Dict[str, float] = {}
    c: Dict[str, int] = {}
    for r in rows:
        s[r.type] = s.get(r.type, 0.0) + _as_float(r.amount)
        c[r.type] = c.get(r.type, 0) + 1
    avg = {t: (s[t] / c[t] if c[t] else 0.0) for t in s}
    return [int(r.id) for r in rows if avg.get(r.type, 0) > 0 and _as_float(r.amount) > avg[r.type] * threshold]


async def _distinct(db: AsyncSession, column: str) -> list:
    if column not in ("category", "participant"):
        return []
    rows = (await db.execute(text(
        f"SELECT DISTINCT {column} AS v FROM fin_transactions "
        f"WHERE {column} IS NOT NULL AND {column} != '' ORDER BY v ASC LIMIT 200"))).fetchall()
    return [r.v for r in rows]


# ── endpoints ─────────────────────────────────────────────────────────

@router.get("/data")
async def api_data(
    request: Request,
    page: int = Query(1),
    per_page: int = Query(25),
    sort: str = Query("date"),
    dir: str = Query("desc"),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        filters = _parse_filters(request)
        page = max(1, page)
        if per_page < 1:
            per_page = 25
        if sort not in _SORT_COLS:
            sort = "date"
        order = "ASC" if str(dir).lower() == "asc" else "DESC"
        limit = max(1, min(500, per_page))
        offset = max(0, (page - 1) * per_page)

        where, params = _build_filters(filters)
        total = (await db.execute(text("SELECT COUNT(*) FROM fin_transactions" + where), params)).scalar() or 0
        rows = (await db.execute(text(
            f"SELECT * FROM fin_transactions{where} ORDER BY {sort} {order}, id DESC "
            f"LIMIT {limit} OFFSET {offset}"), params)).fetchall()

        settings = await _fin_settings(db)
        months = (await db.execute(text(
            "SELECT DISTINCT TO_CHAR(\"date\", 'YYYY-MM') AS m FROM fin_transactions ORDER BY m DESC"))).fetchall()

        def g(k, default=""):
            v = settings.get(k)
            return v if v is not None else default

        return {
            "summary": await _summary(db),
            "averages": await _averages(db),
            "chart": await _chart(db, filters),
            "categories": await _categories(db, filters),
            "transactions": [_format_row(r) for r in rows],
            "pagination": {
                "page": page, "per_page": per_page, "total": int(total),
                "pages": (int(total) + max(1, per_page) - 1) // max(1, per_page),
            },
            "settings": {
                "currency": g("currency", "₽"),
                "decimals": int(g("decimals", 2) or 2),
                "auto_refresh": int(g("auto_refresh", 0) or 0),
                "avg_period": g("avg_period", "day"),
                "platega_merchant_id": g("platega_merchant_id"),
                "platega_secret_raw": decrypt(g("platega_secret")),
                "platega_days_back": int(g("platega_days_back", 150) or 150),
                "platega_auto_sync": int(g("platega_auto_sync", 0) or 0),
                "platega_last_sync": g("platega_last_sync"),
                "platega_last_error": g("platega_last_error"),
                "platega_last_sync_ok": int(g("platega_last_sync_ok", 0) or 0),
                "yookassa_shop_id": g("yookassa_shop_id"),
                "yookassa_secret_raw": decrypt(g("yookassa_secret_key")),
                "yookassa_days_back": int(g("yookassa_days_back", 30) or 30),
                "yookassa_auto_sync": int(g("yookassa_auto_sync", 0) or 0),
                "yookassa_last_sync": g("yookassa_last_sync"),
                "yookassa_last_error": g("yookassa_last_error"),
                "yookassa_last_sync_ok": int(g("yookassa_last_sync_ok", 0) or 0),
                "yookassa_commissions": _commissions(g("yookassa_commissions")),
            },
            "all_months": [r.m for r in months],
            "all_categories": await _distinct(db, "category"),
            "all_participants": await _distinct(db, "participant"),
            "anomalies": await _anomalies(db, filters),
        }
    except Exception as e:  # mirror PHP catch
        return JSONResponse(status_code=500, content={"error": f"Ошибка загрузки данных: {e}"})


_DEFAULT_COMMISSIONS = {"bank_card": 3, "sbp": 0.5, "yoo_money": 3, "sberbank": 3,
                        "tinkoff_bank": 3, "mobile": 6, "cash": 3, "qiwi": 3}
_SUPPORTED_METHODS = list(_DEFAULT_COMMISSIONS.keys())


def _commissions(raw: str) -> dict:
    import json
    base = dict(_DEFAULT_COMMISSIONS)
    if raw:
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                base.update(d)
        except Exception:
            pass
    return base


def _validate_tx(d: dict) -> Optional[str]:
    ds = str(d.get("date") or "")
    if len(ds) != 10 or ds[4] != "-" or ds[7] != "-":
        return "Некорректная дата"
    try:
        datetime.strptime(ds, "%Y-%m-%d")
    except ValueError:
        return "Некорректная дата"
    if d.get("type") not in ("income", "expense"):
        return "Некорректный тип"
    if str(d.get("category") or "").strip() == "":
        return "Категория обязательна"
    if _as_float(d.get("amount")) <= 0:
        return "Сумма должна быть больше нуля"
    return None


def _clean_tx(d: dict) -> dict:
    return {
        "date": datetime.strptime(str(d["date"]), "%Y-%m-%d").date(),
        "type": str(d["type"]),
        "category": str(d.get("category") or "").strip(),
        "participant": str(d.get("participant") or "").strip() or None,
        "amount": round(_as_float(d["amount"]), 2),
        "description": str(d.get("description") or "").strip(),
    }


@router.post("/add")
async def api_add(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    err = _validate_tx(body)
    if err:
        return api_error(400, E.INVALID_INPUT, err)
    data = _clean_tx(body)
    cols = ", ".join(data.keys())
    ph = ", ".join(f":{k}" for k in data)
    res = await db.execute(text(f"INSERT INTO fin_transactions ({cols}) VALUES ({ph}) RETURNING id"), data)
    new_id = int(res.scalar())
    await db.commit()
    return {"success": True, "id": new_id}


@router.post("/edit")
async def api_edit(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    row_id = int(body.get("id") or 0)
    existing = (await db.execute(text("SELECT id FROM fin_transactions WHERE id = :id"), {"id": row_id})).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Запись не найдена")
    err = _validate_tx(body)
    if err:
        return api_error(400, E.INVALID_INPUT, err)
    data = _clean_tx(body)
    sets = ", ".join(f"{k} = :{k}" for k in data)
    await db.execute(text(f"UPDATE fin_transactions SET {sets} WHERE id = :__id"), {**data, "__id": row_id})
    await db.commit()
    return {"success": True}


@router.post("/delete")
async def api_delete(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    row_id = int(body.get("id") or 0)
    existing = (await db.execute(text("SELECT id FROM fin_transactions WHERE id = :id"), {"id": row_id})).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Запись не найдена")
    await db.execute(text("DELETE FROM fin_transactions WHERE id = :id"), {"id": row_id})
    await db.commit()
    return {"success": True}


def _extract_ids(body: dict) -> Optional[List[int]]:
    ids = body.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return None
    try:
        out = []
        seen = set()
        for x in ids:
            i = int(x)
            if i not in seen:
                seen.add(i)
                out.append(i)
    except (TypeError, ValueError):
        return None
    if not out or len(out) > 1000:
        return None
    return out


@router.post("/delete-bulk")
async def api_delete_bulk(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    ids = _extract_ids(body)
    if ids is None:
        return api_error(400, E.INVALID_INPUT, "Не выбрано ни одной записи")
    total = 0
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        params = {f"i{n}": v for n, v in enumerate(chunk)}
        ph = ", ".join(f":i{n}" for n in range(len(chunk)))
        res = await db.execute(text(f"DELETE FROM fin_transactions WHERE id IN ({ph})"), params)
        total += res.rowcount
    await db.commit()
    return {"success": True, "deleted": total}


async def _bulk_update(db: AsyncSession, ids: List[int], data: dict) -> int:
    allowed = ["type", "category", "participant", "description"]
    sets = []
    params: Dict[str, Any] = {}
    for key in allowed:
        if key not in data:
            continue
        val = data[key]
        if key == "participant" and val == "":
            val = None
        sets.append(f"{key} = :{key}")
        params[key] = val
    if not sets:
        return 0
    total = 0
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        idp = {f"i{n}": v for n, v in enumerate(chunk)}
        ph = ", ".join(f":i{n}" for n in range(len(chunk)))
        res = await db.execute(text(f"UPDATE fin_transactions SET {', '.join(sets)} WHERE id IN ({ph})"),
                               {**params, **idp})
        total += res.rowcount
    return total


@router.post("/bulk/type")
async def api_bulk_type(request: Request, admin: AdminUser = Depends(get_current_admin),
                        db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    t = body.get("type") or ""
    if t not in ("income", "expense"):
        return api_error(400, E.INVALID_INPUT, "Некорректный тип")
    ids = _extract_ids(body)
    if ids is None:
        return api_error(400, E.INVALID_INPUT, "Не выбрано ни одной записи")
    updated = await _bulk_update(db, ids, {"type": t})
    await db.commit()
    return {"success": True, "updated": updated}


@router.post("/bulk/category")
async def api_bulk_category(request: Request, admin: AdminUser = Depends(get_current_admin),
                            db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    cat = str(body.get("category") or "").strip()
    if cat == "":
        return api_error(400, E.INVALID_INPUT, "Категория не может быть пустой")
    ids = _extract_ids(body)
    if ids is None:
        return api_error(400, E.INVALID_INPUT, "Не выбрано ни одной записи")
    updated = await _bulk_update(db, ids, {"category": cat})
    await db.commit()
    return {"success": True, "updated": updated}


@router.post("/bulk/participant")
async def api_bulk_participant(request: Request, admin: AdminUser = Depends(get_current_admin),
                               db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    p = str(body.get("participant") or "").strip()
    ids = _extract_ids(body)
    if ids is None:
        return api_error(400, E.INVALID_INPUT, "Не выбрано ни одной записи")
    updated = await _bulk_update(db, ids, {"participant": p})
    await db.commit()
    return {"success": True, "updated": updated}


@router.post("/bulk/description")
async def api_bulk_description(request: Request, admin: AdminUser = Depends(get_current_admin),
                              db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    d = str(body.get("description") or "").strip()
    ids = _extract_ids(body)
    if ids is None:
        return api_error(400, E.INVALID_INPUT, "Не выбрано ни одной записи")
    updated = await _bulk_update(db, ids, {"description": d})
    await db.commit()
    return {"success": True, "updated": updated}


def _csv_rows(rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow(["date", "type", "category", "participant", "amount", "description", "record_id"])
    for r in rows:
        w.writerow([
            _dstr(r.date),
            "Доход" if r.type == "income" else "Расход",
            r.category,
            r.participant or "",
            _as_float(r.amount),
            r.description or "",
            r.record_id or "",
        ])
    return "\ufeff" + buf.getvalue()


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/csv")
async def api_export_csv(request: Request, admin: AdminUser = Depends(get_current_admin),
                         db: AsyncSession = Depends(get_db)):
    filters = _parse_filters(request)
    where, params = _build_filters(filters)
    rows = (await db.execute(text(
        "SELECT * FROM fin_transactions" + where + " ORDER BY date ASC, id ASC"), params)).fetchall()
    return _csv_response(_csv_rows(rows), f"finance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")


@router.post("/export/selected")
async def api_export_selected(request: Request, admin: AdminUser = Depends(get_current_admin),
                              db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    ids = _extract_ids(body)
    if ids is None:
        return api_error(400, E.INVALID_INPUT, "Не выбрано ни одной записи")
    params = {f"i{n}": v for n, v in enumerate(ids)}
    ph = ", ".join(f":i{n}" for n in range(len(ids)))
    rows = (await db.execute(text(
        f"SELECT * FROM fin_transactions WHERE id IN ({ph}) ORDER BY date ASC, id ASC"), params)).fetchall()
    return _csv_response(_csv_rows(rows), f"finance_selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")


@router.post("/import")
async def api_import(request: Request, admin: AdminUser = Depends(get_current_admin),
                     db: AsyncSession = Depends(get_db)):
    form = await request.form()
    upload = form.get("file")
    if upload is None or not getattr(upload, "filename", ""):
        return api_error(400, E.INVALID_INPUT, "Файл не загружен")
    raw = (await upload.read()).decode("utf-8", errors="replace")
    if raw.startswith("\ufeff"):
        raw = raw[1:]

    imported = skipped = 0
    errors: List[str] = []

    for line in raw.splitlines():
        line = line.rstrip("\r\n")
        if line == "":
            continue
        delim = ";" if line.count(";") >= line.count(",") else ","
        fields = next(csv.reader([line], delimiter=delim))
        fields = [f.strip() for f in fields]
        if not fields:
            continue
        if fields[0].lower() == "date":
            continue  # header
        if len(fields) < 5:
            continue
        ds = fields[0]
        t = _csv_type(fields[1] if len(fields) > 1 else "")
        cat = fields[2] if len(fields) > 2 else ""
        part = fields[3] if len(fields) > 3 else ""
        amt = _as_float((fields[4] if len(fields) > 4 else "0").replace(",", "."))
        desc = fields[5] if len(fields) > 5 else ""
        rid = (fields[6] if len(fields) > 6 else "").strip()

        try:
            datetime.strptime(ds, "%Y-%m-%d")
        except ValueError:
            continue
        if t == "" or amt <= 0:
            skipped += 1
            continue
        if cat == "":
            cat = "Другое"
        clean = _clean_tx({"date": ds, "type": t, "category": cat,
                           "participant": part, "amount": amt, "description": desc})
        if rid:
            exists = (await db.execute(text("SELECT id FROM fin_transactions WHERE record_id = :r LIMIT 1"),
                                       {"r": rid})).fetchone()
            if exists:
                skipped += 1
                continue
            clean["record_id"] = rid
        else:
            dup = (await db.execute(text(
                "SELECT COUNT(*) FROM fin_transactions WHERE date = :d AND type = :t "
                "AND COALESCE(participant, '') = :p AND amount = :a"),
                {"d": clean["date"], "t": clean["type"], "p": clean["participant"] or "", "a": clean["amount"]})).scalar()
            if dup:
                skipped += 1
                continue
        try:
            cols = ", ".join(clean.keys())
            ph = ", ".join(f":{k}" for k in clean)
            await db.execute(text(f"INSERT INTO fin_transactions ({cols}) VALUES ({ph})"), clean)
            imported += 1
        except Exception as e:
            errors.append(f"{ds}: {e}")
            skipped += 1

    await db.commit()
    return {"success": True, "imported": imported, "skipped": skipped, "errors": errors[:20]}


def _csv_type(v: str) -> str:
    t = v.strip().lower()
    if t in ("доход", "income", "приход", "плюс", "прибыль"):
        return "income"
    if t in ("расход", "expense", "отток", "минус"):
        return "expense"
    return ""


@router.get("/settings")
async def api_settings_get(admin: AdminUser = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return await _fin_settings(db)


@router.post("/settings")
async def api_settings_post(request: Request, admin: AdminUser = Depends(get_current_admin),
                            db: AsyncSession = Depends(get_db)):
    import json
    body = await json_body(request)
    for key in _SETTINGS_ALLOWED:
        if key not in body:
            continue
        value = body[key]
        if key in ("decimals", "auto_refresh"):
            value = int(_as_float(value))
        if key == "yookassa_days_back":
            value = int(_as_float(value))
            if value < 1 or value > 730:
                value = 30
        if key == "yookassa_auto_sync":
            value = 1 if _as_float(value) else 0
        if key in _JSON_ARRAY_KEYS:
            if isinstance(value, str):
                try:
                    value = json.loads(value) if value != "" else []
                except Exception:
                    value = []
            value = json.dumps(list(value), ensure_ascii=False) if isinstance(value, list) else "[]"
        if key in _SECRET_KEYS and value == "":
            continue
        if key in _SECRET_KEYS and value != "":
            value = encrypt(str(value))
        await _upsert_fin_setting(db, key, str(value))
    await db.commit()
    return {"success": True}
