# -*- coding: utf-8 -*-
from workbook_linker import analyze_workbooks


def test_links_records_across_files_by_normalized_student_code():
    report = analyze_workbooks([
        {"file": "registry.xlsx", "sheet": "Students", "students": [{"name": "Ali", "code": "١٢٣٤", "nationalId": ""}]},
        {"file": "fees.xlsx", "sheet": "Fees", "students": [{"name": "Ali", "code": "1234", "nationalId": ""}]},
    ])
    assert report["workbook_count"] == 2
    assert report["match_group_count"] == 1
    assert report["automatic_merge_performed"] is False


def test_reports_conflict_when_same_code_has_different_identity_values():
    report = analyze_workbooks([
        {"file": "a.xlsx", "students": [{"name": "Ali", "code": "77", "nationalId": "111"}]},
        {"file": "b.xlsx", "students": [{"name": "Omar", "code": "77", "nationalId": "222"}]},
    ])
    assert report["conflict_count"] == 1
    assert report["match_groups"][0]["requires_review"] is True


def test_name_only_does_not_create_cross_file_match():
    report = analyze_workbooks([
        {"file": "a.xlsx", "students": [{"name": "Shared Name"}]},
        {"file": "b.xlsx", "students": [{"name": "Shared Name"}]},
    ])
    assert report["match_group_count"] == 0
