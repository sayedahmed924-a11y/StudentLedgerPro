# -*- coding: utf-8 -*-
"""Offline cross-workbook relationship analysis for student records."""
from __future__ import annotations
from collections import defaultdict
import re
from typing import Any, Iterable

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

def _key(value: Any) -> str:
    text = "" if value is None else str(value).strip().translate(_DIGITS)
    return re.sub(r"[^0-9A-Za-zء-ي]", "", text).lower()

def analyze_workbooks(workbooks: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Compare rows from multiple workbook results; do not merge or choose winners.

    Each input item: {file, sheet, students:[{name,code,nationalId,...}]}.
    Matches require a strong exact normalized key (student code or national ID).
    Conflicting non-empty values are returned for human review.
    """
    workbooks = list(workbooks)
    records = []
    for book in workbooks:
        for student in book.get("students", []):
            records.append({
                "file": str(book.get("file", "")),
                "sheet": str(book.get("sheet", "")),
                "student": dict(student),
            })
    indexes: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, record in enumerate(records):
        student = record["student"]
        for field in ("code", "nationalId"):
            value = _key(student.get(field))
            if value:
                indexes[(field, value)].append(i)
    groups = []
    seen = set()
    for (field, value), indices in indexes.items():
        unique = sorted(set(indices))
        if len(unique) < 2:
            continue
        identity = (field, value, tuple(unique))
        if identity in seen:
            continue
        seen.add(identity)
        names = sorted({_key(records[i]["student"].get("name")) for i in unique if _key(records[i]["student"].get("name"))})
        codes = sorted({_key(records[i]["student"].get("code")) for i in unique if _key(records[i]["student"].get("code"))})
        nids = sorted({_key(records[i]["student"].get("nationalId")) for i in unique if _key(records[i]["student"].get("nationalId"))})
        groups.append({
            "match_field": field, "normalized_key": value,
            "record_indices": unique,
            "sources": [{"file": records[i]["file"], "sheet": records[i]["sheet"], "name": records[i]["student"].get("name", "")} for i in unique],
            "conflict": len(names) > 1 or len(codes) > 1 or len(nids) > 1,
            "requires_review": True,
        })
    return {
        "workbook_count": len(workbooks),
        "record_count": len(records),
        "match_group_count": len(groups),
        "conflict_count": sum(1 for group in groups if group["conflict"]),
        "match_groups": groups,
        "records": records,
        "automatic_merge_performed": False,
    }
