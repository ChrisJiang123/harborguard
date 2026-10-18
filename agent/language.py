"""Output language and text budgets; transport contract character caps stay unchanged."""
from __future__ import annotations

import os
import re

CJK = re.compile(r"[\u4e00-\u9fff]")
WORD_LIMITS = {"summary": 25, "explanation": 120, "uncertainties": 15}
CHAR_LIMITS = {"summary": 60, "explanation": 300, "uncertainties": 40}
CONTACT_NAMES = {
    "uuv": "underwater vehicle",
    "fish_school": "school of fish",
    "debris": "debris",
    "marine_mammal": "marine mammal",
    "unknown": "unidentified contact",
}


def language(value: str | None = None) -> str:
    value = (os.environ.get("AGENT_LANG", "en") if value is None else value).strip().lower()
    if value not in {"en", "zh"}:
        raise ValueError("AGENT_LANG must be en or zh")
    return value


def text_errors(draft, lang: str | None = None) -> list[str]:
    lang = language(lang)
    errors = []
    for field, values in (("summary", [draft.summary]), ("explanation", [draft.explanation]),
                          ("uncertainties", draft.uncertainties)):
        for text in values:
            if lang == "en" and CJK.search(text):
                errors.append(f"{field} must be English (CJK output rejected)")
            length = len(text.split()) if lang == "en" else len(text)
            limit = WORD_LIMITS[field] if lang == "en" else CHAR_LIMITS[field]
            if length > limit:
                errors.append(f"{field} exceeds {limit} {'words' if lang == 'en' else 'characters'}")
    return errors


def clip_field(text: str, field: str, lang: str | None = None) -> str:
    lang = language(lang)
    text = text.strip()
    if lang == "en":
        text = " ".join(text.split()[:WORD_LIMITS[field]])
    # Contract v1 also imposes hard character caps at the backend boundary.
    limit = CHAR_LIMITS[field]
    if len(text) <= limit:
        return text
    shortened = text[:limit - 1]
    if lang == "en" and " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return shortened + "…"
