"""Tests for the theme.php parser (single source of truth for theme options)."""
from pathlib import Path

from web.backend.core.theme_config import _HEXAVEIL
from web.backend.core.theme_php import load_theme_options, parse_php_array

REPO_ROOT = Path(__file__).resolve().parents[3]
THEME_PHP = REPO_ROOT / "templates" / "themes" / "hexaveil" / "theme.php"


def test_parse_php_array_basics():
    src = """<?php
    // comment
    return [
        'name' => 'Test',
        'options' => [
            'Group' => [
                'a' => ['label' => 'A', 'type' => 'text', 'default' => 'x'],
                'b' => ['label' => 'B', 'type' => 'select', 'options' => ['1' => 'Yes', '0' => 'No'], 'default' => '1'],
            ],
        ],
    ];
    """
    parsed = parse_php_array(src)
    assert parsed["name"] == "Test"
    assert parsed["options"]["Group"]["b"]["options"] == {"1": "Yes", "0": "No"}


def test_double_quoted_newlines():
    src = '<?php return ["k" => "a\\nb\\nc"];'
    parsed = parse_php_array(src)
    assert parsed["k"] == "a\nb\nc"


def test_hexaveil_theme_php_matches_mirror():
    assert THEME_PHP.is_file(), f"missing {THEME_PHP}"
    parsed = parse_php_array(THEME_PHP.read_text(encoding="utf-8"))
    assert parsed["name"] == _HEXAVEIL["name"]
    assert parsed["options"] == _HEXAVEIL["options"]


def test_load_theme_options_from_repo_root():
    loaded = load_theme_options(str(REPO_ROOT), "hexaveil")
    assert loaded is not None
    assert loaded["name"] == "HexaVeil (лендинг)"
    assert loaded["options"] == _HEXAVEIL["options"]


def test_load_theme_options_missing_theme():
    assert load_theme_options(str(REPO_ROOT), "does-not-exist") is None
    assert load_theme_options(None, "hexaveil") is None


def test_get_theme_config_prefers_theme_php(tmp_path, monkeypatch):
    theme_dir = tmp_path / "templates" / "themes" / "hexaveil"
    theme_dir.mkdir(parents=True)
    (theme_dir / "theme.php").write_text(
        "<?php return ['name' => 'FromFile', 'options' => "
        "['G' => ['k' => ['label' => 'L', 'type' => 'text', 'default' => 'D']]]];",
        encoding="utf-8",
    )

    class _Settings:
        root_path = str(tmp_path)

    monkeypatch.setattr("web.backend.core.config.get_cms_settings", lambda: _Settings())

    from web.backend.core.theme_config import get_theme_config

    cfg = get_theme_config("hexaveil")
    assert cfg["name"] == "FromFile"
    assert cfg["options"] == {"G": {"k": {"label": "L", "type": "text", "default": "D"}}}
