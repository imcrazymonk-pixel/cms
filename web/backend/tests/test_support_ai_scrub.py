"""B1b-1 — очистка переписки и замок исходящего ответа.

Покрывает §8 плана: `scrub` вычищает URL/ключи/UUID/карты/телефоны/IP/tg-id/
токены; `outbound.check` блокирует IP, домен вне allowlist, UUID, ключи,
PAN, hex, `vless://`, иероглифы и мета-слова, но пропускает обычный русский
текст и разрешённые домены.

Без сети и БД.
"""
import pytest

from web.backend.core.support.ai.outbound import check
from web.backend.core.support.ai.scrub import MASK, looks_sensitive, scrub

ALLOWED = ("hexaveil.xyz", "cabinet.fortf.ru")


# ── scrub ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "secret",
    [
        "vless://uuid@host:443?type=tcp",
        "sub://abcdef",
        "ss://YWVzOnBhc3M@host:8388",
        "https://cabinet.fortf.ru/sub/abc?token=secret",
        "ivan.petrov@example.com",
        "550e8400-e29b-41d4-a716-446655440000",
        "a" * 40,
        "1234 5678 9012 3456",
        "+7 999 123-45-67",
        "10.0.0.1",
        "123456789",
        "sk-abcdefghijklmnopqrst",
        "123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    ],
)
def test_scrub_masks_secret(secret):
    cleaned = scrub(f"до {secret} после")
    assert secret not in cleaned
    assert MASK in cleaned


def test_scrub_masks_plain_url():
    cleaned = scrub("Скачайте с https://example.com/file?token=abc и всё")
    assert "https://" not in cleaned
    assert "[скрыто]" in cleaned


def test_scrub_collapses_spaces_and_keeps_plain_text():
    assert scrub("Германия   не  подключается,  помогите") == "Германия не подключается, помогите"


def test_scrub_empty_and_idempotent():
    assert scrub("") == ""
    once = scrub("пиши на ivan@example.com")
    assert scrub(once) == once


def test_looks_sensitive():
    assert looks_sensitive("ключ " + "b" * 32)
    assert looks_sensitive("vless://abc")
    assert looks_sensitive("tg 123456789")
    assert not looks_sensitive("Германия не подключается")


# ── outbound: пропускаем нормальное ───────────────────────────────────────

def test_outbound_allows_plain_russian():
    verdict = check("Здравствуйте! Обновите подписку в личном кабинете и попробуйте снова.", ALLOWED)
    assert verdict["ok"] is True
    assert verdict["hits"] == []
    assert verdict["reason"] == ""


def test_outbound_does_not_trip_meta_ii_inside_russian_word():
    verdict = check("Проблема наблюдается в России и других регионах.", ALLOWED)
    assert verdict["ok"] is True


@pytest.mark.parametrize(
    "url",
    [
        "https://hexaveil.xyz",
        "https://hexaveil.xyz/faq?x=1",
        "http://cabinet.fortf.ru/",
        "https://CABINET.FORTF.RU/sub",
    ],
)
def test_outbound_allows_allowlist_domains(url):
    assert check(f"Откройте {url}", ALLOWED)["ok"] is True


def test_outbound_accepts_allowed_domains_as_csv():
    assert check("Сайт https://hexaveil.xyz", "hexaveil.xyz,cabinet.fortf.ru")["ok"] is True


# ── outbound: блокируем внутреннее ────────────────────────────────────────

@pytest.mark.parametrize(
    ("text", "hit"),
    [
        ("Сервер 10.0.0.1 недоступен", "ip-адрес"),
        ("Зайдите на https://evil.example.com", "домен вне allowlist"),
        ("Ваш ключ 550e8400-e29b-41d4-a716-446655440000", "uuid"),
        ("токен " + "a" * 40, "длинный ключ"),
        ("ключ sk-abcdefghijklmnopqrst", "ключ провайдера"),
        ("конфиг vless://uuid@host:443", "ссылка подписки"),
        ("бот 123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "токен бота"),
        ("карта 1234 5678 9012 3456", "номер карты"),
        ("[[link:unknown]]", "неизвестная ссылка"),
        ("你好, помогите", "иероглифы"),
        ("こんにちは", "иероглифы"),
        ("안녕하세요", "иероглифы"),
        ("Это ответ ИИ", "упоминание ИИ"),
        ("искусственный интеллект подсказал", "мета-слово"),
        ("нейросеть сгенерировала", "мета-слово"),
        ("модель уверена", "мета-слово"),
        ("в базе знаний нет ответа", "мета-слово"),
        ("см. КБ", "упоминание базы знаний"),
        ("промпт слишком длинный", "мета-слово"),
        ("ассистент отвечает", "мета-слово"),
    ],
)
def test_outbound_blocks_forbidden(text, hit):
    verdict = check(text, ALLOWED)
    assert verdict["ok"] is False
    assert hit in verdict["hits"]
    assert verdict["reason"]


def test_outbound_blocks_allowed_and_foreign_mixed():
    verdict = check("Наш сайт https://hexaveil.xyz, а это https://evil.example.com", ALLOWED)
    assert verdict["ok"] is False
    assert "домен вне allowlist" in verdict["hits"]


def test_outbound_does_not_block_allowed_domain_in_path():
    verdict = check("Инструкция: https://hexaveil.xyz/faq#cabinet.fortf.ru", ALLOWED)
    assert verdict["ok"] is True
