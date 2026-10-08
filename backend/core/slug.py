"""Slug generation — mirrors PHP helpers.php.

Two variants (both exist in PHP and are used in different places):
  - simple_slug(): inline regex used for posts/categories/pages
        strtolower(trim(preg_replace('/[^a-zA-Z0-9\\-]+/', '-', $s), '-'))
  - slugify(): full transliteration used by Post::setTags()
"""
import os
import re

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch",
    "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D",
    "Е": "E", "Ё": "Yo", "Ж": "Zh", "З": "Z", "И": "I",
    "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N",
    "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
    "У": "U", "Ф": "F", "Х": "H", "Ц": "C", "Ч": "Ch",
    "Ш": "Sh", "Щ": "Sch", "Ъ": "", "Ы": "Y", "Ь": "",
    "Э": "E", "Ю": "Yu", "Я": "Ya",
    "№": "",
}

_SIMPLE_RE = re.compile(r"[^a-zA-Z0-9\-]+")
_NAME_RE = re.compile(r"[^a-z0-9-]+")
_SLUGIFY_INVALID = re.compile(r"[^a-z0-9\s-]")
_SLUGIFY_COLLAPSE = re.compile(r"[\s-]+")


def simple_slug(text: str) -> str:
    """Inline slug used by posts create (no transliteration)."""
    text = _SIMPLE_RE.sub("-", text or "")
    return text.strip("-").lower()


def name_slug(text: str) -> str:
    """Category/page inline slug (class is lowercase-only in PHP)."""
    text = _NAME_RE.sub("-", text or "")
    return text.strip("-").lower()


def slugify(text: str) -> str:
    """Transliterating slug used by Post::setTags()."""
    text = "".join(_TRANSLIT.get(ch, ch) for ch in (text or ""))
    text = text.lower()
    text = _SLUGIFY_INVALID.sub("", text)
    text = _SLUGIFY_COLLAPSE.sub("-", text)
    text = text.strip("-")
    return text or os.urandom(6).hex()  # PHP uniqid() fallback
