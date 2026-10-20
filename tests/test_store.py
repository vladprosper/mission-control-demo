import copy
import json
import tempfile
import sqlite3
import unittest
from datetime import timedelta
from pathlib import Path
from mission_control.adapters import load_mock_file
from mission_control.store import (ValidationError, connect, import_records, initialize,
                                   report, timestamp, validate)

ROOT = Path(__file__).resolve().parents[1]
AS_OF = timestamp("2026-10-19T12:00:00Z")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.tmp.name) / "test.sqlite3")
        initialize(self.db)
        self.rows = load_mock_file(ROOT / "examples/synthetic.json")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def state(self):
        return (list(map(tuple, self.db.execute("SELECT * FROM records ORDER BY source,external_id"))),
                list(map(tuple, self.db.execute("SELECT * FROM imports ORDER BY id"))))

    def test_fixture_import_counts(self):
        self.assertEqual(import_records(self.db, self.rows, AS_OF), dict(inserted=12, updated=0, duplicates=0))
        data = report(self.db, AS_OF)
        self.assertEqual(data["statuses"], dict(planned=2, drafted=3, scheduled=2, submitted=2, verified=3))
        self.assertEqual(data["quality"], dict(stale=3, unknown_source_dates=2, missing_metrics=6))

    def test_reimport_idempotent_records(self):
        import_records(self.db, self.rows, AS_OF)
        records_before = self.state()[0]
        self.assertEqual(import_records(self.db, self.rows, AS_OF), dict(inserted=0, updated=0, duplicates=12))
        self.assertEqual(self.state()[0], records_before)

    def test_csv_json_equivalence(self):
        import_records(self.db, self.rows, AS_OF)
        result = import_records(self.db, load_mock_file(ROOT / "examples/synthetic.csv"), AS_OF)
        self.assertEqual(result["duplicates"], 12)

    def test_exact_duplicates_within_batch(self):
        self.assertEqual(import_records(self.db, [self.rows[0]] * 3, AS_OF), dict(inserted=1, updated=0, duplicates=2))

    def test_conflicting_duplicates_reject_entire_batch(self):
        before = self.state()
        with self.assertRaises(ValidationError):
            import_records(self.db, [self.rows[0], dict(self.rows[0], title="Conflict")], AS_OF)
        self.assertEqual(self.state(), before)

    def test_invalid_second_row_atomic(self):
        import_records(self.db, self.rows, AS_OF)
        before = self.state()
        with self.assertRaises(ValidationError):
            import_records(self.db, load_mock_file(ROOT / "examples/invalid-batch.json"), AS_OF)
        self.assertEqual(self.state(), before)

    def test_stale_update_rolls_back_prior_insert(self):
        import_records(self.db, self.rows, AS_OF)
        before = self.state()
        changed = dict(self.rows[0], title="Conflict", source_updated_at="2026-10-18T11:00:00Z")
        with self.assertRaises(ValidationError):
            import_records(self.db, [dict(self.rows[1], external_id="NEW"), changed], AS_OF)
        self.assertEqual(self.state(), before)

    def test_database_failure_rolls_back_prior_insert(self):
        self.db.execute("CREATE TRIGGER fail_import BEFORE INSERT ON records WHEN NEW.external_id='FAIL' BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
        before = self.state()
        with self.assertRaises(sqlite3.IntegrityError):
            import_records(self.db, [self.rows[0], dict(self.rows[1], external_id="FAIL")], AS_OF)
        self.assertEqual(self.state(), before)

    def test_equal_timestamp_change_rejected(self):
        import_records(self.db, self.rows, AS_OF)
        with self.assertRaises(ValidationError):
            import_records(self.db, [dict(self.rows[0], title="Changed")], AS_OF)

    def test_newer_update(self):
        import_records(self.db, self.rows, AS_OF)
        result = import_records(self.db, load_mock_file(ROOT / "examples/newer-update.json"), AS_OF)
        self.assertEqual(result, dict(inserted=0, updated=1, duplicates=0))
        self.assertEqual(report(self.db, AS_OF)["statuses"]["drafted"], 4)

    def test_source_scoped_identity(self):
        rows = [self.rows[0], dict(self.rows[0], source="mock_manual")]
        self.assertEqual(import_records(self.db, rows, AS_OF)["inserted"], 2)

    def test_missing_is_not_zero(self):
        import_records(self.db, self.rows, AS_OF)
        records = report(self.db, AS_OF)["records"]
        self.assertEqual(sum(r["metric_value"] == 0 for r in records), 1)
        self.assertEqual(sum(r["metric_value"] is None for r in records), 6)

    def test_freshness_boundary(self):
        row = dict(self.rows[0], source_date="2026-10-12T12:00:00Z")
        import_records(self.db, [row], AS_OF)
        self.assertEqual(report(self.db, AS_OF)["records"][0]["freshness"], "fresh")
        self.assertEqual(report(self.db, AS_OF + timedelta(seconds=1))["records"][0]["freshness"], "stale")

    def test_unknown_date_stays_unknown_after_import(self):
        import_records(self.db, [dict(self.rows[0], source_date=None)], AS_OF)
        self.assertEqual(report(self.db, AS_OF)["records"][0]["freshness"], "unknown")

    def test_timestamp_normalization(self):
        row = dict(self.rows[0], source_updated_at="2026-10-19T12:00:00+02:00")
        self.assertEqual(validate(row, AS_OF)["source_updated_at"], "2026-10-19T10:00:00Z")

    def test_reject_invalid_fields_and_dates(self):
        for changes in ({"source": "notion"}, {"status": "published"}, {"surprise": 1},
                        {"title": " "}, {"source_date": "yesterday"},
                        {"source_updated_at": "2026-10-19T10:00:00"},
                        {"source_updated_at": "2026-10-20T10:00:00Z"},
                        {"source_date": "2026-10-19T11:00:00Z"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                validate(dict(self.rows[0], **changes), AS_OF)

    def test_reject_invalid_metrics(self):
        for metric in (-1, float("nan"), float("inf"), True, "12"):
            with self.subTest(metric=metric), self.assertRaises(ValidationError):
                validate(dict(self.rows[0], metric_value=metric, metric_unit="views"), AS_OF)
        for changes in ({"metric_unit": "views"}, {"metric_value": 1}, {"metric_unit": "dollars", "metric_value": 1}):
            with self.assertRaises(ValidationError):
                validate(dict(self.rows[0], **changes), AS_OF)

    def test_status_evidence_requirements(self):
        cases = [dict(self.rows[2], scheduled_for=None), dict(self.rows[3], submitted_at=None),
                 dict(self.rows[4], evidence_url=None), dict(self.rows[4], verified_at=None),
                 dict(self.rows[4], evidence_url="https://real.example/evidence"),
                 dict(self.rows[4], verified_at="2026-10-19T07:00:00Z"),
                 dict(self.rows[0], submitted_at="2026-10-19T08:00:00Z"),
                 dict(self.rows[3], verified_at="2026-10-19T09:00:00Z")]
        for row in cases:
            with self.subTest(row=row), self.assertRaises(ValidationError):
                validate(row, AS_OF)

    def test_sql_looking_text_is_literal(self):
        title = "'); DROP TABLE records; -- <script>fictional</script>"
        import_records(self.db, [dict(self.rows[0], title=title)], AS_OF)
        self.assertEqual(report(self.db, AS_OF)["records"][0]["title"], title)

    def test_empty_report(self):
        self.assertEqual(report(self.db, AS_OF)["records"], [])

    def test_reject_empty_or_wrong_batches(self):
        for batch in ([], {}, [None], ["bad"], [self.rows[0]] * 10001):
            with self.assertRaises(ValidationError):
                import_records(self.db, batch, AS_OF)

    def test_historical_time_not_misrepresented(self):
        import_records(self.db, self.rows, AS_OF)
        with self.assertRaises(ValidationError):
            report(self.db, AS_OF - timedelta(hours=1))

    def test_csv_malformed_and_nonfinite(self):
        path = Path(self.tmp.name) / "bad.csv"
        for content in ("title,title\na,b\n", "title,status\na\n", "title\na,b\n", "metric_value\nnope\n"):
            path.write_text(content)
            with self.assertRaises(ValidationError):
                load_mock_file(path)


if __name__ == "__main__":
    unittest.main()
