# -*- coding: utf-8 -*-
import unittest

import pandas as pd

from excel_intelligence import (
    compose_header_values,
    detect_header_structure,
    find_nonempty_regions,
    is_repeated_header_row,
)

ONTOLOGY = {
    "name": {"headers": ["اسم الطالب", "الاسم بالكامل", "student name"]},
    "nationalId": {"headers": ["الرقم القومي", "national id", "nid"]},
    "code": {"headers": ["كود الطالب", "student code"]},
    "seatingNo": {"headers": ["رقم الجلوس", "seat no"]},
}


class ExcelLayoutTests(unittest.TestCase):
    def test_detects_two_row_headers(self):
        frame = pd.DataFrame([
            ["كشف الطلاب", None, None],
            ["بيانات الطالب", "بيانات الطالب", "بيانات الطالب"],
            ["الاسم", "الرقم القومي", "كود الطالب"],
            ["أحمد محمد علي", "30101011234567", "123456"],
        ])
        row, depth, confidence, matches = detect_header_structure(frame, ONTOLOGY)
        self.assertEqual(row, 1)
        self.assertEqual(depth, 2)
        self.assertGreaterEqual(matches, 3)
        self.assertGreater(confidence, 0)
        self.assertEqual(
            compose_header_values(frame, row, depth),
            ["بيانات الطالب الاسم", "بيانات الطالب الرقم القومي", "بيانات الطالب كود الطالب"],
        )

    def test_detects_blank_separated_regions(self):
        frame = pd.DataFrame([
            ["اسم الطالب", "الرقم القومي"],
            ["أحمد", "30101011234567"],
            [None, None],
            ["اسم الطالب", "الرقم القومي"],
            ["محمد", "30101021234567"],
        ])
        self.assertEqual(find_nonempty_regions(frame, 0), [(0, 1), (3, 4)])

    def test_recognizes_repeated_header_row(self):
        headers = ["اسم الطالب", "الرقم القومي", "كود الطالب"]
        self.assertTrue(is_repeated_header_row(headers, headers, ONTOLOGY))
        self.assertFalse(is_repeated_header_row(["أحمد محمد", "30101011234567", "123456"], headers, ONTOLOGY))


if __name__ == "__main__":
    unittest.main()
