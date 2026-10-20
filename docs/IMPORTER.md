# Importer CLI and Python API

## Scope

This utility accepts already-normalized local files. It performs no network requests, authentication, extraction or scheduling. You can write your own exporter to map a source system to [DATA_CONTRACT.md](DATA_CONTRACT.md). Never put credentials in records or evidence URLs.

The reusable path is `load_file → prepare_batch/import_records → SQLite → report/export`. The browser story is not required.

## Commands

All global options go before the command. Use `python3 -m mission_control --help` and `<command> --help`.

| Command | Result / side effect |
| --- | --- |
| `validate FILE` | Parse, normalize, check intra-file conflicts. JSON summary; no DB access. Does not check conflicts with stored records. |
| `init` | Initialize an empty database with version 1; existing v1 stays unchanged. |
| `import FILE` | Validate file, initialize if new, then atomically insert/update/skip. JSON counts. |
| `report` | Open existing DB read-only; JSON records, statuses, quality and last five successful import summaries. |
| `export` | Open existing DB read-only; JSON array containing only input-contract fields, suitable for reimport. |
| `schema` | JSON containing schema version and SQL text; no DB access. |
| `serve --port 0` | Optional read-only demo server, fictional DBs only. Not needed for importing. |

Options: `--db PATH` (default `output/records.sqlite3`), `--as-of ISO_TIMESTAMP` (current UTC if omitted), `--freshness-days NUMBER` (report/export validation, default 7; finite and nonnegative), `--fictional` (labels a newly initialized database only). All fixture content is synthetic even if a CLI-created database carries the default user-supplied marker. Labels describe database intent; they are not sensitive-data detection.

Exit 0 means success; exit 2 means a parse, validation, database or OS error. JSON success goes to stdout; human-readable error goes to stderr. File validation reports the row number for record-level failures. JSON parser syntax errors use the parser's line/column messages. SQLite transaction failures roll back and propagate.

## Idempotency and failures

Identical normalized records skip without modifying the stored row's `imported_at`. Each successful call still commits an import-summary row. A changed record with the same source/ID needs a strictly newer source update timestamp. Conflicts in any row reject the whole batch, even after another row has been staged. Failures do not create a durable failed-attempt log.

A newly initialized schema can remain if a subsequent database write fails; atomicity covers record changes and their import summary, not database-file creation. Malformed files are rejected before initialization by the CLI. Caller-owned transactions are refused rather than implicitly committed or rolled back.

## Worked example: replay, correction and rejection

For example, start with a new `output/tutorial.sqlite3` and run the commands in the [README](../README.md). The JSON and CSV fixtures represent the same two records, so changing the file format does not create new identities:

| Input, in order | Expected counts or error | Stored result |
| --- | --- | --- |
| `examples/importer/records.json` | inserted 2, updated 0, duplicates 0 | Two records |
| `examples/importer/records.csv` | inserted 0, updated 0, duplicates 2 | Same two records and original import times |
| `examples/importer/newer.json` | inserted 0, updated 1, duplicates 0 | ART-101 changes from drafted to scheduled |
| `examples/importer/invalid.json` | Exit 2; second row has a negative metric | Neither row is written; no new import summary |

The successful calls add three import-summary rows. The rejected call adds none. Validation alone cannot detect a conflict with an older stored snapshot: it checks the file without opening the database. Import also checks stored update precedence.

For example, at `2026-10-19T12:00:00Z`, the fixture's observed zero clicks remains `0`; its missing metric remains `null`. A report with a seven-day threshold flags the old observation as stale. Reimporting that observation today does not make its source date newer.

For example, after importing `newer.json`, importing `records.json` again tries to replace the scheduled ART-101 with its older draft. This command exits 2 with `Changed records require a strictly newer source_updated_at`; both records and successful-import summaries remain unchanged:

```sh
python3 -m mission_control --db output/tutorial.sqlite3 --as-of 2026-10-19T12:00:00Z import examples/importer/records.json
```

An exporter must supply the current snapshot or repeat the unchanged latest record. This store does not automatically merge fields from old and new exports.

## Python calls

Import from `mission_control` while running from the repository root:

- `connect(path)`: opens/creates the dedicated DB and parent directory; sets `sqlite3.Row` and a five-second busy timeout. Caller closes it.
- `initialize(db, fictional=False)`: initializes only an empty unversioned DB; verifies current-version shape for an existing store. Does not migrate or relabel existing records.
- `load_file(path)`: reads UTF-8/UTF-8-BOM JSON or CSV, ≤5 MB. No DB access.
- `prepare_batch(rows, as_of=None)`: returns `(normalized_unique_rows, duplicate_count)`. No DB access; does not check stored-update precedence.
- `import_records(db, rows, as_of=None)`: owns one transaction and returns inserted/updated/duplicates counts. Pass a connection with no active transaction.
- `report(db, as_of=None, freshness_days=7)`: current report with dated freshness; no writes.
- `timestamp(text)`: parses timezone-aware ISO 8601 into UTC. Supply aware datetimes to the API.
- `ValidationError`: catch for input/state errors; SQLite and file errors can also propagate through the Python API.

Use `contextlib.closing(connect(...))` to close the connection. A SQLite connection's own `with` statement manages transactions, not closing. Give separate threads separate importer connections; the core is synchronous. The demo's in-memory state has its own locks.

## SQL example

```sql
SELECT source, external_id, status, metric_value, metric_unit, source_date
FROM record_details
WHERE metric_value IS NULL OR source_date IS NULL;
```

The query does not conflate unknown metrics with observed zero. For totals, group by metric unit and apply your own source/period semantics—this schema has no measurement-period field and cannot establish cross-source comparability.

## Errors and troubleshooting

| Error | Resolution |
| --- | --- |
| `Row N: ...` | Correct that source record and retry the complete batch. No earlier row was committed. |
| Changed records require a newer timestamp | Export the source's corrected snapshot with its actual update time. Do not invent a newer date just to force an overwrite. |
| Schema version 0/unknown unsupported | Follow [SCHEMA.md](SCHEMA.md); use a fresh dedicated DB or an explicit reviewed conversion. |
| Schema shape mismatch | Wrong/altered database; do not force the version to match. |
| `database is locked` | Finish the other writer's transaction, then retry. No built-in retry loop. |
| Report time precedes stored data | Use an as-of at/after import and update times. This store cannot reconstruct historical snapshots. |
| No such function `json_valid` | Use Python linked against SQLite with JSON support. No extensions are downloaded by this utility. |
| DB not found on report/export | Check the path; read-only commands never create an empty database. |

Export preserves normalized source fields, not import timestamps or historical import-summary rows. Importing an export into a new database creates new local import provenance.

## When this contract fits

Use it when each source supplies a stable record ID, a trustworthy update time and a snapshot that maps to the five statuses. For example, two exports containing `editorial_tracker/ART-101` can be reconciled by timestamp without creating a second article. A different ID creates a different record even if its title matches.

It is a poor fit for event streams, exact-decimal financial records, arbitrary nested documents, or sources without reliable IDs/update times. There is no deletion/tombstone field: a record missing from the next file remains in SQLite. Imports replace complete snapshots, so omitted optional fields become null rather than retaining their previous values. Reports load the current records into memory and have no paging. These are limits of the current utility, not hidden configuration options.
