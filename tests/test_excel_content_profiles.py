# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

import pandas as pd
from openpyxl import Workbook

from excel_intelligence import (
    expand_merged_cells,
    find_ambiguous_columns,
    load_best_sheet,
    profile_columns,
)


class ExcelContentProfileTests(unittest.TestCase):
    def test_profiles_detect_national_id_and_arabic_text_patterns(self):
        frame = pd.DataFrame([
            ["30101011234567", "أحمد محمد"],
            ["30202021234567", "محمد علي"],
            ["30303031234567", "سارة حسن"],
            ["30404041234567", "محمود حسن"],
        ])
        profiles = profile_columns(frame)
        self.assertEqual(profiles[0]["national_id_ratio"], 1.0)
        self.assertEqual(profiles[1]["arabic_text_ratio"], 1.0)
        hints = find_ambiguous_columns(profiles)
        self.assertTrue(any(h["column_index"] == 0 and h["pattern"] == "nationalId" for h in hints))

    def test_load_best_sheet_uses_merged_header_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "merged_students.xlsx")
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "بيانات"
            sheet.merge_cells("A1:B1")
            sheet["A1"] = "بيانات الطالب"
            sheet["A2"] = "الاسم"
            sheet["B2"] = "الرقم القومي"
            sheet["A3"] = "أحمد محمد علي"
            sheet["B3"] = "30101011234567"
            workbook.save(path)
            workbook.close()
            ontology = {
                "name": {"headers": ["الاسم", "اسم الطالب"]},
                "nationalId": {"headers": ["الرقم القومي"]},
            }
            data, name, header, info = load_best_sheet(path, ontology)
            self.assertEqual(name, "بيانات")
            self.assertEqual(header, 1)
            self.assertGreaterEqual(info["matched_fields"], 2)
            self.assertGreaterEqual(info["merged_ranges_expanded"], 1)

    def test_expands_merged_header_cells_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "merged.xlsx")
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "بيانات"
            sheet.merge_cells("A1:C1")
            sheet["A1"] = "بيانات الطالب"
            sheet["A2"] = "الاسم"
            sheet["B2"] = "الرقم"
            sheet["C2"] = "الكود"
            workbook.save(path)
            workbook.close()

            frame = pd.DataFrame([
                ["بيانات الطالب", None, None],
                ["الاسم", "الرقم", "الكود"],
                ["أحمد محمد", "30101011234567", "123456"],
            ])
            expanded, count = expand_merged_cells(path, "بيانات", frame)
            self.assertEqual(count, 1)
            self.assertEqual(expanded.iloc[0].tolist(), ["بيانات الطالب"] * 3)
            # The input dataframe is not modified in place.
            self.assertIsNone(frame.iloc[0, 1])


if __name__ == "__main__":
    unittest.main()
