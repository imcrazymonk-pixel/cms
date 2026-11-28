"""B2c — chat-history import (plan §7 and §8).

No network and no real database: parsers are pure, the runner uses an in-memory
job store, and API tests override ``get_support_service`` exactly like
``test_support_stage_a.py``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.api.v1.support import imports as imports_api
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.imports import cluster, runner, tg_json, tg_text
from web.backend.core.support.imports.errors import ImportParseError, ImportTooLarge
from web.backend.core.support.settings import SupportSettings
from web.backend.core.support.store import jobs as jobs_store
from web.backend.core.support.store import qa as qa_store
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")

TEXT_SAMPLE = """\
[28.11.2026 12:34:56] Поддержка HexaVeil: Здравствуйте! Чем помочь?
[28.11.2026 12:35:10] Иван: Не подключается Германия
проверял на телефоне и ноутбуке
[28.11.2026 12:36:00] Поддержка HexaVeil: Проверьте подписку и перезапустите клиент
[28.11.2026 12:37:00] Иван: Не подключается Германия
[28.11.2026 12:38:00] Поддержка HexaVeil: Обновите подписку в кабинете
"""

# Runner sample: both client questions share a topic, so clustering yields one
# article candidate (dry-run must still not persist it).
RUNNER_SAMPLE = """\
[28.11.2026 12:35:10] Иван: Не подключается Германия
[28.11.2026 12:36:00] Поддержка HexaVeil: Проверьте подписку и перезапустите клиент
[28.11.2026 12:37:00] Иван: Не подключается Германия
[28.11.2026 12:38:00] Поддержка HexaVeil: Обновите подписку в кабинете
"""


# ── tg_text ───────────────────────────────────────────────────────────────


def test_text_parses_two_date_formats_and_seconds_optional():
    payload = (
        "[28.11.2026 12:34:56] Поддержка HexaVeil: Первое\n"
        "[28.11.26 12:35] Иван: Второе\n"
    )
    messages = tg_text.parse_text(payload)
    assert [m["author"] for m in messages] == ["Поддержка HexaVeil", "Иван"]
    assert messages[0]["timestamp"] == datetime(2026, 11, 28, 12, 34, 56)
    assert messages[1]["timestamp"] == datetime(2026, 11, 28, 12, 35, 0)


def test_text_continuation_lines_are_merged():
    messages = tg_text.parse_text(TEXT_SAMPLE)
    assert len(messages) == 5
    assert messages[1]["text"] == (
        "Не подключается Германия\nпроверял на телефоне и ноутбуке"
    )


def test_text_cp1251_fallback():
    raw = (
        "[28.11.2026 12:35:10] Иван: Не подключается Германия\n"
        "[28.11.2026 12:36:00] Поддержка: Проверьте подписку\n"
    ).encode("cp1251")
    assert tg_text.decode_bytes(raw).startswith("[28.11.2026")
    messages = tg_text.parse_text(raw)
    assert messages[0]["author"] == "Иван"
    assert messages[0]["is_operator"] is False
    assert messages[1]["is_operator"] is True


def test_text_without_headers_is_a_parse_error():
    with pytest.raises(ImportParseError) as exc:
        tg_text.parse_text("просто текст без заголовков")
    assert "headers" in str(exc.value)


def test_text_pairs_client_then_operator_with_side_limit():
    messages = tg_text.parse_text(TEXT_SAMPLE)
    pairs = tg_text.build_pairs(messages)
    assert len(pairs) == 2
    assert pairs[0]["question"].startswith("Не подключается Германия")
    assert pairs[0]["answer"].startswith("Проверьте подписку")


def test_text_custom_operator_names():
    payload = (
        "[28.11.2026 12:35:10] Иван: Не подключается Германия\n"
        "[28.11.2026 12:36:00] Вася: Проверьте подписку и перезапустите клиент\n"
    )
    assert tg_text.build_pairs(tg_text.parse_text(payload)) == []
    pairs = tg_text.build_pairs(
        tg_text.parse_text(payload, operator_names=["Вася"])
    )
    assert len(pairs) == 1


# ── tg_json ───────────────────────────────────────────────────────────────


def _json_payload() -> dict:
    return {
        "name": "Support",
        "messages": [
            {
                "id": 1,
                "type": "message",
                "date": "2026-11-28T12:35:10",
                "from": "Иван",
                "from_id": "user1",
                "text": [
                    "Не подключается ",
                    {"type": "bold", "text": "Германия"},
                    "!",
                ],
            },
            {"id": 2, "type": "service", "date": "2026-11-28T12:35:20", "text": "joined"},
            {
                "id": 3,
                "type": "message",
                "date": "2026-11-28T12:36:00",
                "from": "Поддержка HexaVeil",
                "from_id": "op1",
                "reply_to_message_id": 1,
                "text": "Проверьте подписку и перезапустите клиент",
            },
        ],
    }


def test_json_flattens_text_array_and_skips_service_messages():
    messages = tg_json.parse_json(_json_payload())
    assert len(messages) == 2
    assert messages[0]["text"] == "Не подключается Германия!"


def test_json_reply_to_has_priority_for_pairs():
    messages, pairs = tg_json.parse_pairs(_json_payload())
    assert [m["msg_id"] for m in messages] == [1, 3]
    assert len(pairs) == 1
    assert pairs[0]["question"] == "Не подключается Германия!"
    assert pairs[0]["answer"] == "Проверьте подписку и перезапустите клиент"


def test_json_alternation_without_reply_ids():
    payload = {
        "messages": [
            {
                "id": 1,
                "type": "message",
                "date": "2026-11-28T12:35:10",
                "from": "Иван",
                "from_id": "user1",
                "text": "Не подключается Германия",
            },
            {
                "id": 2,
                "type": "message",
                "date": "2026-11-28T12:36:00",
                "from": "Оператор",
                "from_id": "op1",
                "text": "Проверьте подписку и перезапустите клиент",
            },
        ]
    }
    pairs = tg_json.build_pairs(tg_json.parse_json(payload))
    assert len(pairs) == 1
    assert pairs[0]["question"] == "Не подключается Германия"


def test_json_broken_payload_reports_position():
    with pytest.raises(ImportParseError) as exc:
        tg_json.parse_json('{"messages": [')
    message = str(exc.value)
    assert "line 1" in message and "column" in message


def test_json_missing_messages_array_is_rejected():
    with pytest.raises(ImportParseError):
        tg_json.parse_json({"name": "export"})


# ── dedupe key + clustering ───────────────────────────────────────────────


def test_dedupe_key_is_stable_across_order_case_and_spaces():
    first = qa_store.external_key("Не подключается Германия", "Перезапустите клиент")
    second = qa_store.external_key(
        "  германия   НЕ подключается! ",
        "перезапустите   КЛИЕНТ",
    )
    assert first == second
    assert len(first) == 64


def test_cluster_groups_repeated_topics_only():
    pairs = [
        {"question": "Не подключается Германия", "answer": "Проверьте подписку"},
        {"question": "Германия не подключается", "answer": "Обновите подписку"},
        {"question": "Как оплатить тариф", "answer": "В кабинете есть оплата"},
    ]
    candidates = cluster.build_candidates(pairs)
    assert len(candidates) == 1
    assert candidates[0]["occurrences"] == 2
    assert candidates[0]["topic"] == "германия-подключается"


def test_cluster_caps_candidates_at_200():
    pairs = [
        {"question": f"Проблема номер{i} подключение", "answer": "Ответ оператора"}
        for i in range(250)
    ]
    # Topics differ only by the number token; token list for each has ≤3 words,
    # so every pair is its own group and nothing reaches two occurrences.
    assert cluster.build_candidates(pairs) == []


# ── runner ────────────────────────────────────────────────────────────────


class FakeJobStore:
    """In-memory ``support_job`` + QA dedupe, no DB."""

    def __init__(self):
        self.jobs: dict[int, dict] = {}
        self.next_id = 1
        self.batch_calls: list[list[dict]] = []
        self.candidates: list[dict] = []
        self.seen_keys: set[str] = set()
        self.busy = False

    async def create_job(self, *, kind, payload=None, created_by=None, total=None):
        if self.busy or any(
            job["kind"] == kind and job["status"] in ("queued", "running")
            for job in self.jobs.values()
        ):
            raise jobs_store.JobBusy(kind)
        job = {
            "id": self.next_id,
            "kind": kind,
            "status": "queued",
            "progress": 0,
            "total": total,
            "payload": payload or {},
            "result": None,
            "error": None,
            "started_at": None,
            "finished_at": None,
        }
        self.jobs[self.next_id] = job
        self.next_id += 1
        return dict(job)

    async def get_job(self, job_id):
        job = self.jobs.get(int(job_id))
        return dict(job) if job is not None else None

    async def claim_job(self, job_id):
        job = self.jobs.get(int(job_id))
        if job is None or job["status"] != "queued":
            return None
        job["status"] = "running"
        job["started_at"] = datetime.now(timezone.utc)
        return dict(job)

    async def update_job(self, job_id, **kwargs):
        job = self.jobs[int(job_id)]
        job.update(kwargs)
        return dict(job)

    async def finish_job(self, job_id, *, status="done", result=None, error=None):
        job = self.jobs[int(job_id)]
        job.update(
            status=status,
            result=result,
            error=error,
            finished_at=datetime.now(timezone.utc),
        )
        return dict(job)

    async def cancel_job(self, job_id):
        job = self.jobs.get(int(job_id))
        if job is None:
            return None
        if job["status"] in ("queued", "running"):
            job.update(
                status="error",
                error="cancelled",
                finished_at=datetime.now(timezone.utc),
            )
        return dict(job)

    async def add_qa_pairs_batch(self, pairs, *, source="import"):
        self.batch_calls.append(list(pairs))
        created = duplicates = 0
        for pair in pairs:
            key = qa_store.external_key(pair["question"], pair["answer"])
            if key in self.seen_keys:
                duplicates += 1
                continue
            self.seen_keys.add(key)
            created += 1
        return created, duplicates

    async def create_candidate(self, **kwargs):
        self.candidates.append(kwargs)
        return len(self.candidates)


def _service(store: FakeJobStore) -> SimpleNamespace:
    return SimpleNamespace(store=store, settings=SupportSettings(), import_tasks=set())


async def _seed_job(store: FakeJobStore, **overrides) -> int:
    payload = {
        "kind": "text",
        "text": overrides.pop("text", RUNNER_SAMPLE),
        "payload": overrides.pop("payload", None),
        "operator_names": overrides.pop("operator_names", None),
        "dry_run": overrides.pop("dry_run", False),
    }
    job = await store.create_job(kind=runner.JOB_KIND, payload=payload)
    return int(job["id"])


@pytest.mark.asyncio
async def test_runner_dry_run_writes_nothing():
    store = FakeJobStore()
    job_id = await _seed_job(store, dry_run=True)

    result = await runner.run_job(_service(store), job_id)

    assert store.batch_calls == []
    assert store.candidates == []
    assert result["questions"] == 2
    assert result["pairs_created"] == 0
    assert result["would_create"] == 2
    assert result["would_create_candidates"] >= 1
    assert store.jobs[job_id]["status"] == "done"
    assert store.jobs[job_id]["progress"] == 100


@pytest.mark.asyncio
async def test_runner_repeat_import_skips_all_duplicates():
    store = FakeJobStore()
    service = _service(store)

    first = await runner.run_job(service, await _seed_job(store))
    second = await runner.run_job(service, await _seed_job(store))

    assert first["pairs_created"] == 2
    assert first["skipped_duplicates"] == 0
    assert second["pairs_created"] == 0
    assert second["skipped_duplicates"] == 2
    assert store.jobs[2]["status"] == "done"


@pytest.mark.asyncio
async def test_runner_parse_error_finishes_job_with_error():
    store = FakeJobStore()
    job_id = await _seed_job(store, text="без заголовков вообще")

    result = await runner.run_job(_service(store), job_id)

    assert store.jobs[job_id]["status"] == "error"
    assert store.jobs[job_id]["error"].startswith("IMPORT_PARSE_FAILED")
    assert result["errors"]


@pytest.mark.asyncio
async def test_runner_cancelled_job_stops_without_writing():
    store = FakeJobStore()
    job_id = await _seed_job(store)
    await store.cancel_job(job_id)

    result = await runner.run_job(_service(store), job_id)

    assert store.batch_calls == []
    assert result["status"] == "error"
    assert result["error"] == "cancelled"


# ── store/jobs.py ─────────────────────────────────────────────────────────


class _Result:
    def __init__(self, *, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _ExistingJobSession:
    async def execute(self, statement, params=None):
        return _Result(row=SimpleNamespace(_mapping={"id": 9}))


@pytest.mark.asyncio
async def test_create_job_raises_busy_when_active_job_exists():
    with pytest.raises(jobs_store.JobBusy):
        await jobs_store.create_job(_ExistingJobSession(), kind="kb_import")


class _ClaimSession:
    def __init__(self):
        self.sql = ""

    async def execute(self, statement, params=None):
        self.sql = str(statement)
        return _Result(
            row=SimpleNamespace(
                _mapping={"id": 5, "kind": "kb_import", "status": "running"}
            )
        )


@pytest.mark.asyncio
async def test_claim_job_is_queued_to_running_transition():
    session = _ClaimSession()
    job = await jobs_store.claim_job(session, 5)
    assert job["status"] == "running"
    assert "status = 'running'" in session.sql
    assert "status = 'queued'" in session.sql


# ── API ───────────────────────────────────────────────────────────────────


class FakeService:
    def __init__(self):
        self.settings = SupportSettings()
        self.store = FakeJobStore()
        self.import_tasks: set = set()


@pytest.fixture
def fake_service():
    return FakeService()


@pytest.fixture
def override_imports(fake_service, monkeypatch):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    monkeypatch.setattr(imports_api.import_runner, "spawn", lambda service, job_id: None)
    yield fake_service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_import_creates_job(client: AsyncClient, override_imports):
    response = await client.post(
        "/api/support/kb/import",
        json={"kind": "text", "text": TEXT_SAMPLE, "dry_run": True},
    )
    assert response.status_code == 200
    job_id = response.json()["data"]["job_id"]
    assert override_imports.store.jobs[job_id]["status"] == "queued"
    assert override_imports.store.jobs[job_id]["payload"]["dry_run"] is True


@pytest.mark.asyncio
async def test_post_import_accepts_result_json_object(client: AsyncClient, override_imports):
    response = await client.post(
        "/api/support/kb/import",
        json={"kind": "result_json", "payload": _json_payload()},
    )
    assert response.status_code == 200
    job = override_imports.store.jobs[response.json()["data"]["job_id"]]
    assert job["payload"]["kind"] == "result_json"


@pytest.mark.asyncio
async def test_post_import_second_active_job_returns_409(client: AsyncClient, override_imports):
    await client.post("/api/support/kb/import", json={"kind": "text", "text": TEXT_SAMPLE})

    response = await client.post(
        "/api/support/kb/import", json={"kind": "text", "text": TEXT_SAMPLE}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_BUSY"


@pytest.mark.asyncio
async def test_post_import_too_large_returns_413(
    client: AsyncClient, override_imports, monkeypatch
):
    monkeypatch.setattr(imports_api.import_runner.tg_text, "MAX_TEXT_BYTES", 5)
    response = await client.post(
        "/api/support/kb/import", json={"kind": "text", "text": "0123456789"}
    )
    assert response.status_code == 413
    assert response.json()["code"] == "IMPORT_TOO_LARGE"
    assert override_imports.store.jobs == {}


@pytest.mark.asyncio
async def test_post_import_requires_body_for_kind(client: AsyncClient, override_imports):
    response = await client.post("/api/support/kb/import", json={"kind": "result_json"})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_get_import_job_returns_progress_and_result(client: AsyncClient, override_imports):
    job = await override_imports.store.create_job(
        kind=runner.JOB_KIND,
        payload={"kind": "text", "text": TEXT_SAMPLE},
    )
    await override_imports.store.update_job(int(job["id"]), progress=2, total=2)
    await override_imports.store.finish_job(
        int(job["id"]), status="done", result={"questions": 2}
    )

    response = await client.get(f"/api/support/kb/import/{job['id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "done"
    assert data["progress"] == 2
    assert data["result"] == {"questions": 2}
    assert data["finished_at"] is not None


@pytest.mark.asyncio
async def test_get_missing_import_job_returns_404(client: AsyncClient, override_imports):
    response = await client.get("/api/support/kb/import/999")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_cancel_import_job_marks_error_cancelled(client: AsyncClient, override_imports):
    job = await override_imports.store.create_job(
        kind=runner.JOB_KIND,
        payload={"kind": "text", "text": TEXT_SAMPLE},
    )

    response = await client.post(f"/api/support/kb/import/{job['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "error", "error": "cancelled"}


def test_check_size_rejects_json_over_limit(monkeypatch):
    monkeypatch.setattr(tg_json, "MAX_JSON_BYTES", 10)
    with pytest.raises(ImportTooLarge):
        runner.check_size("result_json", payload={"messages": ["0123456789"]})
