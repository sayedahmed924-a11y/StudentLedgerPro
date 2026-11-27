# -*- coding: utf-8 -*-
import unittest

import pandas as pd

from excel_intelligence import (
    detect_table_candidates,
    find_duplicate_candidates,
    map_header_columns,
    normalize_student_value,
)

ONTOLOGY = {
    "name": {"headers": ["اسم الطالب", "الاسم", "student name"]},
    "nationalId": {"headers": ["الرقم القومي", "national id"]},
    "code": {"headers": ["كود الطالب", "student code"]},
}


class MultiTableAndDuplicateTests(unittest.TestCase):
    def test_maps_different_column_orders_without_reusing_columns(self):
        headers = ["كود الطالب", "اسم الطالب", "الرقم القومي"]
        mapping = map_header_columns(headers, ONTOLOGY)
        self.assertEqual(mapping["code"]["column_index"], 0)
        self.assertEqual(mapping["name"]["column_index"], 1)
        self.assertEqual(mapping["nationalId"]["column_index"], 2)
        self.assertEqual(len({v["column_index"] for v in mapping.values()}), 3)

    def test_finds_two_tables_with_different_column_orders(self):
        frame = pd.DataFrame([
            ["اسم الطالب", "الرقم القومي", "كود الطالب"],
            ["أحمد محمد", "30101011234567", "A-1"],
            ["محمد علي", "30201011234567", "A-2"],
            [None, None, None],
            ["كود الطالب", "اسم الطالب", "الرقم القومي"],
            ["B-1", "سارة حسن", "30301011234567"],
        ])
        tables = detect_table_candidates(frame, ONTOLOGY)
        self.assertEqual(len(tables), 2)
        self.assertEqual(tables[0]["column_mapping"]["name"]["column_index"], 0)
        self.assertEqual(tables[1]["column_mapping"]["name"]["column_index"], 1)
        self.assertEqual(tables[1]["data_start"], 5)

    def test_duplicate_detection_uses_strong_ids_and_weak_names(self):
        records = [
            {"nationalId": "٣٠١٠١٠١١٢٣٤٥٦٧", "code": "A-1", "name": "أحمد محمد"},
            {"nationalId": "30101011234567", "code": "A-2", "name": "احمد محمد"},
            {"nationalId": "30201011234567", "code": "A-3", "name": "أحمد محمد"},
        ]
        groups = find_duplicate_candidates(records)
        strong = [g for g in groups if g["strength"] == "strong"]
        weak = [g for g in groups if g["strength"] == "weak"]
        self.assertTrue(any(g["field"] == "nationalId" for g in strong))
        self.assertTrue(any(g["field"] == "name" for g in weak))
        self.assertTrue(all(g["review_required"] for g in groups))
        self.assertEqual(normalize_student_value(" ٣٠١-٠١ "), "30101")

    def test_same_name_alone_is_never_strong_duplicate(self):
        groups = find_duplicate_candidates([
            {"name": "محمد أحمد"}, {"name": "محمد أحمد"}
        ])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["strength"], "weak")


if __name__ == "__main__":
    unittest.main()
