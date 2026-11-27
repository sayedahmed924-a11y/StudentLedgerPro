# -*- coding: utf-8 -*-
"""Explainable deterministic column assignment for Excel imports."""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Iterable


def explain_assignments(candidates: Iterable[tuple], columns: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose a one-to-one mapping and retain score evidence and alternatives.

    Candidate tuple format: (combined_score, field, column_index, header_score, content_score).
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        if len(item) < 5:
            continue
        score, field, column_index, header_score, content_score = item[:5]
        if column_index < 0 or column_index >= len(columns):
            continue
        grouped[str(field)].append({
            "field": str(field), "column_index": int(column_index),
            "header": str(columns[column_index].get("name", "")),
            "score": round(float(score), 2),
            "header_score": round(float(header_score), 2),
            "content_score": round(float(content_score), 2),
        })
    ordered = sorted(
        (candidate for values in grouped.values() for candidate in values),
        key=lambda item: (item["score"], item["header_score"], item["content_score"]),
        reverse=True,
    )
    assigned_fields, assigned_columns, selected = set(), set(), {}
    for candidate in ordered:
        field, col = candidate["field"], candidate["column_index"]
        if field in assigned_fields or col in assigned_columns:
            continue
        assigned_fields.add(field)
        assigned_columns.add(col)
        alternatives = sorted(grouped[field], key=lambda x: x["score"], reverse=True)
        gap = candidate["score"] - (alternatives[1]["score"] if len(alternatives) > 1 else 0)
        if candidate["score"] >= 80 and gap >= 10:
            confidence = "high"
        elif candidate["score"] >= 60:
            confidence = "medium"
        else:
            confidence = "low"
        reasons = []
        if candidate["header_score"] >= 60:
            reasons.append("تشابه عنوان العمود مع أسماء الحقل المعروفة")
        if candidate["content_score"] >= 60:
            reasons.append("محتوى الخلايا يتوافق مع نمط الحقل")
        if not reasons:
            reasons.append("تطابق محدود؛ يحتاج مراجعة بشرية")
        selected[field] = {
            **candidate, "confidence": confidence,
            "reason": "، ".join(reasons),
            "score_gap": round(gap, 2),
            "alternatives": alternatives[:3],
            "review_required": confidence != "high",
        }
    return {
        "assignments": selected,
        "assigned_count": len(selected),
        "review_count": sum(1 for item in selected.values() if item["review_required"]),
        "unassigned_fields": sorted(set(grouped) - set(selected)),
    }
