"""One fictional article and one recurring review, recorded as SQLite snapshots."""
import copy
import json
import sqlite3
import threading

ARTICLE_ID = "ARTICLE-07"
ROUTINE_ID = "REVIEW-01"
STEPS = [
    {"title": "An article I can return to.", "label": "Paused draft", "date": "8 September", "time": "0:00–0:25", "action": "open_review", "button": "Open its scheduled review", "say": "I put this article aside with a specific open question. The draft, working argument and next action stay connected."},
    {"title": "The schedule tells me what should happen.", "label": "Scheduled review", "date": "12 September · before the run", "time": "0:25–0:45", "action": "show_run", "button": "Show the sample review run", "say": "This recurring instruction checks new public material against the article’s question. Being scheduled does not mean it has run."},
    {"title": "The review finished. My decision hasn’t.", "label": "New evidence", "date": "12 September · after the run", "time": "0:45–1:15", "action": "open_update", "button": "Review the article update", "say": "The run read three of four sources and found something relevant. One source was inaccessible. The finding is linked to the article, but its implication still needs my review."},
    {"title": "I decide what the evidence changes.", "label": "Your decision", "date": "12 September · editorial review", "time": "1:15–1:45", "action": "record_decision", "button": "Record my decision and revise the draft", "say": "After checking the example, I separate two permissions: negotiating price and changing contractual terms. An agent can record my decision; it does not make that judgment for me."},
    {"title": "The decision and the draft now agree.", "label": "Draft revised", "date": "12 September · ready to resume", "time": "1:45–2:05", "action": "show_results", "button": "Jump to later publication results", "say": "My decision is saved with its source, and draft version 4 reflects it. Agents save the decision and revise the draft; the local importer updates reporting. Now we jump ahead to the fictional published article."},
    {"title": "Results create the next useful question.", "label": "Published results", "date": "30 September · later in the story", "time": "2:05–2:40", "action": "carry_question", "button": "Add this question to the next review", "say": "Views and impressions keep their own definitions and dates. They do not prove subscriber impact. A reader asks how an agent recognizes a clause outside its authority; that is a new research direction."},
    {"title": "The same review now has a better question.", "label": "Next question", "date": "3 October · next scheduled review", "time": "2:40–3:00", "action": "reset", "button": "Restart the three-minute demo", "say": "I can return to the same article and see what changed, why it changed, and what the next review should investigate. One article, one recurring instruction, and a clear place to resume."},
]


def initial_state():
    return {"article": {"id": ARTICLE_ID, "title": "When AI agents negotiate a purchase", "project": "The Sovereign AI Enterprise", "status": "Paused draft", "draft_version": 3, "argument": "A purchasing agent needs limits beyond a budget.", "question": "Does the evidence show agents negotiating terms independently, or only choosing among offers?", "next_action": "Check whether the cited example actually supports the negotiation claim.", "decision_status": "No new evidence reviewed"},
            "routine": {"id": ROUTINE_ID, "name": "Purchasing-agent research review", "instruction": "Check new public material against the article’s open question. Link relevant findings and flag what still needs checking.", "recurrence": "Weekly", "next_run": "12 September · 09:00", "status": "Scheduled", "run_status": "No run shown yet"},
            "run": None, "finding": None, "decision": None, "publication": None, "reader_question": None, "next_question": None, "events": []}


def validate_state(state):
    """Check links and distinct decision/run states, not the truth of evidence."""
    if state["article"]["id"] != ARTICLE_ID or state["routine"]["id"] != ROUTINE_ID:
        raise ValueError("The walkthrough must retain one article and one review identity")
    if state["finding"]:
        if not state["run"] or state["finding"]["run_id"] != state["run"]["id"] or state["finding"]["article_id"] != ARTICLE_ID:
            raise ValueError("Finding must link this article to the observed run")
    if state["run"] and state["run"]["routine_id"] != ROUTINE_ID:
        raise ValueError("The run must belong to the same recurring review")
    if state["decision"] and state["decision"]["actor"] != "You":
        raise ValueError("The editorial decision must be the owner's")
    if state["decision"] and not state["finding"]:
        raise ValueError("Decision needs its finding")
    if state["decision"] and state["decision"]["finding_id"] != state["finding"]["id"]:
        raise ValueError("Decision must retain the finding that informed it")
    if state["article"]["draft_version"] > 3 and not state["decision"]:
        raise ValueError("Draft revision requires the owner's recorded decision")
    if state["publication"]:
        if not state["decision"] or state["publication"]["manuscript_version"] != state["article"]["draft_version"]:
            raise ValueError("Publication observations must refer to the reviewed manuscript")
        for item in state["publication"]["metrics"]:
            if not all(item.get(k) for k in ("destination_id", "definition", "collected_at", "period")):
                raise ValueError("A measurement needs a destination, definition, date and period")
    if state["next_question"] and (not state["reader_question"] or state["next_question"]["routine_id"] != ROUTINE_ID or state["next_question"]["article_id"] != ARTICLE_ID):
        raise ValueError("Next question must return to the same recurring review")


class Story:
    def __init__(self):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE snapshots (revision INTEGER PRIMARY KEY, step INTEGER NOT NULL, state TEXT NOT NULL)")
        self.db.execute("INSERT INTO snapshots VALUES (0,0,?)", (json.dumps(initial_state()),))
        self.db.commit()

    def state(self):
        with self.lock:
            row = self.db.execute("SELECT * FROM snapshots ORDER BY revision DESC LIMIT 1").fetchone()
            value = json.loads(row["state"])
            return {"fictional": True, "revision": row["revision"], "step": row["step"], "guide": STEPS[row["step"]],
                    "steps": [{"label": s["label"]} for s in STEPS], "state": value,
                    "boundary": "One fictional article and review. No real agent, schedule, source update or publication is executed."}

    def advance(self, action, expected_revision):
        with self.lock:
            current = self.state()
            if type(expected_revision) is not int or expected_revision != current["revision"]:
                raise ValueError("This view is out of date. Reload before continuing.")
            if action != current["guide"]["action"] and action != "reset":
                raise ValueError("Follow the next step in the article story")
            step = 0 if action == "reset" else current["step"] + 1
            value = initial_state() if action == "reset" else copy.deepcopy(current["state"])
            if action == "show_run":
                value["run"] = {"id": "RUN-12SEP", "routine_id": ROUTINE_ID, "date": "12 September · 09:00", "status": "Completed with a source gap", "sources_read": 3, "sources_total": 4,
                    "sources": [{"name": "Public purchasing-agent trial report", "status": "Read", "date": "12 September", "detail": "A relevant finding was linked to the article."}, {"name": "Public trial methodology", "status": "Read", "date": "12 September", "detail": "Background and scope recorded."}, {"name": "Public implementation notes", "status": "Read", "date": "12 September", "detail": "Supporting context recorded."}, {"name": "Public supplementary page", "status": "Unavailable", "date": "Previous observation: 5 September", "detail": "Access failed; its earlier observation date stays visible."}]}
                value["finding"] = {"id": "FINDING-12SEP", "article_id": ARTICLE_ID, "run_id": "RUN-12SEP", "summary": "The trial agent negotiated price, but changes to cancellation terms needed human approval.", "proposal": "Treat permission to negotiate price separately from permission to change contractual terms.", "assessment": "Your review pending", "source": "Public purchasing-agent trial report · fictional example"}
                value["routine"]["run_status"] = value["run"]["status"]
                value["routine"]["next_run"] = "19 September · 09:00"
                value["article"]["decision_status"] = "Your review pending"
                value["events"].append({"actor": "Review agent (simulated)", "text": "Linked the finding to the article's research record. The argument was not changed."})
            elif action == "open_update":
                value["events"].append({"actor": "You", "text": "Opened the source-linked finding and its proposed implication."})
            elif action == "record_decision":
                decision = "Permission to negotiate price and permission to change contractual terms are separate. An agent may have the first while needing human approval for the second."
                value["decision"] = {"id": "DECISION-12SEP", "actor": "You", "finding_id": value["finding"]["id"], "text": decision, "date": "12 September", "record": "Research record · mock Notion"}
                value["finding"]["assessment"] = "Reviewed by you"
                value["article"].update(argument=decision, draft_version=4, status="Draft ready for review", decision_status="Decision recorded", next_action="Review the revised draft before publication.")
                value["events"].extend([{"actor": "You", "text": "Accepted the distinction after reviewing the illustrative evidence."}, {"actor": "Agent (simulated)", "text": "Saved your decision and source reference in the mock research record; revised manuscript v3 to v4."}, {"actor": "Local reporting program", "text": "Validated the linked story state and recorded the new reporting snapshot in SQLite."}])
            elif action == "show_results":
                value["article"]["status"] = "Published · illustrative later state"
                value["publication"] = {"date": "20 September", "manuscript_version": 4, "metrics": [
                    {"platform": "Substack", "destination_id": "SUB-ARTICLE-07", "destination": "Individual article · matched to manuscript v4", "value": 1840, "unit": "views", "definition": "Platform-reported article views; not a subscriber count.", "collected_at": "30 September", "period": "20–30 September"},
                    {"platform": "LinkedIn", "destination_id": "LI-POST-07", "destination": "Related platform post · separate destination identity", "value": 4320, "unit": "impressions", "definition": "Platform-reported displays of the related post; distinct from article views.", "collected_at": "30 September", "period": "20–30 September"}], "subscriber_impact": None}
                value["reader_question"] = {"id": "QUESTION-30SEP", "article_id": ARTICLE_ID, "text": "How would the agent recognize a cancellation clause that falls outside its authority?", "proposed_next_action": "Examine how purchasing agents detect terms that need human approval and hand the decision back.", "status": "Your assessment pending"}
                value["events"].append({"actor": "Illustrative timeline", "text": "Jumped to the same article's later publication observations; nothing was published by this demo."})
            elif action == "carry_question":
                value["reader_question"]["status"] = "Accepted as the next research question"
                question = value["reader_question"]["proposed_next_action"]
                value["next_question"] = {"article_id": ARTICLE_ID, "routine_id": ROUTINE_ID, "text": question, "status": "Queued for research; answer not established"}
                value["routine"].update(instruction=question, next_run="3 October · 09:00")
                value["article"].update(next_action=question, question=value["reader_question"]["text"])
                value["events"].append({"actor": "You + simulated recordkeeping", "text": "Carried the reader question into the existing recurring review. No new agent or real automation was created."})
            validate_state(value)
            with self.db:
                self.db.execute("INSERT INTO snapshots VALUES (?,?,?)", (current["revision"] + 1, step, json.dumps(value)))
            return self.state()

    def close(self):
        with self.lock:
            self.db.close()
