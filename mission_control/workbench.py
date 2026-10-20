"""Real importer experiments on a disposable in-memory SQLite sandbox."""
import hashlib
import json
import sqlite3
import threading
import uuid
from pathlib import Path
from .adapters import load_mock_file
from .store import FIELDS, ValidationError, import_records, report, timestamp

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
SCENARIOS = [
    {"id": "replay", "title": "Replay a collection packet", "description": "Import the same 12 observations. Identical content is skipped without making its source dates newer."},
    {"id": "draft", "title": "Accept a newer draft", "description": "A newer source snapshot moves N-01 from planned to drafted. Preview the field-level change before applying."},
    {"id": "invalid", "title": "Reject an invalid packet", "description": "The second row has an unsupported status. Whole-batch validation prevents the first row from being written."},
    {"id": "rollback", "title": "Roll back a partial write", "description": "A new row is staged, then a conflicting old snapshot is encountered. The importer rolls the entire transaction back."},
    {"id": "verify", "title": "Record fictional verification", "description": "A submitted record gains a verification timestamp and a fictional evidence reference. Its old observation date stays stale."},
    {"id": "refresh", "title": "Refresh an observed zero", "description": "A newly collected source observation clears one stale date while keeping the measured zero. Refreshing the page alone cannot do this."},
]


def scenario_rows(key):
    if key not in {s["id"] for s in SCENARIOS}:
        raise ValidationError("Unknown scenario")
    if key == "replay":
        return load_mock_file(EXAMPLES / "synthetic.csv")
    if key in ("draft", "invalid"):
        return load_mock_file(EXAMPLES / ("newer-update.json" if key == "draft" else "invalid-batch.json"))
    rows = load_mock_file(EXAMPLES / "synthetic.json")
    if key == "rollback":
        return [dict(rows[0], external_id="TRY-01", title="Fictional row that must not survive"),
                dict(rows[1], title="Conflicting older snapshot", source_updated_at="2026-10-19T09:30:00Z")]
    if key == "verify":
        return [dict(rows[3], status="verified", verified_at="2026-10-19T11:15:00Z",
                     source_updated_at="2026-10-19T11:30:00Z", evidence_url="https://example.invalid/evidence/N-04")]
    return [dict(rows[7], source_date="2026-10-19T11:30:00Z", source_updated_at="2026-10-19T11:45:00Z")]


def memory_copy(source):
    target = sqlite3.connect(":memory:", check_same_thread=False)
    target.row_factory = sqlite3.Row
    source.backup(target)
    return target


def fingerprint(db):
    # Includes record provenance and successful import audit summaries.
    snapshot = {table: [list(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY 1,2")]
                for table in ("records", "imports")}
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def changes(before, after):
    old = {(r["source"], r["external_id"]): r for r in before["records"]}
    result = []
    for row in after["records"]:
        previous = old.get((row["source"], row["external_id"]), {})
        for field in FIELDS:
            if previous.get(field) != row.get(field):
                result.append({"record": f"{row['source']}/{row['external_id']}", "field": field,
                               "before": previous.get(field), "after": row.get(field)})
    return result


class Workbench:
    def __init__(self, baseline, as_of):
        self.lock = threading.RLock()
        self.as_of = as_of or timestamp("2026-10-19T12:00:00Z")
        self.baseline = memory_copy(baseline)
        self.db = memory_copy(self.baseline)
        self.revision = 0
        self.previews = {}
        self.history = []

    def state(self):
        with self.lock:
            return {"fictional": True, "revision": self.revision, "report": report(self.db, self.as_of),
                    "scenarios": [dict(s, rows=scenario_rows(s["id"])) for s in SCENARIOS],
                    "history": self.history[-20:][::-1], "sandbox": "Disposable in-memory SQLite; source database unchanged"}

    def execute(self, db, key):
        rows = scenario_rows(key)
        events = [{"stage": "adapter", "outcome": "loaded", "message": f"Loaded {len(rows)} fictional rows through the file-only mock adapter"}]
        before = report(db, self.as_of)
        before_hash = fingerprint(db)
        try:
            counts = import_records(db, rows, self.as_of, events=events)
            accepted, error = True, None
        except ValidationError as exc:
            counts, accepted, error = None, False, str(exc)
        after = report(db, self.as_of)
        after_hash = fingerprint(db)
        events.append({"stage": "report", "outcome": "projected", "message": f"Projected {len(after['records'])} records; failed imports retain the original state"})
        return {"scenario": key, "accepted": accepted, "error": error, "counts": counts,
                "events": events, "changes": changes(before, after), "before_hash": before_hash,
                "after_hash": after_hash, "unchanged": before_hash == after_hash, "report": after}

    def preview(self, key):
        with self.lock:
            trial = memory_copy(self.db)
            try:
                result = self.execute(trial, key)
            finally:
                trial.close()
            token = uuid.uuid4().hex
            self.previews = {token: (self.revision, key, result["accepted"])}
            result.update(mode="preview", revision=self.revision, preview_token=token)
            self.record(result)
            return result

    def apply(self, key, token):
        with self.lock:
            preview = self.previews.pop(token, None)
            if preview != (self.revision, key, True):
                raise ValidationError("Preview is missing, rejected, already used, or stale. Preview again before applying.")
            result = self.execute(self.db, key)
            if result["accepted"]:
                self.revision += 1
            result.update(mode="apply", revision=self.revision)
            self.record(result)
            return result

    def record(self, result):
        self.history.append({"sequence": len(self.history) + 1, "mode": result["mode"],
                             "scenario": result["scenario"], "accepted": result["accepted"],
                             "counts": result["counts"], "error": result["error"], "revision": self.revision})
        self.history = self.history[-100:]

    def reset(self):
        with self.lock:
            self.db.close()
            self.db = memory_copy(self.baseline)
            self.revision += 1
            self.previews.clear()
            self.history.clear()
            return self.state()

    def close(self):
        with self.lock:
            self.db.close()
            self.baseline.close()
