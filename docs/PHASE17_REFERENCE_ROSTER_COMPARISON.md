# Phase 17 — Reference roster comparison

## Features
- Lists academic periods previously stored in the append-only student history.
- Lets the operator explicitly select one historical period as the reference roster or skip the comparison.
- Compares the current import preview with that selected period.
- Reports newly appearing students, students absent from the current roster, and students whose name/code changed.
- Normalizes Arabic/Persian/Western digits and uses national ID as the preferred identity key.
- Shows counts and sample source details before import approval.

## Safety and limitations
- A student is only labelled missing after an operator selects a reference period; no inference is made from arbitrary files.
- Records without a usable national ID or student code are excluded from new/missing classification.
- When national ID is missing in the reference or current record, code is used as a fallback; code changes may therefore prevent identity continuity.
- The report is read-only and does not delete, merge, or alter student records.
- Class/team transfer detection requires those fields to be reliably extracted and stored in historical snapshots; this phase does not claim transfer classification.

## Tests
`tests/test_reference_roster_comparison.py` covers new/missing/changed classification, period listing, Arabic digit normalization, and records without identity.
