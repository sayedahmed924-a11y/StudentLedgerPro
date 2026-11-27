import tempfile
import unittest
from pathlib import Path
from student_database import StudentDatabase
from academic_reports import build_academic_report

class AcademicReportsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = StudentDatabase(Path(self.temp.name) / "test.sqlite3")
        self.db.import_students([
            {"name": "أحمد علي", "code": "1001", "nationalId": "29901011234567"},
            {"name": "John Doe", "code": "2001", "nationalId": "P1234567", "isExpat": True},
            {"name": "طالب ناقص", "hasNidError": True, "errorNotes": ["رقم قومي ناقص"]},
        ], "roster.xlsx")
    def tearDown(self): self.temp.cleanup()
    def test_all_students(self):
        _, rows, summary = build_academic_report(self.db)
        self.assertEqual(len(rows), 3)
        self.assertEqual(summary["total"], 3)
    def test_expatriates(self):
        _, rows, _ = build_academic_report(self.db, "expatriates")
        self.assertEqual(len(rows), 1)
    def test_missing_and_audit(self):
        _, missing, _ = build_academic_report(self.db, "missing_identity")
        _, issues, _ = build_academic_report(self.db, "audit_issues")
        self.assertEqual(len(missing), 1)
        self.assertEqual(len(issues), 1)
    def test_source_summary(self):
        _, rows, _ = build_academic_report(self.db, "source_summary")
        self.assertEqual(rows[0]["عدد الطلاب"], 3)
    def test_search(self):
        _, rows, _ = build_academic_report(self.db, query="2001")
        self.assertEqual(len(rows), 1)

if __name__ == "__main__": unittest.main()
