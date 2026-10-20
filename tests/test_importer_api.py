"""End-to-end public API and CLI contracts, using only invented records."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from mission_control import (ValidationError, connect, initialize, import_records,
                             load_file, prepare_batch, report, timestamp)
from mission_control.server import make_server

ROOT = Path(__file__).resolve().parents[1]
AS_OF = timestamp("2026-10-19T12:00:00Z")


class ImporterAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "records.sqlite3"
        self.db = connect(self.path)
        initialize(self.db)
        self.rows = load_file(ROOT / "examples/importer/records.json")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_non_mock_sources_units_and_https_evidence(self):
        self.assertEqual(import_records(self.db, self.rows, AS_OF)["inserted"], 2)
        data = report(self.db, AS_OF)
        self.assertFalse(data["fictional"])
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["records"][1]["metric_unit"], "clicks")
        self.assertEqual(data["records"][1]["evidence_url"], "https://example.org/evidence/issue-42")

    def test_schema_view_is_directly_queryable(self):
        import_records(self.db, self.rows, AS_OF)
        rows = self.db.execute("SELECT source,status,metric_value,metric_unit FROM record_details ORDER BY source").fetchall()
        self.assertIsNone(rows[0]["metric_value"])
        self.assertEqual((rows[1]["metric_value"], rows[1]["metric_unit"]), (0, "clicks"))
        self.assertEqual(self.db.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_custom_freshness_threshold(self):
        import_records(self.db, self.rows, AS_OF)
        self.assertEqual(report(self.db, AS_OF)["quality"]["stale"], 1)
        self.assertEqual(report(self.db, AS_OF, freshness_days=14)["quality"]["stale"], 0)
        for bad in (-1, True, float('nan'), float('inf')):
            with self.assertRaises(ValidationError):
                report(self.db, AS_OF, bad)
        with self.assertRaises(ValidationError):
            report(self.db, datetime(2026, 10, 19))

    def test_file_validation_has_no_database_side_effect(self):
        before = self.db.total_changes
        rows, dupes = prepare_batch(self.rows + [self.rows[0]], AS_OF)
        self.assertEqual((len(rows), dupes), (2, 1))
        self.assertEqual(self.db.total_changes, before)
        with self.assertRaisesRegex(ValidationError, "Row 2"):
            prepare_batch(load_file(ROOT / "examples/importer/invalid.json"), AS_OF)
        with self.assertRaisesRegex(ValidationError, "Conflicting duplicate"):
            prepare_batch([self.rows[0], dict(self.rows[0], title="Changed")], AS_OF)

    def test_reject_unsafe_or_malformed_evidence_urls(self):
        for url in ('http://example.org/a', 'file:///tmp/evidence', 'https://user:secret@example.org/a',
                    'https:///missing-host', 'https://example.org/a b', 'https://[broken'):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                prepare_batch([dict(self.rows[1], evidence_url=url)], AS_OF)

    def test_nested_import_does_not_commit_callers_work(self):
        self.db.execute("INSERT INTO demo_metadata VALUES ('pending','owned by caller')")
        with self.assertRaisesRegex(ValidationError, "active transaction"):
            import_records(self.db, self.rows, AS_OF)
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.assertIsNone(self.db.execute("SELECT value FROM demo_metadata WHERE key='pending'").fetchone())

    def test_unknown_schema_refused_without_mutation(self):
        self.db.execute("PRAGMA user_version=99")
        before = self.path.read_bytes()
        for action in (lambda: initialize(self.db), lambda: import_records(self.db, self.rows, AS_OF), lambda: report(self.db, AS_OF)):
            with self.assertRaises(ValidationError):
                action()
        self.assertEqual(self.path.read_bytes(), before)

    def test_unversioned_existing_database_is_not_adopted(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE customer_data(value TEXT)")
            with self.assertRaisesRegex(ValidationError, "Schema version 0"):
                initialize(db)
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [('customer_data',)])

    def test_wrong_shape_version_one_refused(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE records(value TEXT)")
            db.execute("PRAGMA user_version=1")
            with self.assertRaisesRegex(ValidationError, "shape mismatch"):
                initialize(db)

    def test_reinitialize_does_not_relabel_user_database_as_fictional(self):
        initialize(self.db, fictional=True)
        self.assertFalse(report(self.db, AS_OF)["fictional"])
        with self.assertRaisesRegex(ValidationError, "fictional databases only"):
            make_server(self.path)

    def test_json_csv_round_trip_keeps_source_dates_and_zero(self):
        import_records(self.db, self.rows, AS_OF)
        before = list(map(tuple, self.db.execute("SELECT * FROM records ORDER BY source")))
        result = import_records(self.db, load_file(ROOT / "examples/importer/records.csv"), AS_OF)
        self.assertEqual(result, {"inserted": 0, "updated": 0, "duplicates": 2})
        self.assertEqual(before, list(map(tuple, self.db.execute("SELECT * FROM records ORDER BY source"))))


class ImporterCLITests(unittest.TestCase):
    def test_documented_clean_workflow_and_export_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "fresh.sqlite3"
            def run(*args, target=db, ok=True):
                result = subprocess.run([sys.executable, '-m', 'mission_control', '--db', str(target),
                                         '--as-of', '2026-10-19T12:00:00Z', *args], cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0 if ok else 2, result.stderr)
                return json.loads(result.stdout) if ok else result
            validation = run('validate', 'examples/importer/records.json')
            self.assertFalse(validation['database_checked'])
            self.assertFalse(db.exists())
            self.assertEqual(run('schema')['schema_version'], 1)
            self.assertFalse(db.exists())
            run('report', ok=False)
            self.assertFalse(db.exists())
            error = run('import', 'examples/importer/invalid.json', ok=False)
            self.assertIn('Row 2', error.stderr)
            self.assertFalse(db.exists())
            self.assertEqual(run('import', 'examples/importer/records.json')['inserted'], 2)
            self.assertEqual(run('import', 'examples/importer/records.csv')['duplicates'], 2)
            before = db.read_bytes()
            run('import', 'examples/importer/invalid.json', ok=False)
            self.assertEqual(db.read_bytes(), before)
            self.assertEqual(run('import', 'examples/importer/newer.json')['updated'], 1)
            self.assertEqual(run('report')['statuses']['scheduled'], 1)
            exported = run('export')
            path = Path(tmp) / 'export.json'
            path.write_text(json.dumps(exported))
            other = Path(tmp) / 'other.sqlite3'
            self.assertEqual(run('import', str(path), target=other)['inserted'], 2)
            self.assertEqual(run('export', target=other), exported)
