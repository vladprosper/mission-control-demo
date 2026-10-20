# Return to the same article

The main dashboard has three contextual actions, all tied to fictional article `ARTICLE-07`, “When AI agents negotiate a purchase”:

- **Open manuscript** opens a local fictional manuscript excerpt at the current story version. It changes from v3 to v4 only after the owner decision.
- **Open Notion record** opens the local mock research record, including the same article, version, finding, decision, open question and next action.
- **Continue conversation** opens a local handoff containing the current article context. It explicitly reports that the existing article-conversation link is not configured. It does not create, send to or pretend to resume a live AI chat.

The destinations are rendered by `openArticleTarget` in `static/story.js` using the current validated story state. No external URL is invented and no real manuscript, Notion page or private conversation is inspected or opened.

## Connect actual work later

The owner must supply the corresponding manuscript location, Notion record URL and **existing conversation URL for that article**. Verify each destination's identity and access before replacing the local demo target. The documentation/inventory conversation used to inform this demo is not a substitute for the article's own conversation.

There is no URL configuration or live connector hidden behind the demo. Wiring and checking actual destinations remains configuration work after those locations are supplied. Opening a fresh blank chat does not preserve the existing conversation history. A saved handoff can help transfer context, but is not proof that history, files, permissions or model memory were retained.
