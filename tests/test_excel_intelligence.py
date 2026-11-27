# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

import pandas as pd

from excel_intelligence import detect_header_row, load_best_sheet, normalize_header


ONTOLOGY = {
    "name": {"headers": ["اسم الطالب", "الاسم بالكامل", "student name"]},
    "nationalId": {"headers": ["الرقم القومي", "national id", "nid"]},
    "code": {"headers": ["كود الطالب", "student code"]},
    "seatingNo": {"headers": ["رقم الجلوس", "seat no"]},
}


class ExcelIntelligenceTests(unittest.TestCase):
    def test_normalizes_arabic_diacritics_and_digits(self):
        self.assertEqual(normalize_header("أَرْقَام ١٢٣"), "ارقام 123")

    def test_detects_header_after_title_and_blank_rows(self):
        frame = pd.DataFrame([
            ["كشف الطلاب للعام الجامعي", None, None],
            [None, None, None],
            ["ملاحظات", None, None],
            ["اسم الطالب", "الرقم القومي", "كود الطالب"],
            ["أحمد محمد علي", "30101011234567", "123456"],
        ])
        row, confidence, matches = detect_header_row(frame, ONTOLOGY)
        self.assertEqual(row, 3)
        self.assertGreaterEqual(matches, 3)
        self.assertGreater(confidence, 0)

    def test_selects_relevant_sheet_not_first_sheet(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "students.xlsx")
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                pd.DataFrame([["تعليمات"], ["يرجى مراجعة البيانات"]]).to_excel(
                    writer, sheet_name="تعليمات", header=False, index=False
                )
                pd.DataFrame([
                    ["كشف الطلاب"],
                    ["اسم الطالب", "الرقم القومي", "كود الطالب", "رقم الجلوس"],
                    ["أحمد محمد علي", "30101011234567", "123456", "1001"],
                ]).to_excel(writer, sheet_name="بيانات الطلاب", header=False, index=False)
            frame, sheet, row, info = load_best_sheet(path, ONTOLOGY)
            self.assertEqual(sheet, "بيانات الطلاب")
            self.assertEqual(row, 1)
            self.assertEqual(info["matched_fields"], 4)
            self.assertEqual(frame.shape[0], 3)


if __name__ == "__main__":
    unittest.main()
