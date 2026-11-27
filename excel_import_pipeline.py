# -*- coding: utf-8 -*-
"""Unified, review-first import preparation for StudentLedgerPro.

This module is intentionally deterministic and offline. It prepares a normalized
view of extracted student records while retaining the original cells and source
coordinates. It never writes to SQLite or merges/deletes records.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


CANONICAL_FIELDS = ("name", "code", "nationalId", "isExpat")


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def prepare_import_preview(
    students: Iterable[dict[str, Any]],
    *,
    source_file: str = "",
    source_sheet: str = "",
    table_index: int = 1,
) -> dict[str, Any]:
    """Return canonical rows, warnings and duplicate groups without persisting.

    The incoming student dictionaries are copied. Original cell arrays and audit
    fields are retained; missing values remain empty rather than being guessed.
    """
    rows = []
    warnings = []
    code_buckets: dict[str, list[int]] = defaultdict(list)
    nid_buckets: dict[str, list[int]] = defaultdict(list)

    for index, original in enumerate(students):
        student = dict(original)
        cells = list(student.get("cells") or [])
        canonical = {
            "name": _text(student.get("name")),
            "code": _text(student.get("code")),
            "nationalId": _text(student.get("nationalId")),
            "isExpat": bool(student.get("isExpat", False)),
        }
        row_warnings = []
        if not canonical["name"]:
            row_warnings.append("اسم الطالب غير محدد")
        if not canonical["code"] and not canonical["nationalId"]:
            row_warnings.append("لا يوجد كود طالب أو رقم قومي للمراجعة")
        if canonical["code"]:
            code_buckets[canonical["code"]].append(index)
        if canonical["nationalId"] and not canonical["isExpat"]:
            nid_buckets[canonical["nationalId"]].append(index)

        rows.append({
            **canonical,
            "cells": cells,
            "audit": dict(student),
            "source_file": source_file,
            "source_sheet": source_sheet,
            "source_row": student.get("sourceRow"),
            "table_index": int(table_index),
            "review_warnings": row_warnings,
        })
        if row_warnings:
            warnings.append({"record_index": index, "messages": row_warnings})

    duplicate_groups = []
    for field, buckets in (("code", code_buckets), ("nationalId", nid_buckets)):
        for value, indices in buckets.items():
            if len(indices) > 1:
                duplicate_groups.append({
                    "field": field,
                    "value": value,
                    "record_indices": indices,
                    "requires_review": True,
                })

    return {
        "rows": rows,
        "row_count": len(rows),
        "warning_count": len(warnings),
        "warnings": warnings,
        "duplicate_groups": duplicate_groups,
        "duplicate_group_count": len(duplicate_groups),
        "source": {
            "file": source_file,
            "sheet": source_sheet,
            "table_index": int(table_index),
        },
        "ready_to_commit": not warnings and not duplicate_groups,
    }


def select_preview_rows(preview: dict[str, Any], approved_indices: Iterable[int]) -> list[dict[str, Any]]:
    """Select explicitly approved preview rows; invalid indices are ignored."""
    rows = preview.get("rows") or []
    selected = []
    seen = set()
    for raw_index in approved_indices:
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= len(rows) or index in seen:
            continue
        seen.add(index)
        row = rows[index]
        # Convert back to the established StudentDatabase import contract.
        student = dict(row.get("audit") or {})
        student.update({
            "name": row["name"],
            "code": row["code"],
            "nationalId": row["nationalId"],
            "isExpat": row["isExpat"],
            "cells": list(row["cells"]),
            "sourceSheet": row["source_sheet"],
            "sourceRow": row["source_row"],
            "sourceTable": row["table_index"],
        })
        selected.append(student)
    return selected
