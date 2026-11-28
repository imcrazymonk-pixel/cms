"""Telegram Desktop plain-text export parser (plan §7.2).

Supported line format::

    [28.11.2026 12:34:56] Поддержка HexaVeil: Здравствуйте!
    [28.11.26 12:35] Иван: Не подключается Германия
    продолжение предыдущего сообщения без заголовка

Rules:

* header regex is exactly the one from the plan — two date formats
  (``DD.MM.YYYY`` and ``DD.MM.YY``), optional seconds;
* lines without a header are continuations of the previous message;
* the operator is recognized from ``operator_names`` (case-insensitive,
  substring match so decorated names like «Поддержка HexaVeil ✅» still work);
* consecutive client → operator blocks produce a pair, at most three messages
  from each side are merged into one block;
* decoding is ``utf-8-sig`` first, then ``cp1251`` (old Windows clients);
* no headers at all → :class:`ImportParseError`.

Everything here is pure and synchronous: the runner calls it inside
``asyncio.to_thread``.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable, Sequence

from web.backend.core.support.imports.errors import ImportParseError, ImportTooLarge

DEFAULT_OPERATOR_NAMES: tuple[str, ...] = (
    "Поддержка HexaVeil",
    "Поддержка",
    "Support",
    "HexaVeil",
    "Администратор",
)

HEADER_RE = re.compile(
    r"^\[(\d{1,2})\.(\d{1,2})\.(\d{2,4})[ ,]+"
    r"(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s*([^:\n]{1,80}):\s?(.*)$"
)

MAX_TEXT_BYTES = 20 * 1024 * 1024
MAX_MESSAGES = 200_000
MAX_SIDE_MESSAGES = 3


def decode_bytes(data: bytes) -> str:
    """``utf-8-sig`` → ``cp1251`` → :class:`ImportParseError`."""
    if not isinstance(data, (bytes, bytearray)):
        raise ImportParseError("expected bytes to decode")
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return bytes(data).decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportParseError(
        "cannot decode the file as UTF-8 or Windows-1251; re-export the chat as UTF-8"
    )


def check_text_size(text: str | bytes) -> None:
    """Reject a text paste larger than 20 MiB before parsing."""
    size = len(text.encode("utf-8")) if isinstance(text, str) else len(text)
    if size > MAX_TEXT_BYTES:
        raise ImportTooLarge(
            f"text is {size} bytes; the limit is {MAX_TEXT_BYTES} bytes (20 MiB)"
        )


def _normalize_year(raw: str) -> int:
    year = int(raw)
    if len(raw) <= 2:
        year += 2000
    return year


def _build_timestamp(
    day: str, month: str, year: str, hour: str, minute: str, second: str | None
) -> datetime:
    return datetime(
        _normalize_year(year),
        int(month),
        int(day),
        int(hour),
        int(minute),
        int(second or 0),
    )


def _operator_matcher(operator_names: Iterable[str] | None) -> tuple[str, ...]:
    names = tuple(
        str(name).strip().casefold()
        for name in (operator_names or DEFAULT_OPERATOR_NAMES)
        if str(name).strip()
    )
    return names or tuple(name.casefold() for name in DEFAULT_OPERATOR_NAMES)


def is_operator_name(author: str, matcher: Sequence[str]) -> bool:
    """Case-insensitive substring match against configured operator names."""
    value = str(author or "").strip().casefold()
    if not value:
        return False
    return any(name in value for name in matcher)


def parse_text(
    text: str | bytes,
    operator_names: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Parse a text export into messages with continuation lines merged.

    Each message is ``{date, timestamp, author, text, is_operator}``.
    Raises :class:`ImportParseError` when the input has no recognizable header
    or contains more than 200 000 messages.
    """
    raw = decode_bytes(text) if isinstance(text, (bytes, bytearray)) else str(text or "")
    check_text_size(raw)

    matcher = _operator_matcher(operator_names)
    messages: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    headers = 0

    for raw_line in raw.splitlines():
        line = raw_line.rstrip("\r")
        match = HEADER_RE.match(line)
        if match:
            headers += 1
            day, month, year, hour, minute, second, author, body = match.groups()
            current = {
                "date": f"{day.zfill(2)}.{month.zfill(2)}.{year} "
                        f"{hour.zfill(2)}:{minute}:{second or '00'}",
                "timestamp": _build_timestamp(day, month, year, hour, minute, second),
                "author": author.strip(),
                "text": body.strip(),
                "is_operator": is_operator_name(author, matcher),
            }
            messages.append(current)
            if len(messages) > MAX_MESSAGES:
                raise ImportTooLarge(
                    f"chat contains more than {MAX_MESSAGES} messages"
                )
            continue

        stripped = line.strip()
        if not stripped:
            # Blank separator between messages — never a continuation.
            continue
        if current is not None:
            current["text"] = f"{current['text']}\n{stripped}".strip()

    if headers == 0:
        raise ImportParseError(
            "no message headers found; expected lines like "
            "[28.11.2026 12:34:56] Operator: text"
        )

    return [message for message in messages if str(message.get("text") or "").strip()]


def build_pairs(
    messages: Sequence[dict[str, Any]],
    *,
    max_side: int = MAX_SIDE_MESSAGES,
) -> list[dict[str, Any]]:
    """Merge consecutive same-sender blocks and pair client → operator.

    Only blocks immediately followed by an operator block become a pair; an
    operator greeting before the first client message is ignored.
    """
    if max_side < 1:
        max_side = 1

    blocks: list[dict[str, Any]] = []
    for message in messages:
        operator = bool(message.get("is_operator"))
        if blocks and blocks[-1]["is_operator"] == operator:
            blocks[-1]["messages"].append(message)
        else:
            blocks.append({"is_operator": operator, "messages": [message]})

    pairs: list[dict[str, Any]] = []
    for left, right in zip(blocks, blocks[1:]):
        if left["is_operator"] or not right["is_operator"]:
            continue
        question = "\n".join(
            str(item.get("text") or "").strip()
            for item in left["messages"][:max_side]
            if str(item.get("text") or "").strip()
        ).strip()
        answer = "\n".join(
            str(item.get("text") or "").strip()
            for item in right["messages"][:max_side]
            if str(item.get("text") or "").strip()
        ).strip()
        if not question or not answer:
            continue
        pairs.append(
            {
                "question": question,
                "answer": answer,
                "messages": len(left["messages"][:max_side])
                + len(right["messages"][:max_side]),
            }
        )
    return pairs


def parse_pairs(
    text: str | bytes,
    operator_names: Iterable[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convenience: ``(messages, pairs)`` in one call."""
    messages = parse_text(text, operator_names)
    return messages, build_pairs(messages)
