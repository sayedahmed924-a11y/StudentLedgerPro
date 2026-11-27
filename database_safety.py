# -*- coding: utf-8 -*-
"""Verified SQLite backup, integrity inspection and guarded restore."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

REQUIRED_TABLES = {"students", "app_users", "import_batches"}


def _inspect_path(path):
    target = Path(path)
    if not target.is_file() or target.stat().st_size == 0:
        raise ValueError("ملف قاعدة البيانات غير موجود أو فارغ.")
    conn = sqlite3.connect("file:" + target.resolve().as_posix() + "?mode=ro", uri=True, timeout=20)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError("فشل فحص سلامة قاعدة البيانات: " + str(integrity))
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValueError("النسخة لا تحتوي الجداول الأساسية: " + ", ".join(sorted(missing)))
        counts = {}
        for table in sorted(tables & {
            "students", "app_users", "import_batches", "student_history",
            "activity_log", "semantic_memory", "workbook_learning",
            "user_mapping_corrections"
        }):
            counts[table] = int(conn.execute('SELECT COUNT(*) FROM "' + table + '"').fetchone()[0])
        return {
            "path": str(target),
            "size_bytes": target.stat().st_size,
            "integrity": integrity,
            "tables": len(tables),
            "counts": counts,
        }
    finally:
        conn.close()


def inspect_database(database):
    result = _inspect_path(database.path)
    with database._connection() as conn:
        result["journal_mode"] = conn.execute("PRAGMA journal_mode").fetchone()[0]
    return result


def create_verified_backup(database, destination):
    target = Path(destination)
    if target.resolve() == database.path.resolve():
        raise ValueError("اختر مساراً مختلفاً عن ملف قاعدة البيانات.")
    database.backup(target)
    try:
        report = _inspect_path(target)
        with database._connection() as live:
            live_counts = {
                table: int(live.execute('SELECT COUNT(*) FROM "' + table + '"').fetchone()[0])
                for table in report["counts"]
                if live.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            }
        if report["counts"] != live_counts:
            raise ValueError("فشل التحقق: أعداد السجلات في النسخة لا تطابق قاعدة البيانات الحالية.")
        report["verified"] = True
        return report
    except Exception:
        try:
            target.unlink()
        except OSError:
            pass
        raise


def restore_verified_backup(database, source_path):
    source = Path(source_path)
    if source.resolve() == database.path.resolve():
        raise ValueError("لا يمكن استعادة قاعدة البيانات من الملف النشط نفسه.")
    source_report = _inspect_path(source)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safety = database.path.with_name(database.path.stem + ".before_restore_" + stamp + database.path.suffix)
    database.backup(safety)
    # Restore with SQLite's online backup API; it handles active WAL databases safely.
    src = sqlite3.connect("file:" + source.resolve().as_posix() + "?mode=ro", uri=True, timeout=30)
    dst = database._connect()
    try:
        src.backup(dst)
        dst.commit()
    except Exception:
        dst.rollback()
        raise
    finally:
        dst.close()
        src.close()
    restored = inspect_database(database)
    restored["safety_backup"] = str(safety)
    restored["restored_from"] = str(source)
    restored["source_counts"] = source_report["counts"]
    return restored
