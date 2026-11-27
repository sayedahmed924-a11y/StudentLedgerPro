# -*- coding: utf-8 -*-
from field_mapping_explainer import explain_assignments


def test_assignment_is_one_to_one_and_explains_high_confidence_match():
    columns = [{"name": "اسم الطالب"}, {"name": "رقم الطالب"}]
    report = explain_assignments([
        (96, "name", 0, 94, 98),
        (91, "code", 0, 90, 92),
        (93, "code", 1, 95, 91),
    ], columns)
    assert report["assignments"]["name"]["column_index"] == 0
    assert report["assignments"]["code"]["column_index"] == 1
    assert report["assignments"]["name"]["confidence"] == "high"
    assert report["assignments"]["name"]["reason"]


def test_medium_confidence_is_marked_for_review():
    report = explain_assignments([(67, "nationalId", 0, 60, 74)], [{"name": "بيانات"}])
    item = report["assignments"]["nationalId"]
    assert item["confidence"] == "medium"
    assert item["review_required"] is True
    assert report["review_count"] == 1


def test_invalid_column_and_incomplete_candidate_are_ignored():
    report = explain_assignments([(90, "name", 8, 90, 90), (88, "code", 0)], [{"name": "الاسم"}])
    assert report["assigned_count"] == 0
    assert report["unassigned_fields"] == []
