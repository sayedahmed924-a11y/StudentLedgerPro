# Phase 10 — Unified, review-first Excel import

This phase adds an offline preparation layer between Excel parsing and SQLite persistence.

## Behavior
- Builds canonical student fields while retaining original cell values.
- Tracks source file, worksheet, source row and table index.
- Flags records without a name or without both a student code and national ID.
- Reports repeated student codes and national IDs as review groups.
- Requires explicit confirmation in the desktop UI before writing the batch.
- Preserves append-only imports; it does not merge, overwrite, or delete existing student records.

## Safety
The preview layer never guesses missing identifiers. Duplicate groups are warnings, not automatic merge instructions. Declining confirmation leaves SQLite unchanged.

## Tests
The test module covers provenance, missing-field warnings, duplicate reporting and explicit row selection.
