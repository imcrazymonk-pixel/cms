"""Tests for the login rate limiter (mirrors Remnawave login_guard)."""
from web.backend.core.rate_limit import LoginGuard


def test_login_guard_blocks_after_max_attempts():
    g = LoginGuard(max_attempts=3, window_seconds=60)
    assert g.is_blocked("1.2.3.4") is False
    for _ in range(3):
        g.record_failure("1.2.3.4")
    assert g.is_blocked("1.2.3.4") is True


def test_login_guard_reset():
    g = LoginGuard(max_attempts=2, window_seconds=60)
    g.record_failure("5.6.7.8")
    g.record_failure("5.6.7.8")
    assert g.is_blocked("5.6.7.8") is True
    g.reset("5.6.7.8")
    assert g.is_blocked("5.6.7.8") is False


def test_login_guard_per_key_isolation():
    g = LoginGuard(max_attempts=1, window_seconds=60)
    g.record_failure("a")
    assert g.is_blocked("a") is True
    assert g.is_blocked("b") is False


def test_login_guard_window_expiry():
    g = LoginGuard(max_attempts=1, window_seconds=-1)  # negative window → always expired
    g.record_failure("x")
    assert g.is_blocked("x") is False
