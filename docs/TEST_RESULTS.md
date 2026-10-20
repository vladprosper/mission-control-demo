# Release verification

Run on 20 October 2026 with Python 3.14.0 and SQLite on macOS. The original 64-test suite and smoke commands passed all 12 hosted jobs (Python 3.11–3.14 × Ubuntu/macOS/Windows) in [run 39415764459](https://github.com/vladprosper/mission-control-demo/actions/runs/39415764459), commit `9edf551`. The [current workflow](https://github.com/vladprosper/mission-control-demo/actions/workflows/ci.yml) records results for subsequent commits.

## Automated results

- `python3 -m unittest discover -s tests -v`: **65 tests passed locally in a clean copy**, including the new malformed-input regression. The checked-in [earlier output](unit-tests.txt) records 64 tests; use Actions logs for current commit evidence.
- `python3 scripts/smoke_test.py`: **all three groups pass**. [Full output](smoke-test.txt).

The unit tests cover atomic batch writes and rollback, normalization, duplicate replay, newer/equal/older snapshots, source-scoped identity, missing versus zero, timestamp consistency, source freshness, provenance relationships, concurrent story revisions, injected SQLite snapshot failure, preview isolation and single-use tokens.

The smoke test exercises CLI imports, invalid-batch rollback, HTTP assets/reporting, rejected paths, disabled writes in read-only mode, exact-origin and JSON guards, technical workbench preview/apply/reset, all six story transitions, stale-revision rejection and unchanged baseline database bytes. It creates a temporary database and OS-assigned loopback ports. The sandbox initially prevented socket binding; the same smoke command then passed with permission to open temporary loopback listeners.

Additional reusable-core tests cover arbitrary source namespaces, units and HTTPS evidence references, SQL view queries, schema version and shape rejection without mutation, caller transaction preservation, custom freshness thresholds, input-only validation, read-only reports, the complete documented fresh-DB workflow and export/reimport equivalence.

The added CLI regression rejects JSON `null`, duplicate JSON fields, unterminated CSV fields/headers, out-of-range metrics and UTC-overflow timestamps. Each case exits 2 without a traceback or a newly created database. The documented stale-replay command was executed and preserved database bytes. The final local smoke rerun was interrupted by loss of the Mac connection; its result is unconfirmed. Hosted CI runs both commands for each commit.

## Scope

The original story interface and its seven scenes plus architecture were visually reviewed during creation of the linked walkthrough. This source export preserves that runtime UI and removes the separate GIF-capture endpoint/assets. Automated checks verify the exported server and runtime assets; there is no claim of an exhaustive cross-browser, accessibility, security, performance or production-readiness audit.

No live AI agent, Notion, Metricool, publisher or scheduler was tested or connected. All values, dates, actions and outcomes are synthetic. The tests establish behavior of this demonstration, not the correctness of a real operational system.
