import tempfile
import unittest
from pathlib import Path

from student_database import StudentDatabase
from extended_reports import build_extended_report


class ExtendedReportsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = StudentDatabase(Path(self.temp.name) / "test.sqlite3")
        self.db.import_students([
            {"name": "أحمد", "code": "1001", "nationalId": "29901011234567",
             "hasNidError": True, "errorNotes": ["رقم قومي غير صحيح"]},
            {"name": "محمود", "code": "1002", "hasBiometricError": True},
            {"name": "John", "code": "2001", "isExpat": True,
             "hasMilitaryError": True, "isCriticalMilitary": True},
            {"name": "سعيد", "code": "1004", "hasSeatingError": True},
        ], "roster.xlsx")
        self.db.log_activity("admin", "login", "successful")
        with self.db._connection() as conn:
            conn.execute("INSERT INTO import_batches(source_file,imported_count) VALUES(?,?)",
                         ("roster.xlsx", 4))
            conn.execute(
                "INSERT INTO workbook_learning(file_extension,sheet_name,header_signature,header_count) "
                "VALUES(?,?,?,?)", (".xlsx", "طلاب", '["اسم","كود"]', 2)
            )
            conn.execute(
                "INSERT INTO user_mapping_corrections(field_name,alias,file_extension,sheet_name,corrected_by) "
                "VALUES(?,?,?,?,?)", ("name", "اسم الطالب", ".xlsx", "طلاب", "admin")
            )
            conn.execute(
                "INSERT INTO app_users(username,password_hash,password_salt,role) VALUES(?,?,?,?)",
                ("admin", "secret-hash-must-not-leak", "secret-salt", "admin")
            )

    def tearDown(self):
        self.temp.cleanup()

    def test_audit_specific_reports(self):
        self.assertEqual(len(build_extended_report(self.db, "nid_errors")[1]), 1)
        self.assertEqual(len(build_extended_report(self.db, "biometric_errors")[1]), 1)
        self.assertEqual(len(build_extended_report(self.db, "military_errors")[1]), 1)
        self.assertEqual(len(build_extended_report(self.db, "seating_errors")[1]), 1)

    def test_operational_reports(self):
        self.assertEqual(len(build_extended_report(self.db, "imports")[1]), 2)
        self.assertEqual(len(build_extended_report(self.db, "activity")[1]), 1)
        self.assertEqual(len(build_extended_report(self.db, "workbook_learning")[1]), 1)
        self.assertEqual(len(build_extended_report(self.db, "mapping_corrections")[1]), 1)

    def test_user_report_never_exposes_credentials(self):
        _, rows, _ = build_extended_report(self.db, "system_users")
        self.assertEqual(rows[0]["اسم المستخدم"], "admin")
        self.assertNotIn("password_hash", str(rows))
        self.assertNotIn("secret-hash", str(rows))

    def test_search_and_limit(self):
        _, rows, summary = build_extended_report(self.db, "nid_errors", query="أحمد", limit=0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(summary["limited_to"], 1)

    def test_unknown_report(self):
        with self.assertRaises(ValueError):
            build_extended_report(self.db, "not_a_report")


if __name__ == "__main__":
    unittest.main()
