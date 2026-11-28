#!/usr/bin/env python3
"""Mapping-only import of the legacy support bot history.

Reads ``topics.json`` (``{"topics": [{"userId": ..., "topicId": ...}]}``) and
creates/patches ``support_conversation`` rows so old Telegram dialogs keep
their staff-forum topic mapping. Nothing else is written: no message bodies,
no Outbox calls, no messages to clients.

Dry-run is the default; pass ``--apply`` to write.

Usage (from the repository root)::

    python tools/support_import_history.py --help
    python tools/support_import_history.py --topics /opt/support-bot/data/topics.json
    python tools/support_import_history.py --topics ... --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable, Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_TOPICS_PATH = "/opt/support-bot/data/topics.json"
CHANNEL = "telegram"


class TopicsError(ValueError):
    """Malformed or unreadable ``topics.json``."""


def parse_topics(raw: str) -> list[dict[str, Any]]:
    """Parse the raw JSON text into ``[{"userId": int, "topicId": str}]``.

    The whole file is rejected when any entry is malformed — a partial import
    would leave an inconsistent mapping.
    """
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TopicsError(f"invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise TopicsError("root must be an object with a 'topics' array")
    topics = payload.get("topics")
    if not isinstance(topics, list):
        raise TopicsError("'topics' must be an array")

    pairs: list[dict[str, Any]] = []
    for index, item in enumerate(topics):
        if not isinstance(item, dict):
            raise TopicsError(f"topics[{index}] must be an object")
        if "userId" not in item or "topicId" not in item:
            raise TopicsError(f"topics[{index}] needs userId and topicId")

        user_raw = item["userId"]
        try:
            user_id = int(user_raw)
        except (TypeError, ValueError) as exc:
            raise TopicsError(f"topics[{index}].userId must be an integer") from exc

        topic_raw = item["topicId"]
        if isinstance(topic_raw, bool) or not isinstance(topic_raw, (str, int)):
            raise TopicsError(f"topics[{index}].topicId must be a string or integer")
        topic_id = str(topic_raw).strip()
        if not topic_id:
            raise TopicsError(f"topics[{index}].topicId must not be empty")

        pairs.append({"userId": user_id, "topicId": topic_id})
    return pairs


def load_topics(path: str | Path) -> list[dict[str, Any]]:
    """Read and parse ``topics.json`` from disk."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise TopicsError(f"cannot read {path}: {exc}") from exc
    return parse_topics(raw)


class _AsyncSession(Protocol):
    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any: ...


SessionFactory = Callable[[], Any]


def _default_session_factory() -> SessionFactory:
    from web.backend.core.support.store import open_session

    return open_session


def _row_get(row: Any, name: str) -> Any:
    """Read a column from a SQLAlchemy Row or a plain mapping (test doubles)."""
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return mapping.get(name)
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


async def classify_pair(db: _AsyncSession, pair: dict[str, Any]) -> tuple[str, int | None]:
    """Return ``(create|exists|conflict, conversation_id)`` for one pair.

    ``conflict`` means the stored mapping is already non-empty and differs —
    the import never overwrites a value written by a live channel.
    """
    from sqlalchemy import text

    row = (
        await db.execute(
            text(
                "SELECT id, source_id, tg_user_id FROM support_conversation "
                "WHERE channel = :channel AND external_id = :external_id"
            ),
            {"channel": CHANNEL, "external_id": str(pair["userId"])},
        )
    ).fetchone()
    if row is None:
        return "create", None

    conversation_id = int(_row_get(row, "id"))
    stored_topic = _row_get(row, "source_id")
    stored_user = _row_get(row, "tg_user_id")
    if stored_topic is not None and str(stored_topic) != pair["topicId"]:
        return "conflict", conversation_id
    if stored_user is not None and int(stored_user) != pair["userId"]:
        return "conflict", conversation_id
    return "exists", conversation_id


async def apply_pair(db: _AsyncSession, pair: dict[str, Any]) -> str:
    """Write one mapping pair inside the caller's transaction."""
    from web.backend.core.support.store import conversations

    status, conversation_id = await classify_pair(db, pair)
    if status == "conflict":
        return "conflict"

    if status == "exists" and conversation_id is not None:
        await conversations.fill_conversation_mapping(
            db,
            conversation_id,
            tg_user_id=pair["userId"],
            source_id=pair["topicId"],
        )
        return "exists"

    conversation_id, created = await conversations.upsert_conversation(
        db,
        channel=CHANNEL,
        external_id=str(pair["userId"]),
        tg_user_id=pair["userId"],
        source_id=pair["topicId"],
        subject=f"Telegram {pair['userId']}",
    )
    if created:
        await conversations.set_status(db, conversation_id, "closed")
        return "create"

    # Lost a race with the live poller between SELECT and INSERT: never force
    # a status change, only fill what is still NULL.
    status, _ = await classify_pair(db, pair)
    if status == "conflict":
        return "conflict"
    await conversations.fill_conversation_mapping(
        db,
        conversation_id,
        tg_user_id=pair["userId"],
        source_id=pair["topicId"],
    )
    return "exists"


async def run_import(
    pairs: list[dict[str, Any]],
    *,
    apply: bool = False,
    session_factory: SessionFactory | None = None,
    out: Callable[[str], None] = print,
) -> dict[str, int]:
    """Process pairs, one transaction per dialog. Returns the summary counters."""
    factory = session_factory or _default_session_factory()
    summary = {"total": len(pairs), "create": 0, "exists": 0, "conflict": 0, "errors": 0}
    seen_users: dict[int, str] = {}

    for pair in pairs:
        user_id = pair["userId"]
        topic_id = pair["topicId"]
        if user_id in seen_users:
            summary["conflict"] += 1
            out(f"conflict userId={user_id} topicId={topic_id} (duplicate in file)")
            continue
        seen_users[user_id] = topic_id

        try:
            if apply:
                async with factory() as db:
                    status = await apply_pair(db, pair)
            else:
                async with factory() as db:
                    status, _ = await classify_pair(db, pair)
        except Exception as exc:  # noqa: BLE001 — one bad row must not abort the rest
            summary["errors"] += 1
            out(f"error userId={user_id} topicId={topic_id}: {type(exc).__name__}: {exc}")
            continue

        summary[status] += 1
        out(f"{status} userId={user_id} topicId={topic_id}")

    out(
        "summary: total={total} create={create} exists={exists} "
        "conflict={conflict} errors={errors}".format(**summary)
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Mapping-only import of legacy support topics.json into "
            "support_conversation. Dry-run by default; no message bodies, "
            "no outbound messages."
        )
    )
    parser.add_argument(
        "--topics",
        default=DEFAULT_TOPICS_PATH,
        help=f"path to topics.json (default: {DEFAULT_TOPICS_PATH})",
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
        help="write the mapping (explicit opt-in)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="process at most N pairs",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be a positive integer")

    try:
        pairs = load_topics(args.topics)
    except TopicsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.limit is not None:
        pairs = pairs[: args.limit]

    mode = "apply" if args.apply else "dry-run"
    print(f"{mode}: {len(pairs)} pair(s) from {args.topics}")

    summary = asyncio.run(run_import(pairs, apply=bool(args.apply)))
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
