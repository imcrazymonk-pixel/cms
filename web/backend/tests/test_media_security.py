"""Security tests for media path handling (path traversal protection)."""
from web.backend.api.v1.media import safe_public_path


def test_safe_path_ok(monkeypatch):
    monkeypatch.setenv("PUBLIC_DIR", "/tmp/pub")
    from web.backend.core.config import get_cms_settings
    get_cms_settings.cache_clear()
    p = safe_public_path("/public/uploads/a.jpg")
    assert p is not None
    assert "uploads" in str(p) and "a.jpg" in str(p)


def test_safe_path_traversal_rejected(monkeypatch):
    monkeypatch.setenv("PUBLIC_DIR", "/tmp/pub")
    from web.backend.core.config import get_cms_settings
    get_cms_settings.cache_clear()
    assert safe_public_path("/public/../etc/passwd") is None
    assert safe_public_path("../../etc/passwd") is None
