# -*- coding: utf-8 -*-
from student_database import StudentDatabase


def test_reference_comparison_reports_new_missing_and_changed_students(tmp_path):
    db = StudentDatabase(tmp_path / "roster.sqlite3")
    reference = [
        {"name": "Ali", "code": "10", "nationalId": "1001"},
        {"name": "Mona", "code": "20", "nationalId": "2002"},
        {"name": "Sara", "code": "30", "nationalId": "3003"},
    ]
    batch = db.import_students(reference, "old.xlsx")
    db.record_student_history(reference, "2025/2026", "old.xlsx", batch)
    current = [
        {"name": "Ali", "code": "10", "nationalId": "1001"},
        {"name": "Mona Ahmed", "code": "25", "nationalId": "2002"},
        {"name": "New Student", "code": "40", "nationalId": "4004"},
    ]
    result = db.compare_with_reference_roster(current, "2025/2026")
    assert len(result["new_students"]) == 1
    assert result["new_students"][0]["name"] == "New Student"
    assert len(result["missing_students"]) == 1
    assert result["missing_students"][0]["name"] == "Sara"
    assert len(result["changed_students"]) == 1
    assert result["changed_students"][0]["old_code"] == "20"


def test_reference_periods_are_listed_and_comparison_is_explicit(tmp_path):
    db = StudentDatabase(tmp_path / "roster.sqlite3")
    students = [{"name": "Ali", "code": "1", "nationalId": "123"}]
    db.record_student_history(students, "2024/2025", "a.xlsx")
    db.record_student_history(students, "2025/2026", "b.xlsx")
    assert db.list_history_periods() == ["2025/2026", "2024/2025"]
    result = db.compare_with_reference_roster([], "2024/2025")
    assert result["reference_count"] == 1
    assert len(result["missing_students"]) == 1


def test_arabic_indic_national_ids_match_reference(tmp_path):
    db = StudentDatabase(tmp_path / "roster.sqlite3")
    old = [{"name": "Ahmed", "code": "8", "nationalId": "١٢٣٤٥"}]
    db.record_student_history(old, "2025/2026", "old.xlsx")
    current = [{"name": "Ahmed", "code": "8", "nationalId": "12345"}]
    result = db.compare_with_reference_roster(current, "2025/2026")
    assert result["new_students"] == []
    assert result["missing_students"] == []
    assert result["changed_students"] == []


def test_blank_identity_is_not_classified_as_new(tmp_path):
    db = StudentDatabase(tmp_path / "roster.sqlite3")
    result = db.compare_with_reference_roster(
        [{"name": "Unknown", "code": "", "nationalId": ""}], "2025/2026"
    )
    assert result["new_students"] == []
    assert result["missing_students"] == []
