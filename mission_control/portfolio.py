"""Fictional fixtures illustrating the owner-supplied architecture description."""
import copy

RELEASE_CANDIDATES = [
    {"id": "personal-public", "label": "Personal / public research note", "owner": "personal", "agent_domain": "personal", "sensitivity": "public", "release": "metadata", "fields": {"alias": "Atlas Review / research register", "status": "drafted", "due_date": "2026-10-23", "source_ref": "PERSONAL-21", "source_text": "Invented manuscript text: this field is not reporting metadata."}},
    {"id": "work-restricted", "label": "Work / restricted brief", "owner": "work", "agent_domain": "work", "sensitivity": "confidential", "release": "neutral", "fields": {"alias": "Work brief 07", "status": "planned", "due_date": "2026-10-24", "source_ref": "WORK-07", "title": "Fictional confidential source title", "client": "Invented Client A", "source_text": "Invented restricted source content; never copied into reporting."}},
    {"id": "personal-excluded", "label": "Personal / excluded from reporting", "owner": "personal", "agent_domain": "personal", "sensitivity": "confidential", "release": "exclude", "fields": {"alias": "Do not release even a neutral alias", "status": "planned", "due_date": "2026-10-25", "source_text": "Entirely fictional excluded material."}},
    {"id": "wrong-domain", "label": "Work record / wrong agent domain", "owner": "work", "agent_domain": "personal", "sensitivity": "public", "release": "metadata", "fields": {"alias": "Fictional public work item", "status": "drafted", "due_date": "2026-10-23"}},
]


def evaluate_release(candidate):
    candidate = copy.deepcopy(candidate)
    if candidate["agent_domain"] != candidate["owner"]:
        allowed, reason = False, "Agent domain does not match the owning domain. Public sensitivity does not grant cross-domain processing permission."
    elif candidate["release"] == "exclude":
        allowed, reason = False, "Destination policy excludes this item entirely. No alias, existence marker, or metadata is released."
    else:
        allowed, reason = True, "Explicit fixture policy permits only alias, status, due date and neutral source reference. Source text and other fields stay out."
    packet = {key: candidate["fields"][key] for key in ("alias", "status", "due_date", "source_ref") if key in candidate["fields"]} if allowed else {}
    if allowed:
        packet["owner"] = candidate["owner"]
    return {"allowed": allowed, "reason": reason, "released": packet,
            "withheld_fields": sorted(set(candidate["fields"]) - set(packet)),
            "boundary": "An executable allowlist over fictional fixtures; not authentication, encryption, or a production policy engine."}


def portfolio():
    data = {"fictional": True, "reference": {"title": "The Architecture Behind My AI Assisted Work", "basis": "Owner-supplied architecture description; sections on ownership, agent access, evidence, refresh and recovery. Reference design is distinguished from demo implementation."},
            "release_candidates": [dict(c, result=evaluate_release(c)) for c in RELEASE_CANDIDATES],
            "article": {"id": "ARTICLE-21", "project": "Atlas Review · fictional publication", "title": "Why teams need a research register", "owner": "personal", "decision": "Focus the argument on preserving consequential research decisions. Next: inspect the comments for follow-up questions.", "manuscript": "MANUSCRIPT-21 · version 3", "decision_ref": "MOCK-NOTION-21", "next_action": "Reconcile the LinkedIn destination before attributing its metrics to this article."},
            "destinations": [
                {"id": "DEST-SUB-21", "platform": "Substack", "url": "https://example.invalid/atlas/research-register", "expected_article": "ARTICLE-21", "resolved_article": "ARTICLE-21", "relationship": "matched", "note": "Fictional verification fixture identifies this individual article, rather than the publication homepage."},
                {"id": "DEST-LI-21", "platform": "LinkedIn", "url": "https://example.invalid/linkedin/home", "expected_article": "ARTICLE-21", "resolved_article": None, "relationship": "unreconciled", "note": "The fixture resolves to a homepage. The article relationship is not established; the measurement must not be attributed to ARTICLE-21."}],
            "observations": [
                {"metric": "Article views", "value": 1840, "unit": "Substack views", "definition": "Platform-reported views for this fictional article; not unique readers or subscribers.", "source": "mock_substack", "collected_at": "2026-09-30T12:00:00Z", "period": "16–30 Sep 2026", "scope": "DEST-SUB-21", "state": "dated observation", "attributable": True},
                {"metric": "Post impressions", "value": 920, "unit": "LinkedIn impressions", "definition": "Fictional platform impression count; destination relationship remains unresolved.", "source": "mock_linkedin", "collected_at": "2026-10-05T12:00:00Z", "period": "1–5 Oct 2026", "scope": "DEST-LI-21", "state": "unreconciled destination", "attributable": False},
                {"metric": "Publication subscribers", "value": 12, "unit": "net subscribers", "definition": "Publication-level change over the period. No causal attribution to one article is established.", "source": "mock_substack", "collected_at": "2026-09-30T12:00:00Z", "period": "1–30 Sep 2026", "scope": "publication", "state": "publication only", "attributable": False},
                {"metric": "Comment count", "value": None, "unit": "comments", "definition": "Collection unavailable. Unknown is retained rather than replaced with zero.", "source": "mock_substack", "collected_at": None, "period": "Not collected", "scope": "DEST-SUB-21", "state": "source inaccessible", "attributable": False}],
            "refresh_sources": [
                {"source": "mock_notion", "state": "collected", "last_observation": "2026-10-19T09:00:00Z", "attempted_at": "2026-10-19T11:00:00Z", "note": "Dated packet collected; schema and identity still require validation."},
                {"source": "mock_substack", "state": "access unavailable", "last_observation": "2026-09-30T12:00:00Z", "attempted_at": "2026-10-19T11:00:00Z", "note": "Failed attempt retains the previous observation date and measurements."},
                {"source": "mock_linkedin", "state": "identity unresolved", "last_observation": "2026-10-05T12:00:00Z", "attempted_at": "2026-10-19T11:00:00Z", "note": "A plausible URL is not enough; reconcile the destination before article attribution."}],
            "routine": {"title": "Weekly operations review · fictional routine", "instruction": "Review next actions, source freshness and outstanding approvals.", "scheduled_for": "2026-10-20T09:00:00Z", "observed_run": "2026-10-12T09:00:00Z", "checklist": "3 of 4 checks recorded", "approval": "Pending evidence review", "completion": "Not verified", "note": "Schedule, observed run, checklist, approval and verified completion are distinct records. This demo does not execute a routine."}}
    for destination in data["destinations"]:
        destination["relationship"] = reconcile_destination(destination["expected_article"], destination["resolved_article"])
    destinations = {d["id"]: d for d in data["destinations"]}
    for observation in data["observations"]:
        destination = destinations.get(observation["scope"])
        observation["attributable"] = bool(destination and destination["relationship"] == "matched" and observation["collected_at"] and observation["value"] is not None)
    return data


def reconcile_destination(expected_article, resolved_article):
    return "matched" if resolved_article is not None and resolved_article == expected_article else "unreconciled"
