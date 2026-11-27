import tempfile
import unittest
from pathlib import Path

from student_database import StudentDatabase
from custom_reports import build_custom_report, available_report_fields


class CustomReportsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = StudentDatabase(Path(self.temp.name) / "test.sqlite3")
        self.db.import_students([
            {"name": "أحمد علي", "code": "1001", "nationalId": "29901011234567",
             "isExpat": True, "hasNidError": True, "errorNotes": ["مراجعة الرقم"]},
            {"name": "محمود حسن", "code": "1002", "nationalId": "29901011234568",
             "isExpat": False},
            {"name": "أحمد محمد", "code": "1003", "nationalId": "29901011234569",
             "isExpat": True, "hasMilitaryError": True},
        ], "students.xlsx")

    def tearDown(self):
        self.temp.cleanup()

    def test_available_fields_are_explicit(self):
        self.assertIn("national_id", available_report_fields())

    def test_filter_contains_and_selected_fields(self):
        report = build_custom_report(self.db, fields=["name", "student_code"],
            filters=[{"field": "name", "op": "contains", "value": "أحمد"}])
        self.assertEqual(report["total_matched"], 2)
        self.assertEqual(list(report["rows"][0]), ["اسم الطالب", "كود الطالب"])

    def test_boolean_filter_and_grouping(self):
        report = build_custom_report(self.db, fields=["name"],
            filters=[{"field": "is_expat", "op": "eq", "value": "نعم"}],
            group_by="source_file")
        self.assertEqual(report["rows"][0]["عدد الطلاب"], 2)

    def test_sort_pagination_and_limit(self):
        report = build_custom_report(self.db, fields=["name"], sort_by="name",
                                     descending=True, limit=1, offset=1)
        self.assertEqual(len(report["rows"]), 1)
        self.assertEqual(report["total_matched"], 3)

    def test_date_and_range_filter(self):
        report = build_custom_report(self.db, fields=["name"],
            filters=[{"field": "id", "op": "between", "value": ["1", "2"]}])
        self.assertEqual(report["total_matched"], 2)

    def test_reject_unsafe_sql_or_invalid_fields(self):
        with self.assertRaises(ValueError):
            build_custom_report(self.db, fields=["name; DROP TABLE students"])
        with self.assertRaises(ValueError):
            build_custom_report(self.db, filters=[{"field": "name", "op": "raw_sql", "value": "x"}])

    def test_database_is_read_only_for_report_generation(self):
        before = self.db.count_students()
        build_custom_report(self.db, filters=[{"field": "name", "op": "contains", "value": "أحمد"}])
        self.assertEqual(self.db.count_students(), before)


if __name__ == "__main__":
    unittest.main()
