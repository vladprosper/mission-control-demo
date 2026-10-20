"""Validated snapshot import. No real platform clients or credentials."""
import hashlib
import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

STATUSES = ("planned", "drafted", "scheduled", "submitted", "verified")
SCHEMA_VERSION = 1
SOURCE_PATTERN = re.compile(r"[a-z][a-z0-9_.-]{0,63}")
UNIT_PATTERN = re.compile(r"[a-z][a-z0-9_/-]{0,31}")
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
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValidationError("Timestamp is outside the supported UTC range") from exc


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
    if not SOURCE_PATTERN.fullmatch(result["source"]):
        raise ValidationError("source: lowercase slug, 1–64 characters (letters, digits, _, ., -)")
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
        raise ValidationError("Verified records require verified_at and evidence URL")
    if status in ("planned", "drafted", "scheduled") and (result["submitted_at"] or result["verified_at"]):
        raise ValidationError("Pre-submission status cannot carry submission/verification timestamps")
    if status != "verified" and (result["verified_at"] or result["evidence_url"]):
        raise ValidationError("Only verified records carry verification evidence")
    if result["verified_at"] and timestamp(result["verified_at"]) < timestamp(result["submitted_at"]):
        raise ValidationError("Verification cannot precede submission")
    evidence = result["evidence_url"]
    if evidence is not None:
        if not isinstance(evidence, str) or len(evidence) > 2048 or any(c.isspace() or ord(c) < 32 for c in evidence):
            raise ValidationError("evidence_url: HTTPS URL of at most 2048 characters required")
        try:
            parsed = urlsplit(evidence)
            valid_url = parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
            _ = parsed.port
        except ValueError:
            valid_url = False
        if not valid_url:
            raise ValidationError("evidence_url: absolute HTTPS URL without embedded credentials required")
    metric = result["metric_value"]
    if metric is not None:
        try:
            valid_metric = not isinstance(metric, bool) and isinstance(metric, (int, float)) and math.isfinite(metric) and metric >= 0
        except OverflowError:
            valid_metric = False
        if not valid_metric:
            raise ValidationError("metric_value must be a finite nonnegative number or null")
    unit = result["metric_unit"]
    if unit is not None and (not isinstance(unit, str) or not UNIT_PATTERN.fullmatch(unit)):
        raise ValidationError("metric_unit: lowercase unit slug, 1–32 characters, or null")
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


def check_schema(db):
    """Fail closed on unknown versions; imports never migrate a database implicitly."""
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version != SCHEMA_VERSION:
        raise ValidationError(f"Schema version {version} unsupported; expected {SCHEMA_VERSION}. See docs/SCHEMA.md")
    expected = {
        "demo_metadata": ["key", "value"],
        "records": ["source", "external_id", "payload", "digest", "imported_at"],
        "imports": ["id", "imported_at", "inserted", "updated", "duplicates"],
        "record_details": ["source", "external_id", "title", "workstream", "status", "source_date",
                           "source_updated_at", "scheduled_for", "submitted_at", "verified_at",
                           "evidence_url", "metric_value", "metric_unit", "imported_at"],
    }
    for table, columns in expected.items():
        if [r[1] for r in db.execute(f"PRAGMA table_info({table})")] != columns:
            raise ValidationError(f"Schema shape mismatch: {table}; refusing to use this database")


def initialize(db, fictional=False):
    """Initialize an empty database only, or accept our current schema unchanged.

    Existing unversioned databases are rejected, not relabeled or overwritten.
    The fictional marker is set at creation and never inferred from filenames.
    """
    if db.in_transaction:
        raise ValidationError("Initialization requires a connection with no active transaction")
    objects = db.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    if objects:
        check_schema(db)
        return
    if db.execute("PRAGMA user_version").fetchone()[0] != 0:
        raise ValidationError("Refusing to initialize an empty database with an existing schema version")
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    try:
        db.executescript("BEGIN IMMEDIATE;\n" + schema)
        db.execute("INSERT INTO demo_metadata VALUES ('dataset', ?)",
                   ("FICTIONAL DEMO ONLY" if fictional else "USER-SUPPLIED RECORDS",))
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        db.commit()
    except Exception:
        db.rollback()
        raise


def prepare_batch(rows, as_of=None):
    """Validate/normalize without a database. Return unique rows and duplicate count.

    This does not check update precedence against records already in a database.
    """
    as_of = as_of or utcnow()
    if not isinstance(rows, list) or not rows or len(rows) > 10000:
        raise ValidationError("Batch must be a nonempty list of at most 10000 records")
    if as_of.tzinfo is None:
        raise ValidationError("Import time must include timezone")
    unique, duplicates = {}, 0
    for index, row in enumerate(rows, 1):
        try:
            normalized = validate(row, as_of)
            key = (normalized["source"], normalized["external_id"])
            if key in unique:
                if digest(normalized) != digest(unique[key]):
                    raise ValidationError("Conflicting duplicate key within batch")
                duplicates += 1
            else:
                unique[key] = normalized
        except ValidationError as exc:
            raise ValidationError(f"Row {index}: {exc}") from exc
    return list(unique.values()), duplicates


def digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def import_records(db, rows, as_of=None, events=None):
    as_of = as_of or utcnow()
    def event(stage, outcome, message):
        if events is not None:
            events.append({"stage": stage, "outcome": outcome, "message": message})
    check_schema(db)
    if db.in_transaction:
        raise ValidationError("Import requires a connection with no active transaction")
    try:
        validated, duplicates = prepare_batch(rows, as_of)
    except ValidationError as exc:
        event("validation", "rejected", f"{exc}; no transaction opened")
        raise
    event("validation", "passed", f"All {len(rows)} rows passed schema, timing and evidence checks")
    counts = {"inserted": 0, "updated": 0, "duplicates": duplicates}
    unique = {(row["source"], row["external_id"]): row for row in validated}
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


def report(db, as_of=None, freshness_days=7):
    check_schema(db)
    if isinstance(freshness_days, bool) or not isinstance(freshness_days, (int, float)) or not math.isfinite(freshness_days) or freshness_days < 0:
        raise ValidationError("freshness_days must be a finite nonnegative number")
    as_of = as_of or utcnow()
    if as_of.tzinfo is None:
        raise ValidationError("Report time must include timezone")
    records = []
    for stored in db.execute("SELECT payload, imported_at FROM records ORDER BY source, external_id"):
        row = json.loads(stored["payload"])
        # No time travel: older reports need retained snapshots, which this demo does not store.
        if timestamp(row["source_updated_at"]) > as_of or timestamp(stored["imported_at"]) > as_of:
            raise ValidationError("Report time precedes stored data; historical snapshots are not retained")
        age = (as_of - timestamp(row["source_date"])).total_seconds() / 86400 if row["source_date"] else None
        row.update(imported_at=stored["imported_at"], age_days=round(age, 1) if age is not None else None,
                   freshness="unknown" if age is None else "stale" if age > freshness_days else "fresh")
        records.append(row)
    marker = db.execute("SELECT value FROM demo_metadata WHERE key='dataset'").fetchone()
    return {"fictional": bool(marker and marker[0] == "FICTIONAL DEMO ONLY"), "schema_version": SCHEMA_VERSION, "as_of": iso(as_of), "freshness_threshold_days": freshness_days,
            "records": records, "statuses": {s: sum(r["status"] == s for r in records) for s in STATUSES},
            "quality": {"stale": sum(r["freshness"] == "stale" for r in records),
                        "unknown_source_dates": sum(r["source_date"] is None for r in records),
                        "missing_metrics": sum(r["metric_value"] is None for r in records)},
            "imports": [dict(r) for r in db.execute("SELECT * FROM imports ORDER BY id DESC LIMIT 5")]}
