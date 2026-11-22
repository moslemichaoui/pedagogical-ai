"""Small, dependency-free text helpers shared by services and routes."""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Iterable, List, Optional

ARABIC_RANGES = (
    ("\u0600", "\u06ff"),
    ("\u0750", "\u077f"),
    ("\u08a0", "\u08ff"),
    ("\ufb50", "\ufdff"),
    ("\ufe70", "\ufeff"),
)

_TASHKEEL = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
_WHITESPACE = re.compile(r"[ \t\u00a0\u200b]+")
_NEWLINES = re.compile(r"\n{3,}")
_FENCE = re.compile(r"^\s*```(?:json|JSON)?\s*|\s*```\s*$")


def has_arabic(text: Optional[str]) -> bool:
    """Return True when *text* contains at least one Arabic codepoint."""
    if not text:
        return False
    return any(start <= char <= end for char in text for start, end in ARABIC_RANGES)


def arabic_ratio(text: Optional[str]) -> float:
    """Share of letters in *text* that are Arabic (0.0 – 1.0)."""
    if not text:
        return 0.0
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if has_arabic(c)) / len(letters)


def normalize_arabic(text: Optional[str]) -> str:
    """Normalise Arabic for matching: no diacritics, unified alef/ya/ta."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = _TASHKEEL.sub("", text)
    text = (
        text.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
        .replace("ة", "ه")
        .replace("ؤ", "و")
        .replace("ئ", "ي")
    )
    return _WHITESPACE.sub(" ", text).strip()


def clean_text(text: Optional[str]) -> str:
    """Collapse runaway whitespace without touching meaning."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE.sub(" ", text)
    return _NEWLINES.sub("\n\n", text).strip()


def truncate(text: Optional[str], limit: int, suffix: str = "…") -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - len(suffix))].rstrip() + suffix


def split_lines(value: Optional[str]) -> List[str]:
    """Turn a textarea value into a clean list of non-empty lines."""
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


def _balanced_object(text: str) -> Optional[str]:
    """Extract the first balanced ``{...}`` block, ignoring braces in strings."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def extract_json(text: Optional[str]) -> Optional[dict]:
    """Parse JSON from an LLM response, tolerating fences and prose."""
    if not text:
        return None
    candidates: List[str] = [text.strip(), _FENCE.sub("", text.strip())]
    block = _balanced_object(text)
    if block:
        candidates.append(block)
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def scale_durations(durations: Iterable[int], target: int) -> List[int]:
    """Scale positive durations so they sum exactly to *target*.

    Uses largest-remainder rounding, then fixes any drift on the largest slice
    so every value stays at least one minute.
    """
    values = [max(1, int(value or 1)) for value in durations]
    if not values:
        return []
    target = max(len(values), int(target))
    total = sum(values)
    if total == target:
        return values
    exact = [value * target / total for value in values]
    floors = [max(1, int(value)) for value in exact]
    remainder = target - sum(floors)
    order = sorted(range(len(values)), key=lambda i: exact[i] - floors[i], reverse=True)
    index = 0
    while remainder > 0:
        floors[order[index % len(order)]] += 1
        remainder -= 1
        index += 1
    while remainder < 0:
        # Take minutes back from the largest slice, never below one.
        biggest = max(range(len(floors)), key=lambda i: floors[i])
        if floors[biggest] <= 1:
            break
        floors[biggest] -= 1
        remainder += 1
    return floors


def parse_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def safe_filename(value: Optional[str], fallback: str = "document") -> str:
    """ASCII-safe slug for download names (Arabic titles are preserved in UI)."""
    if not value:
        return fallback
    value = unicodedata.normalize("NFKD", value)
    value = re.sub(r"[^\w\u0600-\u06FF\- ]+", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value[:80] or fallback
