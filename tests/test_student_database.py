import tempfile
import unittest
from pathlib import Path

from student_database import StudentDatabase


class StudentDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = StudentDatabase(Path(self.tmp.name) / "test.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_crud_and_search(self):
        student_id = self.db.add_student("أحمد محمد", "123", "29901011234567")
        self.assertEqual(len(self.db.search_students("أحمد")), 1)
        self.assertTrue(self.db.update_student(student_id, name="أحمد علي", student_code="456"))
        self.assertEqual(self.db.search_students("456")[0]["name"], "أحمد علي")
        self.assertTrue(self.db.delete_student(student_id))
        self.assertEqual(self.db.count_students(), 0)

    def test_import_and_backup(self):
        self.db.import_students([{"name": "سارة", "code": "7", "cells": ["سارة"]}], "sample.xlsx")
        backup = Path(self.tmp.name) / "backup.sqlite3"
        self.db.backup(backup)
        copied = StudentDatabase(backup)
        self.assertEqual(copied.count_students(), 1)

    def test_user_authentication_and_roles(self):
        user_id = self.db.create_user("operator", "StrongPass123", "editor")
        self.assertGreater(user_id, 0)
        self.assertIsNone(self.db.authenticate("operator", "incorrect"))
        user = self.db.authenticate("OPERATOR", "StrongPass123")
        self.assertEqual(user["role"], "editor")
        self.assertTrue(self.db.set_user_active(user_id, False))
        self.assertIsNone(self.db.authenticate("operator", "StrongPass123"))

    def test_activity_log(self):
        self.db.log_activity("admin", "IMPORT", "sample.xlsx")
        self.assertEqual(self.db.recent_activity()[0]["action"], "IMPORT")

    def test_semantic_learning_persists_and_reinforces_confidence(self):
        self.assertFalse(self.db.remember_semantic_mapping("name", "uncertain", 0.60))
        self.assertTrue(self.db.remember_semantic_mapping("name", "student name", 0.90))
        self.assertAlmostEqual(self.db.get_semantic_aliases("name")["student name"], 0.90)
        self.assertTrue(self.db.remember_semantic_mapping("name", "student name", 0.80))
        self.assertAlmostEqual(self.db.get_semantic_aliases("name")["student name"], 0.85)
        stats = self.db.semantic_memory_stats()
        self.assertEqual(stats["aliases"], 1)
        self.assertEqual(stats["observations"], 2)

    def test_semantic_learning_survives_database_reopen(self):
        self.db.remember_semantic_mapping("code", "student code", 0.95)
        reopened = StudentDatabase(self.db.path)
        self.assertIn("student code", reopened.get_semantic_aliases("code"))


if __name__ == "__main__":
    unittest.main()
