import tempfile
import unittest
from pathlib import Path

from student_database import StudentDatabase
from database_safety import (
    create_verified_backup, inspect_database, restore_verified_backup
)


class DatabaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = StudentDatabase(self.root / "live.sqlite3")
        self.db.add_student("أحمد", "1001", "29901011234567")
        self.db.create_user("admin", "strong-password", "admin")

    def tearDown(self):
        self.temp.cleanup()

    def test_integrity_inspection_reports_core_counts(self):
        report = inspect_database(self.db)
        self.assertEqual(report["integrity"], "ok")
        self.assertEqual(report["counts"]["students"], 1)
        self.assertEqual(report["counts"]["app_users"], 1)

    def test_backup_is_verified_and_restorable(self):
        backup = self.root / "backups" / "verified.sqlite3"
        report = create_verified_backup(self.db, backup)
        self.assertTrue(report["verified"])
        self.db.add_student("محمود", "1002", "29901011234568")
        restored = restore_verified_backup(self.db, backup)
        self.assertEqual(self.db.count_students(), 1)
        self.assertTrue(Path(restored["safety_backup"]).is_file())
        self.assertEqual(restored["integrity"], "ok")

    def test_rejects_invalid_backup_without_touching_live_db(self):
        invalid = self.root / "bad.sqlite3"
        invalid.write_text("not a sqlite database", encoding="utf-8")
        with self.assertRaises((ValueError, Exception)):
            restore_verified_backup(self.db, invalid)
        self.assertEqual(self.db.count_students(), 1)

    def test_backup_cannot_overwrite_live_database(self):
        with self.assertRaises(ValueError):
            create_verified_backup(self.db, self.db.path)


if __name__ == "__main__":
    unittest.main()
