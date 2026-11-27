# -*- coding: utf-8 -*-
"""Lightweight academic reports based only on persisted StudentLedgerPro fields."""
from __future__ import annotations

import json
from collections import Counter

REPORTS = {
    "all_students": "كشف جميع الطلاب",
    "expatriates": "كشف الطلاب الوافدين",
    "local_students": "كشف الطلاب غير المصنفين كوافدين",
    "missing_identity": "طلاب ببيانات تعريف ناقصة",
    "audit_issues": "طلاب لديهم ملاحظات تدقيق",
    "source_summary": "ملخص الطلاب حسب ملف المصدر",
}


def _safe_json(value, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def build_academic_report(database, report_type="all_students", query=""):
    """Return (Arabic title, rows, summary); does not infer academic year/class/status."""
    if report_type not in REPORTS:
        raise ValueError("نوع التقرير غير معروف.")
    sql = """
        SELECT id,name,student_code,national_id,is_expat,source_file,
               row_data,audit_data,created_at,updated_at
        FROM students ORDER BY id
    """
    with database._connection() as conn:
        records = [dict(row) for row in conn.execute(sql).fetchall()]

    needle = str(query or "").strip().casefold()
    filtered = []
    for item in records:
        name = str(item.get("name") or "")
        code = str(item.get("student_code") or "")
        nid = str(item.get("national_id") or "")
        if needle and needle not in " ".join((name, code, nid, str(item.get("source_file") or ""))).casefold():
            continue
        audit = _safe_json(item.get("audit_data"), {})
        notes = audit.get("errorNotes") or []
        has_issue = any(bool(audit.get(key)) for key in (
            "hasNidError", "hasBiometricError", "hasMilitaryError",
            "isCriticalMilitary", "hasSeatingError"
        )) or bool(notes)
        if report_type == "expatriates" and not item["is_expat"]:
            continue
        if report_type == "local_students" and item["is_expat"]:
            continue
        if report_type == "missing_identity" and all((name.strip(), code.strip(), nid.strip())):
            continue
        if report_type == "audit_issues" and not has_issue:
            continue
        item["_audit"] = audit
        item["_notes"] = notes
        filtered.append(item)

    if report_type == "source_summary":
        counts = Counter(str(row.get("source_file") or "غير محدد") for row in filtered)
        rows = [{"ملف المصدر": source, "عدد الطلاب": count}
                for source, count in sorted(counts.items(), key=lambda pair: pair[0].casefold())]
    else:
        rows = []
        for item in filtered:
            audit = item["_audit"]
            rows.append({
                "م": item["id"],
                "اسم الطالب": item["name"],
                "كود الطالب": item["student_code"],
                "الرقم القومي/المعرف": item["national_id"],
                "التصنيف": "وافد" if item["is_expat"] else "غير وافد",
                "ملف المصدر": item["source_file"],
                "أخطاء الرقم القومي": "نعم" if audit.get("hasNidError") else "لا",
                "تعارض النوع": "نعم" if audit.get("hasBiometricError") else "لا",
                "ملاحظات التجنيد": "نعم" if (audit.get("hasMilitaryError") or audit.get("isCriticalMilitary")) else "لا",
                "تكرار رقم الجلوس": "نعم" if audit.get("hasSeatingError") else "لا",
                "تفاصيل الملاحظات": " | ".join(str(note) for note in item["_notes"]),
                "تاريخ الإضافة": item["created_at"],
            })
    total = len(filtered)
    summary = {
        "total": total,
        "expatriates": sum(1 for item in filtered if item["is_expat"]),
        "local": sum(1 for item in filtered if not item["is_expat"]),
        "missing_name": sum(1 for item in filtered if not str(item.get("name") or "").strip()),
        "missing_code": sum(1 for item in filtered if not str(item.get("student_code") or "").strip()),
        "missing_national_id": sum(1 for item in filtered if not str(item.get("national_id") or "").strip()),
    }
    return REPORTS[report_type], rows, summary
