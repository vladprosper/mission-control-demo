# Synthetic import contract

Every example is fictional. `synthetic.json` and `synthetic.csv` represent the same 12 records. Blank CSV cells map to `null`; JSON uses `null` explicitly. Unknown keys, malformed CSV widths, and duplicate CSV headers are rejected. Inputs are limited to 5 MB and batches to 10,000 nonempty object records.

| Field | Meaning and validation |
| --- | --- |
| `source` | Required; `mock_notion`, `mock_metricool`, or `mock_manual` only. |
| `external_id` | Required string; unique together with source. No cross-source fuzzy matching. |
| `title`, `workstream` | Required nonempty strings, each at most 240 characters. |
| `status` | Required; one of the six states below. |
| `source_date` | Optional timezone-aware observation timestamp; controls source freshness. |
| `source_updated_at` | Required timezone-aware snapshot timestamp; controls update precedence. Must not follow import time. |
| `scheduled_for` | Optional timezone-aware intended execution time; required for scheduled records. No job is created. |
| `submitted_at` | Required for submitted and verified; forbidden before submission. |
| `verified_at` | Required only for verified; cannot precede submitted_at. |
| `evidence_url` | Required only for verified; must use `https://example.invalid/evidence/`. It is displayed as text and never fetched. |
| `metric_value`, `metric_unit` | Both absent/null or both present. Finite nonnegative numeric value (bools rejected); unit is views/items/hours. Zero is valid. |

All timestamp values normalize to UTC. Source observation, submission, and verification timestamps cannot follow `source_updated_at`. Required strings are trimmed. Numeric values normalize to float so `3` and `3.0` deduplicate equally across CSV and JSON.

| Status | Demo meaning | Does not establish |
| --- | --- | --- |
| planned | Intent recorded | A prepared draft |
| drafted | Material prepared | A scheduled time |
| scheduled | Time assigned in the snapshot | A platform scheduling action |
| submitted | Handoff timestamp supplied | Delivery or external success |
| verified | Submission + verification timestamp + fictional evidence reference supplied | A real-world verified result |

Statuses are source assertions with structural validation, not audited workflow achievements. The importer does not infer progression from a date, metric, or previous state. A newer snapshot can correct or regress status. Scheduled timestamps may remain on submitted or verified snapshots as context; they do not prove execution.

## Atomicity and deduplication

1. Parse the whole file and validate every row before writes.
2. Build identity keys from `(source, external_id)`. Identical normalized rows in a batch count as duplicates. Two differing snapshots with the same key within one batch reject the batch.
3. Use `BEGIN IMMEDIATE` for writes. Hash the full canonical validated row using SHA-256. An identical stored digest skips the record without changing its original `imported_at`.
4. Changed content needs a strictly newer `source_updated_at`; an older or equal timestamp rejects the whole batch, including any preceding inserts or updates.
5. Commit the data and one successful import summary together. Any validation or database failure rolls back everything in that transaction. Reimports add a successful summary even if every record was duplicate. Failed attempts appear as CLI errors, with no persistent failure audit.

The hash is a deduplication aid, not evidence signing or tamper protection. Identity matching does not detect semantically duplicate content with different external IDs. Import summaries contain counts, not a full event history.

## Time, freshness, and missing data

`source_date` is the fictional observation date, `source_updated_at` is when that snapshot changed, and `imported_at` is when this importer accepted a changed record. These are separate fields. A successful duplicate import does not rewrite record provenance.

Age is `(report_as_of - source_date)` in fractional 24-hour days. Fresh ≤ 7; stale > 7; missing = unknown. Classification uses unrounded age; UI age rounds to one decimal. All dates shown are UTC. The rule is a demonstration threshold, not a service-level objective.

A report earlier than any retained import/update time fails rather than presenting latest records as historical truth. Missing source dates never borrow the import date. Missing metrics are never filled with zero, and there is no aggregate mixing views, items, or hours.
