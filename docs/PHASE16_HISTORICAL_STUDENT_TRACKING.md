# Phase 16 — Historical student tracking

## Features
- Optional academic-period label during multi-workbook import (e.g. 2026/2027); blank skips history tracking.
- Append-only SQLite snapshots keyed primarily by normalized national ID, with student code as fallback.
- Stores period, name, code, national ID, source file/sheet/row and import batch reference.
- Compares incoming records with the latest prior snapshot and flags changed student code or name.
- Displays historical changes before import approval and records snapshots only after a successful batch insert.
- History can be retrieved by normalized identity.

## Safety and limitations
- Historical snapshots are append-only; no previous snapshot is overwritten.
- This phase does not infer that a student is missing from a new roster. A missing-student report requires an explicitly selected authoritative roster/period comparison.
- National ID is used as the stable key when present. If absent, student code is used, so a code change cannot be linked reliably without a national ID.
- No automatic merge, deletion or correction is performed.

## Tests
`tests/test_student_history.py` covers code/name changes, append-only retrieval, missing identity, empty period and same-period exclusion.
