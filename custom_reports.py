# -*- coding: utf-8 -*-
"""Safe, configurable reports over the fields StudentLedgerPro actually stores."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime

FIELD_LABELS = {
    "id": "رقم السجل",
    "name": "اسم الطالب",
    "student_code": "كود الطالب",
    "national_id": "الرقم القومي/المعرف",
    "is_expat": "وافد",
    "source_file": "ملف المصدر",
    "created_at": "تاريخ الإضافة",
    "updated_at": "تاريخ التعديل",
    "hasNidError": "خطأ الرقم القومي",
    "hasBiometricError": "تعارض النوع",
    "hasMilitaryError": "ملاحظة التجنيد",
    "isCriticalMilitary": "حالة تجنيد حرجة",
    "hasSeatingError": "تكرار رقم الجلوس",
    "errorNotes": "تفاصيل الملاحظات",
}
OPERATORS = {
    "eq", "ne", "contains", "not_contains", "starts_with",
    "gt", "gte", "lt", "lte", "between", "is_empty", "not_empty",
}
BASE_FIELDS = tuple(FIELD_LABELS)
FLAG_FIELDS = {"hasNidError", "hasBiometricError", "hasMilitaryError",
               "isCriticalMilitary", "hasSeatingError"}


def available_report_fields():
    return dict(FIELD_LABELS)


def _truth(value):
    return bool(value)


def _normal_value(row, field):
    if field in FLAG_FIELDS:
        return bool(row.get("_audit", {}).get(field))
    if field == "errorNotes":
        notes = row.get("_audit", {}).get("errorNotes") or []
        return " | ".join(str(x) for x in notes)
    if field == "is_expat":
        return bool(row.get(field))
    return row.get(field)


def _matches(actual, operator, expected):
    if operator not in OPERATORS:
        raise ValueError("عامل المقارنة غير مدعوم.")
    text = "" if actual is None else str(actual)
    target = "" if expected is None else str(expected)
    if operator == "is_empty":
        return not text.strip()
    if operator == "not_empty":
        return bool(text.strip())
    if operator == "contains":
        return target.casefold() in text.casefold()
    if operator == "not_contains":
        return target.casefold() not in text.casefold()
    if operator == "starts_with":
        return text.casefold().startswith(target.casefold())
    if operator in {"eq", "ne"}:
        if isinstance(actual, bool):
            wanted = target.casefold() in {"1", "true", "yes", "نعم", "وافد"}
            result = actual == wanted
        else:
            result = text.strip().casefold() == target.strip().casefold()
        return result if operator == "eq" else not result
    if operator in {"gt", "gte", "lt", "lte", "between"}:
        try:
            number = float(actual)
            low = float(expected[0]) if operator == "between" else float(expected)
            high = float(expected[1]) if operator == "between" else None
        except (TypeError, ValueError, IndexError):
            # ISO date/time values compare lexicographically in their stored form.
            if actual is None:
                return False
            number, low = text, target
            high = str(expected[1]) if operator == "between" else None
        if operator == "gt": return number > low
        if operator == "gte": return number >= low
        if operator == "lt": return number < low
        if operator == "lte": return number <= low
        return low <= number <= high
    return False


def build_custom_report(database, fields=None, filters=None, group_by=None,
                        sort_by=None, descending=False, limit=500, offset=0,
                        scan_limit=50000):
    """Build a report without accepting SQL fragments or changing stored records.

    Filters are dictionaries: {"field": "name", "op": "contains", "value": "أحمد"}.
    Grouping currently offers safe counts and expatriate/local counts.
    """
    fields = list(fields or ("id", "name", "student_code", "national_id", "is_expat", "source_file"))
    if not fields or any(field not in FIELD_LABELS for field in fields):
        raise ValueError("اختر حقولاً صحيحة للتقرير.")
    if len(set(fields)) != len(fields):
        raise ValueError("لا يمكن تكرار الحقل نفسه.")
    filters = list(filters or [])
    for rule in filters:
        if rule.get("field") not in FIELD_LABELS or rule.get("op") not in OPERATORS:
            raise ValueError("يوجد شرط تصفية غير صالح.")
        if rule["op"] == "between" and (not isinstance(rule.get("value"), (list, tuple)) or len(rule["value"]) != 2):
            raise ValueError("شرط النطاق يحتاج إلى قيمتين.")
    if group_by and group_by not in FIELD_LABELS:
        raise ValueError("حقل التجميع غير صالح.")
    if sort_by and sort_by not in FIELD_LABELS:
        raise ValueError("حقل الترتيب غير صالح.")

    limit = max(1, min(int(limit), 5000))
    offset = max(0, int(offset))
    scan_limit = max(1, min(int(scan_limit), 100000))
    with database._connection() as conn:
        records = [dict(row) for row in conn.execute(
            "SELECT id,name,student_code,national_id,is_expat,source_file,created_at,updated_at,audit_data "
            "FROM students ORDER BY id LIMIT ?", (scan_limit,)
        ).fetchall()]

    prepared = []
    for record in records:
        try:
            audit = json.loads(record.get("audit_data") or "{}")
        except (TypeError, ValueError):
            audit = {}
        record["_audit"] = audit if isinstance(audit, dict) else {}
        if all(_matches(_normal_value(record, rule["field"]), rule["op"], rule.get("value"))
               for rule in filters):
            prepared.append(record)

    if group_by:
        groups = defaultdict(lambda: {"count": 0, "expatriates": 0, "local": 0})
        for record in prepared:
            key = _normal_value(record, group_by)
            if isinstance(key, bool):
                key = "نعم" if key else "لا"
            if key in (None, ""):
                key = "غير محدد"
            item = groups[str(key)]
            item["count"] += 1
            item["expatriates"] += int(bool(record.get("is_expat")))
            item["local"] += int(not bool(record.get("is_expat")))
        grouped = [{"القيمة": key, "عدد الطلاب": value["count"],
                    "وافدون": value["expatriates"], "غير وافدين": value["local"]}
                   for key, value in groups.items()]
        grouped.sort(key=lambda row: row["عدد الطلاب"], reverse=True)
        total = len(grouped)
        rows = grouped[offset:offset + limit]
        columns = ["القيمة", "عدد الطلاب", "وافدون", "غير وافدين"]
    else:
        if sort_by:
            prepared.sort(key=lambda row: str(_normal_value(row, sort_by) or "").casefold(),
                          reverse=bool(descending))
        total = len(prepared)
        page = prepared[offset:offset + limit]
        columns = [FIELD_LABELS[field] for field in fields]
        rows = []
        for record in page:
            output = {}
            for field in fields:
                value = _normal_value(record, field)
                if field == "is_expat":
                    value = "نعم" if value else "لا"
                output[FIELD_LABELS[field]] = value if value is not None else ""
            rows.append(output)

    return {
        "title": "تقرير مخصص",
        "columns": columns,
        "rows": rows,
        "total_matched": total,
        "scanned": len(records),
        "truncated": len(records) >= scan_limit,
        "limit": limit,
        "offset": offset,
        "group_by": group_by,
    }


def export_report_excel(report, path):
    import pandas as pd
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(report["rows"], columns=report["columns"]).to_excel(
            writer, index=False, sheet_name="التقرير"
        )


def export_report_pdf(report, path):
    """Export an Arabic-capable PDF; requires reportlab + arabic-reshaper + python-bidi."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError as exc:
        raise RuntimeError("تصدير PDF العربي يحتاج تثبيت reportlab وarabic-reshaper وpython-bidi.") from exc

    import os
    candidates = [
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    ]
    font_path = next((candidate for candidate in candidates if os.path.isfile(candidate)), None)
    if not font_path:
        raise RuntimeError("لم يتم العثور على خط عربي مناسب لتصدير PDF.")
    pdfmetrics.registerFont(TTFont("StudentLedgerArabic", font_path))

    def rtl(value):
        return get_display(arabic_reshaper.reshape(str(value if value is not None else "")))

    doc = SimpleDocTemplate(path, pagesize=landscape(A4), rightMargin=20, leftMargin=20,
                            topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ArabicTitle", parent=styles["Title"],
                                 fontName="StudentLedgerArabic", alignment=TA_CENTER)
    cell_style = ParagraphStyle("ArabicCell", parent=styles["BodyText"],
                                fontName="StudentLedgerArabic", fontSize=7,
                                leading=9, alignment=TA_RIGHT)
    story = [Paragraph(rtl(report.get("title", "تقرير مخصص")), title_style),
             Spacer(1, 10),
             Paragraph(rtl("عدد النتائج: " + str(report["total_matched"])), cell_style),
             Spacer(1, 8)]
    matrix = [[Paragraph(rtl(column), cell_style) for column in report["columns"]]]
    for row in report["rows"]:
        matrix.append([Paragraph(rtl(row.get(column, "")), cell_style)
                       for column in report["columns"]])
    if len(matrix) == 1:
        matrix.append([Paragraph(rtl("لا توجد بيانات"), cell_style)] +
                      [Paragraph("", cell_style) for _ in report["columns"][1:]])
    table = Table(matrix, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "StudentLedgerArabic"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    if report.get("truncated"):
        story.extend([Spacer(1, 8), Paragraph(rtl("تنبيه: تم الوصول إلى حد فحص السجلات."), cell_style)])
    doc.build(story)
