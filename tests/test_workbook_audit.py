# -*- coding: utf-8 -*-
from workbook_audit import audit_workbooks


def test_duplicate_code_inside_same_sheet_is_error():
    report = audit_workbooks([{
        "file": "registry.xlsx", "sheet": "Students",
        "students": [
            {"name": "Ali", "code": "١٢٣", "nationalId": "111"},
            {"name": "Ali", "code": "123", "nationalId": "111"},
        ],
    }])
    assert report["severity_counts"]["error"] == 1
    assert report["findings"][0]["type"] == "duplicate_student_code"
    assert report["findings"][0]["sources"][0]["file"] == "registry.xlsx"


def test_cross_workbook_same_code_with_different_identity_is_conflict():
    report = audit_workbooks([
        {"file": "a.xlsx", "sheet": "A", "students": [
            {"name": "Ali", "code": "55", "nationalId": "111"}]},
        {"file": "b.xlsx", "sheet": "B", "students": [
            {"name": "Omar", "code": "٥٥", "nationalId": "222"}]},
    ])
    conflicts = [item for item in report["findings"]
                 if item["type"] == "cross_file_identity_conflict"]
    assert len(conflicts) == 1
    assert conflicts[0]["severity"] == "error"
    assert len(conflicts[0]["sources"]) == 2


def test_missing_critical_fields_are_reported_with_severity():
    report = audit_workbooks([{
        "file": "empty_fields.xlsx", "sheet": "Students",
        "students": [{"name": "", "code": "", "nationalId": ""}],
    }])
    kinds = {item["type"] for item in report["findings"]}
    assert {"missing_name", "missing_code", "missing_national_id"} <= kinds
    assert report["severity_counts"]["warning"] == 2
    assert report["severity_counts"]["info"] == 1


def test_national_id_associated_with_multiple_codes_is_reported():
    report = audit_workbooks([
        {"file": "a.xlsx", "sheet": "A", "students": [
            {"name": "Ali", "code": "10", "nationalId": "123456"}]},
        {"file": "b.xlsx", "sheet": "B", "students": [
            {"name": "Ali", "code": "20", "nationalId": "١٢٣٤٥٦"}]},
    ])
    assert any(item["type"] == "national_id_collision" for item in report["findings"])
    assert report["automatic_changes"] == 0
