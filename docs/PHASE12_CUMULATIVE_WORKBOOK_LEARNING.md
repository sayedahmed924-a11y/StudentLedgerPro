# Phase 12 — Cumulative workbook learning

## What is learned
- Workbook extension and worksheet label.
- A normalized signature of the detected column headings (not student rows).
- Counts of user-approved imports using the same structure.
- Confirmed relationships between worksheet types when matching student keys appear across imported workbooks.

## How it is used
Before import, the app compares each workbook's header signature with previously approved profiles and reports similar known layouts. After a successful batch import, it stores the profile. Confirmed cross-file matches update a lightweight relationship counter.

## Privacy and safety
No student names, IDs, or row contents are stored in the learning profile. Learning occurs only after user approval. It does not change column mappings, merge records, or delete data automatically. The feature is SQLite-only and works offline.

## Tests
`tests/test_workbook_learning.py` checks profile persistence/similarity, relationship counting and invalid relationship rejection.
