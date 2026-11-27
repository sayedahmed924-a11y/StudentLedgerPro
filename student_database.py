# -*- coding: utf-8 -*-
"""Persistent single-computer SQLite storage for StudentLedgerPro."""
from __future__ import annotations

import json
import os
import sqlite3
import hashlib
import hmac
import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def default_database_path() -> Path:
    """Use a per-user writable data directory, never the EXE/install directory."""
    root = os.environ.get("APPDATA")
    if root:
        base = Path(root) / "StudentLedgerPro"
    else:
        base = Path.home() / ".studentledgerpro"
    base.mkdir(parents=True, exist_ok=True)
    return base / "student_ledger.sqlite3"


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

    @contextmanager
    def _connection(self):
        """Commit/rollback and always close the SQLite handle (important on Windows)."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self):
        with self._connection() as conn:
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'editor', 'viewer')),
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)


    @staticmethod
    def _password_digest(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 240000
        ).hex()

    def user_count(self) -> int:
        with self._connection() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0])

    def create_user(self, username: str, password: str, role: str = "viewer") -> int:
        username = str(username).strip()
        if len(username) < 3:
            raise ValueError("اسم المستخدم يجب ألا يقل عن 3 أحرف.")
        if len(password) < 8:
            raise ValueError("كلمة المرور يجب ألا تقل عن 8 أحرف.")
        if role not in ("admin", "editor", "viewer"):
            raise ValueError("نوع الصلاحية غير صحيح.")
        salt = secrets.token_hex(16)
        digest = self._password_digest(password, salt)
        with self._connection() as conn:
            cur = conn.execute(
                "INSERT INTO app_users(username,password_hash,password_salt,role) VALUES(?,?,?,?)",
                (username, digest, salt, role),
            )
            return int(cur.lastrowid)

    def authenticate(self, username: str, password: str):
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id,username,password_hash,password_salt,role FROM app_users "
                "WHERE username=? COLLATE NOCASE AND active=1",
                (str(username).strip(),),
            ).fetchone()
        if not row:
            return None
        candidate = self._password_digest(password, row["password_salt"])
        if not hmac.compare_digest(candidate, row["password_hash"]):
            return None
        return {"id": row["id"], "username": row["username"], "role": row["role"]}

    def list_users(self):
        with self._connection() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT id,username,role,active,created_at FROM app_users ORDER BY username"
            ).fetchall()]

    def set_user_active(self, user_id: int, active: bool) -> bool:
        with self._connection() as conn:
            cur = conn.execute("UPDATE app_users SET active=? WHERE id=?",
                               (int(bool(active)), int(user_id)))
            return cur.rowcount > 0

    def log_activity(self, username: str, action: str, details: str = ""):
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO activity_log(username,action,details) VALUES(?,?,?)",
                (username, action, details),
            )

    def recent_activity(self, limit: int = 200):
        with self._connection() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT username,action,details,created_at FROM activity_log "
                "ORDER BY id DESC LIMIT ?", (max(1, min(int(limit), 1000)),)
            ).fetchall()]

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
        with self._connection() as conn:
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
        with self._connection() as conn:
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
        with self._connection() as conn:
            cur = conn.execute("""
                UPDATE students SET name=?, student_code=?, national_id=?, is_expat=?,
                    updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (name.strip(), student_code.strip(), national_id.strip(),
                  int(bool(is_expat)), int(student_id)))
            return cur.rowcount > 0

    def delete_student(self, student_id: int) -> bool:
        with self._connection() as conn:
            cur = conn.execute("DELETE FROM students WHERE id=?", (int(student_id),))
            return cur.rowcount > 0

    def search_students(self, query: str = "", limit: int = 500) -> list[dict[str, Any]]:
        q = f"%{query.strip()}%"
        with self._connection() as conn:
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
        with self._connection() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM students").fetchone()[0])

    def backup(self, destination: str | os.PathLike) -> str:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() == self.path.resolve():
            raise ValueError("لا يمكن أن يكون ملف النسخة الاحتياطية هو ملف قاعدة البيانات نفسه.")
        source = self._connect()
        dest = sqlite3.connect(str(target), timeout=30)
        try:
            source.backup(dest)
            dest.commit()
        finally:
            dest.close()
            source.close()
        return str(target)

