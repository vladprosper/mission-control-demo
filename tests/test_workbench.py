import sqlite3
import unittest
from mission_control.store import ValidationError, import_records, initialize, timestamp
from mission_control.workbench import Workbench, fingerprint, scenario_rows
from mission_control.portfolio import RELEASE_CANDIDATES, evaluate_release, portfolio, reconcile_destination


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.row_factory=sqlite3.Row
        initialize(self.db)
        import_records(self.db,scenario_rows("replay"),timestamp("2026-10-19T12:00:00Z"))
        self.lab=Workbench(self.db,timestamp("2026-10-19T12:00:00Z"))

    def tearDown(self):
        self.lab.close()
        self.db.close()

    def test_preview_changes_trial_only(self):
        before=fingerprint(self.lab.db)
        result=self.lab.preview("draft")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["counts"]["updated"],1)
        self.assertEqual(fingerprint(self.lab.db),before)
        self.assertTrue(any(c["field"]=="status" and c["after"]=="drafted" for c in result["changes"]))

    def test_apply_requires_preview_and_cannot_replay_token(self):
        with self.assertRaises(ValidationError): self.lab.apply("draft","invented")
        preview=self.lab.preview("draft")
        result=self.lab.apply("draft",preview["preview_token"])
        self.assertEqual(result["counts"]["updated"],1)
        self.assertEqual(self.lab.state()["report"]["statuses"]["drafted"],4)
        with self.assertRaises(ValidationError): self.lab.apply("draft",preview["preview_token"])

    def test_reset_invalidates_preview(self):
        preview=self.lab.preview("draft")
        self.lab.reset()
        with self.assertRaises(ValidationError): self.lab.apply("draft",preview["preview_token"])

    def test_preview_cannot_be_applied_to_different_scenario(self):
        preview=self.lab.preview("draft")
        with self.assertRaises(ValidationError): self.lab.apply("refresh",preview["preview_token"])

    def test_duplicate_replay_retains_record_dates(self):
        before=self.lab.state()["report"]["records"]
        preview=self.lab.preview("replay")
        self.assertEqual(preview["counts"]["duplicates"],12)
        self.lab.apply("replay",preview["preview_token"])
        self.assertEqual(self.lab.state()["report"]["records"],before)

    def test_invalid_packet_never_starts_transaction(self):
        result=self.lab.preview("invalid")
        self.assertFalse(result["accepted"])
        self.assertTrue(result["unchanged"])
        self.assertFalse(any(e["stage"]=="transaction" for e in result["events"]))
        with self.assertRaises(ValidationError): self.lab.apply("invalid",result["preview_token"])

    def test_rollback_trace_records_staged_insert_but_no_surviving_data(self):
        result=self.lab.preview("rollback")
        self.assertFalse(result["accepted"])
        self.assertTrue(result["unchanged"])
        self.assertEqual(result["changes"],[])
        outcomes=[e["outcome"] for e in result["events"]]
        self.assertIn("inserted",outcomes)
        self.assertIn("rolled_back",outcomes)

    def test_apply_does_not_modify_baseline_source(self):
        before=fingerprint(self.db)
        preview=self.lab.preview("verify")
        self.lab.apply("verify",preview["preview_token"])
        self.assertEqual(fingerprint(self.db),before)
        self.assertEqual(self.lab.state()["report"]["statuses"]["verified"],4)

    def test_refresh_resolves_stale_and_keeps_zero(self):
        preview=self.lab.preview("refresh")
        self.lab.apply("refresh",preview["preview_token"])
        report=self.lab.state()["report"]
        self.assertEqual(report["quality"]["stale"],2)
        row=next(r for r in report["records"] if r["external_id"]=="M-04")
        self.assertEqual(row["metric_value"],0)
        self.assertEqual(row["freshness"],"fresh")

    def test_reset_restores_baseline(self):
        preview=self.lab.preview("draft")
        self.lab.apply("draft",preview["preview_token"])
        state=self.lab.reset()
        self.assertEqual(state["report"]["statuses"]["planned"],2)
        self.assertEqual(state["history"],[])

    def test_history_distinguishes_attempts(self):
        self.lab.preview("invalid")
        preview=self.lab.preview("draft")
        self.lab.apply("draft",preview["preview_token"])
        history=self.lab.state()["history"]
        self.assertEqual([r["mode"] for r in history],["apply","preview","preview"])
        self.assertFalse(history[-1]["accepted"])

    def test_unknown_scenario_rejected(self):
        with self.assertRaises(ValidationError): self.lab.preview("real-platform-call")


class PolicyAndLineageTests(unittest.TestCase):
    def test_confidential_item_releases_only_approved_metadata(self):
        result=evaluate_release(RELEASE_CANDIDATES[1])
        self.assertTrue(result["allowed"])
        self.assertEqual(set(result["released"]),{"alias","status","due_date","source_ref","owner"})
        self.assertNotIn("client",result["released"])
        self.assertNotIn("source_text",result["released"])

    def test_exclusion_releases_no_existence_marker(self):
        self.assertEqual(evaluate_release(RELEASE_CANDIDATES[2])["released"],{})

    def test_public_sensitivity_does_not_override_ownership(self):
        result=evaluate_release(RELEASE_CANDIDATES[3])
        self.assertFalse(result["allowed"])
        self.assertEqual(result["released"],{})

    def test_no_source_text_released_by_any_fixture(self):
        for candidate in RELEASE_CANDIDATES:
            self.assertNotIn("source_text",evaluate_release(candidate)["released"])

    def test_destination_identity_controls_attribution(self):
        self.assertEqual(reconcile_destination("A","A"),"matched")
        self.assertEqual(reconcile_destination("A","B"),"unreconciled")
        self.assertEqual(reconcile_destination("A",None),"unreconciled")
        data=portfolio()
        self.assertEqual([o["attributable"] for o in data["observations"]],[True,False,False,False])
        self.assertIsNone(data["observations"][-1]["value"])


if __name__=="__main__": unittest.main()
