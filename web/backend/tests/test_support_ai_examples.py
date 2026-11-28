"""B2b — operator examples, QA dedupe and message feedback (plan §2.4/§4.1/§5.4).

No network and no real database: store tests use a tiny fake ``AsyncSession``
that records SQL, API tests override dependencies with an in-memory store
(same pattern as ``test_support_kb.py``).
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.examples import (
    MAX_EXAMPLES_CHARS,
    render_examples,
)
from web.backend.core.support.ai.chunks import select_chunks
from web.backend.core.support.ai.prompt import build_prompt
from web.backend.core.support.ai.provider import AiCompletion
from web.backend.core.support.ai.responder import AiResponder, AiRuntime, _normalize_used
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.settings import SupportSettings
from web.backend.core.support.store import qa as qa_store
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")
_UTC = timezone.utc


class _Result:
    def __init__(self, *, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


# ── normalization / dedupe key ────────────────────────────────────────────


def test_external_key_ignores_case_spaces_punctuation_and_word_order():
    first = qa_store.external_key(
        "Германия не подключается!", "Обновите подписку в кабинете."
    )
    second = qa_store.external_key(
        "  не подключается   ГЕРМАНИЯ  ", "обновите   подписку в кабинете"
    )
    assert first == second
    assert len(first) == 64
    assert qa_store.external_key("Германия не подключается", "ответ") != first


def test_clean_example_scrubs_secrets_and_masks_order_numbers():
    cleaned = qa_store.clean_example(
        "Заказ 1234567, ключ vless://secret и почта user@example.com",
        600,
    )
    assert "1234567" not in cleaned
    assert "vless://secret" not in cleaned
    assert "user@example.com" not in cleaned
    assert "[номер]" in cleaned
    assert "[скрыто]" in cleaned


def test_is_meaningful_rejects_fillers():
    assert not qa_store.is_meaningful("ок")
    assert not qa_store.is_meaningful("спасибо!")
    assert not qa_store.is_meaningful("минуту")
    assert qa_store.is_meaningful("Обновите подписку в приложении")


# ── add_qa_pair ───────────────────────────────────────────────────────────


class AddSession:
    def __init__(self, *, inserted: bool):
        self.inserted = inserted
        self.sql = ""
        self.params: dict = {}

    async def execute(self, statement, params):
        self.sql = str(statement)
        self.params = dict(params)
        return _Result(
            row=SimpleNamespace(_mapping={"id": 17}) if self.inserted else None
        )


@pytest.mark.asyncio
async def test_add_qa_pair_uses_external_key_and_on_conflict_do_nothing():
    db = AddSession(inserted=True)

    pair_id = await qa_store.add_qa_pair(
        db,
        "Германия не подключается",
        "Перезапустите клиент и проверьте подписку",
        source="feedback",
        conversation_id=7,
    )

    assert pair_id == 17
    assert "ON CONFLICT (external_key) DO NOTHING" in db.sql
    assert db.params["source"] == "feedback"
    assert db.params["conversation_id"] == 7
    assert db.params["external_key"] == qa_store.external_key(
        "Германия не подключается",
        "Перезапустите клиент и проверьте подписку",
    )


@pytest.mark.asyncio
async def test_add_qa_pair_duplicate_returns_none():
    db = AddSession(inserted=False)
    assert (
        await qa_store.add_qa_pair(
            db,
            "Германия не подключается",
            "Перезапустите клиент и проверьте подписку",
        )
        is None
    )


@pytest.mark.asyncio
async def test_add_qa_pair_skips_filler_without_querying_db():
    class ExplodingSession:
        async def execute(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("filler must not reach the database")

    assert (
        await qa_store.add_qa_pair(ExplodingSession(), "Вопрос клиента", "ок")
        is None
    )


# ── similar_examples ──────────────────────────────────────────────────────


class SimilarSession:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params: dict = {}

    async def execute(self, statement, params):
        self.sql = str(statement)
        self.params = dict(params)
        return _Result(rows=self.rows)


def _row(**values):
    return SimpleNamespace(_mapping=values)


@pytest.mark.asyncio
async def test_similar_examples_returns_clean_similar_pairs_only():
    long_answer = (
        "Перезапустите клиент, проверьте подписку и попробуйте другую сеть. "
        + "Дополнительное пояснение " * 40
    )
    db = SimilarSession(
        [
            _row(
                id=1,
                question="Германия не подключается",
                answer=long_answer,
                rank=0.9,
            ),
            # Duplicate answer wording must not flood the prompt.
            _row(
                id=2,
                question="Не подключается Германия",
                answer=long_answer,
                rank=0.8,
            ),
            _row(id=3, question="ок", answer="спасибо", rank=0.7),
            _row(
                id=4,
                question="Не проходит оплата",
                answer="Попробуйте другую карту или напишите в поддержку",
                rank=0.6,
            ),
        ]
    )

    items = await qa_store.similar_examples(db, "германия", limit=3)

    assert "websearch_to_tsquery('russian', :q)" in db.sql
    assert "ts_rank_cd(" in db.sql
    assert db.params["q"] == "германия"
    assert len(items) == 2
    assert items[0]["question"] == "Германия не подключается"
    assert all(len(item["answer"]) <= qa_store.EXAMPLE_MAX for item in items)
    assert all(len(item["question"]) <= qa_store.EXAMPLE_MAX for item in items)
    assert [item["id"] for item in items] == [1, 4]


@pytest.mark.asyncio
async def test_similar_examples_empty_query_does_not_query_db():
    class ExplodingSession:
        async def execute(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("empty query must not reach the database")

    assert await qa_store.similar_examples(ExplodingSession(), "   ") == []


# ── render_examples ───────────────────────────────────────────────────────


def test_render_examples_is_capped_at_900_chars():
    examples = [
        {"question": f"Вопрос {index} " + "q" * 500, "answer": "a" * 600}
        for index in range(3)
    ]
    rendered = render_examples(examples)
    assert rendered
    assert len(rendered) <= MAX_EXAMPLES_CHARS
    assert "Клиент:" in rendered
    assert "Оператор:" in rendered


def test_render_examples_scrubs_secrets():
    rendered = render_examples(
        [
            {
                "question": "Мой ключ vless://secret и почта user@example.com",
                "answer": "Пришлите скриншот ошибки в поддержку",
            }
        ]
    )
    assert "vless://secret" not in rendered
    assert "user@example.com" not in rendered
    assert "[скрыто]" in rendered


# ── KbChunk.doc_id and used[] ─────────────────────────────────────────────


def test_select_chunks_keeps_real_doc_id_and_used_maps_to_it():
    hits = [
        {
            "doc_id": 10,
            "title": "Германия не подключается",
            "body": "Германия не подключается. Перезапустите клиент.",
        }
    ]
    chunks = select_chunks(hits, "германия", budget=3000)

    assert chunks and chunks[0].doc_id == 10

    prompt = build_prompt(
        config=AiConfig(mode="suggest", effective_mode="suggest", has_key=True),
        kb_chunks=chunks,
        examples=[{"question": "Не подключается", "answer": "Перезапустите клиент"}],
    )
    used = _normalize_used([1], prompt.citations)

    assert used == [
        {
            "doc_id": 10,
            "title": "Германия не подключается",
            "chunk": "Германия не подключается. Перезапустите клиент.",
        }
    ]


# ── examples reach the prompt through AiRuntime ───────────────────────────


class CaptureProvider:
    def __init__(self):
        self.messages = None

    async def complete_json(self, messages, config):
        self.messages = messages
        return AiCompletion(
            draft={
                "reply": "Перезапустите клиент",
                "operator_note": "",
                "reason": "ok",
                "needs_human": False,
                "clarify": False,
                "used": [],
                "confidence": 0.95,
            },
            model="fake",
        )


class ResponderStore:
    def __init__(self):
        self.messages = [
            {
                "id": 101,
                "conversation_id": 7,
                "direction": "in",
                "author": "client",
                "text": "Не подключается Германия",
            }
        ]
        self.suggestions = []

    async def get_conversation(self, conversation_id):
        return {"id": 7, "channel": "telegram", "status": "open"}

    async def list_messages(self, conversation_id, *, before_id=None, limit=50):
        return list(self.messages)

    async def supersede_pending(self, conversation_id, *, except_id=None):
        return 0

    async def create_suggestion(self, **kwargs):
        self.suggestions.append(kwargs)
        return 1

    async def get_pause(self, *, now=None):
        return None

    async def human_hold_active(self, conversation_id, minutes, *, now=None):
        return False

    async def last_human_reply_at(self, conversation_id):
        return None

    async def ai_replies_since(self, conversation_id, since):
        return 0


class ResponderOutbox:
    def has_sender(self, channel):
        return True

    def check_window(self, conversation, *, now=None):
        return None


@pytest.mark.asyncio
async def test_runtime_examples_are_injected_into_the_prompt():
    provider = CaptureProvider()

    async def examples(query, *, limit=3):
        return [
            {
                "question": "Не подключается Германия",
                "answer": "Перезапустите клиент и проверьте подписку",
            }
        ]

    async def kb_search(query, *, limit=8):
        return []

    async def no_card(service, conversation):
        return None

    service = SimpleNamespace(
        ai=AiRuntime(
            config=AiConfig(
                mode="suggest",
                effective_mode="suggest",
                has_key=True,
                api_key="sk-test",
            ),
            provider=provider,
            kb_search=kb_search,
            examples=examples,
        ),
        store=ResponderStore(),
        outbox=ResponderOutbox(),
        event_bus=None,
    )

    result = await AiResponder(service, customer_card_builder=no_card).handle_inbound(7)

    assert result is not None
    user_prompt = provider.messages[1]["content"]
    assert "Примеры ответов операторов" in user_prompt
    assert "Перезапустите клиент и проверьте подписку" in user_prompt
    assert service.store.suggestions


# ── feedback API ──────────────────────────────────────────────────────────


class FeedbackStore:
    def __init__(self):
        self.messages = {
            11: {
                "id": 11,
                "conversation_id": 1,
                "direction": "out",
                "author": "agent",
                "text": "Старый ответ оператора",
                "created_at": datetime.now(_UTC),
            }
        }
        self.inbound = {
            1: {
                "id": 10,
                "conversation_id": 1,
                "direction": "in",
                "author": "client",
                "text": "Не подключается Германия",
                "created_at": datetime.now(_UTC),
            }
        }
        self.pairs: list[dict] = []
        self.candidates: list[dict] = []
        self._next_pair = 1

    async def get_message(self, message_id):
        return self.messages.get(int(message_id))

    async def last_inbound_before(self, conversation_id, message_id):
        return self.inbound.get(int(conversation_id)) if int(message_id) == 11 else None

    async def add_qa_pair(
        self,
        question,
        answer,
        *,
        source="operator",
        conversation_id=None,
        external_key=None,
    ):
        pair_id = self._next_pair
        self._next_pair += 1
        self.pairs.append(
            {
                "id": pair_id,
                "question": question,
                "answer": answer,
                "source": source,
                "conversation_id": conversation_id,
            }
        )
        return pair_id

    async def create_candidate(self, **kwargs):
        self.candidates.append(dict(kwargs))
        return len(self.candidates)


class FeedbackService:
    def __init__(self):
        self.settings = SupportSettings()
        self.store = FeedbackStore()


@pytest.fixture
def feedback_service():
    return FeedbackService()


@pytest.fixture
def override_feedback(feedback_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: feedback_service
    yield feedback_service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_feedback_correct_writes_qa_pair(
    client: AsyncClient, override_feedback, feedback_service
):
    response = await client.post(
        "/api/support/messages/11/feedback",
        json={
            "verdict": "correct",
            "correct_answer": "Перезапустите клиент и проверьте подписку",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"qa_pair_id": 1}
    pair = feedback_service.store.pairs[0]
    assert pair["source"] == "feedback"
    assert pair["question"] == "Не подключается Германия"
    assert pair["answer"] == "Перезапустите клиент и проверьте подписку"
    assert pair["conversation_id"] == 1


@pytest.mark.asyncio
async def test_feedback_partial_uses_sent_text(
    client: AsyncClient, override_feedback, feedback_service
):
    response = await client.post(
        "/api/support/messages/11/feedback",
        json={"verdict": "partial", "note": "не хватает деталей"},
    )

    assert response.status_code == 200
    assert feedback_service.store.pairs[0]["answer"] == "Старый ответ оператора"


@pytest.mark.asyncio
async def test_feedback_wrong_creates_pair_and_candidate(
    client: AsyncClient, override_feedback, feedback_service
):
    response = await client.post(
        "/api/support/messages/11/feedback",
        json={
            "verdict": "wrong",
            "correct_answer": "Обновите подписку в кабинете",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"qa_pair_id": 1}
    assert feedback_service.store.pairs[0]["answer"] == "Обновите подписку в кабинете"
    candidate = feedback_service.store.candidates[0]
    assert candidate["source"] == "feedback"
    assert candidate["question"] == "Не подключается Германия"
    assert candidate["answer"] == "Обновите подписку в кабинете"


@pytest.mark.asyncio
async def test_feedback_wrong_without_correct_answer_only_creates_candidate(
    client: AsyncClient, override_feedback, feedback_service
):
    response = await client.post(
        "/api/support/messages/11/feedback",
        json={"verdict": "wrong"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"qa_pair_id": None}
    assert feedback_service.store.pairs == []
    assert len(feedback_service.store.candidates) == 1
    assert feedback_service.store.candidates[0]["answer"] is None


@pytest.mark.asyncio
async def test_feedback_missing_message_returns_404(
    client: AsyncClient, override_feedback
):
    response = await client.post(
        "/api/support/messages/999/feedback",
        json={"verdict": "correct"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_feedback_validates_lengths(client: AsyncClient, override_feedback):
    response = await client.post(
        "/api/support/messages/11/feedback",
        json={"verdict": "correct", "note": "x" * 1001},
    )
    assert response.status_code == 422


# ── facade surface ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_facade_exposes_qa_methods():
    from web.backend.core.support.store import SupportStore

    store = SupportStore()
    for name in (
        "add_qa_pair",
        "similar_examples",
        "get_message",
        "last_inbound_before",
        "create_candidate",
    ):
        assert callable(getattr(store, name))
