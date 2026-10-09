"""Minimal parser for a theme.php definition file.

theme.php is a pure `return [ ... ];` literal (no function calls, no
variables): string keys/values, nested arrays, `=>`, commas. That subset is
parsed here so the API can read the theme's option schema directly from
templates/themes/<theme>/theme.php — the single source of truth — instead of
a hand-maintained Python mirror.

Supported tokens: comments (`//`, `/* */`), single/double quoted strings
(with `\\` escapes and `\n`/`\t`/`\r`), `=>`, `,`, `[`, `]`, and bare
scalars (true/false/null/int/float). Returns {} on any parse error so callers
can fall back to a static config.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

Bare = Tuple[str, str]  # (kind, text) — kind in {"str","bare","[","]","=>",","}


def _tokenize(src: str) -> List[Bare]:
    tokens: List[Bare] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            i = n if j < 0 else j + 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '#':
            j = src.find('\n', i)
            i = n if j < 0 else j + 1
            continue
        if src.startswith('=>', i):
            tokens.append(('=>', '=>'))
            i += 2
            continue
        if c in '[],':
            tokens.append((c, c))
            i += 1
            continue
        if c in ('"', "'"):
            quote = c
            j = i + 1
            buf: List[str] = []
            while j < n:
                ch = src[j]
                if ch == '\\' and j + 1 < n:
                    nxt = src[j + 1]
                    if nxt in ('\n', '\r'):  # line continuation
                        j += 2
                        continue
                    buf.append({'n': '\n', 't': '\t', 'r': '\r'}.get(nxt, nxt))
                    j += 2
                    continue
                if ch == quote:
                    break
                buf.append(ch)
                j += 1
            tokens.append(('str', ''.join(buf)))
            i = j + 1
            continue
        # bare scalar
        j = i
        while j < n and not src[j].isspace() and src[j] not in '[],':
            j += 1
        tokens.append(('bare', src[i:j]))
        i = j
    return tokens


def _parse_value(tokens: List[Bare], pos: int) -> Tuple[Any, int]:
    kind, text = tokens[pos]
    if kind == '[':
        pos += 1
        items: List[Tuple[str, Any, Any]] = []
        while tokens[pos][0] != ']':
            first, pos = _parse_value(tokens, pos)
            if tokens[pos][0] == '=>':
                pos += 1
                second, pos = _parse_value(tokens, pos)
                items.append(('kv', first, second))
            else:
                items.append(('v', first, None))
            if tokens[pos][0] == ',':
                pos += 1
        pos += 1  # consume ']'
        if items and all(it[0] == 'kv' for it in items):
            return {k: v for _, k, v in items}, pos
        return [it[1] for it in items], pos
    if kind == 'str':
        return text, pos + 1
    if kind == 'bare':
        if text == 'true':
            return True, pos + 1
        if text == 'false':
            return False, pos + 1
        if text in ('null', ''):
            return None, pos + 1
        try:
            return int(text), pos + 1
        except ValueError:
            pass
        try:
            return float(text), pos + 1
        except ValueError:
            pass
        return text, pos + 1
    raise ValueError(f"unexpected token {tokens[pos]!r}")


def parse_php_array(src: str) -> Dict[str, Any]:
    """Parse a `return [ ... ];` PHP literal into a Python dict."""
    tokens = _tokenize(src)
    try:
        idx = next(i for i, t in enumerate(tokens) if t[0] == 'bare' and t[1] == 'return')
    except StopIteration:
        return {}
    value, _ = _parse_value(tokens, idx + 1)
    return value if isinstance(value, dict) else {}


_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def load_theme_php(path: Path) -> Dict[str, Any]:
    """Parse a theme.php file, cached by mtime. Returns {} on any failure."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    key = str(path)
    cached = _CACHE.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        parsed = parse_php_array(path.read_text(encoding='utf-8'))
    except Exception:
        parsed = {}
    _CACHE[key] = (mtime, parsed)
    return parsed


def load_theme_options(root_path: Optional[str], theme: str) -> Optional[Dict[str, Any]]:
    """Return {"name":..., "options":...} parsed from theme.php, or None."""
    if not root_path:
        return None
    path = Path(root_path) / "templates" / "themes" / theme / "theme.php"
    parsed = load_theme_php(path)
    if not parsed:
        return None
    options = parsed.get("options")
    if not isinstance(options, dict):
        options = {}
    return {"name": parsed.get("name") or theme, "options": options}
