"""``support_template`` — шаблоны ответов оператора (Этап C, C1).

Стиль ``store/*``: ``AsyncSession`` на входе, коммита нет — транзакцией
владеет фасад ``SupportStore``. SQL-идентификаторы — контролируемые
константы, все значения — bind-параметры.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

_COLUMNS = (
    "id, shortcut, title, body, category, uses, created_by, created_at, updated_at"
)
_MAX_LIMIT = 100
_EDITABLE_FIELDS = ("shortcut", "title", "body", "category")


class TemplateError(Exception):
    """Базовая ошибка store шаблонов."""


class TemplateExists(TemplateError):
    """Шаблон с таким ``shortcut`` уже существует."""

    def __init__(self, shortcut: str):
        self.shortcut = shortcut
        super().__init__(f"template {shortcut!r} already exists")


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row._mapping)


def _clean_required(value: Any, field: str, *, max_len: int) -> str:
    text_value = str(value or "").strip()
    if not text_value:
        raise ValueError(f"{field} must not be empty")
    if len(text_value) > max_len:
        raise ValueError(f"{field} is too long")
    return text_value


def _clean_category(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


async def list_templates(
    db: AsyncSession,
    q: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Список шаблонов с поиском и пагинацией: ``{items, total}``."""
    where: list[str] = []
    params: dict[str, Any] = {}
    if q:
        where.append("(shortcut ILIKE :q OR title ILIKE :q OR body ILIKE :q)")
        params["q"] = f"%{q}%"
    if category:
        where.append("category = :category")
        params["category"] = category

    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    total_row = (
        await db.execute(
            sql_text(f"SELECT COUNT(*) FROM support_template{where_sql}"), params
        )
    ).fetchone()
    total = int(total_row[0]) if total_row is not None else 0

    limit = min(max(int(limit), 1), _MAX_LIMIT)
    offset = max(int(offset), 0)
    rows = (
        await db.execute(
            sql_text(
                f"SELECT {_COLUMNS} FROM support_template{where_sql} "
                "ORDER BY updated_at DESC, id DESC LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": limit, "offset": offset},
        )
    ).fetchall()
    return {"items": [_row_to_dict(row) for row in rows], "total": total}


async def get_template(db: AsyncSession, template_id: int) -> dict[str, Any] | None:
    """Один шаблон по id или ``None``."""
    row = (
        await db.execute(
            sql_text(f"SELECT {_COLUMNS} FROM support_template WHERE id = :id"),
            {"id": int(template_id)},
        )
    ).fetchone()
    return _row_to_dict(row)


async def create_template(
    db: AsyncSession,
    *,
    shortcut: str,
    title: str,
    body: str,
    category: str | None = None,
    created_by: int | None = None,
) -> dict[str, Any]:
    """Создать шаблон; дубль ``shortcut`` → :class:`TemplateExists`."""
    clean_shortcut = _clean_required(shortcut, "shortcut", max_len=32)
    clean_title = _clean_required(title, "title", max_len=120)
    clean_body = _clean_required(body, "body", max_len=4000)
    try:
        row = (
            await db.execute(
                sql_text(
                    f"""
                    INSERT INTO support_template
                        (shortcut, title, body, category, created_by, updated_at)
                    VALUES
                        (:shortcut, :title, :body, :category, :created_by, now())
                    RETURNING {_COLUMNS}
                    """
                ),
                {
                    "shortcut": clean_shortcut,
                    "title": clean_title,
                    "body": clean_body,
                    "category": _clean_category(category),
                    "created_by": int(created_by) if created_by is not None else None,
                },
            )
        ).fetchone()
    except IntegrityError as exc:
        raise TemplateExists(clean_shortcut) from exc
    return _row_to_dict(row) or {}


async def update_template(
    db: AsyncSession, template_id: int, **fields: Any
) -> dict[str, Any] | None:
    """Обновить переданные поля; ``None`` — шаблона нет."""
    assignments = ["updated_at = now()"]
    params: dict[str, Any] = {"id": int(template_id)}
    for key in _EDITABLE_FIELDS:
        if key not in fields:
            continue
        value = fields[key]
        if key == "shortcut":
            value = _clean_required(value, "shortcut", max_len=32)
        elif key == "title":
            value = _clean_required(value, "title", max_len=120)
        elif key == "body":
            value = _clean_required(value, "body", max_len=4000)
        else:
            value = _clean_category(value)
        params[key] = value
        assignments.append(f"{key} = :{key}")

    try:
        row = (
            await db.execute(
                sql_text(
                    f"UPDATE support_template SET {', '.join(assignments)} "
                    f"WHERE id = :id RETURNING {_COLUMNS}"
                ),
                params,
            )
        ).fetchone()
    except IntegrityError as exc:
        raise TemplateExists(str(params.get("shortcut") or "")) from exc
    return _row_to_dict(row)


async def delete_template(db: AsyncSession, template_id: int) -> bool:
    """Удалить шаблон; ``False`` — строки не было."""
    result = await db.execute(
        sql_text("DELETE FROM support_template WHERE id = :id"),
        {"id": int(template_id)},
    )
    return result.rowcount > 0


async def bump_template_use(db: AsyncSession, template_id: int) -> dict[str, Any] | None:
    """``uses = uses + 1`` без изменения ``updated_at``; ``None`` — нет шаблона."""
    row = (
        await db.execute(
            sql_text(
                "UPDATE support_template SET uses = uses + 1 "
                "WHERE id = :id RETURNING id, uses"
            ),
            {"id": int(template_id)},
        )
    ).fetchone()
    return _row_to_dict(row)
