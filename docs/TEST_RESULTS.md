# Release verification

Run on 20 October 2026 with Python 3.14.0 and SQLite on macOS. The source package requires Python 3.11+; other Python versions and operating systems have not been independently exercised for this release.

## Automated results

- `python3 -m unittest discover -s tests -v`: **64 tests, all pass**. [Full output](unit-tests.txt).
- `python3 scripts/smoke_test.py`: **all three groups pass**. [Full output](smoke-test.txt).

The unit tests cover atomic batch writes and rollback, normalization, duplicate replay, newer/equal/older snapshots, source-scoped identity, missing versus zero, timestamp consistency, source freshness, provenance relationships, concurrent story revisions, injected SQLite snapshot failure, preview isolation and single-use tokens.

The smoke test exercises CLI imports, invalid-batch rollback, HTTP assets/reporting, rejected paths, disabled writes in read-only mode, exact-origin and JSON guards, technical workbench preview/apply/reset, all six story transitions, stale-revision rejection and unchanged baseline database bytes. It creates a temporary database and OS-assigned loopback ports. The sandbox initially prevented socket binding; the same smoke command then passed with permission to open temporary loopback listeners.

Additional reusable-core tests cover arbitrary source namespaces, units and HTTPS evidence references, SQL view queries, schema version and shape rejection without mutation, caller transaction preservation, custom freshness thresholds, input-only validation, read-only reports, the complete documented fresh-DB workflow and export/reimport equivalence.

## Scope

The original story interface and its seven scenes plus architecture were visually reviewed during creation of the linked walkthrough. This source export preserves that runtime UI and removes the separate GIF-capture endpoint/assets. Automated checks verify the exported server and runtime assets; there is no claim of an exhaustive cross-browser, accessibility, security, performance or production-readiness audit.

No live AI agent, Notion, Metricool, publisher or scheduler was tested or connected. All values, dates, actions and outcomes are synthetic. The tests establish behavior of this demonstration, not the correctness of a real operational system.
