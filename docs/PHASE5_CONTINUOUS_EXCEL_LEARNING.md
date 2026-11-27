# Phase 5 — Continuous Excel learning

StudentLedgerPro now keeps semantic column-header memory in its existing SQLite database.

## How it works
- The Excel classifier uses built-in header vocabulary, fuzzy matching, and sample cell patterns.
- When a column mapping reaches a confidence score of at least 72/100, its header is saved as an alias for that semantic field.
- Later imports load the saved aliases and use their confidence as part of the header match score.
- Repeated successful matches update the stored confidence using a running average and increment the observation count.
- Low-confidence guesses are not saved, reducing the risk of teaching the system an incorrect mapping.

## Storage and privacy
The learning table is `semantic_memory` in the same per-user SQLite database used by StudentLedgerPro. Learning is local, requires no internet, and adds no machine-learning package or model download.

## Inspect learning memory
The database API provides:
- `get_semantic_aliases(field)`
- `remember_semantic_mapping(field, alias, confidence)`
- `semantic_memory_stats()`

Only users with import permission (admin/editor) can process Excel files and contribute new learning observations.
