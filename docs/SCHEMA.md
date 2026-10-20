# SQLite schema and version policy

Schema version **1** is stored in `PRAGMA user_version`. The authoritative DDL is [schema.sql](../mission_control/schema.sql), applied transactionally by `initialize()`. SQL JSON functions are required. The `schema` CLI prints the DDL without opening a database.

| Object | Purpose |
| --- | --- |
| `records` | Latest normalized JSON payload per `(source, external_id)`, its content digest and local import time |
| `imports` | Counts/time for every successful batch, including duplicate-only replays |
| `demo_metadata` | Database-purpose marker; historical name retained, also used by the generic importer |
| `record_details` | Read-only SQL view exposing each payload field as a column alongside import time |

The composite primary key prevents duplicate source IDs. JSON validity and nonnegative summary counts have SQL constraints. Field types, status/timestamp relationships, URL syntax, normalization and update precedence are enforced by Python, **not all by SQL constraints**. Direct SQL writers can bypass those rules; use the importer for writes. The view is a projection, not a second copy.

Payload JSON keeps the small snapshot contract in one place and makes canonical hashing straightforward. The view makes ordinary SQL queries convenient. No secondary reporting indexes or full record-history tables are provided. This design is suited to small local batches, with a 10,000-row input cap; it has not been benchmarked at scale.

## Version checks

Initialization accepts an empty unversioned database or an existing version-1 store with the expected columns. Imports/reports refuse other versions. Shape checks catch wrong databases and common drift; they do not prove every constraint/trigger is unmodified. The code never automatically rewrites an existing database or bumps an unknown version.

Future schema changes must increment the version and provide an explicit migration or export/reimport procedure with tests. Back up a database before any separately reviewed conversion. Do not set `PRAGMA user_version` manually to bypass validation.

## Original unversioned demonstration (version 0)

The initial published demo used an unversioned schema. It is intentionally rejected by the reusable importer rather than silently adopted. No in-place migration is supplied.

- For disposable fictional demo data, keep the old checkout/output intact and run this version in a fresh checkout. The launcher creates a fresh baseline. Do not reuse the old `output/owner-review.sqlite3`.
- For imported records, preferably reimport the original JSON/CSV source into a **new** version-1 database.
- If only a version-0 database remains, the following read-only Python extraction preserves normalized payloads. Run only against a database you own whose layout is the original demo schema; inspect the exported JSON before importing it into a new database.

```python
import json
import sqlite3
from pathlib import Path
from contextlib import closing

old = Path("output/old-v0.sqlite3").resolve()
with closing(sqlite3.connect(old.as_uri() + "?mode=ro", uri=True)) as db:
    if db.execute("PRAGMA user_version").fetchone()[0] != 0:
        raise ValueError("Expected the original version-0 database")
    columns = [row[1] for row in db.execute("PRAGMA table_info(records)")]
    if columns != ["source", "external_id", "payload", "digest", "imported_at"]:
        raise ValueError("Not the original records table")
    rows = [json.loads(row[0]) for row in db.execute("SELECT payload FROM records ORDER BY source, external_id")]
with open("export-v0.json", "x", encoding="utf-8") as out:
    json.dump(rows, out, indent=2)
```

Then validate and import `export-v0.json` into a new file with the current CLI. Local import times and successful-import history are not preserved by this procedure. Source observation/update/submission/verification fields remain in the exported payload. Keep the old file as provenance; no deletion or overwrite is required.
