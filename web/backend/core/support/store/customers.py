"""Customer profiles — upsert by identity_key (raw SQL, no commit)."""
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row._mapping) if row is not None else None


async def upsert_customer_profile(
    db: AsyncSession,
    *,
    identity_key: str,
    tg_user_id: int | None = None,
    username: str | None = None,
    display_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    meta: dict[str, Any] | None = None,
) -> int:
    """Insert or update a customer profile; returns its id.

    Non-null fields win on conflict (identity_key is the merge key).
    """
    meta_json = json.dumps(meta, ensure_ascii=False) if meta is not None else None
    row = await db.execute(
        text("""
            INSERT INTO support_customer_profile
                (identity_key, tg_user_id, username, display_name, email, phone, meta)
            VALUES
                (:identity_key, :tg_user_id, :username, :display_name, :email, :phone,
                 COALESCE(:meta, '{}')::jsonb)
            ON CONFLICT (identity_key) DO UPDATE SET
                tg_user_id   = COALESCE(EXCLUDED.tg_user_id, support_customer_profile.tg_user_id),
                username     = COALESCE(EXCLUDED.username, support_customer_profile.username),
                display_name  = COALESCE(EXCLUDED.display_name, support_customer_profile.display_name),
                email         = COALESCE(EXCLUDED.email, support_customer_profile.email),
                phone         = COALESCE(EXCLUDED.phone, support_customer_profile.phone)
            RETURNING id
        """),
        {
            "identity_key": identity_key,
            "tg_user_id": tg_user_id,
            "username": username,
            "display_name": display_name,
            "email": email,
            "phone": phone,
            "meta": meta_json,
        },
    )
    return int(row.scalar_one())


async def update_customer_meta(db: AsyncSession, customer_id: int, meta: dict[str, Any] | None) -> bool:
    """Replace the profile meta blob (card cache, etc.). Returns False when missing."""
    meta_json = json.dumps(meta, ensure_ascii=False) if meta is not None else "{}"
    res = await db.execute(
        text("UPDATE support_customer_profile SET meta = :meta::jsonb WHERE id = :id"),
        {"meta": meta_json, "id": customer_id},
    )
    return res.rowcount > 0


async def get_customer_profile(
    db: AsyncSession,
    *,
    identity_key: str | None = None,
    customer_id: int | None = None,
) -> dict[str, Any] | None:
    """Fetch one profile by id or identity_key (raw row → dict)."""
    if customer_id is not None:
        row = (
            await db.execute(
                text("SELECT * FROM support_customer_profile WHERE id = :id"),
                {"id": customer_id},
            )
        ).fetchone()
    else:
        row = (
            await db.execute(
                text("SELECT * FROM support_customer_profile WHERE identity_key = :key"),
                {"key": identity_key},
            )
        ).fetchone()
    return _row_to_dict(row)
