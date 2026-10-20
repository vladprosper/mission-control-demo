-- Snapshot importer schema v1. Applied transactionally by initialize().
-- Payload rules and cross-record timestamp precedence are enforced in Python.
CREATE TABLE demo_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE records (
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    payload TEXT NOT NULL CHECK (json_valid(payload)),
    digest TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source, external_id)
);
CREATE TABLE imports (
    id INTEGER PRIMARY KEY,
    imported_at TEXT NOT NULL,
    inserted INTEGER NOT NULL CHECK (inserted >= 0),
    updated INTEGER NOT NULL CHECK (updated >= 0),
    duplicates INTEGER NOT NULL CHECK (duplicates >= 0)
);
-- Queryable columns without coupling consumers to the JSON envelope.
CREATE VIEW record_details AS
SELECT source, external_id,
       json_extract(payload, '$.title') AS title,
       json_extract(payload, '$.workstream') AS workstream,
       json_extract(payload, '$.status') AS status,
       json_extract(payload, '$.source_date') AS source_date,
       json_extract(payload, '$.source_updated_at') AS source_updated_at,
       json_extract(payload, '$.scheduled_for') AS scheduled_for,
       json_extract(payload, '$.submitted_at') AS submitted_at,
       json_extract(payload, '$.verified_at') AS verified_at,
       json_extract(payload, '$.evidence_url') AS evidence_url,
       json_extract(payload, '$.metric_value') AS metric_value,
       json_extract(payload, '$.metric_unit') AS metric_unit,
       imported_at
FROM records;
