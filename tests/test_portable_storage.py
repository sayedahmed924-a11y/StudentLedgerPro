import sqlite3
import tempfile
import unittest
from pathlib import Path

from portable_storage import resolve_database_path


class PortableStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.app = self.root / "USB" / "StudentLedgerPro"
        self.legacy = self.root / "AppData" / "StudentLedgerPro"
        self.legacy.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_selects_portable_folder_when_writable(self):
        path = resolve_database_path("student_ledger.sqlite3", self.app, self.legacy)
        self.assertEqual(path.parent, self.app)
        self.assertTrue(self.app.is_dir())

    def test_migrates_legacy_database_without_deleting_source(self):
        old = self.legacy / "student_ledger.sqlite3"
        with sqlite3.connect(old) as conn:
            conn.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO students(name) VALUES ('أحمد')")
        new = resolve_database_path("student_ledger.sqlite3", self.app, self.legacy)
        self.assertTrue(old.exists())
        with sqlite3.connect(new) as conn:
            self.assertEqual(conn.execute("SELECT name FROM students").fetchone()[0], "أحمد")
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_existing_portable_database_is_never_overwritten(self):
        self.app.mkdir(parents=True)
        current = self.app / "student_ledger.sqlite3"
        with sqlite3.connect(current) as conn:
            conn.execute("CREATE TABLE keep_me (value TEXT)")
            conn.execute("INSERT INTO keep_me VALUES ('current')")
        old = self.legacy / "student_ledger.sqlite3"
        with sqlite3.connect(old) as conn:
            conn.execute("CREATE TABLE keep_me (value TEXT)")
            conn.execute("INSERT INTO keep_me VALUES ('legacy')")
        result = resolve_database_path("student_ledger.sqlite3", self.app, self.legacy)
        with sqlite3.connect(result) as conn:
            self.assertEqual(conn.execute("SELECT value FROM keep_me").fetchone()[0], "current")
        self.assertTrue(old.exists())


if __name__ == "__main__":
    unittest.main()
