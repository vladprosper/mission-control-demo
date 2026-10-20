"""Validated snapshot import. No real platform clients or credentials."""
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

STATUSES = ("planned", "drafted", "scheduled", "submitted", "verified")
SOURCES = ("mock_notion", "mock_metricool", "mock_manual")
FIELDS = ("source", "external_id", "title", "workstream", "status", "source_date",
          "source_updated_at", "scheduled_for", "submitted_at", "verified_at",
          "evidence_url", "metric_value", "metric_unit")
REQUIRED = ("source", "external_id", "title", "workstream", "status", "source_updated_at")


class ValidationError(ValueError):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value):
    if not isinstance(value, str):
        raise ValidationError("Timestamp must be an ISO 8601 string with timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("Invalid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError("Timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate(row, as_of):
    if not isinstance(row, dict) or set(row) - set(FIELDS):
        raise ValidationError("Each record must be an object with known fields only")
    result = {key: row.get(key) for key in FIELDS}
    for key in REQUIRED:
        value = result[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 240:
            raise ValidationError(f"{key}: nonempty string, at most 240 characters required")
        result[key] = value.strip()
    if result["source"] not in SOURCES:
        raise ValidationError("Only mock sources are allowed")
    if result["status"] not in STATUSES:
        raise ValidationError("Unknown status")
    for key in ("source_date", "source_updated_at", "scheduled_for", "submitted_at", "verified_at"):
        if result[key] is not None:
            result[key] = iso(timestamp(result[key]))
    updated = timestamp(result["source_updated_at"])
    if updated > as_of:
        raise ValidationError("Source update is after import time")
    for key in ("source_date", "submitted_at", "verified_at"):
        if result[key] and timestamp(result[key]) > updated:
            raise ValidationError(f"{key} cannot follow source_updated_at")
    status = result["status"]
    if status == "scheduled" and not result["scheduled_for"]:
        raise ValidationError("Scheduled records require scheduled_for")
    if status in ("submitted", "verified") and not result["submitted_at"]:
        raise ValidationError("Submitted/verified records require submitted_at")
    if status == "verified" and not (result["verified_at"] and result["evidence_url"]):
        raise ValidationError("Verified records require verified_at and fictional evidence URL")
    if status in ("planned", "drafted", "scheduled") and (result["submitted_at"] or result["verified_at"]):
        raise ValidationError("Pre-submission status cannot carry submission/verification timestamps")
    if status != "verified" and (result["verified_at"] or result["evidence_url"]):
        raise ValidationError("Only verified records carry verification evidence")
    if result["verified_at"] and timestamp(result["verified_at"]) < timestamp(result["submitted_at"]):
        raise ValidationError("Verification cannot precede submission")
    evidence = result["evidence_url"]
    if evidence is not None and (not isinstance(evidence, str) or not evidence.startswith("https://example.invalid/evidence/") or len(evidence) > 500):
        raise ValidationError("Evidence must be a fictional example.invalid URL")
    metric = result["metric_value"]
    if metric is not None and (isinstance(metric, bool) or not isinstance(metric, (int, float)) or not math.isfinite(metric) or metric < 0):
        raise ValidationError("metric_value must be a finite nonnegative number or null")
    unit = result["metric_unit"]
    if unit is not None and (not isinstance(unit, str) or unit not in ("views", "items", "hours")):
        raise ValidationError("metric_unit must be views, items, hours, or null")
    if (metric is None) != (unit is None):
        raise ValidationError("Metric and unit must both be present or both null")
    if metric is not None:
        result["metric_value"] = float(metric)  # JSON 3 and CSV 3.0 deduplicate identically.
    return result


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=5000")
    return db


def initialize(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS demo_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    INSERT OR IGNORE INTO demo_metadata VALUES ('dataset', 'FICTIONAL DEMO ONLY');
    CREATE TABLE IF NOT EXISTS records (
        source TEXT NOT NULL, external_id TEXT NOT NULL, payload TEXT NOT NULL,
        digest TEXT NOT NULL, imported_at TEXT NOT NULL,
        PRIMARY KEY (source, external_id));
    CREATE TABLE IF NOT EXISTS imports (
        id INTEGER PRIMARY KEY, imported_at TEXT NOT NULL,
        inserted INTEGER NOT NULL, updated INTEGER NOT NULL, duplicates INTEGER NOT NULL);
    """)


def digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def import_records(db, rows, as_of=None, events=None):
    as_of = as_of or utcnow()
    def event(stage, outcome, message):
        if events is not None:
            events.append({"stage": stage, "outcome": outcome, "message": message})
    if not isinstance(rows, list) or not rows or len(rows) > 10000:
        raise ValidationError("Batch must be a nonempty list of at most 10000 records")
    if as_of.tzinfo is None:
        raise ValidationError("Import time must include timezone")
    # Validate every row before opening a write transaction.
    validated = []
    for index, row in enumerate(rows, 1):
        try:
            validated.append(validate(row, as_of))
        except ValidationError as exc:
            event("validation", "rejected", f"Row {index}: {exc}; no transaction opened")
            raise
    event("validation", "passed", f"All {len(validated)} rows passed schema, timing and evidence checks")
    counts = {"inserted": 0, "updated": 0, "duplicates": 0}
    unique = {}
    for row in validated:
        key = (row["source"], row["external_id"])
        if key in unique:
            if digest(row) != digest(unique[key]):
                event("identity", "rejected", "Conflicting snapshots share one source/ID in this batch")
                raise ValidationError("Conflicting duplicate key within batch")
            counts["duplicates"] += 1
        else:
            unique[key] = row
    try:
        db.execute("BEGIN IMMEDIATE")
        event("transaction", "started", "BEGIN IMMEDIATE; record changes and import summary share one transaction")
        for key, row in unique.items():
            old = db.execute("SELECT payload, digest FROM records WHERE source=? AND external_id=?", key).fetchone()
            new_digest = digest(row)
            if old and old["digest"] == new_digest:
                counts["duplicates"] += 1
                event("identity", "skipped", f"{key[0]}/{key[1]}: identical normalized content")
                continue
            if old:
                previous = json.loads(old["payload"])
                if timestamp(row["source_updated_at"]) <= timestamp(previous["source_updated_at"]):
                    event("identity", "rejected", f"{key[0]}/{key[1]}: changed content has no newer source timestamp")
                    raise ValidationError("Changed records require a strictly newer source_updated_at")
            db.execute("INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?, ?)",
                       (*key, json.dumps(row, sort_keys=True, allow_nan=False), new_digest, iso(as_of)))
            counts["updated" if old else "inserted"] += 1
            event("storage", "updated" if old else "inserted", f"{key[0]}/{key[1]} staged inside transaction")
        db.execute("INSERT INTO imports (imported_at, inserted, updated, duplicates) VALUES (?, ?, ?, ?)",
                   (iso(as_of), counts["inserted"], counts["updated"], counts["duplicates"]))
        db.commit()
        event("transaction", "committed", f"Committed {counts['inserted']} inserts, {counts['updated']} updates, {counts['duplicates']} duplicate skips")
    except Exception:
        db.rollback()
        event("transaction", "rolled_back", "ROLLBACK; all staged record changes and the import summary discarded")
        raise
    return counts


def report(db, as_of=None):
    as_of = as_of or utcnow()
    records = []
    for stored in db.execute("SELECT payload, imported_at FROM records ORDER BY source, external_id"):
        row = json.loads(stored["payload"])
        # No time travel: older reports need retained snapshots, which this demo does not store.
        if timestamp(row["source_updated_at"]) > as_of or timestamp(stored["imported_at"]) > as_of:
            raise ValidationError("Report time precedes stored data; historical snapshots are not retained")
        age = (as_of - timestamp(row["source_date"])).total_seconds() / 86400 if row["source_date"] else None
        row.update(imported_at=stored["imported_at"], age_days=round(age, 1) if age is not None else None,
                   freshness="unknown" if age is None else "stale" if age > 7 else "fresh")
        records.append(row)
    return {"fictional": True, "as_of": iso(as_of), "freshness_threshold_days": 7,
            "records": records, "statuses": {s: sum(r["status"] == s for r in records) for s in STATUSES},
            "quality": {"stale": sum(r["freshness"] == "stale" for r in records),
                        "unknown_source_dates": sum(r["source_date"] is None for r in records),
                        "missing_metrics": sum(r["metric_value"] is None for r in records)},
            "imports": [dict(r) for r in db.execute("SELECT * FROM imports ORDER BY id DESC LIMIT 5")]}
