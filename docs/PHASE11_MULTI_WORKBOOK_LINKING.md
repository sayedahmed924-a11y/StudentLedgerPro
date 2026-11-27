# Phase 11 — Multi-workbook linking and conflict review

## Added capabilities
- Select multiple Excel workbooks in one import operation.
- Process each workbook independently with the existing dynamic Excel processor.
- Link records across files using normalized student code or national ID, including Arabic/Persian digit normalization.
- Report matched groups and identity conflicts with source workbook/sheet information.
- Preserve each record's source file, sheet and source row in the preview/import payload.
- Ask for confirmation before importing; declining leaves the database unchanged.

## Safety rules
- Names alone never establish a cross-file match.
- No automatic student merge, overwrite or deletion is performed.
- Each workbook is saved as its own import batch so its source filename remains traceable.
- Files that fail to parse are reported while valid workbooks can still be reviewed.

## Verification
`tests/test_workbook_linker.py` covers normalized-code linking, conflict reporting and the rule against name-only matching. Run the complete project test suite and review representative anonymized workbooks before merging.
