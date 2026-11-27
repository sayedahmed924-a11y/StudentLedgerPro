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
                CREATE TABLE IF NOT EXISTS student_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_key TEXT NOT NULL,
                    identity_type TEXT NOT NULL,
                    academic_period TEXT NOT NULL,
                    student_name TEXT NOT NULL DEFAULT '',
                    student_code TEXT NOT NULL DEFAULT '',
                    national_id TEXT NOT NULL DEFAULT '',
                    source_file TEXT NOT NULL DEFAULT '',
                    source_sheet TEXT NOT NULL DEFAULT '',
                    source_row TEXT NOT NULL DEFAULT '',
                    import_batch_id INTEGER,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_student_history_identity ON student_history(identity_key, academic_period)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_student_history_period ON student_history(academic_period)")
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workbook_learning (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_hash TEXT NOT NULL UNIQUE,
                    file_extension TEXT NOT NULL DEFAULT '',
                    sheet_name TEXT NOT NULL DEFAULT '',
                    header_signature TEXT NOT NULL DEFAULT '',
                    header_count INTEGER NOT NULL DEFAULT 0,
                    confirmed_imports INTEGER NOT NULL DEFAULT 1,
                    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS confirmed_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    left_field TEXT NOT NULL,
                    right_field TEXT NOT NULL,
                    confirmation_count INTEGER NOT NULL DEFAULT 1,
                    last_confirmed TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(left_field, right_field)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_mapping_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    field_name TEXT NOT NULL,
                    alias TEXT NOT NULL COLLATE NOCASE,
                    file_extension TEXT NOT NULL,
                    sheet_name TEXT NOT NULL,
                    corrected_by TEXT NOT NULL DEFAULT '',
                    confirmation_count INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_confirmed TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(field_name, alias, file_extension, sheet_name)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    field_name TEXT NOT NULL,
                    alias TEXT NOT NULL COLLATE NOCASE,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    success_count INTEGER NOT NULL DEFAULT 1,
                    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (field_name, alias)
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


    def get_semantic_aliases(self, field: str) -> dict[str, float]:
        """Return learned column headings and their confidence for one semantic field."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT alias, confidence FROM semantic_memory WHERE field_name=?",
                (str(field),),
            ).fetchall()
        return {row["alias"]: float(row["confidence"]) for row in rows}

    def remember_semantic_mapping(self, field: str, alias: str, confidence: float) -> bool:
        """Learn a header only when the classifier reports a sufficiently strong match."""
        field, alias = str(field).strip(), str(alias).strip()
        confidence = max(0.0, min(float(confidence), 1.0))
        if not field or not alias or confidence < 0.72:
            return False
        with self._connection() as conn:
            row = conn.execute(
                "SELECT confidence, success_count FROM semantic_memory "
                "WHERE field_name=? AND alias=? COLLATE NOCASE",
                (field, alias),
            ).fetchone()
            if row:
                count = int(row["success_count"])
                updated = ((float(row["confidence"]) * count) + confidence) / (count + 1)
                conn.execute(
                    "UPDATE semantic_memory SET confidence=?, success_count=success_count+1, "
                    "last_seen=CURRENT_TIMESTAMP WHERE field_name=? AND alias=? COLLATE NOCASE",
                    (updated, field, alias),
                )
            else:
                conn.execute(
                    "INSERT INTO semantic_memory(field_name,alias,confidence) VALUES(?,?,?)",
                    (field, alias, confidence),
                )
        return True

    def semantic_memory_stats(self) -> dict[str, int]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS aliases, COALESCE(SUM(success_count),0) AS observations "
                "FROM semantic_memory"
            ).fetchone()
        return {"aliases": int(row["aliases"]), "observations": int(row["observations"])}



    def remember_user_mapping_correction(self, field: str, alias: str,
                                         file_extension: str, sheet_name: str,
                                         corrected_by: str = "") -> bool:
        """Persist an explicit human correction scoped to this workbook type and sheet."""
        field, alias = str(field).strip(), str(alias).strip()
        extension = str(file_extension).lower().strip()
        sheet = str(sheet_name).strip()
        if not all((field, alias, extension, sheet)):
            return False
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO user_mapping_corrections
                    (field_name,alias,file_extension,sheet_name,corrected_by)
                VALUES (?,?,?,?,?)
                ON CONFLICT(field_name,alias,file_extension,sheet_name) DO UPDATE SET
                    confirmation_count=confirmation_count+1,
                    corrected_by=excluded.corrected_by,
                    last_confirmed=CURRENT_TIMESTAMP
            """, (field, alias, extension, sheet, str(corrected_by)))
        return True

    def get_user_mapping_corrections(self, field: str,
                                     file_extension: str, sheet_name: str) -> dict[str, float]:
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT alias,confirmation_count FROM user_mapping_corrections
                WHERE field_name=? AND file_extension=? AND sheet_name=?
                ORDER BY confirmation_count DESC,last_confirmed DESC
            """, (str(field), str(file_extension).lower().strip(), str(sheet_name).strip())).fetchall()
        # A scoped, explicit human correction is strong evidence, but not an unconditional command.
        return {row["alias"]: min(0.98, 0.90 + 0.02 * min(int(row["confirmation_count"])-1, 4))
                for row in rows}

    def mapping_correction_stats(self) -> dict[str, int]:
        with self._connection() as conn:
            row = conn.execute("""
                SELECT COUNT(*) AS corrections,
                       COALESCE(SUM(confirmation_count),0) AS confirmations
                FROM user_mapping_corrections
            """).fetchone()
        return {"corrections": int(row["corrections"]),
                "confirmations": int(row["confirmations"])}

    @staticmethod
    def _profile_hash(file_extension: str, sheet_name: str, headers: list[str]) -> tuple[str, str]:
        import hashlib
        normalized = [str(h).strip().casefold() for h in headers if str(h).strip()]
        signature = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
        payload = json.dumps([str(file_extension).lower(), str(sheet_name).casefold(), normalized],
                             ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest(), signature

    def remember_workbook_profile(self, file_extension: str, sheet_name: str,
                                  headers: list[str]) -> bool:
        """Remember structural metadata only after a user-approved import."""
        clean_headers = [str(h).strip() for h in headers if str(h).strip()]
        if not clean_headers:
            return False
        profile_hash, signature = self._profile_hash(file_extension, sheet_name, clean_headers)
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO workbook_learning
                    (profile_hash,file_extension,sheet_name,header_signature,header_count)
                VALUES (?,?,?,?,?)
                ON CONFLICT(profile_hash) DO UPDATE SET
                    confirmed_imports=confirmed_imports+1,
                    last_seen=CURRENT_TIMESTAMP
            """, (profile_hash, str(file_extension).lower(), str(sheet_name),
                  signature, len(clean_headers)))
        return True

    def find_similar_workbook_profiles(self, file_extension: str,
                                       headers: list[str], limit: int = 5) -> list[dict[str, Any]]:
        """Return prior approved workbook profiles with matching extension and header overlap."""
        current = {str(h).strip().casefold() for h in headers if str(h).strip()}
        if not current:
            return []
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT file_extension,sheet_name,header_signature,header_count,
                       confirmed_imports,last_seen
                FROM workbook_learning
                WHERE file_extension=? ORDER BY confirmed_imports DESC,last_seen DESC
                LIMIT ?
            """, (str(file_extension).lower(), max(1, min(int(limit), 20)))).fetchall()
        results = []
        for row in rows:
            try:
                previous = set(json.loads(row["header_signature"]))
            except (TypeError, ValueError):
                previous = set()
            union = current | previous
            similarity = len(current & previous) / len(union) if union else 0.0
            results.append({
                "sheet_name": row["sheet_name"],
                "similarity": round(similarity, 3),
                "confirmed_imports": int(row["confirmed_imports"]),
                "last_seen": row["last_seen"],
            })
        return sorted(results, key=lambda item: (item["similarity"], item["confirmed_imports"]),
                      reverse=True)

    def workbook_learning_stats(self) -> dict[str, int]:
        with self._connection() as conn:
            row = conn.execute("""
                SELECT COUNT(*) AS profiles,
                       COALESCE(SUM(confirmed_imports),0) AS confirmations
                FROM workbook_learning
            """).fetchone()
        return {"profiles": int(row["profiles"]), "confirmations": int(row["confirmations"])}

    def remember_confirmed_relationship(self, left_field: str, right_field: str) -> bool:
        left, right = str(left_field).strip(), str(right_field).strip()
        if not left or not right or left == right:
            return False
        if right < left:
            left, right = right, left
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO confirmed_relationships(left_field,right_field)
                VALUES (?,?)
                ON CONFLICT(left_field,right_field) DO UPDATE SET
                    confirmation_count=confirmation_count+1,
                    last_confirmed=CURRENT_TIMESTAMP
            """, (left, right))
        return True

    def confirmed_relationships(self) -> list[dict[str, Any]]:
        with self._connection() as conn:
            return [dict(row) for row in conn.execute("""
                SELECT left_field,right_field,confirmation_count,last_confirmed
                FROM confirmed_relationships ORDER BY confirmation_count DESC
            """).fetchall()]

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
                "isCriticalMilitary", "hasSeatingError", "errorNotes",
                "sourceSheet", "sourceRow", "sourceTable"
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


    @staticmethod
    def _history_normalize(value: Any) -> str:
        import re
        text = str(value or "").strip().translate(str.maketrans(
            "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"
        ))
        return re.sub(r"[^0-9A-Za-zء-ي]", "", text).casefold()

    def record_student_history(self, students: list[dict[str, Any]], academic_period: str,
                               source_file: str, import_batch_id: int | None = None) -> dict[str, int]:
        """Append snapshots only after a successful import; never overwrites prior history."""
        period = str(academic_period or "").strip()
        if not period:
            return {"recorded": 0, "code_changes": 0, "name_changes": 0}
        changes = self.compare_student_history(students, period)
        recorded = 0
        with self._connection() as conn:
            for student in students:
                nid = self._history_normalize(student.get("nationalId"))
                code = self._history_normalize(student.get("code"))
                key_type, identity = ("national_id", nid) if nid else ("student_code", code)
                if not identity:
                    continue
                conn.execute("""
                    INSERT INTO student_history
                    (identity_key,identity_type,academic_period,student_name,student_code,
                     national_id,source_file,source_sheet,source_row,import_batch_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    identity, key_type, period, str(student.get("name") or ""),
                    str(student.get("code") or ""), str(student.get("nationalId") or ""),
                    str(source_file), str(student.get("sourceSheet") or ""),
                    str(student.get("sourceRow") or ""), import_batch_id
                ))
                recorded += 1
        return {
            "recorded": recorded,
            "code_changes": sum(1 for item in changes if item["type"] == "code_changed"),
            "name_changes": sum(1 for item in changes if item["type"] == "name_changed"),
        }

    def compare_student_history(self, students: list[dict[str, Any]],
                                academic_period: str = "") -> list[dict[str, Any]]:
        """Compare incoming students to their latest earlier snapshot using stable national ID."""
        findings = []
        with self._connection() as conn:
            for student in students:
                nid = self._history_normalize(student.get("nationalId"))
                code = self._history_normalize(student.get("code"))
                key_type, identity = ("national_id", nid) if nid else ("student_code", code)
                if not identity:
                    continue
                params: list[Any] = [identity, key_type]
                period_clause = ""
                if academic_period:
                    period_clause = " AND academic_period <> ?"
                    params.append(str(academic_period).strip())
                previous = conn.execute(f"""
                    SELECT * FROM student_history
                    WHERE identity_key=? AND identity_type=? {period_clause}
                    ORDER BY recorded_at DESC,id DESC LIMIT 1
                """, params).fetchone()
                if not previous:
                    continue
                old_code = self._history_normalize(previous["student_code"])
                old_name = self._history_normalize(previous["student_name"])
                if code and old_code and code != old_code:
                    findings.append({
                        "type": "code_changed", "severity": "warning",
                        "message": "كود الطالب تغير مقارنة بسجل سابق",
                        "old_value": previous["student_code"], "new_value": student.get("code", ""),
                        "previous_period": previous["academic_period"],
                        "source_file": previous["source_file"], "student_name": student.get("name", ""),
                    })
                if self._history_normalize(student.get("name")) and old_name and self._history_normalize(student.get("name")) != old_name:
                    findings.append({
                        "type": "name_changed", "severity": "warning",
                        "message": "اسم الطالب تغير مقارنة بسجل سابق",
                        "old_value": previous["student_name"], "new_value": student.get("name", ""),
                        "previous_period": previous["academic_period"],
                        "source_file": previous["source_file"], "student_name": student.get("name", ""),
                    })
        return findings


    def list_history_periods(self) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT academic_period FROM student_history
                GROUP BY academic_period ORDER BY academic_period DESC
            """).fetchall()
        return [str(row["academic_period"]) for row in rows]

    def compare_with_reference_roster(self, current_students: list[dict[str, Any]],
                                      reference_period: str) -> dict[str, Any]:
        """Compare a selected current roster against one explicitly selected historical period."""
        period = str(reference_period or "").strip()
        if not period:
            return {"reference_period": "", "new_students": [], "missing_students": [],
                    "changed_students": [], "reference_count": 0, "current_count": 0}
        current_by_id: dict[str, dict[str, Any]] = {}
        for student in current_students:
            nid = self._history_normalize(student.get("nationalId"))
            code = self._history_normalize(student.get("code"))
            identity = ("nid:" + nid) if nid else (("code:" + code) if code else "")
            if identity:
                current_by_id[identity] = student
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT identity_key,identity_type,student_name,student_code,national_id,
                       source_file,source_sheet,source_row
                FROM student_history
                WHERE academic_period=?
                ORDER BY id
            """, (period,)).fetchall()
        reference_by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            identity = ("nid:" if row["identity_type"] == "national_id" else "code:") + row["identity_key"]
            reference_by_id[identity] = dict(row)
        new_students = []
        missing_students = []
        changed_students = []
        for identity, student in current_by_id.items():
            previous = reference_by_id.get(identity)
            if previous is None:
                new_students.append({
                    "name": student.get("name", ""), "code": student.get("code", ""),
                    "nationalId": student.get("nationalId", ""),
                    "sourceFile": student.get("sourceFile", ""),
                    "sourceSheet": student.get("sourceSheet", ""),
                    "sourceRow": student.get("sourceRow", ""),
                })
            else:
                old_code = self._history_normalize(previous.get("student_code"))
                new_code = self._history_normalize(student.get("code"))
                old_name = self._history_normalize(previous.get("student_name"))
                new_name = self._history_normalize(student.get("name"))
                if (old_code and new_code and old_code != new_code) or (old_name and new_name and old_name != new_name):
                    changed_students.append({
                        "old_name": previous.get("student_name", ""),
                        "new_name": student.get("name", ""),
                        "old_code": previous.get("student_code", ""),
                        "new_code": student.get("code", ""),
                        "national_id": student.get("nationalId", ""),
                        "source_file": previous.get("source_file", ""),
                    })
        for identity, previous in reference_by_id.items():
            if identity not in current_by_id:
                missing_students.append({
                    "name": previous.get("student_name", ""),
                    "code": previous.get("student_code", ""),
                    "nationalId": previous.get("national_id", ""),
                    "source_file": previous.get("source_file", ""),
                    "source_sheet": previous.get("source_sheet", ""),
                    "source_row": previous.get("source_row", ""),
                })
        return {
            "reference_period": period,
            "new_students": new_students,
            "missing_students": missing_students,
            "changed_students": changed_students,
            "reference_count": len(reference_by_id),
            "current_count": len(current_by_id),
        }

    def get_student_history(self, identity: str) -> list[dict[str, Any]]:
        key = self._history_normalize(identity)
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT academic_period,student_name,student_code,national_id,
                       source_file,source_sheet,source_row,recorded_at
                FROM student_history
                WHERE identity_key=? ORDER BY recorded_at,id
            """, (key,)).fetchall()
        return [dict(row) for row in rows]

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

