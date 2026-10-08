"""Finance payments — Platega + YooKassa sync (migrated from PHP FinanceController).

Endpoints (mount prefix /admin/finance/api):
  Platega:  POST /platega/preview, /platega/import, /platega/sync; GET /platega/cron-sync; GET+POST /platega/settings
  YooKassa: POST /yookassa/preview, /yookassa/import, /yookassa/sync; GET /yookassa/cron-sync; GET+POST /yookassa/settings

cron-sync endpoints are token-protected and do NOT require a Bearer token (as PHP).
"""
import csv as _csv
import hmac
import io
import json
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.crypto import decrypt, encrypt
from backend.core.database import get_db
from backend.core.errors import E, api_error
from backend.core.request_utils import json_body

router = APIRouter()

PLATEGA_PARTICIPANT = "Platega пополнение"
YOOKASSA_PARTICIPANT = "YooKassa"

_DEFAULT_COMMISSIONS = {"bank_card": 3.0, "sbp": 0.5, "yoo_money": 3.0, "sberbank": 3.0,
                        "tinkoff_bank": 3.0, "mobile": 6.0, "cash": 3.0, "qiwi": 3.0}
_METHOD_LABELS = {
    "bank_card": "Банковская карта", "sbp": "СБП", "yoo_money": "ЮMoney", "sberbank": "Сбербанк",
    "tinkoff_bank": "Тинькофф", "mobile": "Мобильный платёж", "cash": "Наличные", "qiwi": "Qiwi",
    "alfa_bank": "Альфа-Банк", "b2b_sberbank": "СберБизнес", "installment": "Рассрочка", "wechat": "WeChat",
}


# ── settings helpers ──────────────────────────────────────────────────

async def _get_all(db: AsyncSession) -> Dict[str, str]:
    rows = (await db.execute(text("SELECT setting_key, setting_value FROM fin_settings"))).fetchall()
    return {r.setting_key: r.setting_value for r in rows}


async def _set(db: AsyncSession, key: str, value: str) -> None:
    await db.execute(
        text("INSERT INTO fin_settings (setting_key, setting_value) VALUES (:k, :v) "
             "ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value"),
        {"k": key, "v": value},
    )


def _g(settings: dict, key: str, default: str = "") -> str:
    v = settings.get(key)
    return default if v is None else v


# ── dedup helpers ─────────────────────────────────────────────────────

def _dup_key(dt_str: str, type_str: str, participant: str, amount: Any) -> str:
    t = str(type_str).strip().lower()
    t = "income" if t in ("доход", "income", "приход", "плюс", "прибыль") else "expense"
    try:
        amt = f"{round(float(amount), 2):.2f}"
    except (TypeError, ValueError):
        amt = "0.00"
    return f"{dt_str}|{t}|{str(participant).strip()}|{amt}"


async def _existing_keys(db: AsyncSession, participant: str) -> List[str]:
    rows = (await db.execute(text(
        'SELECT "date", "type", COALESCE("participant", \'\') AS participant, "amount" '
        'FROM fin_transactions WHERE participant = :p'), {"p": participant})).fetchall()
    return [_dup_key(str(r.date), r.type, r.participant, r.amount) for r in rows]


async def _existing_record_ids(db: AsyncSession, participant: str) -> List[str]:
    rows = (await db.execute(text(
        'SELECT "record_id" FROM fin_transactions WHERE participant = :p '
        'AND "record_id" IS NOT NULL AND "record_id" != \'\''), {"p": participant})).fetchall()
    return [str(r.record_id) for r in rows]


async def _find_by_record_id(db: AsyncSession, record_id: str) -> Optional[int]:
    if not record_id:
        return None
    r = (await db.execute(text("SELECT id FROM fin_transactions WHERE record_id = :r LIMIT 1"),
                          {"r": record_id})).fetchone()
    return int(r.id) if r else None


async def _find_orphan(db: AsyncSession, d: str, type_: str, category: str, participant: str, amount: float) -> Optional[int]:
    try:
        dval = datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    r = (await db.execute(text(
        "SELECT id FROM fin_transactions WHERE date = :d AND type = :t "
        "AND COALESCE(participant, '') = :p AND COALESCE(category, '') = :c AND amount = :a "
        "AND (record_id IS NULL OR record_id = '') ORDER BY id ASC LIMIT 1"),
        {"d": dval, "t": type_, "p": participant or "", "c": category or "", "a": amount})).fetchone()
    return int(r.id) if r else None


async def _attach_record_id(db: AsyncSession, row_id: int, record_id: str) -> None:
    await db.execute(text("UPDATE fin_transactions SET record_id = :r WHERE id = :id"),
                     {"r": record_id, "id": row_id})


async def _create_tx(db: AsyncSession, d: str, type_: str, category: str, participant: str,
                     amount: float, description: str, record_id: str = "") -> int:
    data: Dict[str, Any] = {
        "date": datetime.strptime(d, "%Y-%m-%d").date(),
        "type": type_,
        "category": category,
        "participant": participant or None,
        "amount": round(float(amount), 2),
        "description": description or "",
    }
    if record_id:
        data["record_id"] = record_id
    cols = ", ".join(data.keys())
    ph = ", ".join(f":{k}" for k in data)
    res = await db.execute(text(f"INSERT INTO fin_transactions ({cols}) VALUES ({ph}) RETURNING id"), data)
    return int(res.scalar())


def _sync_lock_ok(settings: dict, key: str) -> bool:
    lock = int(_g(settings, key, "0") or 0)
    return not (lock and (time.time() - lock) < 30)


# ── Platega ───────────────────────────────────────────────────────────

_PLATEGA_URL = "https://app.platega.io/transaction/export/csv"


async def _fetch_platega_csv(merchant_id: str, secret: str, days_back: int) -> List[dict]:
    now = datetime.now(timezone.utc)
    frm = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    to = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "statuses": ["6", "7"],
        "paymentMethods": ["2", "10", "11", "12", "13"],
        "from": frm, "to": to, "timeZoneId": "Europe/Moscow",
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(_PLATEGA_URL, json=payload, headers={
            "Content-Type": "application/json",
            "X-MerchantId": merchant_id,
            "X-Secret": secret,
        })
        data = None
        try:
            data = r.json()
        except Exception:
            data = None
        if not isinstance(data, dict) or not data.get("url"):
            raise RuntimeError("Platega API response missing url field")
        csv_url = data["url"]
        r2 = await c.get(csv_url, headers={"User-Agent": "HexaVeil/1.0"})
        return _parse_platega_csv(r2.text)


def _parse_platega_csv(text_: str) -> List[dict]:
    if text_.startswith("\ufeff"):
        text_ = text_[1:]
    rows = []
    for line in text_.split("\n"):
        line = line.rstrip("\r\n")
        if line == "":
            continue
        rows.append([f.strip() for f in next(_csv.reader([line], delimiter=";"))])
    if not rows:
        return []
    header = rows.pop(0)
    out = []
    for row in rows:
        out.append({col: (row[i] if i < len(row) else "") for i, col in enumerate(header)})
    return out


async def _platega_preview(db: AsyncSession, merchant_id: str, secret: str, days_back: int) -> List[dict]:
    existing_keys = await _existing_keys(db, PLATEGA_PARTICIPANT)
    existing_ids = await _existing_record_ids(db, PLATEGA_PARTICIPANT)
    rows = await _fetch_platega_csv(merchant_id, secret, days_back)
    preview = []
    for row in rows:
        record_id = str(row.get("RecordId") or "")
        status = str(row.get("Status") or "").upper()
        created = str(row.get("CreatedAt") or "")
        amount = float(row.get("Amount") or 0)
        description = str(row.get("Description") or "")

        if status != "CONFIRMED":
            preview.append({"record_id": record_id, "date": created[:10], "type": "Доход",
                            "participant": PLATEGA_PARTICIPANT, "category": "Прибыль", "amount": 0,
                            "gross": amount, "description": description[:60], "status": "skipped"})
            continue

        date_str = created[0:10]
        try:
            dt = datetime.strptime(created[:19], "%Y-%m-%d %H:%M:%S")
            date_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
        gross = abs(amount)
        net = round(gross * 0.9, 2)
        desc = f"Пополнение на {int(gross)} ₽"
        import re
        m = re.search(r"на\s+(\d+(?:[.,]\d+)?)\s*(?:₽|руб)", description, re.IGNORECASE | re.UNICODE)
        if m:
            desc = f"Пополнение на {int(round(float(m.group(1).replace(',', '.'))))} ₽"

        if record_id:
            is_dup = record_id in existing_ids
            if not is_dup:
                is_dup = (await _find_orphan(db, date_str, "income", "Прибыль",
                                             PLATEGA_PARTICIPANT, net)) is not None
        else:
            is_dup = _dup_key(date_str, "Доход", PLATEGA_PARTICIPANT, net) in existing_keys

        preview.append({"record_id": record_id, "date": date_str, "type": "Доход",
                        "participant": PLATEGA_PARTICIPANT, "category": "Прибыль", "amount": net,
                        "gross": gross, "description": desc,
                        "status": "duplicate" if is_dup else "new"})
    return preview


async def _commit_platega(db: AsyncSession, preview_rows: List[dict], include_ids: List[str]) -> dict:
    existing_keys = await _existing_keys(db, PLATEGA_PARTICIPANT)
    existing_ids = await _existing_record_ids(db, PLATEGA_PARTICIPANT)
    added = skipped = 0
    mapping = {str(t.get("record_id")): t for t in preview_rows}
    for rid in include_ids:
        t = mapping.get(str(rid))
        if not t or t.get("status") != "new":
            skipped += 1
            continue
        record_id = str(t.get("record_id") or "")
        dup_key = None
        if record_id:
            if record_id in existing_ids:
                skipped += 1
                continue
            orphan = await _find_orphan(db, t["date"], "income", str(t.get("category") or ""),
                                        str(t.get("participant") or ""), float(t.get("amount") or 0))
            if orphan is not None:
                await _attach_record_id(db, orphan, record_id)
                existing_ids.append(record_id)
                skipped += 1
                continue
        else:
            dup_key = _dup_key(t["date"], t["type"], t["participant"], t["amount"])
            if dup_key in existing_keys:
                skipped += 1
                continue
        try:
            await _create_tx(db, t["date"], "income", t["category"], t["participant"],
                             float(t["amount"]), str(t.get("description") or ""), record_id)
            if record_id:
                existing_ids.append(record_id)
            else:
                existing_keys.append(dup_key)
            added += 1
        except Exception:
            skipped += 1
    return {"added": added, "skipped": skipped}


async def _stitch_platega(db: AsyncSession, preview_rows: List[dict]) -> int:
    stitched = 0
    for t in preview_rows:
        record_id = str(t.get("record_id") or "")
        if not record_id:
            continue
        if await _find_by_record_id(db, record_id) is not None:
            continue
        orphan = await _find_orphan(db, t["date"], "income", str(t.get("category") or ""),
                                    str(t.get("participant") or ""), float(t.get("amount") or 0))
        if orphan is not None:
            await _attach_record_id(db, orphan, record_id)
            stitched += 1
    return stitched


async def _run_platega_sync(db: AsyncSession) -> tuple[dict, int]:
    settings = await _get_all(db)
    merchant_id = _g(settings, "platega_merchant_id").strip()
    secret = decrypt(_g(settings, "platega_secret")).strip()
    days_back = int(_g(settings, "platega_days_back", "150") or 150)
    if days_back < 1 or days_back > 730:
        days_back = 150

    if not merchant_id or not secret:
        await _set(db, "platega_last_error", "Platega не настроен (merchant_id/secret пусты)")
        await _set(db, "platega_last_sync_ok", "0")
        await db.commit()
        return {"success": False, "error": "Platega не настроен (merchant_id/secret пусты)"}, 400

    if not _sync_lock_ok(settings, "platega_sync_lock"):
        return {"success": True, "added": 0, "skipped": 0, "new": 0, "skipped_lock": True}, 200
    await _set(db, "platega_sync_lock", str(int(time.time())))
    await db.commit()

    try:
        preview = await _platega_preview(db, merchant_id, secret, days_back)
        new_rows = [t for t in preview if t.get("status") == "new"]
        added = skipped = 0
        if new_rows:
            res = await _commit_platega(db, new_rows, [str(t["record_id"]) for t in new_rows])
            added, skipped = res["added"], res["skipped"]
        await _stitch_platega(db, preview)
        await _set(db, "platega_last_sync", datetime.now(timezone.utc).isoformat())
        await _set(db, "platega_last_error", "")
        await _set(db, "platega_last_sync_ok", "1")
        await _set(db, "platega_sync_lock", "")
        await db.commit()
        return {"success": True, "added": added, "skipped": skipped, "new": len(new_rows)}, 200
    except Exception as e:
        await _set(db, "platega_sync_lock", "")
        await _set(db, "platega_last_error", str(e))
        await _set(db, "platega_last_sync_ok", "0")
        await db.commit()
        return {"success": False, "error": str(e)}, 500


@router.post("/platega/preview")
async def platega_preview(request: Request, admin: AdminUser = Depends(get_current_admin),
                          db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    merchant_id = str(body.get("merchant_id") or "").strip()
    secret = str(body.get("secret") or "").strip()
    days_back = int(body.get("days_back") or 150)
    if days_back < 1 or days_back > 730:
        days_back = 150
    settings = await _get_all(db)
    if merchant_id == "":
        merchant_id = _g(settings, "platega_merchant_id").strip()
    if secret == "":
        secret = decrypt(_g(settings, "platega_secret")).strip()
    if not merchant_id or not secret:
        return api_error(400, E.INVALID_INPUT, "Укажите merchant_id и secret")
    try:
        return {"success": True, "transactions": await _platega_preview(db, merchant_id, secret, days_back)}
    except Exception as e:
        return api_error(500, E.INTERNAL_ERROR, f"Platega preview error: {e}")


@router.post("/platega/import")
async def platega_import(request: Request, admin: AdminUser = Depends(get_current_admin),
                         db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    txn = body.get("transactions") or []
    if not isinstance(txn, list):
        return api_error(400, E.INVALID_INPUT, "Некорректные данные")
    include_ids = [str(t["record_id"]) for t in txn if t.get("include") and t.get("record_id") is not None]
    if not include_ids:
        return {"success": True, "added": 0, "skipped": 0}
    try:
        res = await _commit_platega(db, txn, include_ids)
        await _set(db, "platega_last_sync", datetime.now(timezone.utc).isoformat())
        await db.commit()
        return {"success": True, "added": res["added"], "skipped": res["skipped"]}
    except Exception as e:
        return api_error(500, E.INTERNAL_ERROR, f"Ошибка импорта: {e}")


@router.post("/platega/sync")
async def platega_sync(admin: AdminUser = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    res, _code = await _run_platega_sync(db)
    return res


@router.get("/platega/cron-sync")
async def platega_cron_sync(request: Request, db: AsyncSession = Depends(get_db)):
    settings = await _get_all(db)
    stored = _g(settings, "platega_cron_token")
    token = request.query_params.get("token", "")
    if stored == "" or not hmac.compare_digest(stored, token):
        return JSONResponse(status_code=403, content={"success": False, "error": "forbidden"})
    res, code = await _run_platega_sync(db)
    res["cron"] = True
    return JSONResponse(status_code=(200 if res.get("success") else code), content=res)


@router.get("/platega/settings")
async def platega_settings(admin: AdminUser = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    s = await _get_all(db)
    secret = decrypt(_g(s, "platega_secret"))
    return {
        "merchant_id": _g(s, "platega_merchant_id"),
        "secret": ("***" + secret[-4:]) if secret else "",
        "secret_raw": secret,
        "days_back": int(_g(s, "platega_days_back", "150") or 150),
        "auto_sync": int(_g(s, "platega_auto_sync", "0") or 0),
        "last_sync": _g(s, "platega_last_sync"),
        "last_sync_ok": int(_g(s, "platega_last_sync_ok", "0") or 0),
        "last_error": _g(s, "platega_last_error"),
    }


@router.post("/platega/settings")
async def platega_settings_save(request: Request, admin: AdminUser = Depends(get_current_admin),
                                db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    for key in ["platega_merchant_id", "platega_secret", "platega_days_back", "platega_auto_sync"]:
        if key not in body:
            continue
        value = str(body[key])
        if key in ("platega_days_back", "platega_auto_sync"):
            value = str(max(0, int(float(value or 0))))
        if key == "platega_secret":
            if value == "":
                continue
            value = encrypt(value)
        await _set(db, key, value)
    await db.commit()
    return {"success": True}


# ── YooKassa ──────────────────────────────────────────────────────────

_YK_BASE = "https://api.yookassa.ru/v3"


async def _yk_fetch_all(shop_id: str, secret: str, since: str, until: str) -> List[dict]:
    all_items: List[dict] = []
    cursor = None
    async with httpx.AsyncClient(timeout=30, auth=(shop_id, secret)) as c:
        while True:
            params = {"created_at.gte": since, "created_at.lte": until, "limit": "100"}
            if cursor:
                params["cursor"] = cursor
            r = await c.get(f"{_YK_BASE}/payments", params=params, headers={
                "Idempotence-Key": _hex(16),
                "User-Agent": "HexaVeil-CMS/1.0 (Python)",
                "Accept": "application/json",
            })
            body = r.json() if r.content else {}
            if r.status_code in (401, 403):
                raise RuntimeError(f"YooKassa: неверные shop_id или secret_key (HTTP {r.status_code})")
            if r.status_code < 200 or r.status_code >= 300:
                msg = (body.get("message", "") if isinstance(body, dict) else "")
                extra = (body.get("description", "") if isinstance(body, dict) else "")
                raise RuntimeError(f"YooKassa API HTTP {r.status_code}" + (f": {msg} — {extra}" if msg else ""))
            if not isinstance(body, dict):
                raise RuntimeError("YooKassa: не удалось разобрать ответ API")
            all_items.extend(body.get("items") or [])
            cursor = body.get("next_cursor")
            if not cursor:
                break
    return all_items


def _hex(n: int) -> str:
    import os
    return os.urandom(n).hex()


def _commissions(raw: str) -> dict:
    out = dict(_DEFAULT_COMMISSIONS)
    if raw:
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                for m in _DEFAULT_COMMISSIONS:
                    if m in d and float(d[m]) >= 0:
                        out[m] = float(d[m])
        except Exception:
            pass
    return out


def _yk_description(description: str, metadata: dict) -> str:
    desc = description.strip() if description else "Пополнение баланса"
    label_map = {"order_id": "order", "username": "user", "user": "user", "name": "name",
                 "tg_id": "tg", "telegram_id": "tg", "email": "email"}
    parts = []
    for key, label in label_map.items():
        if key not in metadata:
            continue
        v = str(metadata[key]).strip()
        if v:
            parts.append(f"{label}: {v[:40]}")
    if parts:
        desc += " (" + ", ".join(parts) + ")"
    return desc[:140]


async def _yk_preview(db: AsyncSession, shop_id: str, secret: str, days_back: int) -> List[dict]:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    until = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payments = await _yk_fetch_all(shop_id, secret, since, until)

    commissions = _commissions(_g(await _get_all(db), "yookassa_commissions"))
    existing_keys = await _existing_keys(db, YOOKASSA_PARTICIPANT)
    existing_ids = await _existing_record_ids(db, YOOKASSA_PARTICIPANT)

    preview = []
    for p in payments:
        pid = str(p.get("id") or "")
        status = str(p.get("status") or "")
        paid = bool(p.get("paid"))
        created = str(p.get("created_at") or "")
        method = str((p.get("payment_method") or {}).get("type") or "bank_card")
        description = str(p.get("description") or "")
        metadata = p.get("metadata") if isinstance(p.get("metadata"), dict) else {}
        gross = float((p.get("amount") or {}).get("value") or 0)

        record_id = f"yk_{pid}" if pid else ""
        date_str = created[:10]
        desc = _yk_description(description, metadata)
        label = _METHOD_LABELS.get(method, method)

        if status != "succeeded" or not paid:
            preview.append({"record_id": record_id, "date": date_str, "type": "Доход",
                            "participant": YOOKASSA_PARTICIPANT, "category": "Прибыль", "amount": 0,
                            "gross": gross, "commission_pct": None, "method": method, "method_label": label,
                            "description": desc, "status": "skipped"})
            continue

        pct = commissions.get(method, 3.0)
        net = round(gross * (1 - pct / 100), 2)
        if record_id:
            is_dup = record_id in existing_ids
            if not is_dup:
                is_dup = (await _find_orphan(db, date_str, "income", "Прибыль",
                                             YOOKASSA_PARTICIPANT, net)) is not None
        else:
            is_dup = _dup_key(date_str, "Доход", YOOKASSA_PARTICIPANT, net) in existing_keys

        preview.append({"record_id": record_id, "date": date_str, "type": "Доход",
                        "participant": YOOKASSA_PARTICIPANT, "category": "Прибыль", "amount": net,
                        "gross": gross, "commission_pct": pct, "method": method, "method_label": label,
                        "description": desc, "status": "duplicate" if is_dup else "new"})
    return preview


async def _commit_yk(db: AsyncSession, preview_rows: List[dict], include_ids: List[str]) -> dict:
    existing_keys = await _existing_keys(db, YOOKASSA_PARTICIPANT)
    existing_ids = await _existing_record_ids(db, YOOKASSA_PARTICIPANT)
    added = skipped = 0
    mapping = {str(t.get("record_id")): t for t in preview_rows}
    for rid in include_ids:
        t = mapping.get(str(rid))
        if not t:
            skipped += 1
            continue
        if str(t.get("status", "new")) != "new":
            skipped += 1
            continue
        record_id = str(t.get("record_id") or "")
        dup_key = None
        if record_id:
            if record_id in existing_ids:
                skipped += 1
                continue
            orphan = await _find_orphan(db, str(t.get("date") or ""), "income", str(t.get("category") or ""),
                                        str(t.get("participant") or ""), float(t.get("amount") or 0))
            if orphan is not None:
                await _attach_record_id(db, orphan, record_id)
                existing_ids.append(record_id)
                skipped += 1
                continue
        else:
            dup_key = _dup_key(str(t.get("date") or ""), str(t.get("type") or "Доход"),
                               str(t.get("participant") or YOOKASSA_PARTICIPANT), t.get("amount") or 0)
            if dup_key in existing_keys:
                skipped += 1
                continue
        try:
            await _create_tx(db, str(t.get("date") or ""), "income", str(t.get("category") or "Прибыль"),
                             str(t.get("participant") or YOOKASSA_PARTICIPANT), float(t.get("amount") or 0),
                             str(t.get("description") or ""), record_id)
            if record_id:
                existing_ids.append(record_id)
            else:
                existing_keys.append(dup_key)
            added += 1
        except Exception:
            skipped += 1
    return {"added": added, "skipped": skipped}


async def _stitch_yk(db: AsyncSession, preview_rows: List[dict]) -> int:
    stitched = 0
    for t in preview_rows:
        record_id = str(t.get("record_id") or "")
        if not record_id:
            continue
        if await _find_by_record_id(db, record_id) is not None:
            continue
        orphan = await _find_orphan(db, str(t.get("date") or ""), "income", str(t.get("category") or ""),
                                    str(t.get("participant") or ""), float(t.get("amount") or 0))
        if orphan is not None:
            await _attach_record_id(db, orphan, record_id)
            stitched += 1
    return stitched


async def _run_yk_sync(db: AsyncSession) -> tuple[dict, int]:
    settings = await _get_all(db)
    shop_id = _g(settings, "yookassa_shop_id").strip()
    secret = decrypt(_g(settings, "yookassa_secret_key")).strip()
    days_back = int(_g(settings, "yookassa_days_back", "30") or 30)
    if days_back < 1 or days_back > 730:
        days_back = 30

    if not shop_id or not secret:
        await _set(db, "yookassa_last_error", "YooKassa не настроена (shop_id/secret пусты)")
        await _set(db, "yookassa_last_sync_ok", "0")
        await db.commit()
        return {"success": False, "error": "YooKassa не настроена (shop_id/secret пусты)"}, 400

    if not _sync_lock_ok(settings, "yookassa_sync_lock"):
        return {"success": True, "added": 0, "skipped": 0, "new": 0, "skipped_lock": True}, 200
    await _set(db, "yookassa_sync_lock", str(int(time.time())))
    await db.commit()

    try:
        preview = await _yk_preview(db, shop_id, secret, days_back)
        new_rows = [t for t in preview if t.get("status") == "new"]
        added = skipped = 0
        if new_rows:
            res = await _commit_yk(db, new_rows, [str(t["record_id"]) for t in new_rows])
            added, skipped = res["added"], res["skipped"]
        await _stitch_yk(db, preview)
        await _set(db, "yookassa_last_sync", datetime.now(timezone.utc).isoformat())
        await _set(db, "yookassa_last_error", "")
        await _set(db, "yookassa_last_sync_ok", "1")
        await _set(db, "yookassa_sync_lock", "")
        await db.commit()
        return {"success": True, "added": added, "skipped": skipped, "new": len(new_rows)}, 200
    except Exception as e:
        await _set(db, "yookassa_sync_lock", "")
        await _set(db, "yookassa_last_error", str(e))
        await _set(db, "yookassa_last_sync_ok", "0")
        await db.commit()
        return {"success": False, "error": str(e)}, 500


@router.post("/yookassa/preview")
async def yk_preview(request: Request, admin: AdminUser = Depends(get_current_admin),
                     db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    shop_id = str(body.get("shop_id") or "").strip()
    secret = str(body.get("secret") or "").strip()
    days_back = int(body.get("days_back") or 30)
    if days_back < 1 or days_back > 730:
        days_back = 30
    settings = await _get_all(db)
    if shop_id == "":
        shop_id = _g(settings, "yookassa_shop_id").strip()
    if secret == "":
        secret = decrypt(_g(settings, "yookassa_secret_key")).strip()
    if not shop_id or not secret:
        return api_error(400, E.INVALID_INPUT, "Укажите shop_id и secret_key")
    try:
        return {"success": True, "transactions": await _yk_preview(db, shop_id, secret, days_back)}
    except Exception as e:
        return api_error(500, E.INTERNAL_ERROR, f"YooKassa preview error: {e}")


@router.post("/yookassa/import")
async def yk_import(request: Request, admin: AdminUser = Depends(get_current_admin),
                    db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    txn = body.get("transactions") or []
    if not isinstance(txn, list):
        return api_error(400, E.INVALID_INPUT, "Некорректные данные")
    include_ids = [str(t["record_id"]) for t in txn if t.get("include") and t.get("record_id") is not None]
    if not include_ids:
        return {"success": True, "added": 0, "skipped": 0}
    try:
        res = await _commit_yk(db, txn, include_ids)
        await _set(db, "yookassa_last_sync", datetime.now(timezone.utc).isoformat())
        await db.commit()
        return {"success": True, "added": res["added"], "skipped": res["skipped"]}
    except Exception as e:
        return api_error(500, E.INTERNAL_ERROR, f"Ошибка импорта: {e}")


@router.post("/yookassa/sync")
async def yk_sync(admin: AdminUser = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    res, _code = await _run_yk_sync(db)
    return res


@router.get("/yookassa/cron-sync")
async def yk_cron_sync(request: Request, db: AsyncSession = Depends(get_db)):
    settings = await _get_all(db)
    stored = _g(settings, "yookassa_cron_token")
    token = request.query_params.get("token", "")
    if stored == "" or not hmac.compare_digest(stored, token):
        return JSONResponse(status_code=403, content={"success": False, "error": "forbidden"})
    res, code = await _run_yk_sync(db)
    res["cron"] = True
    return JSONResponse(status_code=(200 if res.get("success") else code), content=res)


@router.get("/yookassa/settings")
async def yk_settings(admin: AdminUser = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    s = await _get_all(db)
    secret = decrypt(_g(s, "yookassa_secret_key"))
    return {
        "shop_id": _g(s, "yookassa_shop_id"),
        "secret": ("***" + secret[-4:]) if secret else "",
        "secret_raw": secret,
        "days_back": int(_g(s, "yookassa_days_back", "30") or 30),
        "auto_sync": int(_g(s, "yookassa_auto_sync", "0") or 0),
        "commissions": _commissions(_g(s, "yookassa_commissions")),
        "last_sync": _g(s, "yookassa_last_sync"),
        "last_sync_ok": int(_g(s, "yookassa_last_sync_ok", "0") or 0),
        "last_error": _g(s, "yookassa_last_error"),
    }


@router.post("/yookassa/settings")
async def yk_settings_save(request: Request, admin: AdminUser = Depends(get_current_admin),
                           db: AsyncSession = Depends(get_db)):
    body = await json_body(request)
    if "shop_id" in body:
        await _set(db, "yookassa_shop_id", str(body["shop_id"]).strip())
    if "secret" in body:
        secret = str(body["secret"]).strip()
        if secret:
            await _set(db, "yookassa_secret_key", encrypt(secret))
    if "days_back" in body:
        d = int(float(body["days_back"] or 0))
        if d < 1 or d > 730:
            d = 30
        await _set(db, "yookassa_days_back", str(d))
    if "auto_sync" in body:
        await _set(db, "yookassa_auto_sync", "1" if int(float(body["auto_sync"] or 0)) else "0")
    if isinstance(body.get("commissions"), dict):
        comm = {}
        for method in _DEFAULT_COMMISSIONS:
            if method in body["commissions"]:
                comm[method] = round(float(body["commissions"][method]), 2)
        await _set(db, "yookassa_commissions", json.dumps(comm, ensure_ascii=False))
    await db.commit()
    return {"success": True}
