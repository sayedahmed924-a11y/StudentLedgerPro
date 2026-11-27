# -*- coding: utf-8 -*-
from excel_import_pipeline import prepare_import_preview, select_preview_rows


def test_preview_retains_source_and_original_cells():
    records = [{"name": "Student A", "code": "١٢٣٤", "nationalId": "", "cells": ["Student A", "١٢٣٤"], "sourceRow": 8}]
    preview = prepare_import_preview(records, source_file="sample.xlsx", source_sheet="Sheet1")
    assert preview["row_count"] == 1
    assert preview["rows"][0]["cells"] == ["Student A", "١٢٣٤"]
    assert preview["rows"][0]["source_row"] == 8
    assert preview["rows"][0]["source_sheet"] == "Sheet1"


def test_missing_fields_are_flagged():
    preview = prepare_import_preview([{"name": "", "code": "", "nationalId": ""}])
    assert preview["warning_count"] == 1
    assert not preview["ready_to_commit"]


def test_duplicate_code_is_reported_without_merging():
    records = [{"name": "A", "code": "123", "nationalId": ""}, {"name": "B", "code": "123", "nationalId": ""}]
    preview = prepare_import_preview(records)
    assert preview["duplicate_group_count"] == 1
    assert preview["row_count"] == 2


def test_explicit_selection_preserves_provenance():
    preview = prepare_import_preview([{"name": "A", "code": "1", "sourceRow": 4}], source_sheet="Sheet1")
    selected = select_preview_rows(preview, [0, 0, -1, 5])
    assert len(selected) == 1
    assert selected[0]["sourceRow"] == 4
    assert selected[0]["sourceSheet"] == "Sheet1"
