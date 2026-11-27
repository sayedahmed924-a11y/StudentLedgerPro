# -*- coding: utf-8 -*-
from student_database import StudentDatabase


def test_employee_correction_is_scoped_to_extension_and_sheet(tmp_path):
    db = StudentDatabase(tmp_path / "corrections.sqlite3")
    assert db.remember_user_mapping_correction(
        "code", "رقم القيد", ".xlsx", "قيد الطلاب", "operator"
    )
    assert db.get_user_mapping_corrections("code", ".xlsx", "قيد الطلاب")["رقم القيد"] >= 0.90
    assert db.get_user_mapping_corrections("code", ".xls", "قيد الطلاب") == {}
    assert db.get_user_mapping_corrections("code", ".xlsx", "الرسوم") == {}


def test_repeated_confirmed_corrections_increase_count_and_confidence(tmp_path):
    db = StudentDatabase(tmp_path / "corrections.sqlite3")
    for _ in range(3):
        db.remember_user_mapping_correction("code", "كود الطالب", ".xlsx", "طلاب", "admin")
    corrections = db.get_user_mapping_corrections("code", ".xlsx", "طلاب")
    assert corrections["كود الطالب"] > 0.90
    assert db.mapping_correction_stats() == {"corrections": 1, "confirmations": 3}


def test_empty_correction_is_rejected(tmp_path):
    db = StudentDatabase(tmp_path / "corrections.sqlite3")
    assert not db.remember_user_mapping_correction("", "", ".xlsx", "Sheet1")
    assert db.mapping_correction_stats() == {"corrections": 0, "confirmations": 0}
