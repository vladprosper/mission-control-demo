# Developer guide

## Read the code in this order

1. `adapters.py` loads bounded local JSON/CSV examples.
2. `store.py` defines validation, normalization, source identity, transactions and reporting.
3. `story.py` defines one linked article/review and the allowed six transitions.
4. `workbench.py` copies the baseline and controls preview/apply/reset.
5. `server.py` serves a fixed asset allowlist and small JSON API.
6. `static/story.js` renders the narrative; `app.js` and `experience.js` render the technical lab.

`portfolio.py` contains supplemental fictional technical-lab context. `scripts/review.py` seeds a dedicated local fixture database and starts an interactive foreground server. `python3 -m mission_control` provides import/report commands and a read-only server. There are no third-party runtime dependencies or build steps.

## Storage boundaries

| Store | Lifetime | Changes |
| --- | --- | --- |
| CLI database file | Persists until owner removes it | Explicit CLI imports |
| Review baseline `output/owner-review.sqlite3` | Persists locally | Launcher seeds fixtures; HTTP reads it |
| Story SQLite connection | Server process | Validated snapshots, revision checks |
| Workbench SQLite copy | Server process | Preview tokens, applied synthetic scenarios and reset |

Do not substitute a real database for any of these. Output files are ignored by Git.

## HTTP interface

All routes are local. Start with `python3 scripts/review.py`; use the printed host and port.

| Method / route | Purpose |
| --- | --- |
| `GET /` | Article story |
| `GET /technical/` | Reporting and import workbench |
| `GET /health` | Application/version/fictional marker |
| `GET /api/story` | Story state, revision, guide and interactive flag |
| `GET /api/report` | Baseline report |
| `GET /api/context` | Supplemental fictional lab context |
| `GET /api/workbench` | Interactive sandbox state |
| `POST /api/story/advance` | `{ "action": "...", "revision": 0 }`; action comes from the current guide, or `reset` |
| `POST /api/workbench/preview` | `{ "scenario": "draft" }`; also supports other predefined scenarios in `workbench.py` |
| `POST /api/workbench/apply` | Same scenario plus current `preview_token` |
| `POST /api/workbench/reset` | Empty JSON object |

POST requires an exact matching local Host/Origin, `application/json`, a 1–4096-byte body and the precise expected keys. A mismatched origin returns 403, wrong content type 415, malformed fields 400 and state/validation conflicts 409. Unknown action routes return 404. The lower-level CLI `serve` disables all writes and returns 501 for POST. This is a demo interface, not a stable external API.

## Extending fixtures

Keep examples fictional and use `https://example.invalid/evidence/` for invented evidence. Follow [DATA_CONTRACT.md](DATA_CONTRACT.md). Add a test for the behavioral guarantee you change: rollback after a late-row conflict, update precedence, null versus zero, source freshness or relationship validation. Avoid tests that merely reproduce UI text.

For story changes, preserve the distinction between schedule, observed run, incomplete finding, owner decision and revised manuscript. Validate cross-record links before committing and maintain revision rejection for concurrent browser tabs. Do not turn “verified” into a claim about a real platform without independent evidence retrieval.

## Run checks

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/smoke_test.py
```

The smoke script chooses temporary paths and OS-assigned loopback ports. Tests use only the synthetic package. No production database, browser account or network service is required.

Manually review the six green-button transitions, **How it works**, manuscript/research/conversation targets, and the technical lab's rejected preview and valid apply. Automated HTTP checks do not replace browser layout or accessibility review. No CI workflow is bundled; these are local checks.

## Release contents

Only source, synthetic fixtures, tests and reader-facing documentation are included. Private review logs, machine-specific session metadata, generated databases, portrait assets and GIF capture utilities are excluded. The completed GIF is linked from the public profile. The source export uses the foreground launcher so its lifetime is explicit and no background process management is required.
