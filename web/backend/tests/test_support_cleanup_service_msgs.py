"""Service-bot notification classifier used by import and cleanup."""
import pytest

from tools.support_cleanup_service_msgs import is_service_bot_text


@pytest.mark.parametrize(
    "text",
    [
        "🧾 Новый чек NaloGO создан\n💰 Сумма: 150 ₽",
        "💎 ПРОДЛЕНИЕ ПОДПИСКИ\n👤 Nov4ick",
        "🤖 АВТОМАТИЧЕСКАЯ СМЕНА ПРОМОГРУППЫ",
        "🤖 Remnawave Bedolaga Bot\n✅ Бот успешно запущен",
        "⚠️ Ошибка во время работы\nТип: ConnectError",
        "ℹ️ ТЕХНИЧЕСКИЕ РАБОТЫ",
        "✅ СИСТЕМА БЕКАПОВ\n✅ Бекап успешно создан",
        "🛠 VPN не работает? Пожалуйста, опишите проблему",
    ],
)
def test_service_bot_text_detected(text):
    assert is_service_bot_text(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "Здравствуйте! Не работает VPN",
        "Проверьте подписку и перезапустите клиент",
        "Да",
        "Спасибо, помогло",
        "",
    ],
)
def test_real_dialog_text_not_matched(text):
    assert is_service_bot_text(text) is False
