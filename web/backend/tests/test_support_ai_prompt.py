"""B1b-2a — сборка промпта: scrub, нумерация КБ, operator_note, схема.

Без сети/БД. Проверяются §4.1 и §8 плана
`docs/plans/2026-11-28-support-stage-b.md`.
"""
from __future__ import annotations

from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.links import CustomerLink
from web.backend.core.support.ai.prompt import (
    DRAFT_SCHEMA,
    MAX_EXAMPLE_CHARS,
    MAX_MESSAGES,
    build_prompt,
    build_system_prompt,
    build_user_prompt,
)


def _config(**overrides) -> AiConfig:
    values = {
        "brand": "HexaVeil",
        "language": "ru",
        "allowed_domains": ("hexaveil.xyz", "cabinet.fortf.ru"),
        "require_kb": True,
    }
    values.update(overrides)
    return AiConfig(**values)


def test_draft_schema_is_compact_contract():
    assert DRAFT_SCHEMA == (
        '{"reply":"","operator_note":"","reason":"","needs_human":false,'
        '"no_request":false,"clarify":false,"used":[],"confidence":0.0}'
    )


def test_system_prompt_has_role_rules_and_separate_operator_note():
    system = build_system_prompt(_config())
    lowered = system.lower()

    assert "HexaVeil" in system
    assert "только факты" in lowered
    assert "не выполняй арифметику" in lowered
    assert "не выдумывай ссылки" in lowered
    assert "не упоминай ии" in lowered
    assert "максимум один уточняющий вопрос" in lowered
    assert "operator_note" in system
    assert "заметка для оператора" in lowered
    assert "никогда не смешивай" in lowered
    assert DRAFT_SCHEMA in system
    assert "на русском" in lowered


def test_system_prompt_english_and_links_block():
    config = _config(language="en")
    links = [
        CustomerLink(
            key="cabinet",
            title="Личный кабинет",
            url="https://cabinet.fortf.ru",
            when="нужно проверить подписку",
        )
    ]
    system = build_system_prompt(config, links=links)
    assert "Answer in English" in system
    assert "[[link:cabinet]]" in system
    assert "Личный кабинет" in system


def test_kb_chunks_are_numbered_and_citations_map_ids():
    chunks = [
        {"id": 10, "title": "Германия", "section": "Подключение", "body": "Обновите подписку."},
        {"id": 11, "title": "Оплата", "body": "Оплата картой."},
    ]
    user, citations = build_user_prompt(config=_config(), kb_chunks=chunks)

    assert "[1] Германия — Подключение" in user
    assert "[2] Оплата" in user
    assert [c.index for c in citations] == [1, 2]
    assert [c.doc_id for c in citations] == [10, 11]
    assert citations[0].title == "Германия"
    assert citations[0].section == "Подключение"


def test_conversation_and_examples_are_scrubbed():
    unique_uuid = "123e4567-e89b-12d3-a456-426614174000"
    provider_key = "sk-abcdefgh12345678"
    messages = [
        {
            "direction": "in",
            "author": "client",
            "text": (
                f"Не работает. Вот ключ vless://secret-token и UUID {unique_uuid}, "
                f"сайт https://evil.example/private, токен {provider_key}"
            ),
        },
        {
            "direction": "out",
            "author": "agent",
            "text": "Пришлите email user@example.com или телефон +7 999 123-45-67",
        },
    ]
    examples = [
        {
            "question": "Как подключиться?",
            "answer": f"Откройте https://evil.example/help или напишите {provider_key}",
        }
    ]

    prompt = build_prompt(
        config=_config(),
        messages=messages,
        examples=examples,
        messages_newest_first=False,
    )
    combined = prompt.system + "\n" + prompt.user

    assert "vless://secret-token" not in combined
    assert unique_uuid not in combined
    assert "https://evil.example" not in combined
    assert provider_key not in combined
    assert "user@example.com" not in combined
    assert "+7 999 123-45-67" not in combined
    assert "[скрыто]" in combined


def test_messages_are_chronological_and_limited():
    oldest = [
        {"direction": "in", "text": f"сообщение {index}", "created_at": index}
        for index in range(MAX_MESSAGES + 5)
    ]
    # store отдаёт новые сверху: переворачиваем, чтобы получить хронологию.
    newest_first = list(reversed(oldest))
    user, _ = build_user_prompt(
        config=_config(),
        messages=newest_first,
        messages_newest_first=True,
    )

    positions = [user.index(f"Клиент: сообщение {index}") for index in range(5, MAX_MESSAGES + 5)]
    assert positions == sorted(positions)
    assert "Клиент: сообщение 0" not in user


def test_examples_are_clipped():
    answer = "Ответ " + ("x" * (MAX_EXAMPLE_CHARS + 100))
    user, _ = build_user_prompt(
        config=_config(),
        examples=[{"question": "вопрос", "answer": answer}],
    )
    assert "…" in user
    assert "x" * (MAX_EXAMPLE_CHARS + 50) not in user


def test_safe_customer_card_excludes_personal_data():
    card = {
        "tariff": "Pro",
        "status": "active",
        "expires_at": "2027-01-01",
        "device_count": 3,
        "email": "user@example.com",
        "phone": "+7 999 123-45-67",
        "username": "@private_login",
        "display_name": "Иван Иванов",
        "sub_link": "vless://secret",
    }
    user, _ = build_user_prompt(config=_config(), customer_card=card)

    assert "Карточка клиента" in user
    assert "тариф: Pro" in user
    assert "статус: active" in user
    assert "количество устройств: 3" in user
    assert "user@example.com" not in user
    assert "+7 999 123-45-67" not in user
    assert "@private_login" not in user
    assert "Иван Иванов" not in user
    assert "vless://secret" not in user


def test_card_without_safe_fields_is_omitted():
    user, _ = build_user_prompt(
        config=_config(),
        customer_card={"email": "user@example.com", "username": "@private"},
    )
    assert "Карточка клиента" not in user


def test_client_question_is_scrubbed():
    user, _ = build_user_prompt(
        config=_config(),
        client_text="Мой IP 10.20.30.40, почта user@example.com",
    )
    assert "10.20.30.40" not in user
    assert "user@example.com" not in user
    assert "[скрыто]" in user
