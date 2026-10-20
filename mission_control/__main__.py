import argparse
import json
import sys
import sqlite3
from contextlib import closing
from .adapters import load_mock_file
from .store import ValidationError, connect, import_records, initialize, report, timestamp


def main():
    parser = argparse.ArgumentParser(description="Fictional Mission Control demo; file-only mock adapters")
    parser.add_argument("--db", default="output/demo.sqlite3", help="New synthetic demo database path")
    parser.add_argument("--as-of", help="Fixed UTC reporting/import timestamp; defaults to current UTC")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create empty fictional demo schema")
    importer = commands.add_parser("import", help="Atomically import a synthetic JSON/CSV file")
    importer.add_argument("file")
    commands.add_parser("report", help="Print JSON report")
    server = commands.add_parser("serve", help="Read-only loopback dashboard")
    server.add_argument("--port", type=int, default=0, help="0 selects a free loopback port")
    args = parser.parse_args()
    try:
        as_of = timestamp(args.as_of) if args.as_of else None
        if args.command == "serve":
            from .server import serve
            serve(args.db, args.port, as_of)
            return
        with closing(connect(args.db)) as db:
            initialize(db)
            if args.command == "import":
                result = import_records(db, load_mock_file(args.file), as_of)
            elif args.command == "report":
                result = report(db, as_of)
            else:
                result = {"initialized": True, "fictional": True}
            print(json.dumps(result, indent=2, allow_nan=False))
    except (ValidationError, ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(2, f"Demo error: {exc}\n")


if __name__ == "__main__":
    main()
