# -*- coding: utf-8 -*-
"""Persistent single-computer SQLite storage for StudentLedgerPro."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from portable_storage import resolve_database_path


def default_database_path() -> Path:
    """Use the EXE/source folder when writable; safely migrate legacy AppData DB."""
    app_dir = Path(os.path.dirname(os.path.abspath(
        sys.executable if getattr(sys, "frozen", False) else __file__
    )))
    fallback = Path(os.environ.get("APPDATA", str(Path.home()))) / "StudentLedgerPro"
    return resolve_database_path("student_ledger.sqlite3", app_dir, fallback)


class StudentDatabase:
    def __init__(self, db_path: str | os.PathLike | None = None):
        self.path = Path(db_path) if db_path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(str(self.path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '',
                    student_code TEXT NOT NULL DEFAULT '',
                    national_id TEXT NOT NULL DEFAULT '',
                    is_expat INTEGER NOT NULL DEFAULT 0,
                    source_file TEXT NOT NULL DEFAULT '',
                    row_data TEXT NOT NULL DEFAULT '[]',
                    audit_data TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_students_name ON students(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_students_code ON students(student_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_students_nid ON students(national_id)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS import_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT NOT NULL DEFAULT '',
                    imported_count INTEGER NOT NULL DEFAULT 0,
                    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def _student_values(student: dict[str, Any], source_file: str = ""):
        return (
            str(student.get("name") or ""),
            str(student.get("code") or ""),
            str(student.get("nationalId") or ""),
            1 if student.get("isExpat") else 0,
            source_file,
            json.dumps(student.get("cells") or [], ensure_ascii=False),
            json.dumps({k: student.get(k) for k in (
                "hasNidError", "hasBiometricError", "hasMilitaryError",
                "isCriticalMilitary", "hasSeatingError", "errorNotes"
            )}, ensure_ascii=False),
        )

    def import_students(self, students: list[dict[str, Any]], source_file: str = "") -> int:
        """Append one import batch; repeated imports remain traceable and are not silently overwritten."""
        values = [self._student_values(s, source_file) for s in students]
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO import_batches(source_file, imported_count) VALUES (?, ?)",
                (source_file, len(values)),
            )
            conn.executemany("""
                INSERT INTO students
                (name, student_code, national_id, is_expat, source_file, row_data, audit_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, values)
        return int(cur.lastrowid)

    def add_student(self, name: str, student_code: str = "", national_id: str = "",
                    is_expat: bool = False, cells: list | None = None) -> int:
        if not str(name).strip():
            raise ValueError("اسم الطالب مطلوب.")
        with self._connect() as conn:
            cur = conn.execute("""
                INSERT INTO students(name, student_code, national_id, is_expat, row_data)
                VALUES (?, ?, ?, ?, ?)
            """, (name.strip(), student_code.strip(), national_id.strip(),
                  int(bool(is_expat)), json.dumps(cells or [], ensure_ascii=False)))
            return int(cur.lastrowid)

    def update_student(self, student_id: int, *, name: str, student_code: str = "",
                       national_id: str = "", is_expat: bool = False) -> bool:
        if not str(name).strip():
            raise ValueError("اسم الطالب مطلوب.")
        with self._connect() as conn:
            cur = conn.execute("""
                UPDATE students SET name=?, student_code=?, national_id=?, is_expat=?,
                    updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (name.strip(), student_code.strip(), national_id.strip(),
                  int(bool(is_expat)), int(student_id)))
            return cur.rowcount > 0

    def delete_student(self, student_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM students WHERE id=?", (int(student_id),))
            return cur.rowcount > 0

    def search_students(self, query: str = "", limit: int = 500) -> list[dict[str, Any]]:
        q = f"%{query.strip()}%"
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, name, student_code, national_id, is_expat, source_file,
                       row_data, audit_data, created_at, updated_at
                FROM students
                WHERE (? = '' OR name LIKE ? OR student_code LIKE ? OR national_id LIKE ?)
                ORDER BY id DESC LIMIT ?
            """, (query.strip(), q, q, q, max(1, min(int(limit), 5000)))).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["cells"] = json.loads(item.pop("row_data") or "[]")
            item["audit"] = json.loads(item.pop("audit_data") or "{}")
            item["is_expat"] = bool(item["is_expat"])
            result.append(item)
        return result

    def count_students(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM students").fetchone()[0])

    def backup(self, destination: str | os.PathLike) -> str:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() == self.path.resolve():
            raise ValueError("لا يمكن أن يكون ملف النسخة الاحتياطية هو ملف قاعدة البيانات نفسه.")
        with self._connect() as source, sqlite3.connect(str(target)) as dest:
            source.backup(dest)
        return str(target)

