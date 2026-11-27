# Phase 13 — Explainable Excel field mapping

## Features
- Each candidate mapping records header similarity and sample-content compatibility separately.
- A deterministic one-to-one assignment prevents one Excel column from being assigned to multiple semantic fields.
- The engine records a confidence level, score gap, top alternatives and a human-readable reason for each selected field.
- Medium/low confidence assignments are included in the pre-import confirmation summary for review.
- Only high-confidence mappings are added to semantic alias memory; uncertain guesses are not learned.

## Confidence policy
- High: score >= 80 and at least a 10-point lead over the next candidate for the same field.
- Medium: score >= 60 but does not meet the high-confidence margin.
- Low: below 60.

## Safety
This phase does not automatically merge records or overwrite student data. Existing deterministic classification remains the source of parsed values; the explanation is surfaced before import. Test with anonymized real workbook samples before merging.
