"""HTML export parser (``tools/tgexport_html_parse.py``) — focus fixture.

The fixture mirrors the real Telegram Desktop markup: a created topic, the
bot's ``🆕 Новое обращение`` info message carrying the client id, a forwarded
client message with a photo and a plain operator reply.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import tgexport_html_parse as parser

TOPIC_PAGE = """\
<!DOCTYPE html>
<html><body>
 <div class="message service" id="message36">
  <div class="body details">
Поддержка HexaVeil created topic &laquo;Ilya Hrapkov (@ihrapkov)&raquo;
  </div>
 </div>

 <div class="message default clearfix" id="message37">
  <div class="body">
   <div class="pull_right date details" title="27.07.2026 12:31:02 GMT+03:00">12:31</div>
   <div class="from_name">Поддержка HexaVeil</div>
   <div class="reply_to details">
In reply to <a href="#go_to_message36" onclick="return GoToMessage(36)">this message</a>
   </div>
   <div class="text">
&#127381; Новое обращение<br>Имя: Ilya Hrapkov (<a href="https://t.me/ihrapkov">@ihrapkov</a>)<br>ID: <a href="tel:1211524569">1211524569</a><br>Username: <a href="https://t.me/ihrapkov">@ihrapkov</a>
   </div>
  </div>
 </div>

 <div class="message default clearfix" id="message38">
  <div class="body">
   <div class="pull_right date details" title="27.07.2026 12:31:01 GMT+03:00">12:31</div>
   <div class="from_name">Поддержка HexaVeil</div>
   <div class="pull_left forwarded userpic_wrap">
    <div class="userpic userpic2" style="width: 42px; height: 42px">
     <div class="initials" style="line-height: 42px">ИХ</div>
    </div>
   </div>
   <div class="forwarded body">
    <div class="from_name">
Илья Храпков<span class="date details" title="27.07.2026 12:31:01 GMT+03:00"> 27.07.2026 12:31:01</span>
    </div>
    <div class="reply_to details">
In reply to <a href="#go_to_message36" onclick="return GoToMessage(36)">this message</a>
    </div>
    <div class="media_wrap clearfix">
     <a class="photo_wrap clearfix pull_left" href="photos/photo_1@02-08-2026_09-43-29.jpg">
      <img class="photo" src="photos/photo_1@02-08-2026_09-43-29_thumb.jpg" style="width: 120px; height: 260px"/>
     </a>
    </div>
    <div class="text">
Здравствуйте! Не работает VPN
    </div>
   </div>
  </div>
 </div>

 <div class="message default clearfix" id="message39">
  <div class="body">
   <div class="pull_right date details" title="27.07.2026 12:35:00 GMT+03:00">12:35</div>
   <div class="from_name">Андрей Ковалёв</div>
   <div class="text">Проверьте подписку и перезапустите клиент</div>
  </div>
 </div>
</body></html>
"""


def _write_export(tmp_path: Path) -> Path:
    export = tmp_path / "ChatExport_test"
    export.mkdir()
    (export / "messages.html").write_text(TOPIC_PAGE, encoding="utf-8")
    return export


def test_parses_topic_client_and_messages(tmp_path):
    payload = parser.parse_export(_write_export(tmp_path))

    assert len(payload["topics"]) == 1
    topic = payload["topics"][0]
    assert topic["topic_id"] == "36"
    assert topic["title"] == "Ilya Hrapkov (@ihrapkov)"
    assert topic["client_id"] == 1211524569

    # The bot information message is not part of the history.
    assert [message["id"] for message in topic["messages"]] == ["38", "39"]

    client, operator = topic["messages"]
    assert client["forwarded"] is True
    assert client["from"] == "Илья Храпков"
    assert client["text"] == "Здравствуйте! Не работает VPN"
    assert client["photos"] == [
        {
            "href": "photos/photo_1@02-08-2026_09-43-29.jpg",
            "width": 120,
            "height": 260,
        }
    ]
    assert client["videos"] == []

    assert operator["forwarded"] is False
    assert operator["from"] == "Андрей Ковалёв"
    assert operator["text"] == "Проверьте подписку и перезапустите клиент"
    assert operator["photos"] == []


def test_pages_are_processed_in_order_and_message_ids_deduped(tmp_path):
    export = _write_export(tmp_path)
    second = TOPIC_PAGE.replace('id="message39"', 'id="message40"').replace(
        "Проверьте подписку и перезапустите клиент", "Второе сообщение"
    )
    # Same forwarded message id 38 repeats across the page boundary.
    (export / "messages2.html").write_text(second, encoding="utf-8")

    payload = parser.parse_export(export)
    topic = payload["topics"][0]
    assert [message["id"] for message in topic["messages"]] == ["38", "39", "40"]
    assert topic["messages"][-1]["text"] == "Второе сообщение"


def test_plain_client_message_after_forward_is_marked_inbound(tmp_path):
    export = _write_export(tmp_path)
    extra = (
        TOPIC_PAGE.replace(
            "Проверьте подписку и перезапустите клиент",
            "Ещё вопрос от клиента",
        )
        .replace(
            '<div class="from_name">Андрей Ковалёв</div>',
            '<div class="from_name">Илья Храпков</div>',
        )
        .replace('id="message39"', 'id="message40"')
    )
    (export / "messages2.html").write_text(extra, encoding="utf-8")

    payload = parser.parse_export(export)
    messages = payload["topics"][0]["messages"]
    plain_client = [m for m in messages if m["text"] == "Ещё вопрос от клиента"][0]
    assert plain_client["forwarded"] is True
    assert plain_client["from"] == "Илья Храпков"


def test_title_is_utf8_and_max_limits(tmp_path):
    payload = parser.parse_export(_write_export(tmp_path), max_topics=1, max_messages=1)
    assert payload["topics"][0]["title"].startswith("Ilya")
    assert len(payload["topics"][0]["messages"]) == 1


def test_missing_directory_rejected(tmp_path):
    with pytest.raises(parser.TgexportParseError):
        parser.parse_export(tmp_path / "nope")


def test_empty_directory_rejected(tmp_path):
    with pytest.raises(parser.TgexportParseError):
        parser.parse_export(tmp_path)
