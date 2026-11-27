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


def expand_merged_cells(file_path: str, sheet_name: str, frame: pd.DataFrame):
    """Copy merged-cell anchor values into the covered dataframe cells.

    Excel stores only the top-left value of a merged range. Expanding the value
    in the in-memory dataframe helps multi-row headings without modifying source.
    Unsupported formats safely return the original dataframe.
    """
    frame = frame.copy(deep=True)
    try:
        from openpyxl import load_workbook
        workbook = load_workbook(file_path, read_only=False, data_only=True)
    except Exception:
        return frame, 0
    count = 0
    try:
        if sheet_name not in workbook.sheetnames:
            return frame, 0
        worksheet = workbook[sheet_name]
        for merged_range in worksheet.merged_cells.ranges:
            min_col, min_row, max_col, max_row = merged_range.bounds
            if min_row > len(frame) or min_col > frame.shape[1]:
                continue
            anchor = worksheet.cell(min_row, min_col).value
            if anchor is None:
                continue
            for row_num in range(min_row, min(max_row, len(frame)) + 1):
                for col_num in range(min_col, min(max_col, frame.shape[1]) + 1):
                    frame.iat[row_num - 1, col_num - 1] = str(anchor)
            count += 1
        return frame, count
    finally:
        workbook.close()


def profile_columns(frame: pd.DataFrame, start_row: int = 0, sample_size: int = 250):
    """Build cheap content fingerprints for columns with missing/ambiguous labels."""
    profiles = []
    sample = frame.iloc[start_row:start_row + sample_size]
    for col_index in range(frame.shape[1]):
        values = [str(v).strip() for v in sample.iloc[:, col_index].tolist()
                  if v is not None and not pd.isna(v) and str(v).strip()]
        total = len(values)
        if not total:
            profiles.append({
                "column_index": col_index, "nonempty": 0, "numeric_ratio": 0.0,
                "date_ratio": 0.0, "national_id_ratio": 0.0,
                "arabic_text_ratio": 0.0, "average_length": 0.0,
            })
            continue
        numeric = date_like = national_id = arabic_text = 0
        lengths = []
        for value in values:
            normalized = value.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
            compact = re.sub(r"[\s-]", "", normalized)
            lengths.append(len(value))
            if re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", compact):
                numeric += 1
            if re.fullmatch(r"[23]\d{13}", compact):
                national_id += 1
            if re.search(r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}", compact):
                date_like += 1
            if re.search(r"[\u0600-\u06FF]", value):
                arabic_text += 1
        profiles.append({
            "column_index": col_index,
            "nonempty": total,
            "numeric_ratio": round(numeric / total, 3),
            "date_ratio": round(date_like / total, 3),
            "national_id_ratio": round(national_id / total, 3),
            "arabic_text_ratio": round(arabic_text / total, 3),
            "average_length": round(sum(lengths) / total, 1),
        })
    return profiles


def find_ambiguous_columns(profiles, threshold: float = 0.65):
    """Flag strong value patterns as review hints, never as automatic assignments."""
    hints = []
    for profile in profiles:
        for field, key in (
            ("nationalId", "national_id_ratio"),
            ("numeric", "numeric_ratio"),
            ("date", "date_ratio"),
            ("arabicText", "arabic_text_ratio"),
        ):
            ratio = profile.get(key, 0.0)
            if ratio >= threshold:
                hints.append({
                    "column_index": profile["column_index"],
                    "pattern": field,
                    "ratio": ratio,
                    "review_only": True,
                })
    return hints


def normalize_student_value(value: object) -> str:
    """Canonicalize comparable values while retaining original workbook values elsewhere."""
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().translate(
        str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    )
    text = re.sub(r"[\\u064B-\\u065F\\u0670\\u0640]", "", text)
    text = text.translate(str.maketrans("أإآ", "ااا")).replace("ة", "ه").replace("ى", "ي")
    text = re.sub(r"[^0-9a-zA-Z\\u0621-\\u064A]", "", text.lower())
    return text


def map_header_columns(headers, ontology: Dict, learned: Dict | None = None,
                       threshold: float = 72):
    """Map each semantic field to at most one column; never reuse a column."""
    learned = learned or {}
    candidates = []
    for field, spec in ontology.items():
        aliases = list(spec.get("headers", [])) + list(learned.get(field, {}).keys())
        for index, header in enumerate(headers):
            cell = normalize_header(header)
            best = max((fuzz.ratio(cell, normalize_header(alias)) for alias in aliases
                        if normalize_header(alias)), default=0)
            if best >= threshold:
                candidates.append((best, field, index))
    result = {}
    used_columns = set()
    for score, field, index in sorted(candidates, reverse=True):
        if field not in result and index not in used_columns:
            result[field] = {"column_index": index, "score": round(score, 1)}
            used_columns.add(index)
    return result


def detect_table_candidates(frame: pd.DataFrame, ontology: Dict, learned: Dict | None = None,
                            min_matches: int = 2, scan_rows: int = 250):
    """Find separate header+data tables in one sheet, including repeated header blocks."""
    if frame is None or frame.empty:
        return []
    candidates = []
    limit = min(len(frame), scan_rows)
    row = 0
    while row < limit:
        preview = frame.iloc[row:min(limit, row + 2)].reset_index(drop=True)
        local_header, depth, confidence, matches = detect_header_structure(
            preview, ontology, learned, scan_rows=2
        )
        # Only accept a header when it starts on this physical row.
        if local_header != 0 or matches < min_matches:
            row += 1
            continue
        headers = compose_header_values(frame, row, depth)
        mapping = map_header_columns(headers, ontology, learned)
        if len(mapping) < min_matches:
            row += 1
            continue
        data_start = row + depth
        data_end = data_start
        while data_end < len(frame):
            values = frame.iloc[data_end].tolist()
            if not any(normalize_student_value(v) for v in values):
                break
            if is_repeated_header_row(values, headers, ontology):
                break
            data_end += 1
        if data_end > data_start:
            candidates.append({
                "header_row": row,
                "header_depth": depth,
                "data_start": data_start,
                "data_end": data_end - 1,
                "confidence": confidence,
                "matched_fields": matches,
                "column_mapping": mapping,
                "headers": headers,
                "review_required": confidence < 0.35 or len(mapping) < len(ontology),
            })
            row = data_end
        else:
            row += 1
    return candidates


def find_duplicate_candidates(records, id_field: str = "nationalId",
                              code_field: str = "code", name_field: str = "name"):
    """Find deterministic duplicate groups; never merge or delete student records.

    National ID and student code are strong keys. Name alone is intentionally
    insufficient because different students may share the same name.
    """
    groups = []
    for field, strength in ((id_field, "strong"), (code_field, "strong")):
        buckets = {}
        for index, record in enumerate(records):
            value = normalize_student_value(record.get(field))
            if value:
                buckets.setdefault(value, []).append(index)
        for value, indices in buckets.items():
            if len(indices) > 1:
                groups.append({
                    "field": field, "normalized_value": value,
                    "record_indices": indices, "strength": strength,
                    "review_required": True,
                })
    # A repeated name is only a weak hint, not a duplicate verdict.
    name_buckets = {}
    for index, record in enumerate(records):
        name = normalize_student_value(record.get(name_field))
        if name:
            name_buckets.setdefault(name, []).append(index)
    for value, indices in name_buckets.items():
        if len(indices) > 1:
            groups.append({
                "field": name_field, "normalized_value": value,
                "record_indices": indices, "strength": "weak",
                "review_required": True,
            })
    return groups


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
            preview, _ = expand_merged_cells(file_path, sheet_name, preview)
            row_index, header_depth, confidence, matches = detect_header_structure(
                preview, ontology, learned, scan_rows
            )
            header_values = compose_header_values(preview, row_index, header_depth) if not preview.empty else []
            score, _ = _header_score(header_values, ontology, learned) if header_values else (0, 0)
            candidate = (score, matches, sheet_name, row_index, confidence, header_depth)
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
        data, merged_ranges = expand_merged_cells(file_path, sheet_name, data)
        profiles = profile_columns(data, header_row + header_depth)
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
            "merged_ranges_expanded": merged_ranges,
            "column_profiles": profiles,
            "content_hints": find_ambiguous_columns(profiles),
        }
        return data, sheet_name, header_row, metadata
    finally:
        # Release the workbook file handle before callers clean up temporary files.
        book.close()
