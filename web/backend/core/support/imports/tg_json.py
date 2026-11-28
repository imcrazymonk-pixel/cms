"""Telegram Desktop ``result.json`` parser (plan §7.3).

Root shape::

    {"messages": [ {"id": 1, "type": "message", "date": "...",
                    "from": "Иван", "from_id": "user1",
                    "reply_to_message_id": 0,
                    "text": "..." | [{"type": "link", "text": "..."}] } ] }

Rules:

* ``type != "message"`` is skipped (service events, joins, pins…);
* ``text`` may be a string or an array of strings/objects; chunks are
  concatenated in order into a flat string;
* pairing prefers ``reply_to_message_id`` (the replied message is the
  question); remaining messages are paired by alternating the two
  participants (``from_id``/``from``);
* ``date`` is an ISO string (``date_unixtime`` is the fallback) and is parsed
  for stable ordering;
* malformed JSON raises :class:`ImportParseError` with line/column/offset.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from web.backend.core.support.imports.errors import ImportParseError, ImportTooLarge
from web.backend.core.support.imports.tg_text import (
    DEFAULT_OPERATOR_NAMES,
    decode_bytes,
    is_operator_name,
)

MAX_JSON_BYTES = 50 * 1024 * 1024
MAX_MESSAGES = 200_000


def check_json_size(payload: str | bytes | dict[str, Any] | list[Any]) -> None:
    """Reject a ``result.json`` larger than 50 MiB before parsing."""
    if isinstance(payload, (bytes, bytearray)):
        size = len(payload)
    elif isinstance(payload, str):
        size = len(payload.encode("utf-8"))
    else:
        size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if size > MAX_JSON_BYTES:
        raise ImportTooLarge(
            f"result.json is {size} bytes; the limit is {MAX_JSON_BYTES} bytes (50 MiB)"
        )


def _flatten_text(value: Any) -> str:
    """String or Telegram array of strings/``{type, text}`` objects → flat text."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for chunk in value:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict):
                chunk_text = chunk.get("text")
                if isinstance(chunk_text, str):
                    parts.append(chunk_text)
        return "".join(parts)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def _parse_date(item: dict[str, Any]) -> datetime | None:
    raw = item.get("date")
    if isinstance(raw, str) and raw.strip():
        candidate = raw.strip()
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    raw_ts = item.get("date_unixtime")
    if raw_ts is not None:
        try:
            return datetime.fromtimestamp(float(raw_ts), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None
    return None


def _load_root(payload: str | bytes | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    raw = decode_bytes(payload) if isinstance(payload, (bytes, bytearray)) else str(payload)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ImportParseError(
            f"invalid JSON at line {exc.lineno} column {exc.colno} "
            f"(char {exc.pos}): {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise ImportParseError("result.json root must be an object with a messages[] array")
    return data


def parse_json(
    payload: str | bytes | dict[str, Any],
    operator_names: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Parse ``result.json`` into the same message dicts as the text parser."""
    check_json_size(payload)
    data = _load_root(payload)
    raw_messages = data.get("messages")
    if not isinstance(raw_messages, list):
        raise ImportParseError("result.json has no messages[] array")

    matcher = tuple(
        str(name).strip().casefold()
        for name in (operator_names or DEFAULT_OPERATOR_NAMES)
        if str(name).strip()
    )

    messages: list[dict[str, Any]] = []
    for index, item in enumerate(raw_messages):
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            # Service events, joined/left, pinned messages, calls.
            continue
        author = str(item.get("from") or item.get("from_name") or "").strip()
        from_id = item.get("from_id")
        from_key = str(from_id) if from_id not in (None, "") else author
        if not author and not from_key:
            # Service-like message with no author — nothing to learn from.
            continue
        text = _flatten_text(item.get("text")).strip()
        if not text:
            continue
        reply_raw = item.get("reply_to_message_id")
        try:
            reply_to = int(reply_raw) if reply_raw not in (None, "") else None
        except (TypeError, ValueError):
            reply_to = None
        msg_id_raw = item.get("id")
        try:
            msg_id = int(msg_id_raw) if msg_id_raw not in (None, "") else None
        except (TypeError, ValueError):
            msg_id = None
        messages.append(
            {
                "msg_id": msg_id,
                "from_id": from_key,
                "author": author,
                "text": text,
                "date": _parse_date(item),
                "reply_to": reply_to,
                "is_operator": is_operator_name(author, matcher),
                "_index": index,
            }
        )

    if len(messages) > MAX_MESSAGES:
        raise ImportTooLarge(f"chat contains more than {MAX_MESSAGES} messages")

    messages.sort(
        key=lambda m: (
            1 if m["date"] is None else 0,
            m["date"] or datetime.min.replace(tzinfo=timezone.utc),
            m["_index"],
        )
    )
    return messages


def _participants(messages: Sequence[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for message in messages:
        key = message.get("from_id")
        if key and key not in seen:
            seen.append(key)
    return seen


def _roles(
    messages: Sequence[dict[str, Any]],
) -> tuple[str | None, str | None]:
    """Return ``(client_key, operator_key)``; ``None`` when undecidable."""
    participants = _participants(messages)
    operators = [m["from_id"] for m in messages if m.get("is_operator")]
    if operators:
        operator = operators[0]
        client = next((key for key in participants if key != operator), None)
        return client, operator
    if len(participants) >= 2:
        # No configured name matched: first writer is the client, the other
        # participant answers.
        return participants[0], participants[1]
    return None, None


def build_pairs(messages: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reply-to first, alternating two participants second."""
    if not messages:
        return []

    client_key, operator_key = _roles(messages)
    by_id = {m["msg_id"]: m for m in messages if m.get("msg_id") is not None}
    pairs: list[dict[str, Any]] = []
    used: set[int] = set()

    # 1) Explicit replies: the replied message is the question.
    for message in messages:
        reply_to = message.get("reply_to")
        if reply_to is None:
            continue
        target = by_id.get(reply_to)
        if target is None or not target.get("text"):
            continue
        if target.get("from_id") == message.get("from_id"):
            continue
        question, answer = target, message
        if message.get("is_operator") and not target.get("is_operator"):
            question, answer = target, message
        elif target.get("is_operator") and not message.get("is_operator"):
            question, answer = message, target
        pairs.append(
            {
                "question": str(question["text"]).strip(),
                "answer": str(answer["text"]).strip(),
                "messages": 2,
            }
        )
        if target.get("msg_id") is not None:
            used.add(int(target["msg_id"]))
        if message.get("msg_id") is not None:
            used.add(int(message["msg_id"]))

    # 2) Alternation between the two participants, for messages not covered
    #    by an explicit reply.
    if client_key is None or operator_key is None:
        return [pair for pair in pairs if pair["question"] and pair["answer"]]

    blocks: list[dict[str, Any]] = []
    for message in messages:
        if message.get("msg_id") is not None and int(message["msg_id"]) in used:
            blocks.append({"role": None, "messages": []})
            continue
        key = message.get("from_id")
        if key == operator_key:
            role = "operator"
        elif key == client_key:
            role = "client"
        else:
            role = None
        if role is None:
            blocks.append({"role": None, "messages": []})
            continue
        if blocks and blocks[-1]["role"] == role:
            blocks[-1]["messages"].append(message)
        else:
            blocks.append({"role": role, "messages": [message]})

    for left, right in zip(blocks, blocks[1:]):
        if left["role"] != "client" or right["role"] != "operator":
            continue
        question = "\n".join(
            str(item.get("text") or "").strip()
            for item in left["messages"][:3]
            if str(item.get("text") or "").strip()
        ).strip()
        answer = "\n".join(
            str(item.get("text") or "").strip()
            for item in right["messages"][:3]
            if str(item.get("text") or "").strip()
        ).strip()
        if not question or not answer:
            continue
        pairs.append(
            {
                "question": question,
                "answer": answer,
                "messages": min(len(left["messages"]), 3) + min(len(right["messages"]), 3),
            }
        )

    return [pair for pair in pairs if pair["question"] and pair["answer"]]


def parse_pairs(
    payload: str | bytes | dict[str, Any],
    operator_names: Iterable[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convenience: ``(messages, pairs)`` in one call."""
    messages = parse_json(payload, operator_names)
    return messages, build_pairs(messages)
