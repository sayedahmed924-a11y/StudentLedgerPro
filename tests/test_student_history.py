# -*- coding: utf-8 -*-
from student_database import StudentDatabase


def test_history_records_snapshots_and_detects_code_and_name_changes(tmp_path):
    db = StudentDatabase(tmp_path / "history.sqlite3")
    first = [{"name": "Ahmed Ali", "code": "100", "nationalId": "١٢٣٤٥٦"}]
    batch_id = db.import_students(first, "registry_2025.xlsx")
    saved = db.record_student_history(first, "2025/2026", "registry_2025.xlsx", batch_id)
    assert saved["recorded"] == 1
    changed = [{"name": "Ahmed Mohamed", "code": "200", "nationalId": "123456"}]
    findings = db.compare_student_history(changed, "2026/2027")
    assert {item["type"] for item in findings} == {"code_changed", "name_changed"}
    assert all(item["previous_period"] == "2025/2026" for item in findings)


def test_history_is_append_only_and_can_be_retrieved_by_identity(tmp_path):
    db = StudentDatabase(tmp_path / "history.sqlite3")
    for period, code in [("2024/2025", "10"), ("2025/2026", "11")]:
        records = [{"name": "Sara", "code": code, "nationalId": "998877"}]
        batch = db.import_students(records, f"{period}.xlsx")
        db.record_student_history(records, period, f"{period}.xlsx", batch)
    history = db.get_student_history("٩٩٨٨٧٧")
    assert len(history) == 2
    assert [item["academic_period"] for item in history] == ["2024/2025", "2025/2026"]
    assert [item["student_code"] for item in history] == ["10", "11"]


def test_history_skips_records_without_identity_and_empty_period(tmp_path):
    db = StudentDatabase(tmp_path / "history.sqlite3")
    assert db.record_student_history([{"name": "Unknown"}], "", "unknown.xlsx")["recorded"] == 0
    assert db.record_student_history([{"name": "Unknown"}], "2026/2027", "unknown.xlsx")["recorded"] == 0
    assert db.get_student_history("Unknown") == []


def test_same_period_is_not_compared_against_itself(tmp_path):
    db = StudentDatabase(tmp_path / "history.sqlite3")
    old = [{"name": "Ali", "code": "1", "nationalId": "777"}]
    db.record_student_history(old, "2026/2027", "one.xlsx")
    changed = [{"name": "Ali New", "code": "2", "nationalId": "777"}]
    assert db.compare_student_history(changed, "2026/2027") == []
