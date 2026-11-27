# -*- coding: utf-8 -*-
"""Safe portable SQLite path selection and one-time migration helpers."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path


def _is_writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".studentledgerpro_", dir=directory, delete=True):
            pass
        return True
    except OSError:
        return False


def resolve_database_path(
    filename: str,
    app_dir: str | os.PathLike,
    fallback_dir: str | os.PathLike,
) -> Path:
    """Choose a writable portable location and migrate an older SQLite DB safely.

    Existing destination files always win. A legacy DB is copied with SQLite's
    backup API (safe with WAL), then atomically placed at the new destination.
    The source file is never deleted or modified.
    """
    app_dir = Path(app_dir).expanduser().resolve()
    fallback_dir = Path(fallback_dir).expanduser().resolve()
    target_dir = next((p for p in (app_dir, fallback_dir) if _is_writable(p)), None)
    if target_dir is None:
        raise OSError("لا توجد صلاحية كتابة في مجلد البرنامج أو مجلد بيانات المستخدم.")

    target = target_dir / filename
    if target.exists():
        return target

    legacy = fallback_dir / filename
    if target_dir != fallback_dir and legacy.is_file():
        fd, temp_name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".migrating", dir=target_dir)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            # SQLite backup API includes committed WAL content.
            with sqlite3.connect(str(legacy), timeout=30) as source:
                with sqlite3.connect(str(temp_path), timeout=30) as destination:
                    source.backup(destination)
                    result = destination.execute("PRAGMA integrity_check").fetchone()
                    if not result or result[0] != "ok":
                        raise sqlite3.DatabaseError("فشل التحقق من سلامة قاعدة البيانات بعد النسخ.")
            os.replace(temp_path, target)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    return target
