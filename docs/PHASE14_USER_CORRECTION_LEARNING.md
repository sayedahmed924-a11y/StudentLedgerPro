# Phase 14 — Employee-confirmed mapping corrections

## Features
- During import review, employees can select the correct header for uncertain semantic fields or skip saving a correction.
- Corrections are stored in SQLite and scoped to semantic field + workbook extension + worksheet name.
- Repeated confirmations increase the correction's evidence score, capped below absolute certainty.
- Matching future workbooks use these corrections as additional header evidence.
- Each saved correction is recorded in the activity log with the acting user.

## Safety
- No correction is stored without an explicit employee selection.
- A correction for one worksheet/extension does not automatically apply to another context.
- Corrections affect future imports; they do not silently rewrite the current preview or existing student records.
- This feature does not auto-merge or delete student records.

## Tests
`tests/test_mapping_correction_memory.py` checks context scoping, repeated confirmations and rejection of empty corrections.
