"""The narrative must keep the article, run, owner decision and schedule distinct."""
import copy
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor

from mission_control.story import ARTICLE_ID, ROUTINE_ID, Story, initial_state, validate_state


class StoryTests(unittest.TestCase):
    def setUp(self):
        self.story = Story()
        self.addCleanup(self.story.close)

    def next(self):
        view = self.story.state()
        return self.story.advance(view["guide"]["action"], view["revision"])

    def to_step(self, target):
        while self.story.state()["step"] < target:
            self.next()
        return self.story.state()

    def test_one_article_and_review_through_all_six_clicks(self):
        for step in range(7):
            view = self.story.state()
            self.assertEqual(view["step"], step)
            self.assertEqual(view["state"]["article"]["id"], ARTICLE_ID)
            self.assertEqual(view["state"]["routine"]["id"], ROUTINE_ID)
            self.assertTrue(view["fictional"])
            validate_state(view["state"])
            if step < 6:
                self.next()

    def test_scheduled_instruction_is_not_a_run(self):
        state = self.next()["state"]
        self.assertEqual(state["routine"]["status"], "Scheduled")
        self.assertIsNone(state["run"])
        self.assertIsNone(state["decision"])
        self.assertEqual(state["article"]["draft_version"], 3)

    def test_completed_run_preserves_gap_and_requires_owner_review(self):
        state = self.to_step(2)["state"]
        self.assertEqual(state["run"]["sources_read"], 3)
        self.assertEqual(state["run"]["sources_total"], 4)
        self.assertIn("5 September", state["run"]["sources"][-1]["date"])
        self.assertEqual(state["run"]["sources"][-1]["status"], "Unavailable")
        self.assertEqual(state["article"]["argument"], initial_state()["article"]["argument"])
        self.assertEqual(state["article"]["draft_version"], 3)
        self.assertEqual(state["finding"]["assessment"], "Your review pending")
        self.assertIsNone(state["decision"])

    def test_opening_finding_does_not_accept_it(self):
        state = self.to_step(3)["state"]
        self.assertIsNone(state["decision"])
        self.assertEqual(state["article"]["draft_version"], 3)

    def test_owner_decision_links_evidence_and_revises_draft(self):
        state = self.to_step(4)["state"]
        self.assertEqual(state["decision"]["actor"], "You")
        self.assertEqual(state["decision"]["finding_id"], state["finding"]["id"])
        self.assertEqual(state["article"]["draft_version"], 4)
        self.assertEqual(state["article"]["argument"], state["decision"]["text"])
        self.assertIsNone(state["publication"])

    def test_later_results_have_separate_definitions_and_unknown_attribution(self):
        state = self.to_step(5)["state"]
        publication = state["publication"]
        self.assertEqual(publication["manuscript_version"], 4)
        self.assertIsNone(publication["subscriber_impact"])
        first, second = publication["metrics"]
        self.assertEqual((first["value"], second["value"]), (1840, 4320))
        self.assertEqual((first["unit"], second["unit"]), ("views", "impressions"))
        self.assertNotEqual(first["destination_id"], second["destination_id"])
        for metric in publication["metrics"]:
            self.assertEqual(metric["collected_at"], "30 September")
            self.assertEqual(metric["period"], "20–30 September")
            self.assertTrue(metric["definition"])
        self.assertEqual(state["reader_question"]["article_id"], ARTICLE_ID)

    def test_reader_question_returns_to_same_schedule_with_answer_unknown(self):
        state = self.to_step(6)["state"]
        self.assertEqual(state["next_question"]["routine_id"], ROUTINE_ID)
        self.assertEqual(state["next_question"]["article_id"], ARTICLE_ID)
        self.assertEqual(state["routine"]["instruction"], state["reader_question"]["proposed_next_action"])
        self.assertIn("answer not established", state["next_question"]["status"])

    def test_skipped_steps_and_stale_revisions_do_not_change_state(self):
        before = self.story.state()
        for action, revision in [("record_decision", 0), ("open_review", 1), ("open_review", True), ("open_review", "0")]:
            with self.assertRaises(ValueError):
                self.story.advance(action, revision)
            self.assertEqual(self.story.state(), before)
        self.next()
        with self.assertRaises(ValueError):
            self.story.advance("open_review", 0)
        self.assertEqual(self.story.state()["revision"], 1)

    def test_two_tabs_cannot_apply_the_same_revision_twice(self):
        def apply():
            try:
                self.story.advance("open_review", 0)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: apply(), range(2)))
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(self.story.state()["revision"], 1)

    def test_reset_restores_initial_state_without_reusing_revision(self):
        self.to_step(6)
        view = self.next()
        self.assertEqual(view["step"], 0)
        self.assertEqual(view["revision"], 7)
        self.assertEqual(view["state"], initial_state())

    def test_failed_snapshot_insert_is_atomic(self):
        before = self.story.state()
        self.story.db.execute("CREATE TRIGGER reject_write BEFORE INSERT ON snapshots BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.next()
        self.assertEqual(self.story.state(), before)
        self.assertEqual(self.story.db.execute("SELECT count(*) FROM snapshots").fetchone()[0], 1)

    def test_validator_rejects_broken_provenance_and_missing_measurement_dates(self):
        valid = self.to_step(6)["state"]
        mutations = [
            lambda s: s["run"].update(routine_id="OTHER"),
            lambda s: s["finding"].update(article_id="OTHER"),
            lambda s: s["finding"].update(run_id="OTHER"),
            lambda s: s["decision"].update(actor="Agent"),
            lambda s: s["decision"].update(finding_id="OTHER"),
            lambda s: s.update(decision=None),
            lambda s: s["publication"].update(manuscript_version=3),
            lambda s: s["publication"]["metrics"][0].update(collected_at=None),
            lambda s: s["next_question"].update(routine_id="OTHER"),
            lambda s: s["next_question"].update(article_id="OTHER"),
        ]
        for mutate in mutations:
            state = copy.deepcopy(valid)
            mutate(state)
            with self.assertRaises(ValueError):
                validate_state(state)


if __name__ == "__main__":
    unittest.main()
