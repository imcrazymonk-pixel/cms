"""Терпимый разбор ответа модели.

Модель, даже с `response_format=json_object`, регулярно присылает почти-JSON:
фенсы ```` ```json ````, лишний текст до/после объекта, одинарные кавычки,
висячие запятые, повторы ключей, обрыв по лимиту токенов. Строгий `json.loads`
на таком падает — здесь разбор «как получится» по известным ключам контракта.

Модуль чистый: только stdlib, без I/O и без сети.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

# Контракт ответа. Порядок фиксирован планом §1.3.
DRAFT_KEYS: tuple[str, ...] = (
    "reply",
    "operator_note",
    "reason",
    "needs_human",
    "no_request",
    "clarify",
    "used",
    "confidence",
)

# Camel-case варианты, которые модели иногда пишут по инерции.
_ALIASES = {
    "operatorNote": "operator_note",
    "needsHuman": "needs_human",
    "noRequest": "no_request",
}

_KEY_ALT = "|".join(DRAFT_KEYS + tuple(_ALIASES))
_NEXT_KEY = re.compile(rf'^\s*,\s*"?(?:{_KEY_ALT})"?\s*:')
_ANY_KEY_LATER = re.compile(rf'"(?:{_KEY_ALT})"\s*:')
_BARE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*")
_BARE_TOKEN = re.compile(r"^[^,}\n]*")
_TAG = re.compile(r"<(think|thinking|reasoning|reflection|scratchpad)\b[^>]*>.*?</\1>", re.I | re.S)
_TAG_OPEN = re.compile(r"<(think|thinking|reasoning|reflection|scratchpad)\b[^>]*>.*$", re.I | re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_COMMENT_OPEN = re.compile(r"<!--.*$", re.S)
_FENCE = re.compile(r"```(?:json|JSON)?\s*\n?(.*?)(?:```|$)", re.S)


def _canon_key(key: str) -> str:
    return _ALIASES.get(key, key)


def _strip_fences(raw: str) -> str:
    """Снять ```-ограждение, если оно есть и внутри есть объект."""
    match = _FENCE.search(raw)
    if match and "{" in (match.group(1) or ""):
        return match.group(1).strip()
    return raw.strip()


def strip_thinking(raw: str) -> str:
    """Убрать размышления, HTML-комментарии и ```-фенсы.

    Незакрытый `<think>` означает, что модель не дошла до ответа: всё после
    тега — обрезанное размышление и в ответ не годится.
    """
    if not raw:
        return ""
    text = _TAG.sub("", raw)
    text = _TAG_OPEN.sub("", text)
    text = _COMMENT.sub("", text)
    text = _COMMENT_OPEN.sub("", text)
    return _strip_fences(text)


def extract_json(raw: str) -> str | None:
    """Первый цельный JSON-объект по балансу скобок (строки пропускаются).

    Наивный поиск от первой `{` до последней `}` ломается, если рядом есть
    текст со скобками. Возвращает None, если объект не закрыт.
    """
    text = strip_thinking(raw)
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        ch = text[index]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


@dataclass
class LenientValue:
    """Одно разобранное значение и признак обрыва."""

    value: Any = None
    truncated: bool = False


@dataclass
class LenientResult:
    """Пары по порядку (включая повторы ключей) и признак обрыва объекта."""

    pairs: list[tuple[str, LenientValue]] = field(default_factory=list)
    truncated: bool = False


@dataclass
class MergeResult:
    """Сведённые поля и множество ключей, чьи значения оборвались."""

    fields: dict[str, Any] = field(default_factory=dict)
    truncated: set[str] = field(default_factory=set)

    def __iter__(self):
        # Удобно и как объект, и как `fields, truncated = merge_pairs(...)`.
        yield self.fields
        yield self.truncated


def _decode_string(raw: str) -> str:
    escaped = raw.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    try:
        return json.loads(f'"{escaped}"')
    except (json.JSONDecodeError, ValueError):
        return raw.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def lenient_parse(text: str) -> LenientResult | None:
    """Разобрать первый объект в тексте «как получится».

    Кавычка внутри строки считается закрывающей только если за ней идёт
    известный ключ контракта или конец объекта; иначе это кавычка из текста
    ответа и она экранируется. Одинарные кавычки, голые ключи и висячие
    запятые допускаются.
    """
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None

    pairs: list[tuple[str, LenientValue]] = []
    i = start + 1
    n = len(text)

    def skip_ws() -> None:
        nonlocal i
        while i < n and text[i] in " \t\r\n,":
            i += 1

    while True:
        skip_ws()
        if i >= n:
            return LenientResult(pairs=pairs, truncated=True)
        if text[i] == "}":
            return LenientResult(pairs=pairs, truncated=False)

        # Ключ: в кавычках или голым словом.
        if text[i] in "\"'":
            quote = text[i]
            end = text.find(quote, i + 1)
            if end == -1:
                return LenientResult(pairs=pairs, truncated=True)
            key = text[i + 1 : end]
            i = end + 1
        else:
            bare = _BARE_KEY.match(text[i:])
            if not bare:
                return LenientResult(pairs=pairs, truncated=False) if pairs else None
            key = bare.group(0)
            i += len(key)
        key = _canon_key(key)

        while i < n and text[i].isspace():
            i += 1
        if i >= n or text[i] != ":":
            return LenientResult(pairs=pairs, truncated=i >= n) if pairs else None
        i += 1
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            return LenientResult(pairs=pairs, truncated=True)

        ch = text[i]
        if ch == '"':
            i += 1
            raw = ""
            closed = False
            while i < n:
                c = text[i]
                if c == "\\" and i + 1 < n:
                    raw += c + text[i + 1]
                    i += 2
                    continue
                if c == '"':
                    rest = text[i + 1 :]
                    ends_object = bool(re.match(r"^\s*}", rest)) and not _ANY_KEY_LATER.search(rest)
                    if _NEXT_KEY.match(rest) or ends_object or not rest.strip():
                        closed = True
                        i += 1
                        break
                    # Кавычка из текста ответа — экранируем и идём дальше.
                    raw += '\\"'
                    i += 1
                    continue
                raw += c
                i += 1
            pairs.append((key, LenientValue(value=_decode_string(raw), truncated=not closed)))
            if not closed:
                return LenientResult(pairs=pairs, truncated=True)
        elif ch == "'":
            # Одинарные кавычки: модели смешивают их с JSON, значение берём
            # до ближайшей одинарной кавычки.
            i += 1
            raw = ""
            closed = False
            while i < n:
                c = text[i]
                if c == "\\" and i + 1 < n:
                    raw += c + text[i + 1]
                    i += 2
                    continue
                if c == "'":
                    closed = True
                    i += 1
                    break
                raw += c
                i += 1
            pairs.append((key, LenientValue(value=_decode_string(raw), truncated=not closed)))
            if not closed:
                return LenientResult(pairs=pairs, truncated=True)
        elif ch == "[":
            end = text.find("]", i)
            body = text[i + 1 :] if end == -1 else text[i + 1 : end]
            items = [float(x) if "." in x else int(x) for x in re.findall(r"-?\d+(?:\.\d+)?", body)]
            pairs.append((key, LenientValue(value=items, truncated=end == -1)))
            if end == -1:
                return LenientResult(pairs=pairs, truncated=True)
            i = end + 1
        elif ch == "{":
            # Вложенные объекты контракту не нужны — пропускаем по балансу.
            depth = 0
            in_string = False
            while i < n:
                c = text[i]
                if in_string:
                    if c == "\\":
                        i += 1
                    elif c == '"':
                        in_string = False
                    i += 1
                    continue
                if c == '"':
                    in_string = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            pairs.append((key, LenientValue(value=None, truncated=depth != 0)))
            if depth != 0:
                return LenientResult(pairs=pairs, truncated=True)
        else:
            match = _BARE_TOKEN.match(text[i:])
            token = (match.group(0) if match else "").strip()
            i += len(match.group(0)) if match else 0
            value: Any = token
            if token.lower() == "true":
                value = True
            elif token.lower() == "false":
                value = False
            elif token.lower() == "null":
                value = None
            elif re.fullmatch(r"-?\d+(?:\.\d+)?", token):
                value = float(token) if "." in token else int(token)
            pairs.append((key, LenientValue(value=value, truncated=i >= n)))


def merge_pairs(pairs: Iterable[tuple[str, LenientValue]]) -> MergeResult:
    """Свести пары в поля.

    Повторённый `reply`: первое непустое значение (модель иногда начинает
    ответ заново и дописывает пустой). Остальные ключи — последнее значение,
    как у `json.loads`.
    """
    fields: dict[str, Any] = {}
    truncated: set[str] = set()
    for key, item in pairs:
        if key == "reply" and isinstance(fields.get("reply"), str) and fields["reply"].strip():
            continue
        fields[key] = item.value
        if item.truncated:
            truncated.add(key)
        else:
            truncated.discard(key)
    return MergeResult(fields=fields, truncated=truncated)


def parse_response(raw: str) -> MergeResult | None:
    """Строгий JSON → при неудаче терпимый разбор. Удобная обёртка конвейера."""
    block = extract_json(raw)
    if block is not None:
        try:
            parsed = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            return MergeResult(fields=parsed, truncated=set())

    result = lenient_parse(strip_thinking(raw))
    if result is None or not result.pairs:
        return None
    return merge_pairs(result.pairs)
