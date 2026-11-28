"""Удаление служебных уведомлений ботов из импортированной истории.

Импорт HTML-экспорта захватил сообщения Bedolaga/NaloGO/YooKassa (чеки,
продления, промогруппы, техработы). Скрипт удаляет только строки с
``is_backfill=True`` и явными маркерами ботов, поэтому живые сообщения и
ответы операторов не затрагиваются.

    python tools/support_cleanup_service_msgs.py            # dry-run
    python tools/support_cleanup_service_msgs.py --apply    # удалить
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

SERVICE_BOT_MARKERS: tuple[str, ...] = (
    "Новый чек",
    "ПРОДЛЕНИЕ ПОДПИСКИ",
    "ДОКУПКА УСТРОЙСТВ",
    "КОНВЕРСИЯ ИЗ ТРИАЛА",
    "АКТИВАЦИЯ ТРИАЛА",
    "АВТОМАТИЧЕСКАЯ СМЕНА ПРОМОГРУППЫ",
    "Remnawave Bedolaga Bot",
    "NaloGO",
    "YooKassa",
    "ТЕХНИЧЕСКИЕ РАБОТЫ",
    "СИСТЕМА БЕКАПОВ",
    "Ошибка во время работы",
    "Доступно обновление",
    "Бот успешно запущен",
    "Автоматическое назначение",
    "Очередь чеков",
    "Проблема с отправкой чеков",
    "VPN не работает? Пожалуйста",
)


def is_service_bot_text(text: str | None) -> bool:
    """True для шаблонов сервисных ботов (не для слов клиента)."""
    payload = (text or "").casefold()
    return any(marker.casefold() in payload for marker in SERVICE_BOT_MARKERS)


async def _run(apply: bool) -> int:
    from sqlalchemy import text
    from web.backend.core.database import get_session_factory

    patterns = [f"%{marker}%" for marker in SERVICE_BOT_MARKERS]
    factory = await get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                text("""
                    select id, conversation_id, external_msg_id
                      from support_message
                     where is_backfill
                       and text is not null
                       and text ilike any(cast(:patterns as text[]))
                """),
                {"patterns": patterns},
            )
        ).fetchall()
        message_ids = [int(r.id) for r in rows]
        conversation_ids = sorted({int(r.conversation_id) for r in rows})

        attachments = []
        if message_ids:
            attachments = (
                await session.execute(
                    text("""
                        select id, local_path
                          from support_attachment
                         where message_id = any(cast(:ids as bigint[]))
                    """),
                    {"ids": message_ids},
                )
            ).fetchall()

        print(f"service messages: {len(message_ids)}")
        print(f"conversations affected: {len(conversation_ids)}")
        print(f"attachments: {len(attachments)}")
        if not apply or not message_ids:
            print("dry-run: nothing written")
            return 0

        upload_root = Path(
            os.getenv("UPLOAD_DIR", "/var/www/html/public/uploads")
        ).resolve() / "support"
        paths = [
            Path(str(r.local_path))
            for r in attachments
            if r.local_path and Path(str(r.local_path)).is_file()
        ]

        await session.execute(
            text("delete from support_message where id = any(cast(:ids as bigint[]))"),
            {"ids": message_ids},
        )
        await session.execute(
            text("""
                update support_conversation c
                   set last_message_at = (
                       select max(m.created_at) from support_message m
                        where m.conversation_id = c.id
                   )
                 where c.id = any(cast(:ids as bigint[]))
            """),
            {"ids": conversation_ids},
        )
        await session.commit()

        removed = 0
        for path in paths:
            try:
                if path.resolve().is_relative_to(upload_root):
                    path.unlink(missing_ok=True)
                    removed += 1
            except OSError:
                pass
        print(f"deleted: messages={len(message_ids)} files={removed}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="delete; default dry-run")
    args = parser.parse_args()
    return asyncio.run(_run(args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
