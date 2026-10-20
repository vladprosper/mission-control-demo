# Three minutes · one article, one recurring review

Start `python3 scripts/review.py`. Open its printed loopback URL, without a path. If the old dashboard is already open, reload it. Choose **Restart story** before presenting. All data, source reports, agent actions, dates and results are fictional.

Keep the article and recurring review on the left in view. Use the single green button to advance. There are **six clicks**, followed by an optional restart. Presenter notes are available under every scene.

| Time | Show / click | Say |
| --- | --- | --- |
| 0:00–0:25 | Start: paused article, draft v3. Click **Open its scheduled review**. | “I paused an article about purchasing agents. The draft has an argument, an unresolved question and a specific next action. I can resume without reconstructing the conversation.” |
| 0:25–0:45 | The weekly instruction. Click **Show the sample review run**. | “This recurring instruction checks new public material against that question. A schedule tells me what should happen; it does not prove a run happened.” |
| 0:45–1:15 | Three of four sources read; one gap. Click **Review the article update**. | “The review found a trial where an agent negotiated price but needed human approval for cancellation terms. One source was unavailable and retains its old observation date. The finding needs my judgment; the draft is still unchanged.” |
| 1:15–1:45 | Evidence beside the proposed editorial distinction. Click **Record my decision and revise the draft**. | “I decide that permission to negotiate price and permission to change contractual terms must be separate. The agent can record my decision and revise the draft. It does not make that editorial judgment for me.” |
| 1:45–2:05 | Decision saved, manuscript v4. Click **Jump to later publication results**. | “The decision, source and revised draft now agree. The local reporting view reflects that change. Now we jump to the fictional article’s later publication results; this demo publishes nothing.” |
| 2:05–2:40 | Separate Substack views and LinkedIn impressions; reader question. Click **Add this question to the next review**. | “These measurements have different meanings, destinations and dates. They do not establish subscriber impact. A reader asks how the agent recognizes a clause outside its authority. That suggests the next useful research question.” |
| 2:40–3:00 | The same review carries the new question. No further click required. | “I accept the question into the same recurring review. I can see what changed, why the argument changed, and what to investigate next. One article, one recurring instruction, and a clear place to resume.” |

## Visual narration

The [narrated GIF](https://github.com/vladprosper/vladprosper/blob/main/mission-control-walkthrough.gif) follows these seven captions and the architecture explanation. It lasts 3:35 including that optional explanation. The interactive source demo runs without downloading the GIF or its capture assets.

## Optional architecture explanation

After the story, select **How it works**. A diagram explains:

1. The weekly instruction starts a review agent.
2. The agent links findings; the owner assesses them.
3. An agent writes the owner's decision to the research record and revises manuscript wording.
4. The local Python importer reads permitted reporting records into SQLite.
5. Mission Control presents the linked state, gaps and next action.

The importer does not write back to Notion. The in-app diagram clearly separates the reference workflow from implemented code. The optional technical lab at `/technical/` retains the atomic import, deduplication, freshness, missing-value and status demonstrations. It is outside the three-minute presentation.

## State and boundaries

This is a scripted interactive scenario, not a live assistant or scheduler. Buttons advance validated SQLite story snapshots. Agent work, Notion updates, document edits, scheduled runs and publication observations are simulated. No model or external platform is called. The next research answer remains unknown.

All tabs on this local server share the current story. **Restart story** returns it to the paused draft; restarting the server discards story snapshots. The separate synthetic reporting database is unchanged by story actions. The timeline dates are illustrative labels, not scheduled jobs on this Mac.
