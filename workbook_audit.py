# -*- coding: utf-8 -*-
"""Explainable, read-only audit of student records across Excel workbooks."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable
import re

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize(value: Any) -> str:
    value = "" if value is None else str(value).strip().translate(_DIGITS)
    return re.sub(r"[^0-9A-Za-zء-ي]", "", value).casefold()


def audit_workbooks(workbooks: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return findings with source coordinates; never modify or merge records.

    Expected workbook shape: {file, sheet, students:[{name, code, nationalId, ...}]}.
    Optional sourceRow is preserved when supplied by the importer.
    """
    workbooks = list(workbooks)
    records = []
    for book in workbooks:
        for index, student in enumerate(book.get("students", []), start=1):
            row = dict(student)
            records.append({
                "file": str(book.get("file", "")),
                "sheet": str(book.get("sheet", "")),
                "row": row.get("sourceRow", row.get("row", index)),
                "student": row,
            })

    findings: list[dict[str, Any]] = []

    def add(kind: str, severity: str, message: str, entries: list[int], field: str = ""):
        sources = []
        for idx in entries:
            rec = records[idx]
            sources.append({
                "file": rec["file"], "sheet": rec["sheet"], "row": rec["row"],
                "name": rec["student"].get("name", ""),
            })
        findings.append({
            "type": kind, "severity": severity, "field": field,
            "message": message, "sources": sources,
        })

    code_index: dict[str, list[int]] = defaultdict(list)
    nid_index: dict[str, list[int]] = defaultdict(list)
    for i, rec in enumerate(records):
        student = rec["student"]
        code = normalize(student.get("code"))
        nid = normalize(student.get("nationalId"))
        name = normalize(student.get("name"))
        if code:
            code_index[code].append(i)
        if nid:
            nid_index[nid].append(i)
        if not name:
            add("missing_name", "warning", "اسم الطالب غير موجود", [i], "name")
        if not code:
            add("missing_code", "warning", "كود الطالب غير موجود", [i], "code")
        if not nid:
            add("missing_national_id", "info", "الرقم القومي غير موجود", [i], "nationalId")

    for key, indices in code_index.items():
        if len(indices) > 1:
            sources = {(records[i]["file"], records[i]["sheet"]) for i in indices}
            if len(sources) < len(indices):
                add("duplicate_student_code", "error",
                    f"كود الطالب مكرر داخل مصدر واحد: {key}", indices, "code")
            else:
                names = {normalize(records[i]["student"].get("name")) for i in indices
                         if normalize(records[i]["student"].get("name"))}
                nids = {normalize(records[i]["student"].get("nationalId")) for i in indices
                        if normalize(records[i]["student"].get("nationalId"))}
                if len(names) > 1 or len(nids) > 1:
                    add("cross_file_identity_conflict", "error",
                        f"الكود نفسه مرتبط ببيانات هوية مختلفة: {key}", indices, "code")
                else:
                    add("cross_file_match", "info",
                        f"سجلات متطابقة محتملة للكود: {key} — راجع المصادر قبل الدمج", indices, "code")

    for key, indices in nid_index.items():
        if len(indices) > 1:
            codes = {normalize(records[i]["student"].get("code")) for i in indices
                     if normalize(records[i]["student"].get("code"))}
            names = {normalize(records[i]["student"].get("name")) for i in indices
                     if normalize(records[i]["student"].get("name"))}
            if len(codes) > 1 or len(names) > 1:
                add("national_id_collision", "error",
                    f"الرقم القومي مرتبط بأكثر من كود أو اسم: {key}", indices, "nationalId")

    counts = {level: sum(1 for item in findings if item["severity"] == level)
              for level in ("error", "warning", "info")}
    return {
        "workbook_count": len(workbooks),
        "record_count": len(records),
        "finding_count": len(findings),
        "severity_counts": counts,
        "findings": findings,
        "automatic_changes": 0,
    }
