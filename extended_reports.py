# -*- coding: utf-8 -*-
"""Additional operational and audit reports using existing SQLite tables only."""
from __future__ import annotations

import json

REPORTS = {
    "nid_errors": "تقرير أخطاء الرقم القومي",
    "biometric_errors": "تقرير تعارض النوع",
    "military_errors": "تقرير ملاحظات التجنيد",
    "seating_errors": "تقرير تكرار أرقام الجلوس",
    "imports": "سجل دفعات الاستيراد",
    "activity": "سجل نشاط المستخدمين",
    "workbook_learning": "تقرير تعلم أنماط ملفات Excel",
    "mapping_corrections": "تقرير تصحيحات ربط الأعمدة",
    "system_users": "ملخص حسابات المستخدمين",
}


def _json_object(value):
    try:
        result = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return result if isinstance(result, dict) else {}


def _contains(row, needle):
    if not needle:
        return True
    return needle in " ".join(str(value or "") for value in row.values()).casefold()


def build_extended_report(database, report_type, query="", limit=5000):
    """Return (title, rows, summary). Read-only; never exposes password hashes."""
    if report_type not in REPORTS:
        raise ValueError("نوع التقرير غير معروف.")
    limit = max(1, min(int(limit), 20000))
    needle = str(query or "").strip().casefold()

    with database._connection() as conn:
        if report_type in {"nid_errors", "biometric_errors", "military_errors", "seating_errors"}:
            flag_map = {
                "nid_errors": ("hasNidError",),
                "biometric_errors": ("hasBiometricError",),
                "military_errors": ("hasMilitaryError", "isCriticalMilitary"),
                "seating_errors": ("hasSeatingError",),
            }
            records = conn.execute(
                "SELECT id,name,student_code,national_id,source_file,audit_data "
                "FROM students ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
            rows = []
            for record in records:
                audit = _json_object(record["audit_data"])
                if not any(bool(audit.get(flag)) for flag in flag_map[report_type]):
                    continue
                row = {
                    "م": record["id"],
                    "اسم الطالب": record["name"],
                    "كود الطالب": record["student_code"],
                    "الرقم القومي/المعرف": record["national_id"],
                    "ملف المصدر": record["source_file"],
                    "تفاصيل الملاحظات": " | ".join(
                        str(note) for note in (audit.get("errorNotes") or [])
                    ),
                }
                if _contains(row, needle):
                    rows.append(row)
        elif report_type == "imports":
            records = conn.execute(
                "SELECT id,source_file,imported_count,imported_at "
                "FROM import_batches ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            rows = [{"رقم الدفعة": r["id"], "ملف المصدر": r["source_file"],
                     "عدد السجلات": r["imported_count"], "تاريخ الاستيراد": r["imported_at"]}
                    for r in records]
            rows = [r for r in rows if _contains(r, needle)]
        elif report_type == "activity":
            records = conn.execute(
                "SELECT username,action,details,created_at FROM activity_log "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            rows = [{"المستخدم": r["username"], "العملية": r["action"],
                     "التفاصيل": r["details"], "التاريخ": r["created_at"]}
                    for r in records]
            rows = [r for r in rows if _contains(r, needle)]
        elif report_type == "workbook_learning":
            records = conn.execute(
                "SELECT file_extension,sheet_name,header_count,confirmed_imports,last_seen "
                "FROM workbook_learning ORDER BY confirmed_imports DESC,last_seen DESC LIMIT ?",
                (limit,)
            ).fetchall()
            rows = [{"امتداد الملف": r["file_extension"], "ورقة العمل": r["sheet_name"],
                     "عدد الأعمدة": r["header_count"], "مرات الاستيراد المؤكدة": r["confirmed_imports"],
                     "آخر استخدام": r["last_seen"]} for r in records]
            rows = [r for r in rows if _contains(r, needle)]
        elif report_type == "mapping_corrections":
            records = conn.execute(
                "SELECT field_name,alias,file_extension,sheet_name,corrected_by,"
                "confirmation_count,created_at,last_confirmed "
                "FROM user_mapping_corrections ORDER BY confirmation_count DESC,last_confirmed DESC LIMIT ?",
                (limit,)
            ).fetchall()
            rows = [{"الحقل": r["field_name"], "العنوان البديل": r["alias"],
                     "امتداد الملف": r["file_extension"], "ورقة العمل": r["sheet_name"],
                     "صحح بواسطة": r["corrected_by"], "مرات التأكيد": r["confirmation_count"],
                     "تاريخ الإنشاء": r["created_at"], "آخر تأكيد": r["last_confirmed"]}
                    for r in records]
            rows = [r for r in rows if _contains(r, needle)]
        else:  # system_users: intentionally excludes all credential material
            records = conn.execute(
                "SELECT username,role,active,created_at FROM app_users ORDER BY username LIMIT ?",
                (limit,)
            ).fetchall()
            rows = [{"اسم المستخدم": r["username"], "الصلاحية": r["role"],
                     "الحساب نشط": "نعم" if r["active"] else "لا",
                     "تاريخ الإنشاء": r["created_at"]} for r in records]
            rows = [r for r in rows if _contains(r, needle)]

    return REPORTS[report_type], rows, {"total": len(rows), "limited_to": limit}
