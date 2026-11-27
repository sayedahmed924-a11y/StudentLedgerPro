# Phase 15 — Cross-workbook audit engine

## Capabilities
- Audits multiple workbook outputs together before import confirmation.
- Detects duplicate student codes inside the same workbook sheet.
- Detects the same code associated with different names or national IDs across sources.
- Detects a national ID associated with multiple student codes or names.
- Reports missing student name, student code and national ID with severity levels.
- Preserves workbook, sheet and row provenance in each finding.
- Displays a concise findings summary and up to 15 actionable findings before the user approves import.

## Safety
The audit is read-only. It does not merge, overwrite, delete, or repair records. Arabic and Persian digits are normalized for comparisons. Name-only matches are not treated as proof of identity. Absence from one workbook is not labeled as a missing student because no authoritative expected roster is defined.

## Tests
`tests/test_workbook_audit.py` covers same-sheet duplicates, cross-file identity conflicts, missing fields, and national-ID collisions.
