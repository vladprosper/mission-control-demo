# What this demonstration does and does not establish

## Real implementation

Python serves local assets and JSON over IPv4 loopback. SQLite transactions enforce atomic imported batches. Story actions validate relationships and revisions before committing in-memory snapshots. Tests inject failed writes and stale or conflicting updates.

## Scripted behavior

Research, source reading, agent actions, editorial decisions, document changes, Notion records, schedules, publication and results are fictional fixtures. No model, external API, SDK, account or credential is used. `mock_notion` and `mock_metricool` are labels for local example records. A scheduled instruction does not run a job; a completed scripted run does not prove complete evidence.

Story state, technical reporting and the preview workbench are distinct stores. A story decision changes only the story snapshot. HTTP workbench changes affect its in-memory copy; the baseline file remains unchanged. All tabs on one server share state and can reset it. Closing the server discards story/workbench changes.

## Data limits

Identity is exact `(source, external_id)`, not semantic matching. Deduplication hashes are not signatures. Latest snapshots and successful import summaries are retained, not a full event history or durable failed-import audit. Statuses are structurally checked source assertions; a newer correction can regress status. Freshness is a fixed demonstration threshold. Unknown metrics stay unknown and unlike units are not summed.

## Deployment limits

This is a local development server. It has no user authentication, role-based authorization, TLS, encryption service, backups, durable scheduler, production monitoring or load testing. Same-origin checks, bounded JSON and parameterized SQL do not establish production readiness. Do not expose it on a network or enter real sensitive data.

## Adapting the example

A real integration would require an independently designed read contract, permissions, credential handling, retries, rate limits, retention rules, external evidence reconciliation, user identity, durable workflow history and deployment review. None of that is implemented behind a hidden setting. The fictional reference diagram is an explanatory model, not evidence of a deployed system or the author's professional results.
