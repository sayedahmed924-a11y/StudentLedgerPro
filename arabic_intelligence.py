# -*- coding: utf-8 -*-
"""Lightweight Arabic text intelligence helpers for StudentLedgerPro.

PyArabic is optional at runtime: a small built-in fallback keeps the application
usable on older PCs and in minimal/offline installations.
"""
from __future__ import annotations

import re
from typing import Iterable

try:
    from pyarabic import araby as _araby
except ImportError:
    _araby = None

try:
    from rapidfuzz import fuzz as _fuzz
except ImportError:
    _fuzz = None

_ARABIC_MARKS = re.compile(r"[\u064B-\u065F\u0670]")
_SPACES = re.compile(r"\s+")
_SEPARATORS = re.compile(r"[-_,.]")


def normalize_arabic_text(value: object) -> str:
    """Normalize Arabic text for matching without changing stored source data."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""
    if _araby is not None:
        text = _araby.strip_tashkeel(text)
        text = _araby.strip_tatweel(text)
    else:
        text = text.replace("ـ", "")
        text = _ARABIC_MARKS.sub("", text)
    # Keep the application's established header-matching conventions.
    text = re.sub(r"[أإآ]", "ا", text).replace("ة", "ه").replace("ى", "ي")
    text = _SEPARATORS.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def similarity_score(left: object, right: object) -> float:
    """Return a 0..100 name similarity score; a hint for human review, not a verdict."""
    a, b = normalize_arabic_text(left), normalize_arabic_text(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    if _fuzz is not None:
        return float(max(_fuzz.ratio(a, b), _fuzz.token_sort_ratio(a, b)))
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() * 100.0


def find_possible_duplicate_names(names: Iterable[object], threshold: float = 90.0) -> list[dict[str, object]]:
    """Return review suggestions only; never merges or deletes student records."""
    clean = [(index, str(name or "").strip()) for index, name in enumerate(names)]
    clean = [(index, name) for index, name in clean if name]
    suggestions: list[dict[str, object]] = []
    for pos, (left_index, left_name) in enumerate(clean):
        for right_index, right_name in clean[pos + 1:]:
            score = similarity_score(left_name, right_name)
            if score >= threshold:
                suggestions.append({
                    "left_index": left_index,
                    "right_index": right_index,
                    "left_name": left_name,
                    "right_name": right_name,
                    "score": round(score, 2),
                    "reason": "تشابه في كتابة الاسم بعد تطبيع النص العربي",
                })
    return suggestions
