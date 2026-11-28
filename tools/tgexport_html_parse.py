#!/usr/bin/env python3
"""Local parser for a Telegram Desktop **HTML** chat export.

This is a developer tool, not part of the API runtime: it may use the already
installed ``beautifulsoup4`` and must not be added to the server requirements.

The export is a staff forum ("Поддержка HexaVeil") split into pages::

    ChatExport_2026-11-28/
        messages.html
        messages2.html
        messages3.html
        photos/*
        video_files/*

Rules implemented here (see the task description):

* ``div.message.service`` with ``created topic «…»`` starts a topic; the block
  id (``message<topicId>``) is the forum topic id;
* a client message lives inside ``div.forwarded.body``; an operator message is
  a plain ``div.from_name`` without that wrapper;
* the bot's ``🆕 Новое обращение`` message carries the client's Telegram id in
  ``a[href^="tel:"]`` and is not written to the history itself;
* ``div.reply_to a[href="#go_to_message<id>"]`` points at the topic service
  message and restores the current topic across page boundaries.

Output shape::

    {"topics": [{"topic_id": "36", "title": "…", "client_id": 1211524569,
                 "messages": [{"id": "38", "date": "27.07.2026 12:31:01 GMT+03:00",
                               "from": "…", "forwarded": true, "text": "…",
                               "photos": [{"href": "photos/…jpg",
                                           "width": 120, "height": 260}],
                               "videos": [{"href": "video_files/…mp4"}]}]}]}

Usage::

    python tools/tgexport_html_parse.py --dir ChatExport_2026-11-28 \
        --out _tgexport_normalized.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

PAGE_NAMES = ("messages.html", "messages2.html", "messages3.html")

# Display names that write informational/system messages, not support replies.
BOT_NAMES = frozenset({"Поддержка HexaVeil", "HexaVeil VPN", "Get My ID"})
BOT_INFO_MARKER = "Новое обращение"

_TOPIC_RE = re.compile(r"created topic\s*[«\"](.+?)[»\"]\s*$", re.S)
_TEL_RE = re.compile(r"tel:(\d+)")
_ID_TEXT_RE = re.compile(r"\bID:\s*(\d{5,})")
_GO_TO_RE = re.compile(r"#go_to_message(-?\d+)")
_DATE_SUFFIX_RE = re.compile(r"\s+\d{1,2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*$")
_SIZE_RE = re.compile(r"(width|height)\s*:\s*(\d+)px", re.I)


class TgexportParseError(ValueError):
    """The export directory is missing or unreadable."""


def _decode_html(raw: bytes) -> str:
    """Export files are UTF-8; fall back to cp1251 for broken copies."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1251")


def _read_page(path: Path) -> BeautifulSoup:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise TgexportParseError(f"cannot read {path}: {exc}") from exc
    return BeautifulSoup(_decode_html(raw), "html.parser")


def _message_id(block: Tag) -> str:
    raw = str(block.get("id") or "")
    return raw[len("message") :] if raw.startswith("message") else ""


def _topic_title(text: str) -> str:
    match = _TOPIC_RE.search(text)
    if match:
        return match.group(1).strip()
    # Fallback: everything after the marker, without wrapping quotes.
    tail = text.split("created topic", 1)[-1].strip()
    return tail.strip("«»\"' ")


def _clean_name(element: Tag | None) -> str:
    if element is None:
        return ""
    name = element.get_text(" ", strip=True)
    # Forwarded from_name embeds "<span class=date>…</span>" — drop it.
    return _DATE_SUFFIX_RE.sub("", name).strip()


def _clean_text(element: Tag | None) -> str:
    if element is None:
        return ""
    return element.get_text("\n", strip=True).strip()


def _reply_target(block: Tag) -> str | None:
    link = block.select_one('div.reply_to a[href^="#go_to_message"]')
    if link is None:
        return None
    match = _GO_TO_RE.search(str(link.get("href") or ""))
    return match.group(1) if match else None


def _client_id(block: Tag) -> int | None:
    link = block.select_one('a[href^="tel:"]')
    if link is not None:
        match = _TEL_RE.search(str(link.get("href") or ""))
        if match:
            return int(match.group(1))
    # Some bot versions render the id as plain text instead of a tel: link.
    match = _ID_TEXT_RE.search(block.get_text(" ", strip=True))
    return int(match.group(1)) if match else None


def _parse_size(style: str) -> tuple[int | None, int | None]:
    width = height = None
    for prop, value in _SIZE_RE.findall(style or ""):
        if prop.lower() == "width":
            width = int(value)
        else:
            height = int(value)
    return width, height


def _collect_media(block: Tag) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    photos: list[dict[str, Any]] = []
    videos: list[dict[str, Any]] = []
    seen_photos: set[str] = set()
    seen_videos: set[str] = set()

    for anchor in block.select("a.photo_wrap"):
        href = str(anchor.get("href") or "").strip()
        if not href or href in seen_photos:
            continue
        image = anchor.find("img")
        width, height = _parse_size(str(image.get("style") or "")) if image else (None, None)
        seen_photos.add(href)
        photos.append({"href": href, "width": width, "height": height})

    for anchor in block.select("a.video_file_wrap, a.video_wrap"):
        href = str(anchor.get("href") or "").strip()
        if not href or href in seen_videos:
            continue
        seen_videos.add(href)
        videos.append({"href": href})

    return photos, videos


def _collect_blocks(directory: Path) -> list[Tag]:
    pages: list[Path] = []
    for name in PAGE_NAMES:
        candidate = directory / name
        if candidate.exists():
            pages.append(candidate)
    if not pages:
        raise TgexportParseError(f"no messages*.html pages in {directory}")

    blocks: list[Tag] = []
    for page in pages:
        soup = _read_page(page)
        blocks.extend(soup.find_all("div", class_="message"))
    return blocks


def parse_export(
    directory: str | Path,
    *,
    max_topics: int | None = None,
    max_messages: int | None = None,
) -> dict[str, Any]:
    """Parse the export directory into the normalized ``{"topics": [...]}`` shape."""
    path = Path(directory)
    if not path.is_dir():
        raise TgexportParseError(f"not a directory: {path}")

    blocks = _collect_blocks(path)

    # Pass 1: topics in first-appearance order.
    topics: list[dict[str, Any]] = []
    topic_by_id: dict[str, dict[str, Any]] = {}
    for block in blocks:
        if "service" not in list(block.get("class") or []):
            continue
        text = block.get_text(" ", strip=True)
        if "created topic" not in text:
            continue
        topic_id = _message_id(block)
        if not topic_id or topic_id in topic_by_id:
            continue
        topic = {
            "topic_id": topic_id,
            "title": _topic_title(text),
            "client_id": None,
            "messages": [],
        }
        topics.append(topic)
        topic_by_id[topic_id] = topic

    # Pass 2: messages, keeping the current topic across page boundaries.
    current_topic: str | None = None
    client_names: dict[str, set[str]] = {topic_id: set() for topic_id in topic_by_id}
    seen_ids: dict[str, set[str]] = {topic_id: set() for topic_id in topic_by_id}
    last_by_topic: dict[str, tuple[str, bool]] = {}

    for block in blocks:
        classes = list(block.get("class") or [])

        if "service" in classes:
            topic_id = _message_id(block)
            if topic_id in topic_by_id:
                current_topic = topic_id
            continue

        if "default" not in classes:
            continue

        message_id = _message_id(block)
        if not message_id:
            continue

        joined = "joined" in classes
        forwarded = block.select_one("div.forwarded.body")
        scope: Tag = forwarded if forwarded is not None else block
        from_name = _clean_name(scope.find("div", class_="from_name"))

        target = _reply_target(block)
        if target is not None and target in topic_by_id:
            current_topic = target
        topic_id = target if target in topic_by_id else current_topic
        if topic_id is None:
            continue

        # ``joined`` means "same sender as previous": Telegram omits the avatar
        # and often the from_name. Inherit it instead of dropping the message.
        last = last_by_topic.get(topic_id)
        inherited_client = False
        if joined and not from_name and last is not None:
            from_name, inherited_client = last

        # Bot information message: learn the client id, write nothing.
        if forwarded is None and from_name in BOT_NAMES:
            if BOT_INFO_MARKER in block.get_text(" ", strip=True):
                client_id = _client_id(block)
                if client_id is not None:
                    topic = topic_by_id[topic_id]
                    if topic["client_id"] is None:
                        topic["client_id"] = client_id
            continue

        topic = topic_by_id[topic_id]

        # Plain messages from a name already seen in the forwarded stream are
        # the same client (Telegram only forwards the first message); mark them
        # as inbound for the importer, which keys on this flag.
        is_client = forwarded is not None or inherited_client
        if is_client:
            if from_name:
                client_names[topic_id].add(from_name)
        elif from_name and from_name in client_names[topic_id]:
            is_client = True

        if message_id in seen_ids[topic_id]:
            continue

        text = _clean_text(scope.find("div", class_="text"))
        photos, videos = _collect_media(block)
        if not text and not photos and not videos:
            continue

        date_el = block.select_one(".date[title]")
        date_value = str(date_el.get("title") or "").strip() if date_el else ""

        seen_ids[topic_id].add(message_id)
        last_by_topic[topic_id] = (from_name, is_client)
        topic["messages"].append(
            {
                "id": message_id,
                "date": date_value,
                "from": from_name,
                "forwarded": is_client,
                "text": text,
                "photos": photos,
                "videos": videos,
            }
        )

    if not topics:
        raise TgexportParseError(f"no topics found in {path}")

    if max_topics is not None:
        topics = topics[: max(0, max_topics)]
    if max_messages is not None:
        remaining = max(0, max_messages)
        for topic in topics:
            if remaining <= 0:
                topic["messages"] = []
                continue
            topic["messages"] = topic["messages"][:remaining]
            remaining -= len(topic["messages"])

    return {"topics": topics}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a Telegram Desktop HTML export into normalized JSON."
    )
    parser.add_argument("--dir", required=True, help="export directory")
    parser.add_argument(
        "--out",
        default="_tgexport_normalized.json",
        help="output JSON path (default: _tgexport_normalized.json)",
    )
    parser.add_argument("--max-topics", type=int, default=None, metavar="N")
    parser.add_argument("--max-messages", type=int, default=None, metavar="N")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = parse_export(
            args.dir,
            max_topics=args.max_topics,
            max_messages=args.max_messages,
        )
    except TgexportParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    if out_path.parent and not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    messages = sum(len(topic["messages"]) for topic in payload["topics"])
    print(
        f"parsed topics={len(payload['topics'])} messages={messages} -> {out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
