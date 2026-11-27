# -*- coding: utf-8 -*-
"""Lightweight, offline Excel layout discovery for StudentLedgerPro.

The module deliberately uses pandas + the project's existing rapidfuzz dependency.
It does not infer or alter student values; it only locates the most likely table
header and worksheet for the existing audit pipeline.
"""
from __future__ import annotations

import os
import re
from typing import Dict, Iterable, Tuple

import pandas as pd
from rapidfuzz import fuzz


def normalize_header(value: object) -> str:
    """Normalize Arabic/English header text without changing stored source data."""
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)
    text = text.translate(str.maketrans("أإآ", "ااا"))
    text = text.replace("ة", "ه").replace("ى", "ي")
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
    text = re.sub(r"[_.,;:/\\|()\[\]{}-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _header_score(values: Iterable[object], ontology: Dict, learned: Dict | None = None) -> Tuple[float, int]:
    cells = [normalize_header(v) for v in values]
    cells = [v for v in cells if v]
    if not cells:
        return 0.0, 0
    matched_fields = 0
    total_strength = 0.0
    learned = learned or {}
    for field, spec in ontology.items():
        aliases = list(spec.get("headers", []))
        aliases.extend(learned.get(field, {}).keys())
        best = 0.0
        for cell in cells:
            for alias in aliases:
                alias_norm = normalize_header(alias)
                if not alias_norm:
                    continue
                score = max(
                    fuzz.ratio(cell, alias_norm),
                    fuzz.partial_ratio(cell, alias_norm) * 0.92,
                    fuzz.token_set_ratio(cell, alias_norm) * 0.90,
                )
                if alias_norm == cell:
                    score = 100.0
                best = max(best, score)
        if best >= 72:
            matched_fields += 1
            total_strength += best
    # Distinct semantic fields matter more than many repeated title cells.
    density_bonus = min(len(cells), 12) * 0.35
    return total_strength + matched_fields * 8 + density_bonus, matched_fields


def detect_header_row(frame: pd.DataFrame, ontology: Dict, learned: Dict | None = None,
                      scan_rows: int = 60) -> Tuple[int, float, int]:
    """Return (zero-based row, confidence 0..1, matched semantic field count)."""
    if frame is None or frame.empty:
        return 0, 0.0, 0
    best = (0.0, 0, 0)
    for row_index in range(min(scan_rows, len(frame))):
        values = frame.iloc[row_index].tolist()
        score, matches = _header_score(values, ontology, learned)
        # Small preference for a row with several populated cells; never outweighs
        # a genuine semantic match.
        nonempty = sum(1 for value in values if normalize_header(value))
        score += min(nonempty, 15) * 0.15
        if (score, matches) > (best[0], best[2]):
            best = (score, row_index, matches)
    confidence = min(1.0, best[0] / 260.0) if best[2] else 0.0
    return best[1], confidence, best[2]



def detect_header_structure(frame: pd.DataFrame, ontology: Dict, learned: Dict | None = None,
                            scan_rows: int = 60) -> Tuple[int, int, float, int]:
    """Find one- or two-row headers, including split words across stacked rows."""
    if frame is None or frame.empty:
        return 0, 1, 0.0, 0
    best = (0.0, 0, 1, 0)
    limit = min(scan_rows, len(frame))
    for row_index in range(limit):
        variants = [(1, frame.iloc[row_index].tolist())]
        if row_index + 1 < limit:
            upper = frame.iloc[row_index].tolist()
            lower = frame.iloc[row_index + 1].tolist()
            width = max(len(upper), len(lower))
            combined = []
            for col in range(width):
                a = normalize_header(upper[col]) if col < len(upper) else ""
                b = normalize_header(lower[col]) if col < len(lower) else ""
                combined.append(" ".join(part for part in (a, b) if part))
            variants.append((2, combined))
        for depth, values in variants:
            score, matches = _header_score(values, ontology, learned)
            nonempty = sum(1 for value in values if normalize_header(value))
            score += min(nonempty, 15) * 0.15
            # Prefer the shorter header when evidence is effectively tied.
            candidate = (score, row_index, depth, matches)
            if (candidate[0], candidate[3], -candidate[2]) > (best[0], best[3], -best[2]):
                best = candidate
    confidence = min(1.0, best[0] / 260.0) if best[3] else 0.0
    return best[1], best[2], confidence, best[3]


def compose_header_values(frame: pd.DataFrame, header_row: int, depth: int = 1):
    """Compose stacked header cells while preserving the source dataframe."""
    rows = frame.iloc[header_row:header_row + max(1, depth)]
    headers = []
    for col in range(frame.shape[1]):
        parts = []
        for value in rows.iloc[:, col].tolist():
            normalized = normalize_header(value)
            if normalized and normalized not in parts:
                parts.append(normalized)
        headers.append(" ".join(parts))
    return headers


def find_nonempty_regions(frame: pd.DataFrame, start_row: int = 0):
    """Return contiguous non-empty row regions; blank separators split tables."""
    regions = []
    region_start = None
    for index in range(start_row, len(frame)):
        row = frame.iloc[index]
        populated = any(normalize_header(value) for value in row.tolist())
        if populated and region_start is None:
            region_start = index
        elif not populated and region_start is not None:
            if index - region_start >= 2:
                regions.append((region_start, index - 1))
            region_start = None
    if region_start is not None and len(frame) - region_start >= 2:
        regions.append((region_start, len(frame) - 1))
    return regions


def is_repeated_header_row(values, headers, ontology: Dict) -> bool:
    """Recognize a repeated header inside a sheet so it is not imported as a student."""
    normalized = [normalize_header(v) for v in values]
    normalized = [v for v in normalized if v]
    if len(normalized) < 2:
        return False
    header_norms = {normalize_header(v) for v in headers if normalize_header(v)}
    direct = sum(1 for value in normalized if value in header_norms)
    semantic = _header_score(values, ontology)[1]
    return direct >= 2 or semantic >= 2

def load_best_sheet(file_path: str, ontology: Dict, learned: Dict | None = None,
                    scan_rows: int = 60):
    """Inspect every worksheet's first rows, then load only the winning sheet fully.

    Returns (dataframe, sheet_name, header_row, detection_metadata).
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    try:
        book = pd.ExcelFile(file_path)
    except Exception as exc:
        raise ValueError("تعذر فتح ملف Excel. تحقق من سلامة الملف وامتداده.") from exc

    try:
        if not book.sheet_names:
            raise ValueError("ملف Excel لا يحتوي على أوراق عمل.")
        winner = None
        for sheet_name in book.sheet_names:
            try:
                preview = pd.read_excel(
                    book, sheet_name=sheet_name, header=None, dtype=str,
                    nrows=scan_rows, keep_default_na=False
                )
            except Exception:
                continue
            row_index, confidence, matches = detect_header_row(
                preview, ontology, learned, scan_rows
            )
            score, _ = _header_score(
                preview.iloc[row_index].tolist(), ontology, learned
            ) if not preview.empty else (0, 0)
            candidate = (score, matches, sheet_name, row_index, confidence)
            if winner is None or candidate[:2] > winner[:2]:
                winner = candidate

        if winner is None:
            raise ValueError("لم يتمكن البرنامج من قراءة أي ورقة عمل في الملف.")

        score, matches, sheet_name, header_row, confidence, header_depth = winner
        try:
            data = pd.read_excel(
                book, sheet_name=sheet_name, header=None, dtype=str,
                keep_default_na=False
            )
        except Exception as exc:
            raise ValueError("تعذر قراءة ورقة العمل التي تحتوي على الجدول.") from exc
        if data.empty or data.shape[1] == 0:
            raise ValueError("ورقة العمل المحددة لا تحتوي على بيانات.")
        metadata = {
            "sheet_name": sheet_name,
            "header_row": header_row,
            "header_depth": header_depth,
            "confidence": confidence,
            "matched_fields": matches,
            "score": score,
            "review_required": matches < 2 or confidence < 0.35,
            "available_sheets": list(book.sheet_names),
            "nonempty_regions": find_nonempty_regions(data, header_row + header_depth),
        }
        return data, sheet_name, header_row, metadata
    finally:
        # Release the workbook file handle before callers clean up temporary files.
        book.close()
