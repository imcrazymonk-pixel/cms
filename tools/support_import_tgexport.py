#!/usr/bin/env python3
"""Import a normalized Telegram HTML export into the CMS support history.

Input is the JSON produced by ``tools/tgexport_html_parse.py``. The script
runs **inside the api container** (stdlib only) and writes real
``support_conversation`` / ``support_message`` / ``support_attachment`` rows.

Safety properties:

* dry-run is the default — it only SELECTs, copies no files and prints a plan;
* ``--apply`` is an explicit opt-in and commits one transaction per topic;
* historical rows are ``is_backfill=True``: no Outbox, no notifications, no
  unread counter, no SLA/first-response claims;
* every message is deduplicated on ``(conversation_id, external_msg_id)`` in
  *both* directions, so a repeated import writes nothing new.

Usage (inside the api container)::

    python tools/support_import_tgexport.py \
        --input _tgexport_normalized.json --media-root /tmp/tgexport --dry-run

    python tools/support_import_tgexport.py ... --apply
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import mimetypes
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("support_import_tgexport")

CHANNEL = "telegram"
DATE_FORMAT = "%d.%m.%Y %H:%M:%S GMT%z"
AGENT_AUTHOR = "agent"


class ImportDataError(ValueError):
    """Normalized JSON is malformed."""


# ── input validation ──────────────────────────────────────────────────────


def _as_str(value: Any, *, field: str) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        raise ImportDataError(f"{field} must be a string")
    return str(value)


def _normalize_media(raw: Any, *, field: str) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ImportDataError(f"{field} must be an array")
    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ImportDataError(f"{field}[{index}] must be an object")
        href = _as_str(item.get("href"), field=f"{field}[{index}].href").strip()
        if not href:
            raise ImportDataError(f"{field}[{index}].href must not be empty")
        normalized = {"href": href}
        if "width" in item:
            normalized["width"] = item.get("width")
        if "height" in item:
            normalized["height"] = item.get("height")
        items.append(normalized)
    return items


def normalize_payload(payload: Any) -> dict[str, Any]:
    """Validate/normalize the parser output; raises :class:`ImportDataError`."""
    if not isinstance(payload, dict):
        raise ImportDataError("root must be an object with a 'topics' array")
    topics_raw = payload.get("topics")
    if not isinstance(topics_raw, list):
        raise ImportDataError("'topics' must be an array")

    topics: list[dict[str, Any]] = []
    for t_index, raw_topic in enumerate(topics_raw):
        if not isinstance(raw_topic, dict):
            raise ImportDataError(f"topics[{t_index}] must be an object")
        topic_id = _as_str(raw_topic.get("topic_id"), field=f"topics[{t_index}].topic_id").strip()
        if not topic_id:
            raise ImportDataError(f"topics[{t_index}].topic_id must not be empty")

        client_id_raw = raw_topic.get("client_id")
        if client_id_raw in (None, ""):
            client_id: int | None = None
        else:
            try:
                client_id = int(client_id_raw)
            except (TypeError, ValueError) as exc:
                raise ImportDataError(
                    f"topics[{t_index}].client_id must be an integer or null"
                ) from exc

        messages_raw = raw_topic.get("messages") or []
        if not isinstance(messages_raw, list):
            raise ImportDataError(f"topics[{t_index}].messages must be an array")

        messages: list[dict[str, Any]] = []
        for m_index, raw_message in enumerate(messages_raw):
            if not isinstance(raw_message, dict):
                raise ImportDataError(
                    f"topics[{t_index}].messages[{m_index}] must be an object"
                )
            message_id = _as_str(
                raw_message.get("id"),
                field=f"topics[{t_index}].messages[{m_index}].id",
            ).strip()
            if not message_id:
                raise ImportDataError(
                    f"topics[{t_index}].messages[{m_index}].id must not be empty"
                )
            messages.append(
                {
                    "id": message_id,
                    "date": _as_str(raw_message.get("date"), field="date").strip(),
                    "from": _as_str(raw_message.get("from"), field="from").strip(),
                    "forwarded": bool(raw_message.get("forwarded")),
                    "text": _as_str(raw_message.get("text"), field="text"),
                    "photos": _normalize_media(
                        raw_message.get("photos"), field="photos"
                    ),
                    "videos": _normalize_media(
                        raw_message.get("videos"), field="videos"
                    ),
                }
            )

        topics.append(
            {
                "topic_id": topic_id,
                "title": _as_str(raw_topic.get("title"), field="title").strip(),
                "client_id": client_id,
                "messages": messages,
            }
        )
    return {"topics": topics}


def load_normalized(path: str | Path) -> dict[str, Any]:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ImportDataError(f"cannot read {path}: {exc}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ImportDataError(f"invalid JSON: {exc}") from exc
    return normalize_payload(payload)


# ── helpers ───────────────────────────────────────────────────────────────


def parse_date(value: str) -> datetime:
    """Parse ``DD.MM.YYYY HH:MM:SS GMT+03:00`` into an aware datetime."""
    return datetime.strptime(value.strip(), DATE_FORMAT)


def _external_id(topic: dict[str, Any]) -> str:
    client_id = topic.get("client_id")
    return str(client_id) if client_id else f"topic:{topic['topic_id']}"


def _row_get(row: Any, name: str) -> Any:
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return mapping.get(name)
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


async def find_conversation(db: Any, topic: dict[str, Any]) -> Any | None:
    """Match by forum topic id first, then by the client's Telegram id."""
    from sqlalchemy import text

    row = (
        await db.execute(
            text(
                "SELECT id, channel, external_id, tg_user_id, source_id "
                "FROM support_conversation "
                "WHERE channel = :channel AND source_id = :source_id "
                "ORDER BY id LIMIT 1"
            ),
            {"channel": CHANNEL, "source_id": topic["topic_id"]},
        )
    ).fetchone()
    if row is not None:
        return row

    client_id = topic.get("client_id")
    if client_id is None:
        return None
    return (
        await db.execute(
            text(
                "SELECT id, channel, external_id, tg_user_id, source_id "
                "FROM support_conversation "
                "WHERE channel = :channel AND tg_user_id = :tg_user_id "
                "ORDER BY id LIMIT 1"
            ),
            {"channel": CHANNEL, "tg_user_id": client_id},
        )
    ).fetchone()


async def message_exists_any(db: Any, conversation_id: int, external_msg_id: str) -> bool:
    """True when the transport id is already stored in either direction."""
    from sqlalchemy import text

    row = (
        await db.execute(
            text(
                "SELECT 1 FROM support_message "
                "WHERE conversation_id = :conversation_id "
                "AND external_msg_id = :external_msg_id LIMIT 1"
            ),
            {
                "conversation_id": conversation_id,
                "external_msg_id": external_msg_id,
            },
        )
    ).fetchone()
    return row is not None


def _resolve_media(media_root: Path, href: str) -> Path | None:
    rel = Path(href)
    if rel.is_absolute():
        return None
    root = media_root.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _media_items(message: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for photo in message.get("photos") or []:
        items.append(
            {
                "media_type": "photo",
                "href": photo["href"],
                "width": photo.get("width"),
                "height": photo.get("height"),
            }
        )
    for video in message.get("videos") or []:
        items.append(
            {
                "media_type": "video",
                "href": video["href"],
                "width": None,
                "height": None,
            }
        )
    return items


def _guess_mime(path: Path, media_type: str) -> str | None:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    return "image/jpeg" if media_type == "photo" else "video/mp4"


def _copy_media(
    upload_dir: Path, media_root: Path, href: str, media_type: str
) -> dict[str, Any] | None:
    """Copy one export file into the CMS upload dir; returns insert kwargs."""
    source = _resolve_media(media_root, href)
    if source is None or not source.is_file():
        return None

    digest = _sha256(source)
    extension = Path(href).suffix.lower()
    dest = upload_dir / f"exp_{digest[:16]}{extension}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(source, dest)

    return {
        "media_type": media_type,
        "file_ref": f"export:{href}",
        "local_path": str(dest),
        "bytes_count": source.stat().st_size,
        "original_name": source.name,
        "mime_type": _guess_mime(source, media_type),
        "sha256": digest,
    }


def _empty_summary() -> dict[str, int]:
    return {
        "topics": 0,
        "topics_matched": 0,
        "topics_created": 0,
        "topics_skipped": 0,
        "messages_in": 0,
        "messages_out": 0,
        "media_found": 0,
        "media_missing": 0,
        "duplicates": 0,
        "errors": 0,
    }


async def _process_topic(
    db: Any,
    topic: dict[str, Any],
    *,
    apply: bool,
    media_root: Path,
    upload_dir: Path | None,
    summary: dict[str, int],
    out: Callable[[str], None],
) -> None:
    topic_id = topic["topic_id"]
    messages = topic.get("messages") or []
    if not messages:
        summary["topics_skipped"] += 1
        out(f"skip topic {topic_id} {topic.get('title')!r}: no messages")
        return

    from web.backend.core.support.store import attachments, conversations

    row = await find_conversation(db, topic)
    conversation_id: int | None = None
    external_id = _external_id(topic)
    created_here = False

    if row is not None:
        summary["topics_matched"] += 1
        conversation_id = int(_row_get(row, "id"))
        external_id = str(_row_get(row, "external_id") or external_id)
        stored_source = _row_get(row, "source_id")
        if apply and (stored_source is None or str(stored_source) == ""):
            await conversations.fill_conversation_mapping(
                db,
                conversation_id,
                tg_user_id=topic.get("client_id"),
                source_id=topic_id,
            )
    else:
        if topic.get("client_id") is None:
            summary["topics_skipped"] += 1
            out(
                f"skip topic {topic_id} {topic.get('title')!r}: "
                "no client_id and no existing conversation"
            )
            return
        summary["topics_created"] += 1
        if apply:
            conversation_id, created_here = await conversations.upsert_conversation(
                db,
                channel=CHANNEL,
                external_id=external_id,
                tg_user_id=topic.get("client_id"),
                source_id=topic_id,
                subject=topic.get("title"),
            )
            if not created_here:
                summary["topics_matched"] += 1
                summary["topics_created"] -= 1

    if apply and conversation_id is not None and topic.get("title"):
        await conversations.set_subject(db, conversation_id, str(topic["title"]))

    in_count = out_count = dup_count = 0
    media_found = media_missing = 0
    seen_external: set[str] = set()

    for message in messages:
        external_msg_id = f"staff:{topic_id}:{message['id']}"
        if external_msg_id in seen_external:
            summary["duplicates"] += 1
            dup_count += 1
            continue
        seen_external.add(external_msg_id)

        if conversation_id is not None and await message_exists_any(
            db, conversation_id, external_msg_id
        ):
            summary["duplicates"] += 1
            dup_count += 1
            continue

        try:
            created_at = parse_date(message["date"])
        except (TypeError, ValueError):
            summary["errors"] += 1
            out(
                f"warning: topic {topic_id} message {message['id']}: "
                f"bad date {message.get('date')!r} — skipped"
            )
            continue

        items = _media_items(message)
        if not apply:
            for item in items:
                source = _resolve_media(media_root, item["href"])
                if source is not None and source.is_file():
                    summary["media_found"] += 1
                    media_found += 1
                else:
                    summary["media_missing"] += 1
                    media_missing += 1
                    out(f"warning: topic {topic_id}: media not found: {item['href']}")
            if message["forwarded"]:
                summary["messages_in"] += 1
                in_count += 1
            else:
                summary["messages_out"] += 1
                out_count += 1
            continue

        # --apply: conversation exists by now.
        assert conversation_id is not None
        message_id: int | None = None
        if message["forwarded"]:
            result = await conversations.record_inbound(
                db,
                channel=CHANNEL,
                external_id=external_id,
                text=message["text"] or None,
                external_msg_id=external_msg_id,
                tg_user_id=topic.get("client_id"),
                source_id=topic_id,
                is_backfill=True,
                created_at=created_at,
            )
            if not result.get("message_created"):
                summary["duplicates"] += 1
                dup_count += 1
                continue
            message_id = result.get("message_id")
            summary["messages_in"] += 1
            in_count += 1
        else:
            message_id = await conversations.record_outbound(
                db,
                conversation_id=conversation_id,
                text_value=message["text"],
                external_msg_id=external_msg_id,
                author=AGENT_AUTHOR,
                is_backfill=True,
                created_at=created_at,
            )
            summary["messages_out"] += 1
            out_count += 1

        for item in items:
            assert upload_dir is not None
            try:
                prepared = _copy_media(
                    upload_dir, media_root, item["href"], item["media_type"]
                )
                if prepared is None:
                    summary["media_missing"] += 1
                    media_missing += 1
                    out(f"warning: topic {topic_id}: media not found: {item['href']}")
                    continue
                if message_id is None:
                    continue
                prepared["width"] = item.get("width")
                prepared["height"] = item.get("height")
                await attachments.insert_attachment(
                    db, message_id=message_id, **prepared
                )
            except Exception as exc:  # noqa: BLE001 — media must not lose the message
                summary["errors"] += 1
                out(
                    f"warning: topic {topic_id}: media failed {item['href']}: "
                    f"{type(exc).__name__}: {exc}"
                )
                continue
            summary["media_found"] += 1
            media_found += 1

    if apply and created_here and conversation_id is not None:
        await conversations.set_status(db, conversation_id, "closed")

    out(
        f"topic {topic_id} {topic.get('title')!r}: "
        f"messages in={in_count} out={out_count} dup={dup_count} "
        f"media found={media_found} missing={media_missing}"
    )


def _default_session_factory() -> Callable[[], Any]:
    from web.backend.core.support.store import open_session

    return open_session


async def run_import(
    payload: dict[str, Any],
    *,
    apply: bool = False,
    media_root: str | Path = "/tmp/tgexport",
    upload_dir: str | Path | None = None,
    session_factory: Callable[[], Any] | None = None,
    out: Callable[[str], None] = print,
) -> dict[str, int]:
    """Process the normalized payload. One transaction per topic in apply mode."""
    normalized = normalize_payload(payload)
    topics = normalized["topics"]
    summary = _empty_summary()
    summary["topics"] = len(topics)

    factory = session_factory or _default_session_factory()
    media_path = Path(media_root)
    resolved_upload: Path | None = None
    if apply:
        if upload_dir is not None:
            resolved_upload = Path(upload_dir)
        else:
            from web.backend.core.config import get_cms_settings

            resolved_upload = Path(get_cms_settings().upload_dir) / "support"

    for topic in topics:
        try:
            if apply:
                async with factory() as db:
                    await _process_topic(
                        db,
                        topic,
                        apply=True,
                        media_root=media_path,
                        upload_dir=resolved_upload,
                        summary=summary,
                        out=out,
                    )
            else:
                async with factory() as db:
                    await _process_topic(
                        db,
                        topic,
                        apply=False,
                        media_root=media_path,
                        upload_dir=None,
                        summary=summary,
                        out=out,
                    )
        except Exception as exc:  # noqa: BLE001 — one topic must not abort the rest
            summary["errors"] += 1
            out(
                f"error topic {topic.get('topic_id')}: "
                f"{type(exc).__name__}: {exc}"
            )

    return summary


def _report(summary: dict[str, int], *, mode: str, out: Callable[[str], None]) -> None:
    out(
        f"{mode}: topics={summary['topics']} matched={summary['topics_matched']} "
        f"created={summary['topics_created']} skipped={summary['topics_skipped']}"
    )
    out(
        f"messages: in={summary['messages_in']} out={summary['messages_out']} "
        f"duplicates={summary['duplicates']}"
    )
    out(
        f"media: found={summary['media_found']} missing={summary['media_missing']} "
        f"errors={summary['errors']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import a normalized Telegram HTML export into the CMS support "
            "history. Dry-run is the default; --apply writes."
        )
    )
    parser.add_argument("--input", required=True, help="normalized JSON from tgexport_html_parse.py")
    parser.add_argument(
        "--media-root",
        default="/tmp/tgexport",
        help="directory the export hrefs are relative to (default: /tmp/tgexport)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="only print the plan (default when neither flag is given)",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="write conversations, messages and attachments (explicit opt-in)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = load_normalized(args.input)
    except ImportDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    mode = "apply" if args.apply else "dry-run"
    print(f"{mode}: {len(payload['topics'])} topic(s) from {args.input}")

    try:
        summary = asyncio.run(
            run_import(
                payload,
                apply=bool(args.apply),
                media_root=args.media_root,
            )
        )
    except Exception as exc:  # noqa: BLE001 — fatal setup failure
        print(f"fatal: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    _report(summary, mode=mode, out=print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
