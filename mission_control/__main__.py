"""Local snapshot importer CLI. Commands print JSON; failures exit 2."""
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from .adapters import load_file
from .store import (SCHEMA_VERSION, ValidationError, connect, import_records,
                    initialize, prepare_batch, report, timestamp, utcnow)


def main():
    parser = argparse.ArgumentParser(description="Local JSON/CSV snapshot importer and SQLite reporting")
    parser.add_argument("--db", default="output/records.sqlite3", help="Dedicated importer database path")
    parser.add_argument("--as-of", help="UTC import/report time; defaults to current UTC")
    parser.add_argument("--fictional", action="store_true", help="Mark a newly created database as fictional (for demo serving)")
    parser.add_argument("--freshness-days", type=float, default=7, help="Report freshness threshold, default 7")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize a new versioned schema")
    for name, description in (("import", "Atomically import a local JSON/CSV snapshot"),
                              ("validate", "Validate file only; no database access or writes")):
        command = commands.add_parser(name, help=description)
        command.add_argument("file")
    commands.add_parser("report", help="Read current records and print dated JSON report")
    commands.add_parser("export", help="Export normalized records as a re-importable JSON array")
    commands.add_parser("schema", help="Print schema version and SQL; no database access")
    server = commands.add_parser("serve", help="Read-only loopback UI for fictional databases only")
    server.add_argument("--port", type=int, default=0, help="0 selects a free loopback port")
    args = parser.parse_args()
    try:
        as_of = timestamp(args.as_of) if args.as_of else utcnow()
        if args.command == "schema":
            result = {"schema_version": SCHEMA_VERSION, "sql": Path(__file__).with_name("schema.sql").read_text()}
        elif args.command == "validate":
            rows, duplicates = prepare_batch(load_file(args.file), as_of)
            result = {"valid": True, "unique_records": len(rows), "duplicates_within_file": duplicates,
                      "database_checked": False}
        elif args.command == "serve":
            from .server import serve
            serve(args.db, args.port, as_of)
            return
        elif args.command in ("report", "export"):
            # Read-only URI: a typo must not create an empty database.
            with closing(sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True)) as db:
                db.row_factory = sqlite3.Row
                data = report(db, as_of, args.freshness_days)
                if args.command == "export":
                    from .store import FIELDS
                    result = [{key: row[key] for key in FIELDS} for row in data["records"]]
                else:
                    result = data
        else:
            # Reject malformed input before even creating a new database file.
            rows = load_file(args.file) if args.command == "import" else None
            if args.command == "import":
                prepare_batch(rows, as_of)
            with closing(connect(args.db)) as db:
                initialize(db, fictional=args.fictional)
                result = import_records(db, rows, as_of) if rows is not None else {"initialized": True, "schema_version": SCHEMA_VERSION}
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValidationError, ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(2, f"Importer error: {exc}\n")


if __name__ == "__main__":
    main()
